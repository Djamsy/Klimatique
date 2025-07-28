"""
Scheduler pour l'exécution automatique des requêtes API météo
Gère les tâches planifiées selon le système de quotas
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict
from services.api_quota_manager import quota_manager

logger = logging.getLogger(__name__)

class WeatherScheduler:
    def __init__(self):
        self.running = False
        self.tasks = []
        
    async def start_scheduler(self):
        """Démarre le scheduler avec toutes les tâches périodiques"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        logger.info("Starting weather data scheduler...")
        
        # Tâche principale : exécution des requêtes planifiées
        self.tasks.append(
            asyncio.create_task(self._hourly_weather_update())
        )
        
        # Tâche de nettoyage du cache
        self.tasks.append(
            asyncio.create_task(self._cache_cleanup())
        )
        
        # Tâche de réinitialisation quotidienne
        self.tasks.append(
            asyncio.create_task(self._daily_quota_reset())
        )
        
        logger.info(f"Scheduler started with {len(self.tasks)} tasks")
    
    async def stop_scheduler(self):
        """Arrête le scheduler et toutes ses tâches"""
        if not self.running:
            return
        
        self.running = False
        
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks.clear()
        logger.info("Scheduler stopped")
    
    async def _hourly_weather_update(self):
        """Tâche principale : met à jour les données météo selon planning"""
        while self.running:
            try:
                current_minute = datetime.now().minute
                
                # Exécuter à la 5e minute de chaque heure
                if current_minute == 5:
                    logger.info("Executing hourly weather update...")
                    await quota_manager.execute_scheduled_requests()
                    
                    # Attendre pour éviter double exécution
                    await asyncio.sleep(60)
                
                # Vérifier toutes les minutes
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in hourly weather update: {e}")
                await asyncio.sleep(300)  # Attendre 5 min en cas d'erreur
    
    async def _cache_cleanup(self):
        """Nettoie le cache périodiquement"""
        while self.running:
            try:
                # Nettoyer toutes les 4 heures
                await asyncio.sleep(4 * 60 * 60)
                
                if not self.running:
                    break
                
                logger.info("Starting cache cleanup...")
                
                # Supprimer les entrées expirées
                expired_cutoff = datetime.now() - timedelta(hours=6)
                result = quota_manager.weather_cache.delete_many({
                    'timestamp': {'$lt': expired_cutoff}
                })
                
                logger.info(f"Cache cleanup completed: {result.deleted_count} entries removed")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60 * 60)  # Réessayer dans 1h
    
    async def _daily_quota_reset(self):
        """Réinitialise le quota quotidien à minuit"""
        while self.running:
            try:
                now = datetime.now()
                # Calculer le temps jusqu'à minuit
                midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                seconds_until_midnight = (midnight - now).total_seconds()
                
                logger.info(f"Next quota reset in {seconds_until_midnight/3600:.1f} hours")
                
                # Attendre jusqu'à minuit
                await asyncio.sleep(seconds_until_midnight)
                
                if not self.running:
                    break
                
                # Réinitialiser le quota
                logger.info("Performing daily quota reset...")
                quota_manager.init_daily_quota()
                
                logger.info("Daily quota reset completed")
                
            except Exception as e:
                logger.error(f"Error in daily quota reset: {e}")
                await asyncio.sleep(60 * 60)  # Réessayer dans 1h
    
    async def force_update_commune(self, commune: str) -> Dict:
        """Force la mise à jour d'une commune (bypass planning)"""
        try:
            logger.info(f"Force updating weather data for {commune}")
            
            # Vérifier le quota
            check = await quota_manager.can_make_request(commune)
            if not check['allowed'] and check['reason'] != f"Commune {commune} pas dans la priorité actuelle":
                return {
                    'success': False, 
                    'message': f"Cannot update: {check['reason']}",
                    'quota_info': check
                }
            
            # Importer les services
            from services.openweather_service import OpenWeatherService
            from data.communes_data import get_commune_info
            
            weather_service = OpenWeatherService()
            commune_info = get_commune_info(commune)
            coords = commune_info['coordinates']
            
            # Faire la requête
            weather_data = await weather_service.get_current_and_forecast(coords[0], coords[1])
            
            if weather_data:
                # Mettre en cache
                await quota_manager.cache_weather_data(commune, weather_data)
                await quota_manager.record_api_request(True, commune)
                
                return {
                    'success': True,
                    'message': f"Weather data updated for {commune}",
                    'cached_at': datetime.now().isoformat()
                }
            else:
                await quota_manager.record_api_request(False, commune)
                return {
                    'success': False,
                    'message': f"Failed to fetch weather data for {commune}"
                }
        
        except Exception as e:
            logger.error(f"Error in force update for {commune}: {e}")
            return {
                'success': False,
                'message': f"Error updating {commune}: {str(e)}"
            }
            
    def get_scheduler_status(self) -> Dict:
        """Retourne le statut du scheduler"""
        return {
            'running': self.running,
            'active_tasks': len([t for t in self.tasks if not t.done()]),
            'total_tasks': len(self.tasks),
            'quota_stats': quota_manager.get_quota_stats(),
            'next_update': self._get_next_update_time()
        }
    
    def _get_next_update_time(self) -> str:
        """Calcule la prochaine mise à jour planifiée"""
        now = datetime.now()
        next_hour = now.replace(minute=5, second=0, microsecond=0)
        
        if now.minute >= 5:
            next_hour += timedelta(hours=1)
        
        return next_hour.isoformat()

# Instance globale
weather_scheduler = WeatherScheduler()