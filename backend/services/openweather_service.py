import os
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from models import WeatherData, WeatherForecastDay, RiskLevel, WeatherSource
import asyncio
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

class OpenWeatherService:
    def __init__(self):
        self.api_key = os.environ.get('OPENWEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.onecall_url = "https://api.openweathermap.org/data/3.0/onecall"
        self.api_blocked = False  # Track API status
        
    def generate_fallback_weather_data(self, lat: float, lon: float) -> Dict:
        """Génère des données météo de fallback réalistes pour la Guadeloupe"""
        import random
        
        # Données météo tropicales réalistes pour la Guadeloupe
        base_temp = 26 + random.uniform(-2, 4)  # 24-30°C
        humidity = 75 + random.uniform(-10, 15)  # 65-90%
        pressure = 1013 + random.uniform(-8, 8)  # 1005-1021 hPa
        wind_speed = 15 + random.uniform(-5, 15)  # 10-30 km/h
        precipitation = random.uniform(0, 2)  # 0-2 mm/h normal
        
        # Ajustements selon localisation (côte vs intérieur)
        if lat < 16.15:  # Basse-Terre (plus montagneux)
            precipitation += random.uniform(0, 1)
            humidity += 5
            wind_speed -= 2
        
        current_time = datetime.now()
        
        return {
            'current': {
                'dt': int(current_time.timestamp()),
                'temperature': base_temp,
                'temperature_max': base_temp + random.uniform(1, 3),
                'temperature_min': base_temp - random.uniform(1, 2),
                'humidity': max(50, min(95, humidity)),
                'pressure': pressure,
                'wind_speed': max(5, wind_speed),
                'wind_deg': random.randint(60, 120),  # Vents alizés typiques
                'precipitation_probability': min(100, precipitation * 20),
                'weather': [{
                    'main': 'Clouds' if random.random() > 0.3 else 'Clear',
                    'description': 'Partiellement nuageux' if random.random() > 0.3 else 'Ensoleillé'
                }],
                'rain': {'1h': precipitation} if precipitation > 0.1 else {},
                'source': 'fallback'
            },
            'hourly': [
                {
                    'dt': int((current_time + timedelta(hours=h)).timestamp()),
                    'temp': base_temp + random.uniform(-2, 2),
                    'humidity': max(50, min(95, humidity + random.uniform(-10, 10))),
                    'pressure': pressure + random.uniform(-3, 3),
                    'wind_speed': max(5, wind_speed + random.uniform(-5, 5)),
                    'pop': min(100, precipitation * 20 + random.uniform(-10, 10)),
                    'rain': {'1h': max(0, precipitation + random.uniform(-0.5, 0.5))} if random.random() > 0.7 else {}
                }
                for h in range(24)
            ],
            'daily': [
                {
                    'dt': int((current_time + timedelta(days=d)).timestamp()),
                    'temp': {
                        'max': base_temp + random.uniform(2, 4),
                        'min': base_temp - random.uniform(1, 2)
                    },
                    'humidity': max(50, min(95, humidity + random.uniform(-5, 5))),
                    'pressure': pressure + random.uniform(-2, 2),
                    'wind_speed': max(5, wind_speed + random.uniform(-3, 3)),
                    'pop': min(100, precipitation * 15 + random.uniform(-5, 5)),
                    'rain': max(0, precipitation * 24 + random.uniform(-5, 5))
                }
                for d in range(7)
            ],
            'fallback': True,
            'location': f"Guadeloupe ({lat:.2f}, {lon:.2f})"
        }
        
    async def get_current_and_forecast(self, lat: float, lon: float, commune: str = None) -> Optional[Dict]:
        """Récupère données actuelles et prévisions - utilise le système de quotas"""
        if not self.api_key:
            logger.error("OpenWeatherMap API key not configured")
            return self.generate_fallback_weather_data(lat, lon)
        
        # D'abord, vérifier le cache intelligent
        if commune:
            from services.api_quota_manager import quota_manager
            cached_data = await quota_manager.get_cached_weather_data(commune)
            if cached_data:
                return cached_data.get('weather_data')
        
        # Vérifier le quota avant la requête API
        if commune:
            check = await quota_manager.can_make_request(commune)
            if not check['allowed']:
                logger.warning(f"API quota exceeded for {commune}: {check['reason']}")
                # Essayer le cache même expiré avant fallback
                if commune:
                    expired_cache = quota_manager.weather_cache.find_one(
                        {'commune': commune},
                        sort=[('timestamp', -1)]
                    )
                    if expired_cache:
                        logger.info(f"Using expired cache for {commune}")
                        expired_cache.pop('_id', None)
                        return expired_cache.get('weather_data')
                
                # Sinon, utiliser le fallback
                return self.generate_fallback_weather_data(lat, lon)
            
        try:
            async with httpx.AsyncClient() as client:
                # Utilise One Call API 3.0 pour données complètes
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'units': 'metric',
                    'lang': 'fr',
                    'exclude': 'minutely,alerts'  # Exclut données non nécessaires
                }
                
                response = await client.get(self.onecall_url, params=params, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully fetched OpenWeatherMap data for {lat}, {lon}")
                    return data
                else:
                    logger.error(f"OpenWeatherMap API error {response.status_code}: {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("OpenWeatherMap API timeout")
            return None
        except Exception as e:
            logger.error(f"Error fetching OpenWeatherMap data: {e}")
            return None
    
    async def get_severe_weather_data(self, lat: float, lon: float) -> Optional[Dict]:
        """Récupère données météo extrême pour IA cyclonique avec fallback"""
        data = await self.get_current_and_forecast(lat, lon)
        
        # Si l'API échoue, utiliser les données de fallback
        if not data:
            logger.warning(f"Using fallback weather data for IA at {lat}, {lon}")
            data = self.generate_fallback_weather_data(lat, lon)
            
        try:
            current = data.get('current', {})
            hourly = data.get('hourly', [])
            
            # Adapter les clés selon si c'est fallback ou API réelle
            is_fallback = data.get('fallback', False)
            
            if is_fallback:
                # Données de fallback (structure différente)
                current_severe = {
                    'wind_speed': current.get('wind_speed', 15),  # Déjà en km/h
                    'wind_gust': current.get('wind_speed', 15) * 1.3,
                    'pressure': current.get('pressure', 1013),
                    'temperature': current.get('temperature', 26),
                    'humidity': current.get('humidity', 75),
                    'precipitation': current.get('rain', {}).get('1h', 0),
                    'visibility': 10,  # km
                    'uv_index': 6,
                    'weather_id': 803,  # Partiellement nuageux
                    'timestamp': datetime.fromtimestamp(current.get('dt', datetime.now().timestamp())),
                    'source': 'fallback'
                }
            else:
                # Données API réelles (structure originale)
                current_severe = {
                    'wind_speed': current.get('wind_speed', 0) * 3.6,  # m/s vers km/h
                    'wind_gust': current.get('wind_gust', 0) * 3.6 if 'wind_gust' in current else current.get('wind_speed', 0) * 3.6 * 1.3,
                    'pressure': current.get('pressure', 1013),
                    'temperature': current.get('temp', 25),
                    'humidity': current.get('humidity', 75),
                    'precipitation': self._get_precipitation_rate(current),
                    'visibility': current.get('visibility', 10000) / 1000,  # m vers km
                    'uv_index': current.get('uvi', 5),
                    'weather_id': current.get('weather', [{}])[0].get('id', 800),
                    'timestamp': datetime.fromtimestamp(current.get('dt', datetime.now().timestamp())),
                    'source': 'api'
                }
            
            # Prévisions horaires pour timeline
            timeline_predictions = {}
            for i, hour_data in enumerate(hourly[:24]):  # Prochaines 24h
                if i % 6 == 0:  # Tous les 6h
                    time_key = f"H+{i}"
                    
                    if is_fallback:
                        timeline_predictions[time_key] = {
                            'wind_speed': hour_data.get('wind_speed', 15),
                            'pressure': hour_data.get('pressure', 1013),
                            'temperature': hour_data.get('temp', 26),
                            'humidity': hour_data.get('humidity', 75),
                            'precipitation': hour_data.get('rain', {}).get('1h', 0)
                        }
                    else:
                        timeline_predictions[time_key] = {
                            'wind_speed': hour_data.get('wind_speed', 0) * 3.6,
                            'pressure': hour_data.get('pressure', 1013),
                            'temperature': hour_data.get('temp', 25),
                            'humidity': hour_data.get('humidity', 75),
                            'precipitation': self._get_precipitation_rate(hour_data)
                        }
            
            return {
                'current': current_severe,
                'timeline': timeline_predictions,
                'source': 'fallback' if is_fallback else 'openweathermap',
                'last_update': datetime.now(),
                'fallback_mode': is_fallback
            }
            
        except Exception as e:
            logger.error(f"Error processing severe weather data: {e}")
            return None
    
    def _get_precipitation_rate(self, weather_data: Dict) -> float:
        """Calcule le taux de précipitation en mm/h"""
        rain = weather_data.get('rain', {})
        snow = weather_data.get('snow', {})
        
        rain_1h = rain.get('1h', 0) if rain else 0
        snow_1h = snow.get('1h', 0) if snow else 0
        
        return rain_1h + snow_1h
    
    async def get_hurricane_indicators(self, lat: float, lon: float) -> Dict:
        """Analyse les indicateurs cycloniques spécifiques"""
        data = await self.get_current_and_forecast(lat, lon)
        
        if not data:
            return {'hurricane_risk': 'unknown', 'indicators': []}
        
        current = data.get('current', {})
        daily = data.get('daily', [])
        
        indicators = []
        risk_score = 0
        
        # Analyse pression atmosphérique
        pressure = current.get('pressure', 1013)
        if pressure < 980:
            indicators.append(f"Pression très basse: {pressure} hPa")
            risk_score += 30
        elif pressure < 1000:
            indicators.append(f"Pression basse: {pressure} hPa")
            risk_score += 15
        
        # Analyse vitesse du vent
        wind_speed = current.get('wind_speed', 0) * 3.6
        if wind_speed > 118:  # Force ouragan
            indicators.append(f"Vents d'ouragan: {wind_speed:.0f} km/h")
            risk_score += 40
        elif wind_speed > 88:  # Tempête tropicale
            indicators.append(f"Vents de tempête: {wind_speed:.0f} km/h")
            risk_score += 25
        elif wind_speed > 62:
            indicators.append(f"Vents forts: {wind_speed:.0f} km/h")
            risk_score += 10
        
        # Analyse température et humidité (conditions favorables cyclone)
        temp = current.get('temp', 25)
        humidity = current.get('humidity', 75)
        
        if temp > 26 and humidity > 80:
            indicators.append("Conditions thermiques favorables au développement cyclonique")
            risk_score += 10
        
        # Analyse tendance pression (prochaines heures)
        hourly = data.get('hourly', [])
        if len(hourly) >= 6:
            pressure_trend = hourly[6].get('pressure', pressure) - pressure
            if pressure_trend < -5:
                indicators.append("Chute rapide de pression détectée")
                risk_score += 20
        
        # Classification du risque
        if risk_score >= 70:
            risk_level = 'critique'
        elif risk_score >= 45:
            risk_level = 'élevé'
        elif risk_score >= 20:
            risk_level = 'modéré'
        else:
            risk_level = 'faible'
        
        return {
            'hurricane_risk': risk_level,
            'risk_score': risk_score,
            'indicators': indicators,
            'current_conditions': {
                'pressure': pressure,
                'wind_speed': wind_speed,
                'temperature': temp,
                'humidity': humidity
            },
            'last_analysis': datetime.now()
        }
    
    async def get_multi_location_severe_weather(self, coordinates_list: List[tuple]) -> Dict:
        """Récupère données météo sévère pour plusieurs locations"""
        results = {}
        
        # Traite par petits lots pour éviter rate limiting
        batch_size = 5
        for i in range(0, len(coordinates_list), batch_size):
            batch = coordinates_list[i:i + batch_size]
            
            # Traite le lot en parallèle
            tasks = [
                self.get_severe_weather_data(lat, lon) 
                for lat, lon in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Stocke les résultats
            for j, (lat, lon) in enumerate(batch):
                key = f"{lat:.4f},{lon:.4f}"
                result = batch_results[j]
                
                if isinstance(result, Exception):
                    logger.error(f"Error for {key}: {result}")
                    results[key] = None
                else:
                    results[key] = result
            
            # Délai entre lots
            if i + batch_size < len(coordinates_list):
                await asyncio.sleep(1)  # 1 seconde entre lots
        
        return results
    
    def is_severe_weather_detected(self, weather_data: Dict) -> bool:
        """Détecte si conditions météo extrêmes"""
        if not weather_data:
            return False
        
        current = weather_data.get('current', {})
        
        # Critères météo sévère
        wind_speed = current.get('wind_speed', 0)
        pressure = current.get('pressure', 1013)
        precipitation = current.get('precipitation', 0)
        
        return (
            wind_speed > 90 or      # > 90 km/h
            pressure < 990 or       # < 990 hPa
            precipitation > 20      # > 20 mm/h
        )

    async def get_weather_map_data(self, lat: float, lon: float, layer: str, zoom: int = 8) -> Optional[Dict]:
        """Récupère les données de carte météo (nuages, précipitations, radar)"""
        if not self.api_key:
            logger.error("OpenWeatherMap API key not configured")
            return None
        
        try:
            # Layers disponibles: clouds_new, precipitation_new, pressure_new, wind_new, temp_new, radar
            map_url = f"https://tile.openweathermap.org/map/{layer}/{zoom}/{lat}/{lon}.png"
            
            async with httpx.AsyncClient() as client:
                params = {
                    'appid': self.api_key
                }
                
                response = await client.get(map_url, params=params, timeout=15.0)
                
                if response.status_code == 200:
                    return {
                        'layer': layer,
                        'url': map_url,
                        'data': response.content,
                        'center': [lat, lon],
                        'zoom': zoom,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Weather map API error {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting weather map data: {e}")
            return None
    
    async def get_precipitation_forecast(self, lat: float, lon: float, hours: int = 12) -> Optional[Dict]:
        """Récupère les prévisions de précipitations pour les prochaines heures"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'cnt': hours  # Nombre d'heures
                }
                
                response = await client.get(
                    f"{self.base_url}/forecast/hourly",
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    precipitation_data = []
                    for item in data.get('list', []):
                        precipitation_data.append({
                            'time': item.get('dt'),
                            'time_formatted': datetime.fromtimestamp(item.get('dt')).isoformat(),
                            'precipitation': item.get('rain', {}).get('1h', 0),
                            'precipitation_probability': item.get('pop', 0) * 100,
                            'description': item.get('weather', [{}])[0].get('description', '')
                        })
                    
                    return {
                        'location': {'lat': lat, 'lon': lon},
                        'forecast': precipitation_data,
                        'generated_at': datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Precipitation forecast error {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting precipitation forecast: {e}")
            return None
    
    async def get_cloud_coverage(self, lat: float, lon: float) -> Optional[Dict]:
        """Récupère la couverture nuageuse détaillée"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'units': 'metric'
                }
                
                response = await client.get(
                    f"{self.base_url}/weather",
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        'cloud_coverage': data.get('clouds', {}).get('all', 0),
                        'visibility': data.get('visibility', 0),
                        'weather_condition': data.get('weather', [{}])[0].get('main', ''),
                        'description': data.get('weather', [{}])[0].get('description', ''),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Cloud coverage error {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting cloud coverage: {e}")
            return None

# Instance globale
openweather_service = OpenWeatherService()