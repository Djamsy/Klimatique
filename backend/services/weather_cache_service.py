import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
import logging
from models import (
    WeatherCache, WeatherData, WeatherForecastDay, 
    RiskLevel, WeatherSource, WeatherConfig, APIUsageStats
)

logger = logging.getLogger(__name__)

class WeatherCacheService:
    def __init__(self, db: AsyncIOMotorClient, config: WeatherConfig):
        self.db = db
        self.config = config
        self.openweather_api_key = os.environ.get('OPENWEATHER_API_KEY')
        self.openweather_base_url = "https://api.openweathermap.org/data/3.0"
        self.daily_calls_made = 0
        self.last_reset_date = datetime.now().date()
        
    async def get_daily_usage_stats(self) -> APIUsageStats:
        """Récupère les statistiques d'usage du jour"""
        today = datetime.now().date().isoformat()
        stats = await self.db.api_usage.find_one({"date": today})
        
        if not stats:
            stats = APIUsageStats(date=today)
            await self.db.api_usage.insert_one(stats.dict())
            
        return APIUsageStats(**stats)
    
    async def increment_api_call(self, source: WeatherSource):
        """Incrémente le compteur d'appels API"""
        today = datetime.now().date().isoformat()
        field = f"{source.value}_calls"
        
        await self.db.api_usage.update_one(
            {"date": today},
            {"$inc": {field: 1}},
            upsert=True
        )
        
        if source == WeatherSource.OPENWEATHERMAP:
            self.daily_calls_made += 1
    
    async def can_make_api_call(self) -> bool:
        """Vérifie si on peut encore faire des appels API aujourd'hui"""
        # Reset compteur si nouveau jour
        if datetime.now().date() != self.last_reset_date:
            self.daily_calls_made = 0
            self.last_reset_date = datetime.now().date()
            
        stats = await self.get_daily_usage_stats()
        return stats.openweather_calls < self.config.daily_call_limit
    
    async def get_cached_weather(self, commune: str) -> Optional[WeatherCache]:
        """Récupère la météo depuis le cache"""
        cache = await self.db.weather_cache.find_one({"commune": commune})
        
        if not cache:
            return None
            
        weather_cache = WeatherCache(**cache)
        
        # Vérifie si le cache a expiré
        if datetime.utcnow() > weather_cache.expires_at:
            logger.info(f"Cache expired for {commune}, will refresh")
            return None
            
        # Increment cache hit
        await self.db.api_usage.update_one(
            {"date": datetime.now().date().isoformat()},
            {"$inc": {"cache_hits": 1}},
            upsert=True
        )
        
        return weather_cache
    
    async def fetch_openweather_data(self, commune: str) -> Optional[Dict]:
        """Appelle l'API OpenWeatherMap pour une commune"""
        if not await self.can_make_api_call():
            logger.warning(f"Daily API limit reached, cannot fetch data for {commune}")
            return None
            
        # Récupère les coordonnées de la commune (à améliorer avec vraie géolocalisation)
        coordinates = self._get_commune_coordinates(commune)
        if not coordinates:
            logger.error(f"Coordinates not found for commune: {commune}")
            return None
            
        lat, lon = coordinates
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.openweather_base_url}/onecall"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.openweather_api_key,
                    "units": "metric",
                    "lang": "fr",
                    "exclude": "minutely"
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                await self.increment_api_call(WeatherSource.OPENWEATHERMAP)
                logger.info(f"Successfully fetched OpenWeather data for {commune}")
                
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"Error fetching OpenWeather data for {commune}: {e}")
            return None
    
    def _parse_openweather_response(self, data: Dict, commune: str) -> WeatherCache:
        """Parse la réponse OpenWeatherMap en objet WeatherCache"""
        current = data["current"]
        daily = data["daily"]
        
        # Données météo actuelles
        current_weather = WeatherData(
            temperature_min=daily[0]["temp"]["min"],
            temperature_max=daily[0]["temp"]["max"],
            temperature_current=current["temp"],
            humidity=current["humidity"],
            wind_speed=current["wind_speed"] * 3.6,  # m/s vers km/h
            wind_direction=current.get("wind_deg"),
            precipitation=current.get("rain", {}).get("1h", 0),
            precipitation_probability=int(daily[0]["pop"] * 100),
            pressure=current.get("pressure"),
            visibility=current.get("visibility", 0) / 1000,  # m vers km
            uv_index=current.get("uvi", 0),
            weather_description=current["weather"][0]["description"],
            weather_icon=current["weather"][0]["icon"]
        )
        
        # Prévisions 5 jours
        forecast_5_days = []
        for i, day_data in enumerate(daily[:5]):
            day_weather = WeatherData(
                temperature_min=day_data["temp"]["min"],
                temperature_max=day_data["temp"]["max"],
                humidity=day_data["humidity"],
                wind_speed=day_data["wind_speed"] * 3.6,
                precipitation=day_data.get("rain", {}).get("1h", 0),
                precipitation_probability=int(day_data["pop"] * 100),
                weather_description=day_data["weather"][0]["description"],
                weather_icon=day_data["weather"][0]["icon"]
            )
            
            # Évalue le niveau de risque
            risk_level = self._assess_risk_level(day_weather)
            
            forecast_day = WeatherForecastDay(
                date=(datetime.now() + timedelta(days=i)).date().isoformat(),
                day_name=self._get_day_name(i),
                weather_data=day_weather,
                risk_level=risk_level,
                risk_factors=self._get_risk_factors(day_weather)
            )
            
            forecast_5_days.append(forecast_day)
        
        # Cache avec expiration adaptative selon le risque
        max_risk = max([day.risk_level for day in forecast_5_days], default=RiskLevel.FAIBLE)
        expiry_minutes = self.config.update_frequencies[max_risk]
        
        return WeatherCache(
            commune=commune,
            coordinates=self._get_commune_coordinates(commune),
            current_weather=current_weather,
            forecast_5_days=forecast_5_days,
            source=WeatherSource.OPENWEATHERMAP,
            expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
            last_api_call=datetime.utcnow()
        )
    
    def _assess_risk_level(self, weather: WeatherData) -> RiskLevel:
        """Évalue le niveau de risque météorologique"""
        risk_score = 0
        
        # Vitesse du vent
        if weather.wind_speed > 80:  # km/h
            risk_score += 4
        elif weather.wind_speed > 60:
            risk_score += 3
        elif weather.wind_speed > 40:
            risk_score += 2
        elif weather.wind_speed > 25:
            risk_score += 1
            
        # Précipitations
        if weather.precipitation > 50:  # mm/h
            risk_score += 3
        elif weather.precipitation > 20:
            risk_score += 2
        elif weather.precipitation > 10:
            risk_score += 1
            
        # Probabilité de précipitation
        if weather.precipitation_probability > 80:
            risk_score += 2
        elif weather.precipitation_probability > 60:
            risk_score += 1
            
        # Température extrême
        if weather.temperature_max > 35 or weather.temperature_min < 15:
            risk_score += 1
            
        # Conversion score -> niveau
        if risk_score >= 6:
            return RiskLevel.CRITIQUE
        elif risk_score >= 4:
            return RiskLevel.ELEVE
        elif risk_score >= 2:
            return RiskLevel.MODERE
        else:
            return RiskLevel.FAIBLE
    
    def _get_risk_factors(self, weather: WeatherData) -> List[str]:
        """Identifie les facteurs de risque spécifiques"""
        factors = []
        
        if weather.wind_speed > 60:
            factors.append("Vents violents")
        elif weather.wind_speed > 40:
            factors.append("Vents forts")
            
        if weather.precipitation > 30:
            factors.append("Pluies diluviennes")
        elif weather.precipitation > 15:
            factors.append("Fortes pluies")
            
        if weather.precipitation_probability > 80:
            factors.append("Précipitations quasi-certaines")
            
        if weather.temperature_max > 35:
            factors.append("Chaleur extrême")
            
        return factors
    
    def _get_day_name(self, day_offset: int) -> str:
        """Retourne le nom du jour en français"""
        day_names = ["Aujourd'hui", "Demain", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        
        if day_offset < 2:
            return day_names[day_offset]
        
        target_date = datetime.now() + timedelta(days=day_offset)
        french_days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        return french_days[target_date.weekday()]
    
    def _get_commune_coordinates(self, commune: str) -> Optional[List[float]]:
        """Retourne les coordonnées d'une commune (à améliorer avec vraie base de données)"""
        coordinates_map = {
            "Pointe-à-Pitre": [16.2415, -61.5328],
            "Basse-Terre": [16.0074, -61.7056],
            "Sainte-Anne": [16.2276, -61.3825],
            "Le Moule": [16.3336, -61.3503],
            "Saint-François": [16.2500, -61.2667],
            "Gosier": [16.1833, -61.5167],
            "Petit-Bourg": [16.1833, -61.5833],
            "Lamentin": [16.2500, -61.6000],
            "Capesterre-Belle-Eau": [16.0450, -61.5675],
            "Bouillante": [16.1333, -61.7667]
        }
        return coordinates_map.get(commune)
    
    async def update_weather_cache(self, commune: str) -> Optional[WeatherCache]:
        """Met à jour le cache météo pour une commune"""
        logger.info(f"Updating weather cache for {commune}")
        
        # Essaie de récupérer depuis l'API
        weather_data = await self.fetch_openweather_data(commune)
        
        if not weather_data:
            logger.error(f"Failed to fetch weather data for {commune}")
            await self.db.api_usage.update_one(
                {"date": datetime.now().date().isoformat()},
                {"$inc": {"cache_misses": 1}},
                upsert=True
            )
            return None
        
        # Parse et crée l'objet cache
        weather_cache = self._parse_openweather_response(weather_data, commune)
        
        # Sauvegarde en base
        await self.db.weather_cache.update_one(
            {"commune": commune},
            {"$set": weather_cache.dict()},
            upsert=True
        )
        
        logger.info(f"Weather cache updated successfully for {commune}")
        return weather_cache
    
    async def get_or_update_weather(self, commune: str) -> Optional[WeatherCache]:
        """Récupère la météo depuis le cache ou met à jour si nécessaire"""
        # Essaie d'abord le cache
        cached_weather = await self.get_cached_weather(commune)
        
        if cached_weather:
            logger.info(f"Weather data served from cache for {commune}")
            return cached_weather
        
        # Cache manquant ou expiré, met à jour
        return await self.update_weather_cache(commune)
    
    async def update_all_communes_weather(self):
        """Met à jour la météo pour toutes les communes (tâche cron)"""
        logger.info("Starting weather update for all communes")
        
        for commune in self.config.communes_guadeloupe:
            try:
                await self.update_weather_cache(commune)
                # Petit délai pour éviter de surcharger l'API
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error updating weather for {commune}: {e}")
                continue
        
        logger.info("Completed weather update for all communes")
    
    async def adaptive_update_frequency(self):
        """Ajuste la fréquence de mise à jour selon le niveau de risque global"""
        # Analyse le niveau de risque global
        risk_counts = {level: 0 for level in RiskLevel}
        
        for commune in self.config.communes_guadeloupe:
            cached = await self.get_cached_weather(commune)
            if cached and cached.forecast_5_days:
                max_risk = max([day.risk_level for day in cached.forecast_5_days])
                risk_counts[max_risk] += 1
        
        # Détermine la fréquence globale
        if risk_counts[RiskLevel.CRITIQUE] > 5:
            update_interval = 5  # minutes
            logger.warning("CRITICAL weather conditions detected - increasing update frequency")
        elif risk_counts[RiskLevel.ELEVE] > 10:
            update_interval = 10
            logger.info("HIGH risk conditions detected - moderate update frequency")
        elif risk_counts[RiskLevel.MODERE] > 15:
            update_interval = 30
        else:
            update_interval = 60
            
        return update_interval