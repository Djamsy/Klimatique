"""
Service de planification et gestion des quotas API OpenWeatherMap
Répartit intelligemment les 1000 requêtes quotidiennes sur 24h
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

@dataclass
class APIQuotaConfig:
    daily_limit: int = 1000
    communes_count: int = 32
    priority_hours: List[int] = None  # Heures de forte affluence
    min_refresh_interval: int = 2  # Heures minimum entre maj d'une commune
    
    def __post_init__(self):
        if self.priority_hours is None:
            self.priority_hours = [6, 8, 12, 16, 18, 20]  # Heures de pic

class APIQuotaManager:
    def __init__(self):
        self.config = APIQuotaConfig()
        self.mongo_client = MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017/'))
        self.db = self.mongo_client.meteo_sentinelle
        self.quota_collection = self.db.api_quotas
        self.weather_cache = self.db.weather_cache_advanced
        
        # Communes de Guadeloupe par priorité
        self.communes_priority = {
            'high': [  # Centres urbains et touristiques
                'pointe-a-pitre', 'basse-terre', 'les-abymes', 'baie-mahault',
                'le-gosier', 'sainte-anne', 'saint-francois', 'le-moule'
            ],
            'medium': [  # Communes moyennes
                'petit-bourg', 'lamentin', 'capesterre-belle-eau', 'bouillante',
                'deshaies', 'saint-claude', 'goyave', 'trois-rivieres'
            ],
            'low': [  # Communes moins visitées
                'anse-bertrand', 'port-louis', 'morne-a-l-eau', 'grand-bourg',
                'capesterre-de-marie-galante', 'saint-louis-marie-galante',
                'vieux-habitants', 'pointe-noire', 'baillif', 'vieux-fort',
                'terre-de-bas', 'terre-de-haut', 'la-desirade', 'saint-barthelemy',
                'saint-martin'
            ]
        }
        
        self.init_daily_quota()
    
    def init_daily_quota(self):
        """Initialise le quota quotidien"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        existing_quota = self.quota_collection.find_one({'date': today})
        if not existing_quota:
            # Créer le planning du jour
            schedule = self.generate_daily_schedule()
            
            quota_doc = {
                'date': today,
                'total_limit': self.config.daily_limit,
                'used_requests': 0,
                'remaining_requests': self.config.daily_limit,
                'schedule': schedule,
                'last_reset': datetime.now(),
                'status': 'active'
            }
            
            self.quota_collection.insert_one(quota_doc)
            logger.info(f"Initialized daily quota for {today}: {self.config.daily_limit} requests")
    
    def generate_daily_schedule(self) -> Dict:
        """Génère le planning quotidien des requêtes API"""
        schedule = {}
        total_requests = 0
        
        # Répartir les requêtes sur 24 heures
        for hour in range(24):
            hour_key = f"{hour:02d}:00"
            
            if hour in self.config.priority_hours:
                # Heures de pointe : plus de requêtes
                base_requests = 50
                communes_to_update = (
                    self.communes_priority['high'] + 
                    self.communes_priority['medium'][:4]
                )
            elif hour % 3 == 0:  # Toutes les 3h
                # Heures normales
                base_requests = 35
                communes_to_update = self.communes_priority['high']
            else:
                # Heures creuses
                base_requests = 20
                communes_to_update = self.communes_priority['high'][:4]
            
            # Ajuster selon les limites
            if total_requests + base_requests > self.config.daily_limit:
                base_requests = max(0, self.config.daily_limit - total_requests)
            
            schedule[hour_key] = {
                'planned_requests': base_requests,
                'executed_requests': 0,
                'communes_priority': communes_to_update[:base_requests//2],  # Limiter selon quota
                'status': 'pending',
                'execution_time': None
            }
            
            total_requests += base_requests
            
            if total_requests >= self.config.daily_limit:
                break
        
        logger.info(f"Generated daily schedule: {total_requests} total requests planned")
        return schedule
    
    async def can_make_request(self, commune: str = None) -> Dict:
        """Vérifie si on peut faire une requête API maintenant"""
        today = datetime.now().strftime('%Y-%m-%d')
        current_hour = datetime.now().strftime('%H:00')
        
        quota_doc = self.quota_collection.find_one({'date': today})
        if not quota_doc:
            self.init_daily_quota()
            quota_doc = self.quota_collection.find_one({'date': today})
        
        remaining = quota_doc['remaining_requests']
        schedule = quota_doc.get('schedule', {})
        current_slot = schedule.get(current_hour, {})
        
        # Vérifications
        can_request = False
        reason = ""
        
        if remaining <= 0:
            reason = "Quota quotidien épuisé"
        elif current_slot.get('status') == 'completed':
            reason = f"Slot {current_hour} déjà complété"
        elif commune and commune not in current_slot.get('communes_priority', []):
            reason = f"Commune {commune} pas dans la priorité actuelle"
        else:
            can_request = True
            reason = "Requête autorisée"
        
        return {
            'allowed': can_request,
            'reason': reason,
            'remaining_daily': remaining,
            'current_slot': current_slot.get('planned_requests', 0),
            'next_available': self.get_next_available_slot()
        }
    
    async def record_api_request(self, success: bool, commune: str = None):
        """Enregistre une requête API effectuée"""
        today = datetime.now().strftime('%Y-%m-%d')
        current_hour = datetime.now().strftime('%H:00')
        
        update_query = {'date': today}
        update_data = {
            '$inc': {
                'used_requests': 1,
                'remaining_requests': -1,
                f'schedule.{current_hour}.executed_requests': 1
            },
            '$set': {
                f'schedule.{current_hour}.execution_time': datetime.now()
            }
        }
        
        if success:
            update_data['$set'][f'schedule.{current_hour}.status'] = 'active'
        
        self.quota_collection.update_one(update_query, update_data)
        
        logger.info(f"Recorded API request: success={success}, commune={commune}")
    
    def get_next_available_slot(self) -> Optional[str]:
        """Trouve le prochain créneau disponible"""
        today = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now()
        
        quota_doc = self.quota_collection.find_one({'date': today})
        if not quota_doc:
            return None
        
        schedule = quota_doc.get('schedule', {})
        
        for hour_key in sorted(schedule.keys()):
            slot = schedule[hour_key]
            slot_time = datetime.strptime(f"{today} {hour_key}", '%Y-%m-%d %H:%M')
            
            if (slot_time > current_time and 
                slot.get('status') != 'completed' and
                slot.get('planned_requests', 0) > slot.get('executed_requests', 0)):
                return hour_key
        
        return None
    
    async def get_cached_weather_data(self, commune: str) -> Optional[Dict]:
        """Récupère les données météo en cache pour une commune"""
        cache_doc = self.weather_cache.find_one({
            'commune': commune,
            'timestamp': {'$gt': datetime.now() - timedelta(hours=3)}  # Cache valide 3h
        }, sort=[('timestamp', -1)])
        
        if cache_doc:
            # Nettoyer ObjectId pour JSON
            cache_doc.pop('_id', None)
            logger.info(f"Serving cached weather data for {commune}")
            return cache_doc
        
        return None
    
    async def cache_weather_data(self, commune: str, weather_data: Dict):
        """Met en cache les données météo d'une commune"""
        cache_doc = {
            'commune': commune,
            'weather_data': weather_data,
            'timestamp': datetime.now(),
            'source': 'api_scheduled',
            'expires_at': datetime.now() + timedelta(hours=4)
        }
        
        # Remplacer l'ancien cache
        self.weather_cache.replace_one(
            {'commune': commune},
            cache_doc,
            upsert=True
        )
        
        logger.info(f"Cached weather data for {commune}")
    
    async def execute_scheduled_requests(self):
        """Exécute les requêtes planifiées pour l'heure actuelle"""
        current_hour = datetime.now().strftime('%H:00')
        today = datetime.now().strftime('%Y-%m-%d')
        
        quota_doc = self.quota_collection.find_one({'date': today})
        if not quota_doc:
            return
        
        schedule = quota_doc.get('schedule', {})
        current_slot = schedule.get(current_hour)
        
        if not current_slot or current_slot.get('status') == 'completed':
            return
        
        communes_to_update = current_slot.get('communes_priority', [])
        planned_requests = current_slot.get('planned_requests', 0)
        
        logger.info(f"Executing scheduled requests for {current_hour}: {len(communes_to_update)} communes")
        
        # Importer ici pour éviter les imports circulaires
        from services.openweather_service import OpenWeatherService
        from data.communes_data import get_commune_info
        
        weather_service = OpenWeatherService()
        successful_requests = 0
        
        for commune in communes_to_update[:planned_requests]:
            try:
                # Vérifier quota disponible
                check = await self.can_make_request(commune)
                if not check['allowed']:
                    logger.warning(f"Quota exceeded, stopping scheduled requests")
                    break
                
                # Récupérer les données
                commune_info = get_commune_info(commune)
                coords = commune_info['coordinates']
                
                weather_data = await weather_service.get_current_and_forecast(coords[0], coords[1])
                
                if weather_data:
                    # Mettre en cache
                    await self.cache_weather_data(commune, weather_data)
                    successful_requests += 1
                    
                    # Enregistrer la requête
                    await self.record_api_request(True, commune)
                    
                    # Délai entre requêtes
                    await asyncio.sleep(1)
                else:
                    await self.record_api_request(False, commune)
            
            except Exception as e:
                logger.error(f"Error updating weather for {commune}: {e}")
                await self.record_api_request(False, commune)
        
        # Marquer le slot comme complété
        self.quota_collection.update_one(
            {'date': today},
            {'$set': {f'schedule.{current_hour}.status': 'completed'}}
        )
        
        logger.info(f"Completed scheduled requests for {current_hour}: {successful_requests} successful")
    
    def get_quota_stats(self) -> Dict:
        """Statistiques du quota quotidien"""
        today = datetime.now().strftime('%Y-%m-%d')
        quota_doc = self.quota_collection.find_one({'date': today})
        
        if not quota_doc:
            return {'error': 'No quota data for today'}
        
        schedule = quota_doc.get('schedule', {})
        completed_slots = sum(1 for slot in schedule.values() if slot.get('status') == 'completed')
        
        return {
            'date': today,
            'total_limit': quota_doc['total_limit'],
            'used_requests': quota_doc['used_requests'],
            'remaining_requests': quota_doc['remaining_requests'],
            'usage_percentage': (quota_doc['used_requests'] / quota_doc['total_limit']) * 100,
            'completed_slots': f"{completed_slots}/{len(schedule)}",
            'next_available': self.get_next_available_slot(),
            'cache_entries': self.weather_cache.count_documents({
                'timestamp': {'$gt': datetime.now() - timedelta(hours=4)}
            })
        }

# Instance globale
quota_manager = APIQuotaManager()