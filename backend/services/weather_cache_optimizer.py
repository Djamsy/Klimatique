import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from motor.motor_asyncio import AsyncIOMotorClient
from services.openweather_service import openweather_service
from services.meteo_france_service import meteo_france_service
from data.communes_data import get_all_communes, get_commune_info
import os

logger = logging.getLogger(__name__)

class WeatherCacheOptimizer:
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
        self.db = self.mongo_client.meteo_sentinelle
        self.cache_collection = self.db.weather_cache
        self.api_usage_collection = self.db.api_usage
        
        # Configuration du cache
        self.cache_durations = {
            'vigilance_rouge': 5,      # 5 minutes
            'vigilance_orange': 10,    # 10 minutes
            'vigilance_jaune': 15,     # 15 minutes
            'vigilance_verte': 30,     # 30 minutes
            'forecast': 60,            # 1 heure
            'satellite': 20,           # 20 minutes
            'radar': 10                # 10 minutes
        }
        
        # Limites API
        self.daily_api_limit = 1000
        self.priority_communes = [
            'Pointe-à-Pitre', 'Basse-Terre', 'Sainte-Anne', 
            'Le Moule', 'Saint-François', 'Gosier'
        ]
        
        self.refresh_scheduler = None
        self.is_running = False
    
    async def start_background_refresh(self):
        """Démarre le rafraîchissement automatique en arrière-plan"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting background weather cache refresh")
        
        # Démarrer les tâches de rafraîchissement
        asyncio.create_task(self._vigilance_refresh_loop())
        asyncio.create_task(self._weather_refresh_loop())
        asyncio.create_task(self._satellite_refresh_loop())
        asyncio.create_task(self._cleanup_old_cache())
    
    async def _vigilance_refresh_loop(self):
        """Boucle de rafraîchissement des vigilances"""
        while self.is_running:
            try:
                await self._refresh_vigilance_data()
                await asyncio.sleep(5 * 60)  # Toutes les 5 minutes
            except Exception as e:
                logger.error(f"Error in vigilance refresh loop: {e}")
                await asyncio.sleep(60)  # Attendre 1 minute avant de réessayer
    
    async def _weather_refresh_loop(self):
        """Boucle de rafraîchissement des données météo"""
        while self.is_running:
            try:
                await self._refresh_weather_data()
                await asyncio.sleep(10 * 60)  # Toutes les 10 minutes
            except Exception as e:
                logger.error(f"Error in weather refresh loop: {e}")
                await asyncio.sleep(60)
    
    async def _satellite_refresh_loop(self):
        """Boucle de rafraîchissement des données satellite"""
        while self.is_running:
            try:
                await self._refresh_satellite_data()
                await asyncio.sleep(20 * 60)  # Toutes les 20 minutes
            except Exception as e:
                logger.error(f"Error in satellite refresh loop: {e}")
                await asyncio.sleep(60)
    
    async def _refresh_vigilance_data(self):
        """Rafraîchit les données de vigilance"""
        try:
            vigilance_data = await meteo_france_service.get_vigilance_data('guadeloupe')
            
            cache_entry = {
                'cache_key': 'vigilance_guadeloupe',
                'data': vigilance_data,
                'last_updated': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=self.cache_durations['vigilance_' + vigilance_data['color_level']]),
                'data_type': 'vigilance',
                'source': 'meteo_france'
            }
            
            await self.cache_collection.replace_one(
                {'cache_key': 'vigilance_guadeloupe'},
                cache_entry,
                upsert=True
            )
            
            logger.info(f"Updated vigilance cache: {vigilance_data['color_level']}")
            
        except Exception as e:
            logger.error(f"Error refreshing vigilance data: {e}")
    
    async def _refresh_weather_data(self):
        """Rafraîchit les données météo pour les communes prioritaires"""
        try:
            # Vérifier l'usage API quotidien
            daily_usage = await self._get_daily_api_usage()
            
            if daily_usage >= self.daily_api_limit * 0.8:  # 80% de la limite
                logger.warning(f"API usage high: {daily_usage}/{self.daily_api_limit}")
                communes_to_refresh = self.priority_communes[:3]  # Limiter aux 3 plus importantes
            else:
                communes_to_refresh = get_all_communes()
            
            for commune in communes_to_refresh:
                try:
                    await self._refresh_commune_weather(commune)
                    await asyncio.sleep(1)  # Pause entre les calls
                except Exception as e:
                    logger.error(f"Error refreshing weather for {commune}: {e}")
                    continue
            
            logger.info(f"Refreshed weather data for {len(communes_to_refresh)} communes")
            
        except Exception as e:
            logger.error(f"Error in weather refresh: {e}")
    
    async def _refresh_commune_weather(self, commune: str):
        """Rafraîchit les données météo d'une commune"""
        try:
            commune_info = get_commune_info(commune)
            coords = commune_info['coordinates']
            
            # Récupérer les données OpenWeatherMap
            weather_data = await openweather_service.get_severe_weather_data(coords[0], coords[1])
            
            if not weather_data:
                return
            
            # Mettre à jour l'usage API
            await self._track_api_usage('openweather', commune)
            
            cache_entry = {
                'cache_key': f'weather_{commune}',
                'data': weather_data,
                'last_updated': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=15),
                'data_type': 'weather',
                'source': 'openweather',
                'commune': commune,
                'coordinates': coords
            }
            
            await self.cache_collection.replace_one(
                {'cache_key': f'weather_{commune}'},
                cache_entry,
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error refreshing weather for {commune}: {e}")
    
    async def _refresh_satellite_data(self):
        """Rafraîchit les données satellite et radar"""
        try:
            # Coordonnées centre Guadeloupe
            center_lat, center_lon = 16.25, -61.55
            
            # Données satellite pour nuages
            satellite_data = {
                'clouds': await self._get_satellite_clouds(center_lat, center_lon),
                'precipitation': await self._get_precipitation_data(center_lat, center_lon),
                'radar': await self._get_radar_data(center_lat, center_lon)
            }
            
            cache_entry = {
                'cache_key': 'satellite_guadeloupe',
                'data': satellite_data,
                'last_updated': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=20),
                'data_type': 'satellite',
                'source': 'openweather'
            }
            
            await self.cache_collection.replace_one(
                {'cache_key': 'satellite_guadeloupe'},
                cache_entry,
                upsert=True
            )
            
            # Mettre à jour l'usage API
            await self._track_api_usage('openweather', 'satellite')
            
            logger.info("Updated satellite data cache")
            
        except Exception as e:
            logger.error(f"Error refreshing satellite data: {e}")
    
    async def _get_satellite_clouds(self, lat: float, lon: float) -> Dict:
        """Récupère les données de nuages satellite"""
        try:
            # Utiliser l'API OpenWeatherMap Maps
            map_data = await openweather_service.get_weather_map_data(lat, lon, 'clouds_new')
            return {
                'layer': 'clouds_new',
                'data': map_data,
                'center': [lat, lon],
                'zoom': 8,
                'opacity': 0.6
            }
        except Exception as e:
            logger.error(f"Error getting satellite clouds: {e}")
            return {}
    
    async def _get_precipitation_data(self, lat: float, lon: float) -> Dict:
        """Récupère les données de précipitations"""
        try:
            precip_data = await openweather_service.get_weather_map_data(lat, lon, 'precipitation_new')
            return {
                'layer': 'precipitation_new',
                'data': precip_data,
                'center': [lat, lon],
                'zoom': 8,
                'opacity': 0.7
            }
        except Exception as e:
            logger.error(f"Error getting precipitation data: {e}")
            return {}
    
    async def _get_radar_data(self, lat: float, lon: float) -> Dict:
        """Récupère les données radar"""
        try:
            radar_data = await openweather_service.get_weather_map_data(lat, lon, 'radar')
            return {
                'layer': 'radar',
                'data': radar_data,
                'center': [lat, lon],
                'zoom': 8,
                'opacity': 0.8
            }
        except Exception as e:
            logger.error(f"Error getting radar data: {e}")
            return {}
    
    async def _cleanup_old_cache(self):
        """Nettoie les anciennes entrées du cache"""
        while self.is_running:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                result = await self.cache_collection.delete_many({
                    'expires_at': {'$lt': datetime.utcnow()}
                })
                
                if result.deleted_count > 0:
                    logger.info(f"Cleaned up {result.deleted_count} expired cache entries")
                
                await asyncio.sleep(60 * 60)  # Nettoyer toutes les heures
                
            except Exception as e:
                logger.error(f"Error cleaning cache: {e}")
                await asyncio.sleep(60)
    
    async def _track_api_usage(self, provider: str, endpoint: str):
        """Suit l'usage des APIs"""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            await self.api_usage_collection.update_one(
                {'provider': provider, 'date': today},
                {
                    '$inc': {'call_count': 1},
                    '$push': {
                        'calls': {
                            'endpoint': endpoint,
                            'timestamp': datetime.utcnow()
                        }
                    },
                    '$set': {'last_call': datetime.utcnow()}
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error tracking API usage: {e}")
    
    async def _get_daily_api_usage(self) -> int:
        """Récupère l'usage API quotidien"""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            usage_doc = await self.api_usage_collection.find_one({
                'provider': 'openweather',
                'date': today
            })
            
            return usage_doc.get('call_count', 0) if usage_doc else 0
            
        except Exception as e:
            logger.error(f"Error getting daily API usage: {e}")
            return 0
    
    async def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Récupère les données depuis le cache"""
        try:
            cached_entry = await self.cache_collection.find_one({'cache_key': cache_key})
            
            if not cached_entry:
                return None
            
            # Vérifier l'expiration
            if cached_entry['expires_at'] < datetime.utcnow():
                await self.cache_collection.delete_one({'cache_key': cache_key})
                return None
            
            return cached_entry['data']
            
        except Exception as e:
            logger.error(f"Error getting cached data for {cache_key}: {e}")
            return None
    
    async def get_api_usage_stats(self) -> Dict:
        """Récupère les statistiques d'usage API"""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            usage_stats = await self.api_usage_collection.find({
                'date': {'$gte': today - timedelta(days=7)}
            }).to_list(length=None)
            
            stats = {
                'daily_limit': self.daily_api_limit,
                'today_usage': 0,
                'weekly_usage': 0,
                'efficiency': 0,
                'last_week': []
            }
            
            for day_stats in usage_stats:
                call_count = day_stats.get('call_count', 0)
                stats['weekly_usage'] += call_count
                
                if day_stats['date'] == today:
                    stats['today_usage'] = call_count
                
                stats['last_week'].append({
                    'date': day_stats['date'].isoformat(),
                    'calls': call_count
                })
            
            # Calculer l'efficacité (% de limite utilisée)
            if stats['today_usage'] > 0:
                stats['efficiency'] = (stats['today_usage'] / self.daily_api_limit) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting API usage stats: {e}")
            return {}
    
    async def stop(self):
        """Arrête le service de cache"""
        self.is_running = False
        logger.info("Weather cache optimizer stopped")

# Instance globale
weather_cache_optimizer = WeatherCacheOptimizer()