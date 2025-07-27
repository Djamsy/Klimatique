import re
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import logging

from models import (
    UserSubscription, SubscriptionRequest, ContactRequest, 
    UnsubscribeRequest, UserPreferences, AlertType, RiskLevel
)

logger = logging.getLogger(__name__)

class SubscriptionService:
    def __init__(self, db: AsyncIOMotorClient):
        self.db = db
        
    def _validate_email(self, email: str) -> bool:
        """Valide le format d'un email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_phone(self, phone: str) -> bool:
        """Valide le format d'un numéro de téléphone guadeloupéen"""
        if not phone:
            return True  # Téléphone optionnel
        
        # Formats acceptés: +590590XXXXXX, 0590XXXXXX, 590XXXXXX
        pattern = r'^(\+590|0590|590)[0-9]{6}$'
        return re.match(pattern, phone.replace(' ', '').replace('-', '')) is not None
    
    async def register_user(self, request: SubscriptionRequest) -> Dict[str, Any]:
        """Inscrit un nouvel utilisateur aux alertes"""
        logger.info(f"Registering new user: {request.email}")
        
        # Validation
        if not self._validate_email(request.email):
            return {"success": False, "error": "Format d'email invalide"}
        
        if request.phone and not self._validate_phone(request.phone):
            return {"success": False, "error": "Format de téléphone invalide"}
        
        if not request.communes:
            return {"success": False, "error": "Sélectionnez au moins une commune"}
        
        # Vérifie si l'utilisateur existe déjà
        existing = await self.db.user_subscriptions.find_one({"email": request.email})
        
        if existing:
            # Mise à jour des préférences
            preferences = UserPreferences(
                communes=request.communes,
                alert_types=request.alert_types,
                notification_email=True,
                notification_sms=bool(request.phone)
            )
            
            await self.db.user_subscriptions.update_one(
                {"email": request.email},
                {
                    "$set": {
                        "phone": request.phone,
                        "preferences": preferences.dict(),
                        "active": True
                    }
                }
            )
            
            logger.info(f"Updated existing subscription for {request.email}")
            return {"success": True, "message": "Préférences mises à jour avec succès", "existing_user": True}
        
        # Nouvel utilisateur
        preferences = UserPreferences(
            communes=request.communes,
            alert_types=request.alert_types,
            notification_email=True,
            notification_sms=bool(request.phone)
        )
        
        subscription = UserSubscription(
            email=request.email,
            phone=request.phone,
            preferences=preferences,
            verified_email=False,  # À implémenter: envoi email de vérification
            verified_phone=False
        )
        
        # Sauvegarde en base
        await self.db.user_subscriptions.insert_one(subscription.dict())
        
        # Met à jour les statistiques
        await self.db.api_usage.update_one(
            {"date": datetime.now().date().isoformat()},
            {"$inc": {"new_subscriptions": 1}},
            upsert=True
        )
        
        logger.info(f"Successfully registered new user: {request.email}")
        
        # TODO: Envoyer email de confirmation
        # await self._send_confirmation_email(subscription)
        
        return {
            "success": True, 
            "message": "Inscription réussie ! Vous recevrez les alertes météo selon vos préférences.",
            "subscription_id": subscription.id
        }
    
    async def handle_contact_request(self, request: ContactRequest) -> Dict[str, Any]:
        """Traite une demande de contact"""
        logger.info(f"New contact request from {request.email}, type: {request.type}")
        
        # Validation
        if not self._validate_email(request.email):
            return {"success": False, "error": "Format d'email invalide"}
        
        if not request.message or len(request.message.strip()) < 10:
            return {"success": False, "error": "Message trop court (minimum 10 caractères)"}
        
        # Sauvegarde la demande
        contact_data = {
            "id": str(uuid.uuid4()),
            "email": request.email,
            "message": request.message.strip(),
            "type": request.type,
            "created_at": datetime.utcnow(),
            "status": "pending"
        }
        
        await self.db.contact_requests.insert_one(contact_data)
        
        # Si c'est une demande d'accès bêta, inscription automatique
        if request.type == "beta_access":
            # Inscription aux alertes pour toutes les communes principales
            main_communes = ["Pointe-à-Pitre", "Basse-Terre", "Sainte-Anne", "Le Moule"]
            subscription_request = SubscriptionRequest(
                email=request.email,
                communes=main_communes,
                alert_types=[AlertType.CYCLONE, AlertType.FORTE_PLUIE, AlertType.INONDATION],
                message=request.message
            )
            
            registration_result = await self.register_user(subscription_request)
            
            return {
                "success": True,
                "message": "Demande d'accès bêta enregistrée ! Vous êtes maintenant inscrit aux alertes météo.",
                "beta_access": True,
                "subscription_result": registration_result
            }
        
        return {
            "success": True,
            "message": "Votre message a été envoyé avec succès. Nous vous répondrons rapidement."
        }
    
    async def unsubscribe_user(self, request: UnsubscribeRequest) -> Dict[str, Any]:
        """Désabonne un utilisateur"""
        logger.info(f"Unsubscribe request from {request.email}")
        
        # Validation
        if not self._validate_email(request.email):
            return {"success": False, "error": "Format d'email invalide"}
        
        # Vérifie si l'utilisateur existe
        user = await self.db.user_subscriptions.find_one({"email": request.email})
        
        if not user:
            return {"success": False, "error": "Aucun abonnement trouvé pour cet email"}
        
        # Désactivation de l'abonnement
        await self.db.user_subscriptions.update_one(
            {"email": request.email},
            {
                "$set": {
                    "active": False,
                    "unsubscribed_at": datetime.utcnow(),
                    "unsubscribe_reason": request.reason
                }
            }
        )
        
        logger.info(f"Successfully unsubscribed {request.email}")
        
        return {
            "success": True,
            "message": "Vous avez été désabonné avec succès. Vous ne recevrez plus d'alertes météo."
        }
    
    async def get_subscription_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques d'abonnement"""
        # Total abonnés actifs
        total_active = await self.db.user_subscriptions.count_documents({"active": True})
        
        # Répartition par communes
        pipeline = [
            {"$match": {"active": True}},
            {"$unwind": "$preferences.communes"},
            {"$group": {
                "_id": "$preferences.communes",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        commune_stats = await self.db.user_subscriptions.aggregate(pipeline).to_list(100)
        
        # Répartition par types d'alerte
        pipeline = [
            {"$match": {"active": True}},
            {"$unwind": "$preferences.alert_types"},
            {"$group": {
                "_id": "$preferences.alert_types",
                "count": {"$sum": 1}
            }}
        ]
        
        alert_type_stats = await self.db.user_subscriptions.aggregate(pipeline).to_list(100)
        
        # Inscriptions par jour (7 derniers jours)
        seven_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        pipeline = [
            {"$match": {
                "subscription_date": {"$gte": seven_days_ago},
                "active": True
            }},
            {"$group": {
                "_id": {
                    "year": {"$year": "$subscription_date"},
                    "month": {"$month": "$subscription_date"},
                    "day": {"$dayOfMonth": "$subscription_date"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        daily_stats = await self.db.user_subscriptions.aggregate(pipeline).to_list(100)
        
        # Statistiques notifications
        pipeline = [
            {"$match": {"active": True}},
            {"$group": {
                "_id": None,
                "total_notifications": {"$sum": "$notifications_sent"},
                "avg_notifications": {"$avg": "$notifications_sent"}
            }}
        ]
        
        notification_stats = await self.db.user_subscriptions.aggregate(pipeline).to_list(1)
        
        return {
            "total_active_subscribers": total_active,
            "commune_distribution": {item["_id"]: item["count"] for item in commune_stats},
            "alert_type_preferences": {item["_id"]: item["count"] for item in alert_type_stats},
            "daily_registrations": daily_stats,
            "notification_stats": notification_stats[0] if notification_stats else {"total_notifications": 0, "avg_notifications": 0}
        }
    
    async def get_subscribers_by_commune(self, commune: str) -> List[UserSubscription]:
        """Récupère tous les abonnés d'une commune"""
        subscribers = await self.db.user_subscriptions.find({
            "active": True,
            "preferences.communes": commune
        }).to_list(1000)
        
        return [UserSubscription(**sub) for sub in subscribers]
    
    async def update_user_preferences(self, email: str, new_preferences: UserPreferences) -> Dict[str, Any]:
        """Met à jour les préférences d'un utilisateur"""
        logger.info(f"Updating preferences for {email}")
        
        # Vérifie si l'utilisateur existe
        user = await self.db.user_subscriptions.find_one({"email": email, "active": True})
        
        if not user:
            return {"success": False, "error": "Utilisateur non trouvé"}
        
        # Mise à jour
        await self.db.user_subscriptions.update_one(
            {"email": email},
            {"$set": {"preferences": new_preferences.dict()}}
        )
        
        logger.info(f"Successfully updated preferences for {email}")
        
        return {
            "success": True,
            "message": "Préférences mises à jour avec succès"
        }
    
    async def get_user_subscription(self, email: str) -> Optional[UserSubscription]:
        """Récupère l'abonnement d'un utilisateur"""
        user = await self.db.user_subscriptions.find_one({"email": email})
        
        if user:
            return UserSubscription(**user)
        
        return None