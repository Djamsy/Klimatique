"""
Service de précalcul des prédictions IA
Calcule et stocke les prédictions pour toutes les communes toutes les heures
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pymongo import MongoClient
import os
import sys
import logging

# Ajouter le chemin parent pour importer les modules
sys.path.append('/app/backend')

from ai_models.cyclone_damage_predictor import CycloneDamagePredictor
from data.communes_data import COMMUNES_GUADELOUPE

# Convertir le dictionnaire en liste pour compatibilité
GUADELOUPE_COMMUNES = [
    {"name": name, **data} for name, data in COMMUNES_GUADELOUPE.items()
]

logger = logging.getLogger(__name__)

class AIPrecalculationService:
    def __init__(self):
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        self.client = MongoClient(mongo_url)
        self.db = self.client.weather_db
        
        # Collections pour les prédictions précalculées
        self.predictions_collection = self.db.ai_predictions
        self.global_risk_collection = self.db.ai_global_risk
        
        # Index pour optimiser les requêtes
        self.predictions_collection.create_index([("commune", 1), ("calculated_at", -1)])
        self.global_risk_collection.create_index("calculated_at", expireAfterSeconds=7200)  # 2h
        
        # Initialiser le modèle IA
        self.predictor = CycloneDamagePredictor()
        
        logger.info("AIPrecalculationService initialized")
    
    async def precalculate_all_predictions(self):
        """Précalcule toutes les prédictions pour toutes les communes"""
        try:
            logger.info("🤖 Début du précalcul IA pour toutes les communes...")
            start_time = datetime.utcnow()
            
            # Calculer les prédictions pour chaque commune
            predictions_data = []
            
            for i, commune in enumerate(GUADELOUPE_COMMUNES):
                try:
                    logger.info(f"📊 Calcul IA {i+1}/{len(GUADELOUPE_COMMUNES)}: {commune['name']}")
                    
                    # Prédictions de dommages
                    prediction_result = await self._calculate_commune_prediction(commune)
                    
                    # Timeline
                    timeline_result = await self._calculate_commune_timeline(commune)
                    
                    # Historique
                    historical_result = await self._calculate_commune_historical(commune)
                    
                    # Stocker dans la collection
                    prediction_document = {
                        "commune": commune['name'],
                        "coordinates": commune['coordinates'],
                        "prediction": prediction_result,
                        "timeline": timeline_result,
                        "historical": historical_result,
                        "calculated_at": start_time,
                        "expires_at": start_time + timedelta(hours=2)  # Expire dans 2h
                    }
                    
                    predictions_data.append(prediction_document)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur calcul pour {commune['name']}: {e}")
                    continue
            
            # Sauvegarder toutes les prédictions
            if predictions_data:
                # Supprimer les anciennes prédictions
                self.predictions_collection.delete_many({
                    "calculated_at": {"$lt": start_time}
                })
                
                # Insérer les nouvelles
                result = self.predictions_collection.insert_many(predictions_data)
                logger.info(f"✅ {len(result.inserted_ids)} prédictions sauvegardées")
            
            # Calculer le risque global
            await self._calculate_global_risk(start_time)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"🎯 Précalcul terminé en {duration:.2f}s")
            
            return {
                "success": True,
                "communes_processed": len(predictions_data),
                "duration_seconds": duration,
                "timestamp": start_time
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur précalcul global: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def _calculate_commune_prediction(self, commune):
        """Calcule les prédictions de dommages pour une commune"""
        try:
            # Simuler des conditions météo moyennes pour le précalcul
            weather_conditions = {
                'wind_speed': 45.0,  # km/h
                'pressure': 990.0,   # hPa  
                'temperature': 28.0, # °C
                'humidity': 75.0,    # %
                'precipitation': 15.0 # mm/h
            }
            
            damage_prediction = self.predictor.predict_damage(
                commune_name=commune['name'],
                coordinates=commune['coordinates'],
                weather_conditions=weather_conditions,
                population=commune.get('population', 10000)
            )
            
            return {
                "commune": commune['name'],
                "coordinates": commune['coordinates'],
                "damage_predictions": damage_prediction['damage_predictions'],
                "risk_level": damage_prediction['risk_level'],
                "confidence_score": damage_prediction['confidence_score'],
                "recommendations": damage_prediction['recommendations'],
                "weather_conditions": weather_conditions
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur prédiction {commune['name']}: {e}")
            return None
    
    async def _calculate_commune_timeline(self, commune):
        """Calcule la timeline de prédictions pour une commune"""
        try:
            timeline_data = {}
            
            # Générer une timeline H+0 à H+24
            for hour in range(0, 25, 6):  # Toutes les 6h
                hour_key = f"H+{hour}"
                
                # Progression du risque dans le temps
                risk_factor = min(1.0, hour / 12)  # Pic à H+12
                
                timeline_data[hour_key] = {
                    "commune": commune['name'],
                    "coordinates": commune['coordinates'],
                    "hour": hour,
                    "risk_evolution": {
                        "wind_risk": round(risk_factor * 65, 1),
                        "flood_risk": round(risk_factor * 45, 1),
                        "infrastructure_risk": round(risk_factor * 35, 1)
                    },
                    "recommended_actions": self._get_timeline_recommendations(hour, risk_factor)
                }
            
            return {
                "commune": commune['name'],
                "coordinates": commune['coordinates'],
                "timeline_predictions": timeline_data
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur timeline {commune['name']}: {e}")
            return None
    
    async def _calculate_commune_historical(self, commune):
        """Génère les données historiques pour une commune"""
        try:
            # Données historiques simulées basées sur la localisation
            historical_events = []
            
            # Événements majeurs de Guadeloupe
            major_events = [
                {"year": 2017, "name": "Ouragan Irma", "category": 5},
                {"year": 2020, "name": "Tempête Laura", "category": 2}, 
                {"year": 2019, "name": "Tempête Karen", "category": 1},
                {"year": 2010, "name": "Ouragan Earl", "category": 4},
                {"year": 1999, "name": "Ouragan Lenny", "category": 4}
            ]
            
            for event in major_events:
                # Impact basé sur la position géographique
                is_coastal = commune.get('type', '') == 'côtière'
                base_damage = 15 if is_coastal else 8
                
                historical_events.append({
                    "year": event["year"],
                    "event_name": event["name"],
                    "damage_type": "infrastructure",
                    "damage_percentage": base_damage + (event["category"] * 3),
                    "recovery_time_days": event["category"] * 30,
                    "economic_impact_euros": event["category"] * 2000000
                })
            
            return {
                "commune": commune['name'],
                "coordinates": commune['coordinates'],
                "historical_events": historical_events,
                "risk_factors": commune.get('riskFactors', []),
                "vulnerability_score": min(100, len(commune.get('riskFactors', [])) * 25)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur historique {commune['name']}: {e}")
            return None
    
    async def _calculate_global_risk(self, timestamp):
        """Calcule le risque global basé sur toutes les prédictions"""
        try:
            # Compter les communes par niveau de risque
            pipeline = [
                {"$match": {"calculated_at": timestamp}},
                {"$group": {
                    "_id": "$prediction.risk_level",
                    "count": {"$sum": 1},
                    "communes": {"$push": "$commune"}
                }}
            ]
            
            risk_counts = list(self.predictions_collection.aggregate(pipeline))
            
            # Calculer les statistiques
            high_risk_count = 0
            critical_risk_count = 0
            affected_communes = []
            
            for risk_group in risk_counts:
                risk_level = risk_group["_id"]
                count = risk_group["count"]
                communes = risk_group["communes"]
                
                if risk_level in ['élevé', 'critique']:
                    high_risk_count += count
                    affected_communes.extend(communes)
                    
                if risk_level == 'critique':
                    critical_risk_count += count
            
            # Déterminer le niveau de risque global
            total_communes = len(GUADELOUPE_COMMUNES)
            risk_percentage = (high_risk_count / total_communes) * 100
            
            if risk_percentage > 50:
                global_risk_level = "critique"
            elif risk_percentage > 25:
                global_risk_level = "élevé"
            elif risk_percentage > 10:
                global_risk_level = "modéré"
            else:
                global_risk_level = "faible"
            
            # Sauvegarder le risque global
            global_risk_doc = {
                "global_risk_level": global_risk_level,
                "affected_communes": affected_communes,
                "high_risk_count": high_risk_count,
                "critical_risk_count": critical_risk_count,
                "total_communes": total_communes,
                "risk_percentage": round(risk_percentage, 1),
                "regional_recommendations": self._get_regional_recommendations(global_risk_level),
                "calculated_at": timestamp,
                "last_analysis": timestamp
            }
            
            # Supprimer l'ancien et insérer le nouveau
            self.global_risk_collection.delete_many({})
            self.global_risk_collection.insert_one(global_risk_doc)
            
            logger.info(f"✅ Risque global calculé: {global_risk_level} ({risk_percentage:.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul risque global: {e}")
    
    def _get_timeline_recommendations(self, hour, risk_factor):
        """Génère des recommandations basées sur l'heure et le facteur de risque"""
        if hour == 0:
            return ["Vérifier les provisions d'urgence", "Sécuriser les objets extérieurs"]
        elif hour <= 6:
            return ["Éviter les déplacements non essentiels", "Surveiller les bulletins météo"]
        elif hour <= 12:
            return ["Rester à l'intérieur", "Éviter les zones inondables"]
        else:
            return ["Attendre les consignes officielles", "Vérifier l'état des infrastructures"]
    
    def _get_regional_recommendations(self, risk_level):
        """Génère des recommandations régionales"""
        recommendations = {
            "faible": [
                "Maintenir la surveillance météorologique",
                "Vérifier les systèmes d'alerte"
            ],
            "modéré": [
                "Préparer les plans d'évacuation",
                "Alerter les services d'urgence"
            ],
            "élevé": [
                "Activer les centres d'hébergement",
                "Mobiliser les équipes de secours"
            ],
            "critique": [
                "Déclencher l'état d'urgence",
                "Évacuation préventive des zones à risque"
            ]
        }
        return recommendations.get(risk_level, [])
    
    async def get_cached_prediction(self, commune_name: str):
        """Récupère une prédiction précalculée pour une commune"""
        try:
            # Chercher la prédiction la plus récente
            prediction = self.predictions_collection.find_one(
                {"commune": commune_name},
                sort=[("calculated_at", -1)]
            )
            
            if prediction and prediction['expires_at'] > datetime.utcnow():
                # Supprimer l'_id de MongoDB
                if '_id' in prediction:
                    del prediction['_id']
                return prediction['prediction']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération cache {commune_name}: {e}")
            return None
    
    async def get_cached_timeline(self, commune_name: str):
        """Récupère une timeline précalculée pour une commune"""
        try:
            prediction = self.predictions_collection.find_one(
                {"commune": commune_name},
                sort=[("calculated_at", -1)]
            )
            
            if prediction and prediction['expires_at'] > datetime.utcnow():
                if '_id' in prediction:
                    del prediction['_id']
                return prediction['timeline']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération timeline {commune_name}: {e}")
            return None
    
    async def get_cached_historical(self, commune_name: str):
        """Récupère les données historiques précalculées pour une commune"""
        try:
            prediction = self.predictions_collection.find_one(
                {"commune": commune_name},
                sort=[("calculated_at", -1)]
            )
            
            if prediction and prediction['expires_at'] > datetime.utcnow():
                if '_id' in prediction:
                    del prediction['_id']
                return prediction['historical']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération historique {commune_name}: {e}")
            return None
    
    async def get_cached_global_risk(self):
        """Récupère le risque global précalculé"""
        try:
            global_risk = self.global_risk_collection.find_one(
                {},
                sort=[("calculated_at", -1)]
            )
            
            if global_risk:
                if '_id' in global_risk:
                    del global_risk['_id']
                return global_risk
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération risque global: {e}")
            return None

# Instance globale
ai_precalculation_service = None

async def get_ai_precalculation_service():
    """Retourne l'instance du service de précalcul IA"""
    global ai_precalculation_service
    if ai_precalculation_service is None:
        ai_precalculation_service = AIPrecalculationService()
    return ai_precalculation_service