from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager

# Import models et services
from models import (
    WeatherResponse, WeatherConfig, SubscriptionRequest, ContactRequest,
    UnsubscribeRequest, SatelliteImageRequest, AlertResponse, APIUsageStats,
    RiskLevel, AlertType, CycloneAIResponse, CycloneTimelinePrediction,
    CommuneHistoricalResponse, GlobalCycloneRisk, CycloneDamagePrediction,
    SocialPlatform, SocialCredentialsRequest, SocialCredentialsResponse,
    SocialPostRequest, SocialPostResponse, ScheduledPostRequest,
    ScheduledPostResponse, SocialStatsResponse, TestimonialRequest,
    TestimonialResponse, ActiveUsersResponse
)
from services.ai_precalculation_service import get_ai_precalculation_service
from services.ai_scheduler import start_ai_scheduler, get_ai_scheduler
from services.weather_cache_service import WeatherCacheService
from services.weather_service import WeatherService
from services.alert_service import AlertService
from services.subscription_service import SubscriptionService
from services.openweather_service import openweather_service
from services.meteo_france_service import meteo_france_service
from services.vigilance_alternative_service import vigilance_alternative_service
from services.weather_cache_optimizer import weather_cache_optimizer
from ai_models.cyclone_damage_predictor import cyclone_predictor
from data.communes_data import get_commune_info, get_all_communes

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

# Initialisation des services sociaux et backup (sera fait au démarrage)
social_media_service = None
social_post_scheduler = None
weather_backup_service = None
user_activity_service = None
ai_precalculation_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    logger.info("Starting Météo Sentinelle application...")
    
    # Initialiser les services sociaux et backup
    try:
        global social_media_service, social_post_scheduler, weather_backup_service, user_activity_service, ai_precalculation_service
        
        from services.social_media_service import SocialMediaService
        from services.social_post_scheduler import SocialPostScheduler
        from services.weather_backup_service import WeatherBackupService
        from services.user_activity_service import get_user_activity_service
        
        # Service de backup météo
        weather_backup_service = WeatherBackupService(db)
        
        # Service d'activité utilisateur
        user_activity_service = await get_user_activity_service()
        
        # Service IA précalculation
        ai_precalculation_service = await get_ai_precalculation_service()
        
        # Services sociaux
        social_media_service = SocialMediaService(db)
        social_post_scheduler = SocialPostScheduler(
            db=db,
            weather_service=weather_service,
            social_media_service=social_media_service,
            meteo_france_service=meteo_france_service,
            cyclone_predictor=cyclone_predictor
        )
        
        # Démarrer le scheduler IA
        await start_ai_scheduler()
        
        # Mettre à jour les services globaux
        import services.social_media_service as sms_module
        import services.social_post_scheduler as sps_module
        import services.weather_backup_service as wbs_module
        import services.user_activity_service as uas_module
        import services.ai_precalculation_service as aips_module
        
        sms_module.social_media_service = social_media_service
        sps_module.social_post_scheduler = social_post_scheduler
        wbs_module.weather_backup_service = weather_backup_service
        uas_module.user_activity_service = user_activity_service
        aips_module.ai_precalculation_service = ai_precalculation_service
        
        logger.info("Social media, backup, user activity and AI services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
    
    # Démarrer le scheduler météo
    try:
        from services.weather_scheduler import weather_scheduler
        await weather_scheduler.start_scheduler()
        logger.info("Weather scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start weather scheduler: {e}")
    
    # Démarrer le scheduler social (optionnel - peut être activé via API)
    try:
        # await social_post_scheduler.start_scheduler()
        # logger.info("Social post scheduler started successfully")
        pass
    except Exception as e:
        logger.error(f"Failed to start social post scheduler: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Météo Sentinelle application...")
    
    # Arrêter le scheduler météo
    try:
        from services.weather_scheduler import weather_scheduler  
        await weather_scheduler.stop_scheduler()
        logger.info("Weather scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop weather scheduler: {e}")
    
    # Arrêter le scheduler social
    try:
        if social_post_scheduler and social_post_scheduler.is_running:
            await social_post_scheduler.stop_scheduler()
            logger.info("Social post scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop social post scheduler: {e}")

# Create the main app
app = FastAPI(
    title="Météo Sentinelle - Guadeloupe Weather API",
    description="API météorologique avancée pour la Guadeloupe avec IA prédictive",
    version="2.0.0",
    lifespan=lifespan
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
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

# Démarrer le cache optimizer au démarrage
@app.on_event("startup")
async def startup_event():
    """Démarre les services au démarrage de l'application"""
    await weather_cache_optimizer.start_background_refresh()
    logger.info("Weather cache optimizer started")

@app.on_event("shutdown")
async def shutdown_event():
    """Arrête les services à la fermeture de l'application"""
    await weather_cache_optimizer.stop()
    logger.info("Weather cache optimizer stopped")

# =============================================================================
# ENDPOINTS CACHE ET OPTIMISATION
# =============================================================================

@api_router.get("/cache/stats")
async def get_cache_stats():
    """Récupère les statistiques du cache et de l'usage API"""
    try:
        stats = await weather_cache_optimizer.get_api_usage_stats()
        return {
            "cache_stats": stats,
            "cache_efficiency": {
                "daily_limit": stats.get('daily_limit', 1000),
                "today_usage": stats.get('today_usage', 0),
                "efficiency_percent": stats.get('efficiency', 0),
                "remaining_calls": stats.get('daily_limit', 1000) - stats.get('today_usage', 0)
            },
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur statistiques cache")

@api_router.get("/weather/cached/{commune}")
async def get_cached_weather(commune: str):
    """Récupère les données météo depuis le cache"""
    try:
        cached_data = await weather_cache_optimizer.get_cached_data(f'weather_{commune}')
        
        if not cached_data:
            raise HTTPException(status_code=404, detail="Données non disponibles en cache")
        
        return {
            "commune": commune,
            "data": cached_data,
            "source": "cache",
            "cached": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cached weather for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur cache météo")

# =============================================================================
# ENDPOINTS OVERLAYS MÉTÉO (NUAGES, PLUIE, RADAR)
# =============================================================================

@api_router.get("/weather/overlay/clouds")
async def get_clouds_overlay():
    """Récupère l'overlay des nuages pour la carte"""
    try:
        # Récupérer directement depuis l'API avec nouvelle méthode
        center_lat, center_lon = 16.25, -61.55
        clouds_data = await openweather_service.get_weather_map_data(center_lat, center_lon, 'clouds_new', 8)
        
        if not clouds_data:
            raise HTTPException(status_code=503, detail="Service nuages temporairement indisponible")
        
        return {
            "overlay_type": "clouds",
            "data": clouds_data,
            "source": "api_direct"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clouds overlay: {e}")
        raise HTTPException(status_code=500, detail="Erreur overlay nuages")

@api_router.get("/weather/overlay/precipitation")
async def get_precipitation_overlay():
    """Récupère l'overlay des précipitations pour la carte"""
    try:
        # Vérifier le cache d'abord
        cached_data = await weather_cache_optimizer.get_cached_data('satellite_guadeloupe')
        
        if cached_data and 'precipitation' in cached_data:
            return {
                "overlay_type": "precipitation",
                "data": cached_data['precipitation'],
                "source": "cache"
            }
        
        # Si pas en cache, récupérer depuis l'API
        center_lat, center_lon = 16.25, -61.55
        precip_data = await openweather_service.get_weather_map_data(center_lat, center_lon, 'precipitation_new', 8)
        
        if not precip_data:
            raise HTTPException(status_code=503, detail="Service précipitations temporairement indisponible")
        
        return {
            "overlay_type": "precipitation",
            "data": precip_data,
            "source": "api"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting precipitation overlay: {e}")
        raise HTTPException(status_code=500, detail="Erreur overlay précipitations")

@api_router.get("/weather/overlay/radar")
async def get_radar_overlay():
    """Récupère l'overlay radar pour la carte"""
    try:
        # Vérifier le cache d'abord
        cached_data = await weather_cache_optimizer.get_cached_data('satellite_guadeloupe')
        
        if cached_data and 'radar' in cached_data:
            return {
                "overlay_type": "radar",
                "data": cached_data['radar'],
                "source": "cache"
            }
        
        # Si pas en cache, récupérer depuis l'API
        center_lat, center_lon = 16.25, -61.55
        radar_data = await openweather_service.get_weather_map_data(center_lat, center_lon, 'radar', 8)
        
        if not radar_data:
            raise HTTPException(status_code=503, detail="Service radar temporairement indisponible")
        
        return {
            "overlay_type": "radar",
            "data": radar_data,
            "source": "api"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting radar overlay: {e}")
        raise HTTPException(status_code=500, detail="Erreur overlay radar")

@api_router.get("/weather/precipitation/forecast")
async def get_precipitation_forecast():
    """Récupère les prévisions de précipitations pour les prochaines heures"""
    try:
        center_lat, center_lon = 16.25, -61.55
        forecast_data = await openweather_service.get_precipitation_forecast(center_lat, center_lon, 12)
        
        if not forecast_data:
            raise HTTPException(status_code=503, detail="Service prévisions indisponible")
        
        return {
            "location": "Guadeloupe",
            "forecast": forecast_data,
            "type": "precipitation"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting precipitation forecast: {e}")
        raise HTTPException(status_code=500, detail="Erreur prévisions précipitations")

@api_router.get("/weather/pluviometer/{commune}")
async def get_pluviometer_data(commune: str):
    """Récupère les données pluviométriques pour une commune"""
    try:
        commune_info = get_commune_info(commune)
        coords = commune_info['coordinates']
        
        # Récupérer les données actuelles et les prévisions
        current_data = await openweather_service.get_current_and_forecast(coords[0], coords[1])
        precip_forecast = await openweather_service.get_precipitation_forecast(coords[0], coords[1], 24)
        
        if not current_data:
            raise HTTPException(status_code=503, detail="Données pluviométriques indisponibles")
        
        # Traitement des données pluviométriques
        current_precip = current_data.get('current', {}).get('rain', {}).get('1h', 0)
        
        pluviometer_data = {
            'commune': commune,
            'coordinates': coords,
            'current': {
                'precipitation': current_precip,
                'intensity': get_precipitation_intensity(current_precip),
                'description': get_precipitation_description(current_precip)
            },
            'forecast': precip_forecast['forecast'] if precip_forecast else [],
            'daily_total': sum([item.get('precipitation', 0) for item in (precip_forecast['forecast'] if precip_forecast else [])[:24]]),
            'peak_hour': max((precip_forecast['forecast'] if precip_forecast else [])[:24], key=lambda x: x.get('precipitation', 0), default={}),
            'last_updated': current_data.get('current', {}).get('dt', 0)
        }
        
        return pluviometer_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pluviometer data for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur données pluviométriques")

def get_precipitation_intensity(precip_mm: float) -> str:
    """Détermine l'intensité des précipitations"""
    if precip_mm == 0:
        return "nulle"
    elif precip_mm < 1:
        return "faible"
    elif precip_mm < 4:
        return "modérée"
    elif precip_mm < 10:
        return "forte"
    else:
        return "très forte"

def get_precipitation_description(precip_mm: float) -> str:
    """Description des précipitations"""
    intensity = get_precipitation_intensity(precip_mm)
    descriptions = {
        "nulle": "Pas de précipitation",
        "faible": "Pluie fine",
        "modérée": "Pluie modérée",
        "forte": "Pluie forte",
        "très forte": "Pluie torrentielle"
    }
    return descriptions.get(intensity, "Précipitation")

# =============================================================================
# ENDPOINTS VIGILANCES MÉTÉO FRANCE
# =============================================================================

@api_router.get("/vigilance/guadeloupe")
async def get_vigilance_guadeloupe():
    """Récupère les données de vigilance officielle Météo France pour la Guadeloupe"""
    try:
        vigilance_data = await meteo_france_service.get_vigilance_data('guadeloupe')
        return vigilance_data
    except Exception as e:
        logger.error(f"Error getting vigilance data: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération vigilance")

@api_router.get("/vigilance/theme")
async def get_vigilance_theme():
    """Récupère les couleurs et thème adaptatif basé sur la vigilance"""
    try:
        vigilance_data = await meteo_france_service.get_vigilance_data('guadeloupe')
        
        # Génération du thème adaptatif
        theme = {
            'primary_color': vigilance_data['color_info']['color'],
            'level': vigilance_data['color_level'],
            'level_name': vigilance_data['color_info']['name'],
            'risk_score': vigilance_data['global_risk_score'],
            'header_class': f"bg-{vigilance_data['color_level']}-gradient",
            'badge_class': f"badge-{vigilance_data['color_level']}",
            'alert_class': f"alert-{vigilance_data['color_level']}",
            'risks': vigilance_data['risks'],
            'recommendations': vigilance_data['recommendations']
        }
        
        return theme
    except Exception as e:
        logger.error(f"Error getting vigilance theme: {e}")
        raise HTTPException(status_code=500, detail="Erreur thème vigilance")

@api_router.get("/vigilance/recommendations")
async def get_vigilance_recommendations():
    """Récupère les recommandations officielles basées sur la vigilance"""
    try:
        vigilance_data = await vigilance_alternative_service.get_enhanced_vigilance_data('guadeloupe')
        
        return {
            'vigilance_level': vigilance_data['color_level'],
            'recommendations': vigilance_data['recommendations'],
            'risks': vigilance_data['risks'],
            'official_source': vigilance_data.get('source', 'Enhanced Service'),
            'valid_from': vigilance_data['valid_from'],
            'valid_until': vigilance_data['valid_until'],
            'last_updated': vigilance_data['last_updated'],
            'is_fallback': vigilance_data.get('is_fallback', False)
        }
    except Exception as e:
        logger.error(f"Error getting vigilance recommendations: {e}")
        raise HTTPException(status_code=500, detail="Erreur recommandations vigilance")

@api_router.get("/vigilance/{departement}")
async def get_vigilance_data(departement: str):
    """Récupère les données de vigilance météorologique avec sources alternatives"""
    try:
        # Essayer d'abord le service alternatif (OpenWeatherMap + fallback intelligent)
        vigilance_data = await vigilance_alternative_service.get_enhanced_vigilance_data(departement)
        
        if vigilance_data:
            logger.info(f"Vigilance data retrieved from alternative service for {departement}")
            return vigilance_data
        
        # Fallback vers le service Météo France officiel
        logger.info("Trying official Météo France service")
        vigilance_data = await meteo_france_service.get_vigilance_data(departement)
        
        return vigilance_data
        
    except Exception as e:
        logger.error(f"Error getting vigilance data for {departement}: {e}")
        # Dernier recours : données de fallback
        return await vigilance_alternative_service._generate_enhanced_fallback_data()

# =============================================================================
# ENDPOINTS IA PRÉDICTIVE CYCLONIQUE
# =============================================================================

@api_router.get("/ai/cyclone/predict/{commune}")
async def get_cyclone_prediction(commune: str):
    """Prédiction IA des dommages cycloniques pour une commune (données précalculées)"""
    try:
        logger.info(f"🤖 Récupération prédiction IA précalculée pour {commune}")
        
        if not ai_precalculation_service:
            raise HTTPException(status_code=503, detail="Service IA non disponible")
        
        # Tenter de récupérer depuis le cache
        cached_prediction = await ai_precalculation_service.get_cached_prediction(commune)
        
        if cached_prediction:
            logger.info(f"✅ Prédiction trouvée en cache pour {commune}")
            return cached_prediction
        
        # Fallback: calcul en temps réel si pas de cache
        logger.warning(f"⚠️ Pas de cache pour {commune}, calcul en temps réel")
        
        # Trouver les données de la commune
        commune_data = None
        from data.communes_data import COMMUNES_GUADELOUPE
        
        # Chercher dans le dictionnaire des communes
        if commune in COMMUNES_GUADELOUPE:
            commune_data = {
                "name": commune,
                "coordinates": COMMUNES_GUADELOUPE[commune]["coordinates"],
                "population": COMMUNES_GUADELOUPE[commune].get("population", 10000),
                "type": COMMUNES_GUADELOUPE[commune].get("type", "urbaine")
            }
        else:
            # Chercher par nom (insensible à la casse)
            for commune_name, data in COMMUNES_GUADELOUPE.items():
                if commune_name.lower() == commune.lower():
                    commune_data = {
                        "name": commune_name,
                        "coordinates": data["coordinates"],
                        "population": data.get("population", 10000),
                        "type": data.get("type", "urbaine")
                    }
                    break
        
        if not commune_data:
            raise HTTPException(status_code=404, detail="Commune non trouvée")
        
        # Conditions météo par défaut pour le fallback
        weather_conditions = {
            'wind_speed': 45.0,
            'pressure': 990.0,
            'temperature': 28.0,
            'humidity': 75.0,
            'precipitation': 15.0
        }
        
        damage_prediction = cyclone_predictor.predict_damage(
            commune_name=commune,
            coordinates=commune_data['coordinates'],
            weather_conditions=weather_conditions,
            population=commune_data.get('population', 10000)
        )
        
        return {
            "commune": commune,
            "coordinates": commune_data['coordinates'],
            "damage_predictions": damage_prediction['damage_predictions'],
            "risk_level": damage_prediction['risk_level'],
            "confidence_score": damage_prediction['confidence_score'],
            "recommendations": damage_prediction['recommendations'],
            "weather_conditions": weather_conditions,
            "data_source": "realtime_fallback"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur prédiction IA pour {commune}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction: {str(e)}")

@api_router.get("/ai/cyclone/timeline/{commune}")
async def get_cyclone_timeline(commune: str):
    """Timeline de prédiction cyclonique pour une commune (données précalculées)"""
    try:
        logger.info(f"🕒 Récupération timeline IA précalculée pour {commune}")
        
        if not ai_precalculation_service:
            raise HTTPException(status_code=503, detail="Service IA non disponible")
        
        # Récupérer depuis le cache
        cached_timeline = await ai_precalculation_service.get_cached_timeline(commune)
        
        if cached_timeline:
            logger.info(f"✅ Timeline trouvée en cache pour {commune}")
            return cached_timeline
        
        # Fallback minimal
        logger.warning(f"⚠️ Pas de timeline en cache pour {commune}")
        
        commune_data = None
        from data.communes_data import GUADELOUPE_COMMUNES
        for c in GUADELOUPE_COMMUNES:
            if c['name'].lower() == commune.lower():
                commune_data = c
                break
        
        if not commune_data:
            raise HTTPException(status_code=404, detail="Commune non trouvée")
        
        return {
            "commune": commune,
            "coordinates": commune_data['coordinates'],
            "timeline_predictions": {
                "H+0": {"risk_evolution": {"wind_risk": 10, "flood_risk": 5, "infrastructure_risk": 3}},
                "H+6": {"risk_evolution": {"wind_risk": 25, "flood_risk": 15, "infrastructure_risk": 10}},
                "H+12": {"risk_evolution": {"wind_risk": 45, "flood_risk": 30, "infrastructure_risk": 25}}
            },
            "data_source": "fallback"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur timeline IA pour {commune}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la timeline: {str(e)}")

@api_router.get("/ai/cyclone/historical/{commune}")
async def get_historical_damage(commune: str):
    """Données historiques des dommages cycloniques (données précalculées)"""
    try:
        logger.info(f"📚 Récupération historique IA précalculé pour {commune}")
        
        if not ai_precalculation_service:
            raise HTTPException(status_code=503, detail="Service IA non disponible")
        
        # Récupérer depuis le cache
        cached_historical = await ai_precalculation_service.get_cached_historical(commune)
        
        if cached_historical:
            logger.info(f"✅ Historique trouvé en cache pour {commune}")
            return cached_historical
        
        # Fallback minimal
        logger.warning(f"⚠️ Pas d'historique en cache pour {commune}")
        
        commune_data = None
        from data.communes_data import GUADELOUPE_COMMUNES
        for c in GUADELOUPE_COMMUNES:
            if c['name'].lower() == commune.lower():
                commune_data = c
                break
        
        if not commune_data:
            raise HTTPException(status_code=404, detail="Commune non trouvée")
        
        return {
            "commune": commune,
            "coordinates": commune_data['coordinates'],
            "historical_events": [
                {"year": 2017, "event_name": "Ouragan Irma", "damage_type": "infrastructure", "damage_percentage": 15}
            ],
            "risk_factors": commune_data.get('riskFactors', []),
            "data_source": "fallback"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur historique IA pour {commune}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'historique: {str(e)}")

@api_router.get("/ai/cyclone/global-risk")
async def get_global_risk():
    """Évaluation du risque cyclonique global (données précalculées)"""
    try:
        logger.info("🌍 Récupération risque global IA précalculé")
        
        if not ai_precalculation_service:
            raise HTTPException(status_code=503, detail="Service IA non disponible")
        
        # Récupérer depuis le cache
        cached_global_risk = await ai_precalculation_service.get_cached_global_risk()
        
        if cached_global_risk:
            logger.info("✅ Risque global trouvé en cache")
            return cached_global_risk
        
        # Fallback minimal
        logger.warning("⚠️ Pas de risque global en cache, fallback")
        
        return {
            "global_risk_level": "faible",
            "affected_communes": [],
            "high_risk_count": 0,
            "critical_risk_count": 0,
            "regional_recommendations": [],
            "last_analysis": datetime.utcnow(),
            "data_source": "fallback"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur risque global IA: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul global: {str(e)}")

# Endpoint pour déclencher manuellement un calcul IA
@api_router.post("/ai/recalculate")
async def trigger_ai_recalculation():
    """Déclenche manuellement un recalcul IA (admin)"""
    try:
        scheduler = get_ai_scheduler()
        result = await scheduler.trigger_manual_calculation()
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur recalcul manuel IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint pour le statut du scheduler IA
@api_router.get("/ai/scheduler/status")
async def get_ai_scheduler_status():
    """Retourne le statut du scheduler IA"""
    try:
        scheduler = get_ai_scheduler()
        return scheduler.get_scheduler_status()
        
    except Exception as e:
        logger.error(f"❌ Erreur statut scheduler IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/ai/model/info")
async def get_ai_model_info():
    """Informations sur le modèle IA"""
    try:
        model_info = cyclone_predictor.get_model_info()
        return model_info
    except Exception as e:
        logger.error(f"Error getting AI model info: {e}")
        raise HTTPException(status_code=500, detail="Erreur informations modèle IA")

@api_router.get("/admin/quota/status")
async def get_quota_status():
    """Statistiques du système de quotas API"""
    try:
        from services.api_quota_manager import quota_manager
        from services.weather_scheduler import weather_scheduler
        
        quota_stats = quota_manager.get_quota_stats()
        scheduler_status = weather_scheduler.get_scheduler_status()
        
        return {
            "quota": quota_stats,
            "scheduler": scheduler_status,
            "message": "Système de quotas opérationnel"
        }
    except Exception as e:
        logger.error(f"Error getting quota status: {e}")
        raise HTTPException(status_code=500, detail="Erreur système de quotas")

@api_router.post("/admin/quota/force-update/{commune}")
async def force_update_commune(commune: str):
    """Force la mise à jour météo d'une commune"""
    try:
        from services.weather_scheduler import weather_scheduler
        
        result = await weather_scheduler.force_update_commune(commune)
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=429, detail=result['message'])
    
    except Exception as e:
        logger.error(f"Error forcing update for {commune}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur mise à jour {commune}")

@api_router.post("/admin/scheduler/start")
async def start_scheduler():
    """Démarre le scheduler météo"""
    try:
        from services.weather_scheduler import weather_scheduler
        
        await weather_scheduler.start_scheduler()
        return {"message": "Scheduler démarré avec succès"}
    
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail="Erreur démarrage scheduler")

@api_router.post("/admin/scheduler/stop")
async def stop_scheduler():
    """Arrête le scheduler météo"""
    try:
        from services.weather_scheduler import weather_scheduler
        
        await weather_scheduler.stop_scheduler()
        return {"message": "Scheduler arrêté avec succès"}
    
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail="Erreur arrêt scheduler")
    """Re-entraîne le modèle IA (admin uniquement)"""
    try:
        training_result = cyclone_predictor.train_model(retrain=True)
        return {
            "message": "Modèle IA re-entraîné avec succès",
            "training_metrics": training_result
        }
    except Exception as e:
        logger.error(f"Error retraining AI model: {e}")
        raise HTTPException(status_code=500, detail="Erreur re-entraînement modèle IA")

@api_router.get("/ai/test/{commune}")
async def test_ai_with_fallback(commune: str):
    """Test de l'IA avec données fallback - endpoint de debug"""
    try:
        # Force l'utilisation de données fallback pour test
        from services.openweather_service import OpenWeatherService
        
        # Créer instance temporaire avec fallback forcé
        temp_service = OpenWeatherService()
        
        # Obtenir coordonnées de la commune
        commune_info = get_commune_info(commune)
        coords = commune_info['coordinates']
        
        # Générer données fallback
        fallback_data = temp_service.generate_fallback_weather_data(coords[0], coords[1])
        
        # Adapter au format severe_weather
        severe_weather = {
            'current': {
                'wind_speed': fallback_data['current']['wind_speed'],
                'pressure': fallback_data['current']['pressure'], 
                'temperature': fallback_data['current']['temperature'],
                'humidity': fallback_data['current']['humidity'],
                'precipitation': fallback_data['current'].get('rain', {}).get('1h', 0),
                'source': 'test_fallback'
            },
            'timeline': {},
            'fallback_mode': True
        }
        
        # Test de l'IA
        prediction = cyclone_predictor.predict_damage(
            weather_data=severe_weather['current'],
            commune_info=commune_info
        )
        
        # Adaptation vigilance
        try:
            vigilance_data = await meteo_france_service.get_vigilance_data('guadeloupe')
            vigilance_level = vigilance_data.get('color_level', 'vert')
            adapted_risk = cyclone_predictor.adapt_risk_to_vigilance(
                prediction['risk_level'], vigilance_level
            )
        except:
            adapted_risk = prediction['risk_level']
            vigilance_level = 'unknown'
        
        return {
            "message": "Test IA avec données fallback",
            "commune": commune,
            "fallback_weather": fallback_data['current'],
            "original_risk": prediction['risk_level'],
            "adapted_risk": adapted_risk,
            "vigilance_level": vigilance_level,
            "risk_score": prediction['risk_score'],
            "confidence": prediction['confidence'],
            "recommendations": prediction['recommendations'][:3],
            "test_mode": True
        }
        
    except Exception as e:
        logger.error(f"Error in AI test: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur test IA: {str(e)}")

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
# ENDPOINTS RÉSEAUX SOCIAUX
# =============================================================================

@api_router.post("/social/credentials", response_model=SocialCredentialsResponse)
async def store_social_credentials(credentials: SocialCredentialsRequest):
    """Stocke les identifiants des réseaux sociaux"""
    try:
        from services.social_media_service import social_media_service
        
        success = await social_media_service.store_social_credentials(
            platform=credentials.platform.value,
            credentials=credentials.credentials
        )
        
        return SocialCredentialsResponse(
            success=success,
            platform=credentials.platform,
            message=f"Identifiants {credentials.platform.value} stockés avec succès" if success else "Erreur lors du stockage"
        )
        
    except Exception as e:
        logger.error(f"Error storing social credentials: {e}")
        raise HTTPException(status_code=500, detail="Erreur stockage identifiants")

@api_router.post("/social/post", response_model=SocialPostResponse)  
async def create_social_post(post_request: SocialPostRequest):
    """Crée un post sur les réseaux sociaux"""
    try:
        from services.social_media_service import social_media_service
        
        # Si une commune est spécifiée, récupérer les données météo
        if post_request.commune:
            weather_data = await weather_service.get_weather_for_commune(post_request.commune)
            vigilance_data = await meteo_france_service.get_vigilance_data('guadeloupe')
            
            # Optionnel: ajouter prédiction IA
            ai_prediction = None
            if post_request.include_ai_prediction and weather_data:
                try:
                    coords = weather_data.coordinates
                    severe_weather = await openweather_service.get_severe_weather_data(coords[0], coords[1])
                    
                    if severe_weather:
                        commune_info = get_commune_info(post_request.commune)
                        ai_prediction = cyclone_predictor.predict_damage(
                            weather_data=severe_weather['current'],
                            commune_info=commune_info
                        )
                except Exception as e:
                    logger.warning(f"Could not get AI prediction for social post: {e}")
            
            # Formater le post avec les données météo
            content = social_media_service.format_weather_post(
                weather_data.dict() if weather_data else {},
                vigilance_data,
                ai_prediction
            )
        else:
            # Utiliser le contenu fourni directement
            content = post_request.content
        
        # Poster sur toutes les plateformes ou celles spécifiées
        if post_request.platforms:
            results = {}
            platforms = [p.value for p in post_request.platforms]
            
            if 'twitter' in platforms:
                results['twitter'] = await social_media_service.post_to_twitter(content)
            if 'facebook' in platforms:  
                results['facebook'] = await social_media_service.post_to_facebook(content)
        else:
            results = await social_media_service.post_to_all_platforms(content)
        
        return SocialPostResponse(
            success=any(r.get('success', False) for r in results.values()),
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error creating social post: {e}")
        raise HTTPException(status_code=500, detail="Erreur création post")

@api_router.post("/social/schedule", response_model=ScheduledPostResponse)
async def schedule_social_post(schedule_request: ScheduledPostRequest):
    """Programme un post sur les réseaux sociaux"""
    try:
        from services.social_post_scheduler import social_post_scheduler
        
        platforms = [p.value for p in schedule_request.platforms] if schedule_request.platforms else ['twitter', 'facebook']
        
        job_id = await social_post_scheduler.schedule_custom_post(
            content=schedule_request.content,
            schedule_time=schedule_request.schedule_time,
            platforms=platforms
        )
        
        return ScheduledPostResponse(
            success=True,
            job_id=job_id,
            scheduled_time=schedule_request.schedule_time,
            platforms=schedule_request.platforms or [SocialPlatform.TWITTER, SocialPlatform.FACEBOOK]
        )
        
    except Exception as e:
        logger.error(f"Error scheduling social post: {e}")
        raise HTTPException(status_code=500, detail="Erreur programmation post")

@api_router.delete("/social/schedule/{job_id}")
async def cancel_scheduled_post(job_id: str):
    """Annule un post programmé"""
    try:
        from services.social_post_scheduler import social_post_scheduler
        
        success = await social_post_scheduler.cancel_scheduled_post(job_id)
        
        return {
            "success": success,
            "message": "Post programmé annulé avec succès" if success else "Erreur lors de l'annulation"
        }
        
    except Exception as e:
        logger.error(f"Error cancelling scheduled post: {e}")
        raise HTTPException(status_code=500, detail="Erreur annulation post")

@api_router.get("/social/stats", response_model=SocialStatsResponse)
async def get_social_stats(days: int = 30):
    """Récupère les statistiques des posts sur les réseaux sociaux"""
    try:
        from services.social_media_service import social_media_service
        
        stats = await social_media_service.get_post_statistics(days=days)
        
        return SocialStatsResponse(
            total_posts=stats['total_posts'],
            platform_breakdown=stats['platform_breakdown'],
            period_days=stats['period_days'],
            last_updated=stats.get('last_updated', datetime.now().isoformat())
        )
        
    except Exception as e:
        logger.error(f"Error getting social stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur statistiques réseaux sociaux")

@api_router.get("/social/scheduler/status")
async def get_scheduler_status():
    """Statut du planificateur de posts sociaux"""
    try:
        from services.social_post_scheduler import social_post_scheduler
        
        status = await social_post_scheduler.get_scheduler_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Erreur statut planificateur")

@api_router.post("/social/scheduler/start")
async def start_social_scheduler():
    """Démarre le planificateur de posts sociaux"""
    try:
        from services.social_post_scheduler import social_post_scheduler
        
        await social_post_scheduler.start_scheduler()
        return {"message": "Planificateur de posts sociaux démarré avec succès"}
        
    except Exception as e:
        logger.error(f"Error starting social scheduler: {e}")
        raise HTTPException(status_code=500, detail="Erreur démarrage planificateur")

@api_router.post("/social/scheduler/stop") 
async def stop_social_scheduler():
    """Arrête le planificateur de posts sociaux"""
    try:
        from services.social_post_scheduler import social_post_scheduler
        
        await social_post_scheduler.stop_scheduler()
        return {"message": "Planificateur de posts sociaux arrêté avec succès"}
        
    except Exception as e:
        logger.error(f"Error stopping social scheduler: {e}")
        raise HTTPException(status_code=500, detail="Erreur arrêt planificateur")

@api_router.get("/social/test-connections")
async def test_social_connections():
    """Teste les connexions aux API des réseaux sociaux"""
    try:
        from services.social_media_service import social_media_service
        
        results = social_media_service.test_connections()
        return {
            "connections": results,
            "overall_status": "connected" if any(r.get('connected', False) for r in results.values()) else "disconnected"
        }
        
    except Exception as e:
        logger.error(f"Error testing social connections: {e}")
        raise HTTPException(status_code=500, detail="Erreur test connexions")

# =============================================================================
# ENDPOINTS SYSTÈME DE BACKUP MÉTÉO
# =============================================================================

@api_router.get("/weather/backup/test")
async def test_weather_backup_system():
    """Teste le système de backup météo pour toutes les communes"""
    try:
        from services.weather_backup_service import weather_backup_service
        
        if not weather_backup_service:
            raise HTTPException(status_code=500, detail="Service de backup non initialisé")
        
        results = await weather_backup_service.test_backup_system()
        return results
        
    except Exception as e:
        logger.error(f"Error testing weather backup system: {e}")
        raise HTTPException(status_code=500, detail="Erreur test système backup")

@api_router.get("/weather/backup/status")
async def get_backup_system_status():
    """Statut général du système de backup météo"""
    try:
        from services.weather_backup_service import weather_backup_service
        
        if not weather_backup_service:
            return {
                "status": "disabled",
                "message": "Service de backup non initialisé"
            }
        
        # Tester quelques communes pour avoir un aperçu
        test_communes = ['Pointe-à-Pitre', 'Basse-Terre', 'Sainte-Anne']
        commune_status = {}
        
        for commune in test_communes:
            try:
                latest_backup = await weather_backup_service.get_latest_backup(commune)
                commune_status[commune] = {
                    "has_recent_backup": latest_backup is not None,
                    "backup_age_hours": None
                }
                
                if latest_backup:
                    # Calculer l'âge du backup si possible
                    try:
                        backup_time = datetime.fromisoformat(latest_backup.get('timestamp', ''))
                        age_hours = (datetime.now() - backup_time).total_seconds() / 3600
                        commune_status[commune]["backup_age_hours"] = round(age_hours, 1)
                    except:
                        pass
                        
            except Exception as e:
                commune_status[commune] = {
                    "has_recent_backup": False,
                    "error": str(e)
                }
        
        return {
            "status": "active",
            "commune_status": commune_status,
            "total_communes_supported": len(weather_backup_service.communes_backup),
            "backup_retention_hours": 24,
            "cleanup_retention_days": 7
        }
        
    except Exception as e:
        logger.error(f"Error getting backup system status: {e}")
        raise HTTPException(status_code=500, detail="Erreur statut système backup")

@api_router.get("/weather/backup/{commune}")
async def get_backup_weather(commune: str):
    """Récupère les données météo de backup pour une commune"""
    try:
        from services.weather_backup_service import weather_backup_service
        
        if not weather_backup_service:
            raise HTTPException(status_code=500, detail="Service de backup non initialisé")
        
        backup_data = await weather_backup_service.get_backup_weather_with_fallback(commune)
        return {
            "commune": commune,
            "backup_data": backup_data,
            "source": backup_data.get('source', 'unknown'),
            "is_backup": backup_data.get('is_backup', True),
            "timestamp": backup_data.get('timestamp')
        }
        
    except Exception as e:
        logger.error(f"Error getting backup weather for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération backup météo")

@api_router.post("/weather/backup/cleanup")
async def cleanup_old_weather_backups():
    """Nettoie les anciennes sauvegardes météo"""
    try:
        from services.weather_backup_service import weather_backup_service
        
        if not weather_backup_service:
            raise HTTPException(status_code=500, detail="Service de backup non initialisé")
        
        deleted_count = await weather_backup_service.cleanup_old_backups()
        return {
            "message": f"Nettoyage terminé - {deleted_count} sauvegardes supprimées",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up weather backups: {e}")
        raise HTTPException(status_code=500, detail="Erreur nettoyage backups")

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
# ENDPOINTS ACTIVITÉ UTILISATEUR ET TÉMOIGNAGES  
# =============================================================================

@api_router.post("/users/activity")
async def track_user_activity(request: dict):
    """Enregistre l'activité d'un utilisateur"""
    try:
        session_id = request.get('session_id')
        ip_address = request.get('ip_address')
        user_agent = request.get('user_agent')
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id requis")
        
        if not user_activity_service:
            raise HTTPException(status_code=503, detail="Service activité utilisateur non disponible")
        
        success = await user_activity_service.track_user_activity(
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if success:
            return {"success": True, "message": "Activité enregistrée"}
        else:
            raise HTTPException(status_code=500, detail="Erreur enregistrement activité")
            
    except Exception as e:
        logger.error(f"Error tracking user activity: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.get("/users/active-count", response_model=ActiveUsersResponse)
async def get_active_users_count():
    """Récupère le nombre d'utilisateurs actifs"""
    try:
        if not user_activity_service:
            raise HTTPException(status_code=503, detail="Service activité utilisateur non disponible")
        
        result = await user_activity_service.get_active_users_count()
        return result
        
    except Exception as e:
        logger.error(f"Error getting active users count: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.post("/testimonials")
async def submit_testimonial(testimonial_request: TestimonialRequest):
    """Soumet un nouveau témoignage"""
    try:
        if not user_activity_service:
            raise HTTPException(status_code=503, detail="Service activité utilisateur non disponible")
        
        result = await user_activity_service.submit_testimonial(testimonial_request)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error submitting testimonial: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

@api_router.get("/testimonials", response_model=TestimonialResponse)
async def get_testimonials(limit: int = 6):
    """Récupère les témoignages approuvés"""
    try:
        if not user_activity_service:
            raise HTTPException(status_code=503, detail="Service activité utilisateur non disponible")
        
        if limit > 20:  # Limite max
            limit = 20
        
        result = await user_activity_service.get_testimonials(limit=limit)
        return result
        
    except Exception as e:
        logger.error(f"Error getting testimonials: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

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