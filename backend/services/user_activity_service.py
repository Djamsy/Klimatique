"""
Service de gestion de l'activité utilisateur et des témoignages
Gère le compteur d'utilisateurs actifs et le système de témoignages
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from models import (
    Testimonial, 
    TestimonialRequest, 
    TestimonialResponse,
    ActiveUserSession,
    ActiveUsersResponse
)

class UserActivityService:
    def __init__(self):
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        self.client = MongoClient(mongo_url)
        self.db = self.client.weather_db
        self.testimonials_collection = self.db.testimonials
        self.active_users_collection = self.db.active_users
        
        # Index pour optimiser les requêtes
        self.active_users_collection.create_index("last_activity")
        self.active_users_collection.create_index("session_id", unique=True)
        self.testimonials_collection.create_index("created_at")
        self.testimonials_collection.create_index("approved")
        
        # Démarrer le nettoyage automatique
        asyncio.create_task(self._start_cleanup_task())
    
    # =============================================================================
    # GESTION UTILISATEURS ACTIFS
    # =============================================================================
    
    async def track_user_activity(self, session_id: str, ip_address: str = None, user_agent: str = None) -> bool:
        """Enregistre ou met à jour l'activité d'un utilisateur"""
        try:
            now = datetime.utcnow()
            
            # Mettre à jour ou créer la session
            result = self.active_users_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "last_activity": now,
                        "ip_address": ip_address,
                        "user_agent": user_agent
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            
            return True
            
        except Exception as e:
            print(f"Erreur tracking utilisateur: {e}")
            return False
    
    async def get_active_users_count(self, minutes_threshold: int = 5) -> ActiveUsersResponse:
        """Récupère le nombre d'utilisateurs actifs dans les X dernières minutes"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_threshold)
            
            count = self.active_users_collection.count_documents({
                "last_activity": {"$gte": cutoff_time}
            })
            
            return ActiveUsersResponse(
                active_count=count,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            print(f"Erreur comptage utilisateurs actifs: {e}")
            return ActiveUsersResponse(active_count=0)
    
    async def cleanup_inactive_sessions(self, hours_threshold: int = 1):
        """Supprime les sessions inactives anciennes"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
            
            result = self.active_users_collection.delete_many({
                "last_activity": {"$lt": cutoff_time}
            })
            
            print(f"Nettoyage sessions: {result.deleted_count} sessions supprimées")
            return result.deleted_count
            
        except Exception as e:
            print(f"Erreur nettoyage sessions: {e}")
            return 0
    
    # =============================================================================
    # GESTION TÉMOIGNAGES
    # =============================================================================
    
    async def submit_testimonial(self, testimonial_request: TestimonialRequest) -> Dict[str, Any]:
        """Soumet un nouveau témoignage"""
        try:
            # Créer le témoignage
            testimonial = Testimonial(
                name=testimonial_request.name or "Utilisateur anonyme",
                role=testimonial_request.role or "Utilisateur",
                commune=testimonial_request.commune,
                content=testimonial_request.content.strip(),
                rating=testimonial_request.rating,
                approved=True,  # Auto-approval pour le moment
                created_at=datetime.utcnow(),
                approved_at=datetime.utcnow()
            )
            
            # Insérer en base
            result = self.testimonials_collection.insert_one(testimonial.dict())
            
            if result.inserted_id:
                return {
                    "success": True,
                    "message": "Témoignage soumis avec succès",
                    "testimonial_id": testimonial.id
                }
            else:
                return {
                    "success": False,
                    "message": "Erreur lors de la soumission"
                }
                
        except Exception as e:
            print(f"Erreur soumission témoignage: {e}")
            return {
                "success": False,
                "message": f"Erreur technique: {str(e)}"
            }
    
    async def get_testimonials(self, limit: int = 6, approved_only: bool = True) -> TestimonialResponse:
        """Récupère les témoignages approuvés, limités en nombre"""
        try:
            # Critères de filtre
            filter_criteria = {}
            if approved_only:
                filter_criteria["approved"] = True
            
            # Récupérer les témoignages récents
            cursor = self.testimonials_collection.find(filter_criteria).sort("created_at", -1).limit(limit)
            testimonials_data = list(cursor)
            
            # Convertir en objets Testimonial
            testimonials = []
            for data in testimonials_data:
                # Supprimer l'_id de MongoDB pour éviter les erreurs de sérialisation
                if "_id" in data:
                    del data["_id"]
                testimonials.append(Testimonial(**data))
            
            # Compter le total
            total_count = self.testimonials_collection.count_documents(filter_criteria)
            
            return TestimonialResponse(
                testimonials=testimonials,
                total_count=total_count,
                displayed_count=len(testimonials)
            )
            
        except Exception as e:
            print(f"Erreur récupération témoignages: {e}")
            return TestimonialResponse(
                testimonials=[],
                total_count=0,
                displayed_count=0
            )
    
    async def moderate_testimonial(self, testimonial_id: str, approve: bool) -> Dict[str, Any]:
        """Modère un témoignage (approuver/rejeter)"""
        try:
            update_data = {
                "approved": approve
            }
            
            if approve:
                update_data["approved_at"] = datetime.utcnow()
            
            result = self.testimonials_collection.update_one(
                {"id": testimonial_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                action = "approuvé" if approve else "rejeté"
                return {
                    "success": True,
                    "message": f"Témoignage {action} avec succès"
                }
            else:
                return {
                    "success": False,
                    "message": "Témoignage non trouvé"
                }
                
        except Exception as e:
            print(f"Erreur modération témoignage: {e}")
            return {
                "success": False,
                "message": f"Erreur technique: {str(e)}"
            }
    
    async def delete_testimonial(self, testimonial_id: str) -> Dict[str, Any]:
        """Supprime un témoignage"""
        try:
            result = self.testimonials_collection.delete_one({"id": testimonial_id})
            
            if result.deleted_count > 0:
                return {
                    "success": True,
                    "message": "Témoignage supprimé avec succès"
                }
            else:
                return {
                    "success": False,
                    "message": "Témoignage non trouvé"
                }
                
        except Exception as e:
            print(f"Erreur suppression témoignage: {e}")
            return {
                "success": False,
                "message": f"Erreur technique: {str(e)}"
            }
    
    # =============================================================================
    # TÂCHES DE MAINTENANCE
    # =============================================================================
    
    async def _start_cleanup_task(self):
        """Démarre la tâche de nettoyage automatique"""
        while True:
            try:
                await asyncio.sleep(300)  # Toutes les 5 minutes
                await self.cleanup_inactive_sessions()
            except Exception as e:
                print(f"Erreur tâche de nettoyage: {e}")
                await asyncio.sleep(60)  # Réessayer dans 1 minute en cas d'erreur

# Instance globale du service
user_activity_service = None

async def get_user_activity_service() -> UserActivityService:
    """Retourne l'instance du service d'activité utilisateur"""
    global user_activity_service
    if user_activity_service is None:
        user_activity_service = UserActivityService()
    return user_activity_service