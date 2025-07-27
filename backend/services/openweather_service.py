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
        
    async def get_current_and_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """Récupère données actuelles et prévisions depuis OpenWeatherMap"""
        if not self.api_key:
            logger.error("OpenWeatherMap API key not configured")
            return None
            
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
        """Récupère données météo extrême pour IA cyclonique"""
        data = await self.get_current_and_forecast(lat, lon)
        
        if not data:
            return None
            
        try:
            current = data.get('current', {})
            hourly = data.get('hourly', [])
            
            # Données actuelles pour IA
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
                'timestamp': datetime.fromtimestamp(current.get('dt', datetime.now().timestamp()))
            }
            
            # Prévisions horaires pour timeline
            timeline_predictions = {}
            for i, hour_data in enumerate(hourly[:24]):  # Prochaines 24h
                if i % 6 == 0:  # Tous les 6h
                    time_key = f"H+{i}"
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
                'source': 'openweathermap',
                'last_update': datetime.now()
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

# Instance globale
openweather_service = OpenWeatherService()