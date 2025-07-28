"""
Scheduler pour les calculs IA automatiques
Lance les précalculs de prédictions toutes les heures
"""

import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.ai_precalculation_service import get_ai_precalculation_service

logger = logging.getLogger(__name__)

class AIScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.ai_service = None
        self.is_running = False
        
    async def start(self):
        """Démarre le scheduler"""
        try:
            if self.is_running:
                logger.warning("Scheduler déjà en cours d'exécution")
                return
            
            # Initialiser le service IA
            self.ai_service = await get_ai_precalculation_service()
            
            # Programmer les tâches
            # 1. Précalcul IA toutes les heures
            self.scheduler.add_job(
                self._run_ai_precalculation,
                trigger=IntervalTrigger(hours=1),
                id='ai_precalculation',
                name='Précalcul IA Cyclonique',
                max_instances=1,  # Une seule instance à la fois
                coalesce=True,    # Fusionner les exécutions en attente
                misfire_grace_time=300  # 5 minutes de grâce
            )
            
            # 2. Calcul initial au démarrage (avec délai)
            self.scheduler.add_job(
                self._run_initial_calculation,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=30),
                id='initial_ai_calculation',
                name='Calcul IA Initial'
            )
            
            # 3. Nettoyage des anciennes données (quotidien)
            self.scheduler.add_job(
                self._cleanup_old_data,
                trigger='cron',
                hour=2,  # 2h du matin
                id='cleanup_ai_data',
                name='Nettoyage données IA'
            )
            
            # Démarrer le scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("✅ AI Scheduler démarré avec succès")
            logger.info("📊 Prochains calculs IA programmés toutes les heures")
            
        except Exception as e:
            logger.error(f"❌ Erreur démarrage AI Scheduler: {e}")
            raise
    
    async def stop(self):
        """Arrête le scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("✅ AI Scheduler arrêté")
        except Exception as e:
            logger.error(f"❌ Erreur arrêt scheduler: {e}")
    
    async def _run_ai_precalculation(self):
        """Exécute le précalcul IA"""
        try:
            logger.info("🤖 Début du précalcul IA programmé...")
            start_time = datetime.utcnow()
            
            # Lancer le précalcul
            result = await self.ai_service.precalculate_all_predictions()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            if result['success']:
                logger.info(f"✅ Précalcul IA terminé: {result['communes_processed']} communes en {duration:.2f}s")
            else:
                logger.error(f"❌ Erreur précalcul IA: {result.get('error', 'Erreur inconnue')}")
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du précalcul IA: {e}")
    
    async def _run_initial_calculation(self):
        """Lance le premier calcul au démarrage"""
        try:
            logger.info("🚀 Lancement du calcul IA initial...")
            await self._run_ai_precalculation()
            
            # Supprimer cette tâche unique après exécution
            if self.scheduler.get_job('initial_ai_calculation'):
                self.scheduler.remove_job('initial_ai_calculation')
                
        except Exception as e:
            logger.error(f"❌ Erreur calcul initial: {e}")
    
    async def _cleanup_old_data(self):
        """Nettoie les anciennes données IA"""
        try:
            logger.info("🧹 Nettoyage des anciennes données IA...")
            
            # Supprimer les prédictions expirées (plus de 3 heures)
            cutoff_time = datetime.utcnow() - timedelta(hours=3)
            
            predictions_deleted = self.ai_service.predictions_collection.delete_many({
                "expires_at": {"$lt": cutoff_time}
            })
            
            logger.info(f"🗑️ {predictions_deleted.deleted_count} anciennes prédictions supprimées")
            
        except Exception as e:
            logger.error(f"❌ Erreur nettoyage: {e}")
    
    def get_scheduler_status(self):
        """Retourne le statut du scheduler"""
        try:
            jobs_info = []
            
            for job in self.scheduler.get_jobs():
                jobs_info.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
            
            return {
                "running": self.is_running,
                "scheduler_running": self.scheduler.running if hasattr(self, 'scheduler') else False,
                "jobs": jobs_info,
                "status_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "running": False,
                "error": str(e),
                "status_time": datetime.utcnow().isoformat()
            }
    
    async def trigger_manual_calculation(self):
        """Lance un calcul IA manuel"""
        try:
            logger.info("🎯 Calcul IA manuel déclenché")
            result = await self._run_ai_precalculation()
            return {"success": True, "message": "Calcul IA lancé manuellement"}
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul manuel: {e}")
            return {"success": False, "error": str(e)}

# Instance globale
ai_scheduler = AIScheduler()

async def start_ai_scheduler():
    """Démarre le scheduler IA"""
    await ai_scheduler.start()

async def stop_ai_scheduler():
    """Arrête le scheduler IA"""
    await ai_scheduler.stop()

def get_ai_scheduler():
    """Retourne l'instance du scheduler"""
    return ai_scheduler