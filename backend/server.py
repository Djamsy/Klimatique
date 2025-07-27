from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Import models et services
from models import (
    WeatherResponse, WeatherConfig, SubscriptionRequest, ContactRequest,
    UnsubscribeRequest, SatelliteImageRequest, AlertResponse, APIUsageStats,
    RiskLevel, AlertType
)
from services.weather_cache_service import WeatherCacheService
from services.weather_service import WeatherService
from services.alert_service import AlertService
from services.subscription_service import SubscriptionService

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configuration météo
config = WeatherConfig()

# Services
weather_cache_service = WeatherCacheService(db, config)
weather_service = WeatherService(db, weather_cache_service, config)
alert_service = AlertService(db)
subscription_service = SubscriptionService(db)

# Create the main app
app = FastAPI(title="Météo Sentinelle API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# ENDPOINTS MÉTÉO
# =============================================================================

@api_router.get("/weather/{commune}", response_model=WeatherResponse)
async def get_weather_by_commune(commune: str):
    """Récupère la météo d'une commune (depuis cache optimisé)"""
    try:
        weather = await weather_service.get_weather_for_commune(commune)
        
        if not weather:
            raise HTTPException(status_code=404, detail=f"Météo non disponible pour {commune}")
            
        return weather
    except Exception as e:
        logger.error(f"Error getting weather for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.get("/weather/multiple/{communes}")
async def get_weather_multiple_communes(communes: str):
    """Récupère la météo pour plusieurs communes (séparées par virgules)"""
    try:
        commune_list = [c.strip() for c in communes.split(',')]
        
        if len(commune_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 communes par requête")
        
        weather_data = await weather_service.get_weather_for_multiple_communes(commune_list)
        return weather_data
    except Exception as e:
        logger.error(f"Error getting weather for multiple communes: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.get("/weather/stats")
async def get_weather_statistics():
    """Récupère les statistiques météorologiques globales"""
    try:
        stats = await weather_service.get_weather_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting weather stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

# =============================================================================
# ENDPOINTS SATELLITE NASA
# =============================================================================

@api_router.post("/satellite/image")
async def get_satellite_image(request: SatelliteImageRequest):
    """Récupère une image satellite depuis NASA GIBS"""
    try:
        satellite_image = await weather_service.get_satellite_image(request)
        
        if not satellite_image:
            raise HTTPException(status_code=404, detail="Image satellite non disponible")
            
        return satellite_image
    except Exception as e:
        logger.error(f"Error getting satellite image: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.get("/satellite/layers")
async def get_satellite_layers():
    """Récupère les couches satellite disponibles"""
    try:
        layers = await weather_service.get_satellite_layers_available()
        return layers
    except Exception as e:
        logger.error(f"Error getting satellite layers: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

# =============================================================================
# ENDPOINTS ALERTES
# =============================================================================

@api_router.get("/alerts", response_model=AlertResponse)
async def get_active_alerts():
    """Récupère toutes les alertes météo actives en Guadeloupe"""
    try:
        alerts = await weather_service.get_regional_alerts()
        
        # Statistiques par sévérité
        by_severity = {}
        for alert in alerts:
            severity = alert.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return AlertResponse(
            alerts=alerts,
            total_active=len(alerts),
            by_severity=by_severity,
            last_updated=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.get("/alerts/{commune}")
async def get_alerts_by_commune(commune: str):
    """Récupère les alertes actives pour une commune spécifique"""
    try:
        alerts = await weather_service.get_active_alerts_for_commune(commune)
        return {"commune": commune, "alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"Error getting alerts for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

# =============================================================================
# ENDPOINTS ABONNEMENTS
# =============================================================================

@api_router.post("/subscribe")
async def subscribe_user(request: SubscriptionRequest):
    """Inscription d'un utilisateur aux alertes météo"""
    try:
        result = await subscription_service.register_user(request)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing user: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.post("/contact")
async def handle_contact(request: ContactRequest):
    """Traite une demande de contact/accès bêta"""
    try:
        result = await subscription_service.handle_contact_request(request)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling contact: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.post("/unsubscribe")
async def unsubscribe_user(request: UnsubscribeRequest):
    """Désabonne un utilisateur des alertes"""
    try:
        result = await subscription_service.unsubscribe_user(request)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing user: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.get("/subscribers/stats")
async def get_subscription_statistics():
    """Récupère les statistiques d'abonnement"""
    try:
        stats = await subscription_service.get_subscription_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting subscription stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

# =============================================================================
# ENDPOINTS CONFIGURATION & UTILITAIRES
# =============================================================================

@api_router.get("/config/communes")
async def get_communes_list():
    """Récupère la liste des communes de Guadeloupe"""
    return {
        "communes": config.communes_guadeloupe,
        "total": len(config.communes_guadeloupe),
        "bbox": config.guadeloupe_bbox
    }

@api_router.get("/config/alert-types")
async def get_alert_types():
    """Récupère les types d'alertes disponibles"""
    return {
        "alert_types": [
            {"value": AlertType.CYCLONE, "label": "Cyclone"},
            {"value": AlertType.INONDATION, "label": "Inondation"},
            {"value": AlertType.FORTE_PLUIE, "label": "Fortes pluies"},
            {"value": AlertType.VENT_FORT, "label": "Vents forts"},
            {"value": AlertType.HOULE, "label": "Forte houle"}
        ],
        "risk_levels": [
            {"value": RiskLevel.FAIBLE, "label": "Faible", "color": "#22c55e"},
            {"value": RiskLevel.MODERE, "label": "Modéré", "color": "#f59e0b"},
            {"value": RiskLevel.ELEVE, "label": "Élevé", "color": "#ea580c"},
            {"value": RiskLevel.CRITIQUE, "label": "Critique", "color": "#dc2626"}
        ]
    }

@api_router.get("/status")
async def get_api_status():
    """Status de l'API et statistiques d'usage"""
    try:
        # Usage API aujourd'hui
        usage_stats = await weather_cache_service.get_daily_usage_stats()
        
        # Limite quotidienne
        calls_remaining = max(0, config.daily_call_limit - usage_stats.openweather_calls)
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow(),
            "api_usage": {
                "openweather_calls_today": usage_stats.openweather_calls,
                "calls_remaining": calls_remaining,
                "daily_limit": config.daily_call_limit,
                "cache_efficiency": round(usage_stats.cache_hits / max(usage_stats.cache_hits + usage_stats.cache_misses, 1) * 100, 1)
            },
            "services": {
                "weather_cache": "active",
                "nasa_satellite": "active", 
                "alert_system": "active",
                "subscriptions": "active"
            }
        }
    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }

# =============================================================================
# ENDPOINTS LEGACY (compatibilité avec le frontend existant)
# =============================================================================

@api_router.get("/")
async def root():
    """Endpoint de base pour compatibilité"""
    return {
        "message": "Météo Sentinelle API - Protection météorologique pour la Guadeloupe",
        "version": "1.0.0",
        "services": ["weather", "alerts", "satellite", "subscriptions"]
    }

@api_router.get("/hello")
async def hello():
    """Endpoint de test"""
    return {"message": "Hello from Météo Sentinelle!"}

# =============================================================================
# TÂCHES DE FOND
# =============================================================================

async def background_weather_update():
    """Tâche de fond pour mise à jour météo périodique"""
    while True:
        try:
            logger.info("Starting background weather update")
            
            # Met à jour toutes les communes
            await weather_cache_service.update_all_communes_weather()
            
            # Traite les alertes automatiques
            alerts_generated = await weather_service.process_weather_alerts_from_cache()
            
            # Nettoie les alertes expirées
            expired_cleaned = await alert_service.cleanup_expired_alerts()
            
            logger.info(f"Background update completed: {alerts_generated} alerts generated, {expired_cleaned} expired alerts cleaned")
            
            # Détermine la prochaine fréquence de mise à jour
            next_update_minutes = await weather_cache_service.adaptive_update_frequency()
            
            # Attente avant prochaine mise à jour
            await asyncio.sleep(next_update_minutes * 60)
            
        except Exception as e:
            logger.error(f"Error in background weather update: {e}")
            # En cas d'erreur, attente de 10 minutes avant retry
            await asyncio.sleep(600)

# =============================================================================
# APPLICATION SETUP
# =============================================================================

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    logger.info("Starting Météo Sentinelle API")
    
    # Démarre la tâche de fond pour les mises à jour météo
    asyncio.create_task(background_weather_update())
    
    logger.info("Météo Sentinelle API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("Shutting down Météo Sentinelle API")
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)