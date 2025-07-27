import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from models import (
    WeatherCache, WeatherData, WeatherForecastDay, 
    RiskLevel, WeatherSource, WeatherConfig, APIUsageStats
)
from services.nasa_weather_service import NASAWeatherService

logger = logging.getLogger(__name__)

class WeatherCacheService:
    def __init__(self, db: AsyncIOMotorClient, config: WeatherConfig):
        self.db = db
        self.config = config
        self.nasa_service = NASAWeatherService(db, config)
        
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
    
    async def update_weather_cache(self, commune: str) -> Optional[WeatherCache]:
        """Met à jour le cache météo pour une commune avec NASA"""
        logger.info(f"Updating weather cache for {commune} using NASA API")
        
        # Récupère les données depuis NASA
        weather_cache = await self.nasa_service.get_nasa_weather_for_commune(commune)
        
        if not weather_cache:
            logger.error(f"Failed to get NASA weather data for {commune}")
            await self.db.api_usage.update_one(
                {"date": datetime.now().date().isoformat()},
                {"$inc": {"cache_misses": 1}},
                upsert=True
            )
            return None
        
        # Sauvegarde en base
        await self.db.weather_cache.update_one(
            {"commune": commune},
            {"$set": weather_cache.dict()},
            upsert=True
        )
        
        # Increment API call counter
        await self.increment_api_call(WeatherSource.NASA)
        
        logger.info(f"Weather cache updated successfully for {commune} using NASA data")
        return weather_cache
    
    async def get_or_update_weather(self, commune: str) -> Optional[WeatherCache]:
        """Récupère la météo depuis le cache ou met à jour si nécessaire"""
        # Essaie d'abord le cache
        cached_weather = await self.get_cached_weather(commune)
        
        if cached_weather:
            logger.info(f"Weather data served from cache for {commune}")
            return cached_weather
        
        # Cache manquant ou expiré, met à jour avec NASA
        return await self.update_weather_cache(commune)
    
    async def update_all_communes_weather(self):
        """Met à jour la météo pour toutes les communes (tâche cron)"""
        logger.info("Starting weather update for all communes using NASA API")
        
        # Traite par petits lots pour éviter la surcharge
        batch_size = 5
        communes = self.config.communes_guadeloupe
        
        for i in range(0, len(communes), batch_size):
            batch = communes[i:i + batch_size]
            
            # Traite le lot en parallèle
            tasks = [self.update_weather_cache(commune) for commune in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log des résultats
            for commune, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Error updating weather for {commune}: {result}")
                elif result:
                    logger.info(f"Successfully updated weather for {commune}")
            
            # Délai entre les lots pour éviter de surcharger l'API NASA
            if i + batch_size < len(communes):
                await asyncio.sleep(2)
        
        logger.info("Completed weather update for all communes using NASA API")
    
    async def adaptive_update_frequency(self) -> int:
        """Ajuste la fréquence de mise à jour selon le niveau de risque global"""
        # Analyse le niveau de risque global
        risk_counts = {level: 0 for level in RiskLevel}
        
        for commune in self.config.communes_guadeloupe[:10]:  # Échantillon pour performance
            cached = await self.get_cached_weather(commune)
            if cached and cached.forecast_5_days:
                max_risk = max([day.risk_level for day in cached.forecast_5_days])
                risk_counts[max_risk] += 1
        
        # Détermine la fréquence globale
        if risk_counts[RiskLevel.CRITIQUE] > 2:
            update_interval = 15  # minutes - Surveillance critique
            logger.warning("CRITICAL weather conditions detected - increasing update frequency")
        elif risk_counts[RiskLevel.ELEVE] > 5:
            update_interval = 30  # Surveillance élevée
            logger.info("HIGH risk conditions detected - moderate update frequency")
        elif risk_counts[RiskLevel.MODERE] > 8:
            update_interval = 60  # Surveillance normale
        else:
            update_interval = 120  # Surveillance réduite
            
        logger.info(f"Next update interval set to {update_interval} minutes")
        return update_interval
    
    async def get_weather_summary_stats(self) -> Dict:
        """Génère des statistiques résumées de la météo"""
        stats = {
            "total_communes": len(self.config.communes_guadeloupe),
            "cached_communes": 0,
            "risk_distribution": {level.value: 0 for level in RiskLevel},
            "average_temperature": 0,
            "average_precipitation": 0,
            "total_alerts": 0
        }
        
        total_temp = 0
        total_precip = 0
        cached_count = 0
        
        for commune in self.config.communes_guadeloupe:
            cached = await self.get_cached_weather(commune)
            
            if cached:
                cached_count += 1
                
                # Statistiques météo
                if cached.current_weather:
                    total_temp += cached.current_weather.temperature_current or cached.current_weather.temperature_max
                    total_precip += cached.current_weather.precipitation
                
                # Distribution des risques
                if cached.forecast_5_days:
                    max_risk = max([day.risk_level for day in cached.forecast_5_days])
                    stats["risk_distribution"][max_risk.value] += 1
        
        # Calculs moyennes
        if cached_count > 0:
            stats["cached_communes"] = cached_count
            stats["average_temperature"] = round(total_temp / cached_count, 1)
            stats["average_precipitation"] = round(total_precip / cached_count, 1)
        
        return stats
    
    async def cleanup_old_cache_entries(self) -> int:
        """Nettoie les entrées de cache trop anciennes"""
        # Supprime les entrées expirées depuis plus de 24h
        cutoff_date = datetime.utcnow() - timedelta(hours=24)
        
        result = await self.db.weather_cache.delete_many({
            "expires_at": {"$lt": cutoff_date}
        })
        
        deleted_count = result.deleted_count
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old cache entries")
        
        return deleted_count