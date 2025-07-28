import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class SocialPostScheduler:
    def __init__(self, db, weather_service, social_media_service, meteo_france_service, cyclone_predictor):
        self.db = db
        self.weather_service = weather_service
        self.social_media_service = social_media_service
        self.meteo_france_service = meteo_france_service
        self.cyclone_predictor = cyclone_predictor
        
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        # Configuration par défaut
        self.default_communes = [
            'Pointe-à-Pitre', 'Basse-Terre', 'Les Abymes', 
            'Baie-Mahault', 'Le Gosier', 'Sainte-Anne'
        ]
    
    async def start_scheduler(self):
        """Démarre le planificateur de posts sociaux"""
        try:
            if self.is_running:
                logger.warning("Social post scheduler already running")
                return
            
            # Ajouter les tâches programmées
            await self._setup_scheduled_jobs()
            
            # Démarrer le scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Social post scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Error starting social post scheduler: {e}")
            raise
    
    async def stop_scheduler(self):
        """Arrête le planificateur"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Social post scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping social post scheduler: {e}")
    
    async def _setup_scheduled_jobs(self):
        """Configure les tâches programmées par défaut"""
        
        # Posts météo quotidiens (matin et soir)
        self.scheduler.add_job(
            self._daily_weather_morning_post,
            CronTrigger(hour=7, minute=0),  # 7h00 tous les jours
            id="daily_weather_morning",
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self._daily_weather_evening_post,
            CronTrigger(hour=18, minute=0),  # 18h00 tous les jours
            id="daily_weather_evening",
            replace_existing=True
        )
        
        # Posts de vigilance (toutes les 6 heures si changement)
        self.scheduler.add_job(
            self._vigilance_check_post,
            IntervalTrigger(hours=6),
            id="vigilance_check",
            replace_existing=True
        )
        
        # Posts d'alerte critique (toutes les 30 minutes en cas d'alerte)
        self.scheduler.add_job(
            self._critical_alert_check,
            IntervalTrigger(minutes=30),
            id="critical_alert_check",
            replace_existing=True
        )
        
        # Nettoyage des anciens posts programmés
        self.scheduler.add_job(
            self._cleanup_old_scheduled_posts,
            CronTrigger(hour=1, minute=0),  # 1h00 tous les jours
            id="cleanup_scheduled_posts",
            replace_existing=True
        )
        
        logger.info("Scheduled jobs configured successfully")
    
    async def _daily_weather_morning_post(self):
        """Post météo matinal avec résumé de la journée"""
        try:
            logger.info("Executing daily morning weather post...")
            
            # Sélectionner une commune principale
            commune = 'Pointe-à-Pitre'  # Commune principale
            
            # Récupérer les données météo
            weather_data = await self.weather_service.get_weather_for_commune(commune)
            if not weather_data:
                logger.warning(f"No weather data available for {commune}")
                return
            
            # Récupérer les données de vigilance
            vigilance_data = await self.meteo_france_service.get_vigilance_data('guadeloupe')
            
            # Récupérer la prédiction IA
            try:
                coords = weather_data.coordinates
                from services.openweather_service import openweather_service
                severe_weather = await openweather_service.get_severe_weather_data(coords[0], coords[1])
                
                if severe_weather:
                    from data.communes_data import get_commune_info
                    commune_info = get_commune_info(commune)
                    ai_prediction = self.cyclone_predictor.predict_damage(
                        weather_data=severe_weather['current'],
                        commune_info=commune_info
                    )
                else:
                    ai_prediction = None
                    
            except Exception as e:
                logger.warning(f"Could not get AI prediction for morning post: {e}")
                ai_prediction = None
            
            # Formater le post matinal
            content = self._format_morning_post(weather_data, vigilance_data, ai_prediction)
            
            # Poster sur les réseaux sociaux
            results = await self.social_media_service.post_to_all_platforms(content)
            
            logger.info(f"Morning weather post completed: {results}")
            
        except Exception as e:
            logger.error(f"Error in daily morning weather post: {e}")
    
    async def _daily_weather_evening_post(self):
        """Post météo du soir avec prévisions pour le lendemain"""
        try:
            logger.info("Executing daily evening weather post...")
            
            commune = 'Basse-Terre'  # Alterner avec une autre commune
            
            # Récupérer les données
            weather_data = await self.weather_service.get_weather_for_commune(commune)
            if not weather_data:
                return
            
            vigilance_data = await self.meteo_france_service.get_vigilance_data('guadeloupe')
            
            # Post du soir avec focus sur demain
            content = self._format_evening_post(weather_data, vigilance_data)
            
            results = await self.social_media_service.post_to_all_platforms(content)
            
            logger.info(f"Evening weather post completed: {results}")
            
        except Exception as e:
            logger.error(f"Error in daily evening weather post: {e}")
    
    async def _vigilance_check_post(self):
        """Vérifie les changements de vigilance et poste si nécessaire"""
        try:
            logger.info("Checking vigilance level changes...")
            
            # Récupérer la vigilance actuelle
            current_vigilance = await self.meteo_france_service.get_vigilance_data('guadeloupe')
            current_level = current_vigilance.get('color_level', 'vert')
            
            # Vérifier la dernière vigilance stockée
            last_vigilance = await self.db.vigilance_history.find_one(
                sort=[('timestamp', -1)]
            )
            
            last_level = last_vigilance.get('color_level', 'vert') if last_vigilance else 'vert'
            
            # Si changement de niveau, poster une alerte
            if current_level != last_level:
                logger.info(f"Vigilance change detected: {last_level} -> {current_level}")
                
                # Sauvegarder le nouveau niveau
                await self.db.vigilance_history.insert_one({
                    'color_level': current_level,
                    'vigilance_data': current_vigilance,
                    'timestamp': datetime.now(),
                    'previous_level': last_level
                })
                
                # Poster l'alerte de changement
                content = self._format_vigilance_change_post(current_vigilance, last_level, current_level)
                results = await self.social_media_service.post_to_all_platforms(content)
                
                logger.info(f"Vigilance change post completed: {results}")
            
        except Exception as e:
            logger.error(f"Error in vigilance check post: {e}")
    
    async def _critical_alert_check(self):
        """Vérifie les alertes critiques et poste en urgence"""
        try:
            # Récupérer la vigilance
            vigilance_data = await self.meteo_france_service.get_vigilance_data('guadeloupe')
            current_level = vigilance_data.get('color_level', 'vert')
            
            # Poster seulement si alerte rouge ou orange
            if current_level in ['rouge', 'orange']:
                
                # Vérifier qu'on n'a pas déjà posté récemment
                recent_alert = await self.db.social_posts.find_one({
                    'content': {'$regex': f'ALERTE.*{current_level.upper()}'},
                    'posted_at': {'$gte': datetime.now() - timedelta(hours=2)}
                })
                
                if not recent_alert:
                    content = self._format_critical_alert_post(vigilance_data)
                    results = await self.social_media_service.post_to_all_platforms(content)
                    
                    logger.info(f"Critical alert post completed: {results}")
            
        except Exception as e:
            logger.error(f"Error in critical alert check: {e}")
    
    async def _cleanup_old_scheduled_posts(self):
        """Nettoie les anciens posts programmés"""
        try:
            # Supprimer les posts programmés de plus de 7 jours
            cutoff_date = datetime.now() - timedelta(days=7)
            
            result = await self.db.scheduled_posts.delete_many({
                'created_at': {'$lt': cutoff_date},
                'status': {'$in': ['sent', 'failed']}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old scheduled posts")
            
        except Exception as e:
            logger.error(f"Error cleaning up scheduled posts: {e}")
    
    def _format_morning_post(self, weather_data: Dict, vigilance_data: Dict, ai_prediction: Optional[Dict]) -> str:
        """Formate le post matinal"""
        commune = weather_data.get('commune', 'Guadeloupe')
        temp = weather_data.get('temperature', 'N/A')
        
        vigilance_level = vigilance_data.get('color_level', 'vert')
        vigilance_emojis = {'vert': 'VERT', 'jaune': 'JAUNE', 'orange': 'ORANGE', 'rouge': 'ROUGE'}
        vigilance_text = vigilance_emojis.get(vigilance_level, 'VERT')
        
        content = f"Bonjour Guadeloupe ! \n\n"
        content += f"Météo ce matin à {commune}:\n"
        content += f"Température: {temp}°C\n"
        content += f"Vigilance: {vigilance_text}\n\n"
        
        if ai_prediction:
            risk_level = ai_prediction.get('risk_level', 'faible')
            content += f"Analyse IA: Risque {risk_level.upper()}\n\n"
        
        content += f"Passez une excellente journée !\n\n"
        content += f"#MétéoGuadeloupe #BonjourAntilles\n"
        content += f"{datetime.now().strftime('%H:%M - %d/%m/%Y')}"
        
        return content
    
    def _format_evening_post(self, weather_data: Dict, vigilance_data: Dict) -> str:
        """Formate le post du soir"""
        commune = weather_data.get('commune', 'Guadeloupe')
        temp = weather_data.get('temperature', 'N/A')
        
        vigilance_level = vigilance_data.get('color_level', 'vert')
        vigilance_emojis = {'vert': 'VERT', 'jaune': 'JAUNE', 'orange': 'ORANGE', 'rouge': 'ROUGE'}
        vigilance_text = vigilance_emojis.get(vigilance_level, 'VERT')
        
        content = f"Bonsoir Guadeloupe !\n\n"
        content += f"Météo ce soir à {commune}:\n"
        content += f"Température: {temp}°C\n"
        content += f"Vigilance: {vigilance_text}\n\n"
        
        # Conseils pour la nuit
        if vigilance_level == 'vert':
            content += f"Nuit tranquille en perspective\n"
        else:
            content += f"Restez vigilants cette nuit\n"
        
        content += f"\nBonne soirée !\n\n"
        content += f"#MétéoGuadeloupe #BonsoirAntilles\n"
        content += f"{datetime.now().strftime('%H:%M - %d/%m/%Y')}"
        
        return content
    
    def _format_vigilance_change_post(self, vigilance_data: Dict, old_level: str, new_level: str) -> str:
        """Formate un post de changement de vigilance"""
        content = f"CHANGEMENT DE VIGILANCE\n\n"
        content += f"{old_level.upper()} -> {new_level.upper()}\n\n"
        
        # Recommandations selon le niveau
        recommendations = vigilance_data.get('recommendations', [])
        if recommendations:
            content += f"Consignes:\n{recommendations[0]}\n\n"
        
        content += f"Restez informés et prudents !\n\n"
        content += f"#VigilanceMétéo #Guadeloupe #Sécurité\n"
        content += f"{datetime.now().strftime('%H:%M - %d/%m/%Y')}"
        
        return content
    
    def _format_critical_alert_post(self, vigilance_data: Dict) -> str:
        """Formate un post d'alerte critique"""
        level = vigilance_data.get('color_level', 'rouge')
        
        content = f"ALERTE MÉTÉO\n\n"
        content += f"VIGILANCE {level.upper()} EN COURS\n\n"
        
        # Risques actifs
        risks = vigilance_data.get('risks', [])
        if risks:
            content += f"Phénomenes:\n"
            for risk in risks[:2]:  # Max 2 risques
                content += f"• {risk.get('name', 'Phénomène dangereux')}\n"
            content += f"\n"
        
        # Consignes principales
        recommendations = vigilance_data.get('recommendations', [])
        if recommendations:
            content += f"CONSIGNES URGENTES:\n{recommendations[0]}\n\n"
        
        content += f"Suivez les consignes officielles\n"
        content += f"Restez informés en permanence\n\n"
        content += f"#AlerteMétéo #Urgence #Sécurité"
        
        return content
    
    async def schedule_custom_post(self, content: str, schedule_time: datetime, platforms: List[str] = None) -> str:
        """Programme un post personnalisé"""
        try:
            if platforms is None:
                platforms = ['twitter', 'facebook']
            
            # Générer un ID unique pour la tâche
            job_id = f"custom_post_{datetime.now().timestamp()}"
            
            # Ajouter la tâche au scheduler
            self.scheduler.add_job(
                self._execute_custom_post,
                'date',
                run_date=schedule_time,
                args=[content, platforms],
                id=job_id
            )
            
            # Enregistrer en base
            await self.db.scheduled_posts.insert_one({
                'job_id': job_id,
                'content': content,
                'platforms': platforms,
                'scheduled_time': schedule_time,
                'status': 'scheduled',
                'created_at': datetime.now(),
                'type': 'custom'
            })
            
            logger.info(f"Custom post scheduled with ID: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling custom post: {e}")
            raise
    
    async def _execute_custom_post(self, content: str, platforms: List[str]):
        """Exécute un post personnalisé programmé"""
        try:
            results = {}
            
            if 'twitter' in platforms and self.social_media_service.twitter_client:
                results['twitter'] = await self.social_media_service.post_to_twitter(content)
            
            if 'facebook' in platforms and self.social_media_service.facebook_client:
                results['facebook'] = await self.social_media_service.post_to_facebook(content)
            
            logger.info(f"Custom scheduled post executed: {results}")
            
        except Exception as e:
            logger.error(f"Error executing custom post: {e}")
    
    async def cancel_scheduled_post(self, job_id: str) -> bool:
        """Annule un post programmé"""
        try:
            # Supprimer du scheduler
            self.scheduler.remove_job(job_id)
            
            # Marquer comme annulé en base
            await self.db.scheduled_posts.update_one(
                {'job_id': job_id},
                {'$set': {'status': 'cancelled', 'cancelled_at': datetime.now()}}
            )
            
            logger.info(f"Scheduled post cancelled: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling scheduled post: {e}")
            return False
    
    async def get_scheduler_status(self) -> Dict:
        """Retourne le statut du planificateur"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            scheduled_count = await self.db.scheduled_posts.count_documents({'status': 'scheduled'})
            
            return {
                'is_running': self.is_running,
                'active_jobs': len(jobs),
                'jobs': jobs,
                'scheduled_posts_count': scheduled_count,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {
                'is_running': self.is_running,
                'error': str(e)
            }

# Instance globale (sera initialisée dans server.py)
social_post_scheduler = None