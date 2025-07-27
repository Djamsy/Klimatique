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
    RiskLevel, AlertType, CycloneAIResponse, CycloneTimelinePrediction,
    CommuneHistoricalResponse, GlobalCycloneRisk, CycloneDamagePrediction
)
from services.weather_cache_service import WeatherCacheService
from services.weather_service import WeatherService
from services.alert_service import AlertService
from services.subscription_service import SubscriptionService
from services.openweather_service import openweather_service
from services.meteo_france_service import meteo_france_service
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
        # Vérifier le cache d'abord
        cached_data = await weather_cache_optimizer.get_cached_data('satellite_guadeloupe')
        
        if cached_data and 'clouds' in cached_data:
            return {
                "overlay_type": "clouds",
                "data": cached_data['clouds'],
                "source": "cache"
            }
        
        # Si pas en cache, récupérer depuis l'API
        center_lat, center_lon = 16.25, -61.55
        clouds_data = await openweather_service.get_weather_map_data(center_lat, center_lon, 'clouds_new', 8)
        
        if not clouds_data:
            raise HTTPException(status_code=503, detail="Service nuages temporairement indisponible")
        
        return {
            "overlay_type": "clouds",
            "data": clouds_data,
            "source": "api"
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
        vigilance_data = await meteo_france_service.get_vigilance_data('guadeloupe')
        
        return {
            'vigilance_level': vigilance_data['color_level'],
            'recommendations': vigilance_data['recommendations'],
            'risks': vigilance_data['risks'],
            'official_source': 'Météo France',
            'valid_from': vigilance_data['valid_from'],
            'valid_until': vigilance_data['valid_until'],
            'last_updated': vigilance_data['last_updated'],
            'is_fallback': vigilance_data.get('is_fallback', False)
        }
    except Exception as e:
        logger.error(f"Error getting vigilance recommendations: {e}")
        raise HTTPException(status_code=500, detail="Erreur recommandations vigilance")

# =============================================================================
# ENDPOINTS IA PRÉDICTIVE CYCLONIQUE
# =============================================================================

@api_router.get("/ai/cyclone/predict/{commune}", response_model=CycloneAIResponse)
async def predict_cyclone_damage(commune: str):
    """Prédiction IA des dégâts cycloniques pour une commune"""
    try:
        # Récupère les données météo actuelles
        weather_data = await weather_service.get_weather_for_commune(commune)
        if not weather_data:
            raise HTTPException(status_code=404, detail=f"Données météo non disponibles pour {commune}")
        
        # Récupère les données OpenWeatherMap pour l'IA
        coords = weather_data.coordinates
        severe_weather = await openweather_service.get_severe_weather_data(coords[0], coords[1])
        
        if not severe_weather:
            raise HTTPException(status_code=500, detail="Données météo sévères non disponibles")
        
        # Prépare les informations de la commune
        commune_info = get_commune_info(commune)
        
        # Prédiction IA
        prediction = cyclone_predictor.predict_damage(
            weather_data=severe_weather['current'],
            commune_info=commune_info
        )
        
        # Formate la réponse
        response = CycloneAIResponse(
            commune=commune,
            coordinates=coords,
            damage_predictions=CycloneDamagePrediction(
                infrastructure=prediction['damage_predictions']['infrastructure'],
                agriculture=prediction['damage_predictions']['agriculture'],
                population_impact=prediction['damage_predictions']['population_impact']
            ),
            risk_level=RiskLevel(prediction['risk_level']),
            risk_score=prediction['risk_score'],
            confidence=prediction['confidence'],
            recommendations=prediction['recommendations'],
            weather_context=severe_weather['current']
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting cyclone damage for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur prédiction IA")

@api_router.get("/ai/cyclone/timeline/{commune}", response_model=CycloneTimelinePrediction)
async def predict_cyclone_timeline(commune: str):
    """Prédiction évolution des dégâts cycloniques dans le temps"""
    try:
        # Récupère les données météo actuelles
        weather_data = await weather_service.get_weather_for_commune(commune)
        if not weather_data:
            raise HTTPException(status_code=404, detail=f"Données météo non disponibles pour {commune}")
        
        coords = weather_data.coordinates
        severe_weather = await openweather_service.get_severe_weather_data(coords[0], coords[1])
        
        if not severe_weather:
            raise HTTPException(status_code=500, detail="Données météo sévères non disponibles")
        
        # Prépare les informations de la commune
        commune_info = get_commune_info(commune)
        
        # Prédictions timeline
        timeline_predictions = cyclone_predictor.predict_timeline_damage(
            weather_timeline=severe_weather['timeline'],
            commune_info=commune_info
        )
        
        # Formate les réponses
        formatted_timeline = {}
        for time_key, prediction in timeline_predictions.items():
            formatted_timeline[time_key] = CycloneAIResponse(
                commune=commune,
                coordinates=coords,
                damage_predictions=CycloneDamagePrediction(
                    infrastructure=prediction['damage_predictions']['infrastructure'],
                    agriculture=prediction['damage_predictions']['agriculture'],
                    population_impact=prediction['damage_predictions']['population_impact']
                ),
                risk_level=RiskLevel(prediction['risk_level']),
                risk_score=prediction['risk_score'],
                confidence=prediction['confidence'],
                recommendations=prediction['recommendations'],
                weather_context=severe_weather['timeline'][time_key]
            )
        
        return CycloneTimelinePrediction(
            commune=commune,
            coordinates=coords,
            timeline_predictions=formatted_timeline
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting cyclone timeline for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur prédiction timeline IA")

@api_router.get("/ai/cyclone/historical/{commune}", response_model=CommuneHistoricalResponse)
async def get_historical_cyclone_damage(commune: str):
    """Récupère l'historique des dégâts cycloniques pour une commune"""
    try:
        # Données historiques simulées (à remplacer par une vraie base de données)
        historical_events = [
            {
                "year": 2017,
                "event_name": "Ouragan Irma",
                "damage_type": "infrastructure",
                "impact_level": RiskLevel.CRITIQUE,
                "description": "Destruction massive des infrastructures, coupures d'électricité généralisées",
                "estimated_damage_percent": 85.0
            },
            {
                "year": 2017,
                "event_name": "Ouragan Maria",
                "damage_type": "agriculture",
                "impact_level": RiskLevel.CRITIQUE,
                "description": "Cultures détruites, plantations de bananes ravagées",
                "estimated_damage_percent": 90.0
            },
            {
                "year": 2022,
                "event_name": "Tempête Fiona",
                "damage_type": "infrastructure",
                "impact_level": RiskLevel.MODERE,
                "description": "Coupures d'électricité temporaires, quelques toitures endommagées",
                "estimated_damage_percent": 25.0
            }
        ]
        
        # Analyse de vulnérabilité
        vulnerability_analysis = {
            "risk_factors": [
                "Proximité côtière",
                "Densité population élevée",
                "Infrastructures vieillissantes"
            ],
            "vulnerability_score": 7.5,
            "preparedness_level": "moyenne",
            "evacuation_capacity": "limitée"
        }
        
        coords = [16.25, -61.55]  # Coordonnées par défaut
        
        return CommuneHistoricalResponse(
            commune=commune,
            coordinates=coords,
            historical_events=historical_events,
            vulnerability_analysis=vulnerability_analysis
        )
        
    except Exception as e:
        logger.error(f"Error getting historical data for {commune}: {e}")
        raise HTTPException(status_code=500, detail="Erreur données historiques")

@api_router.get("/ai/cyclone/global-risk", response_model=GlobalCycloneRisk)
async def get_global_cyclone_risk():
    """Évaluation globale du risque cyclonique en Guadeloupe"""
    try:
        # Analyse toutes les communes
        communes = get_all_communes()[:10]  # Limite pour la démo
        high_risk_communes = []
        critical_risk_communes = []
        
        for commune in communes:
            try:
                # Récupère prédiction pour chaque commune
                weather_data = await weather_service.get_weather_for_commune(commune)
                if not weather_data:
                    continue
                    
                coords = weather_data.coordinates
                severe_weather = await openweather_service.get_severe_weather_data(coords[0], coords[1])
                
                if severe_weather:
                    commune_info = get_commune_info(commune)
                    prediction = cyclone_predictor.predict_damage(
                        weather_data=severe_weather['current'],
                        commune_info=commune_info
                    )
                    
                    risk_level = prediction['risk_level']
                    if risk_level == 'critique':
                        critical_risk_communes.append(commune)
                    elif risk_level == 'élevé':
                        high_risk_communes.append(commune)
                        
            except Exception as e:
                logger.warning(f"Error analyzing {commune}: {e}")
                continue
        
        # Détermine le risque global
        if critical_risk_communes:
            global_risk = RiskLevel.CRITIQUE
        elif len(high_risk_communes) >= 3:
            global_risk = RiskLevel.ELEVE
        elif high_risk_communes:
            global_risk = RiskLevel.MODERE
        else:
            global_risk = RiskLevel.FAIBLE
        
        # Recommandations régionales
        regional_recommendations = []
        if global_risk == RiskLevel.CRITIQUE:
            regional_recommendations = [
                "Activation du plan ORSEC",
                "Évacuation préventive recommandée",
                "Fermeture des établissements scolaires",
                "Renforcement des secours"
            ]
        elif global_risk == RiskLevel.ELEVE:
            regional_recommendations = [
                "Vigilance renforcée",
                "Préparation des moyens d'évacuation",
                "Stock d'urgence recommandé",
                "Surveillance météo continue"
            ]
        
        return GlobalCycloneRisk(
            global_risk_level=global_risk,
            affected_communes=high_risk_communes + critical_risk_communes,
            high_risk_count=len(high_risk_communes),
            critical_risk_count=len(critical_risk_communes),
            regional_recommendations=regional_recommendations
        )
        
    except Exception as e:
        logger.error(f"Error getting global cyclone risk: {e}")
        raise HTTPException(status_code=500, detail="Erreur analyse risque global")

@api_router.get("/ai/model/info")
async def get_ai_model_info():
    """Informations sur le modèle IA"""
    try:
        model_info = cyclone_predictor.get_model_info()
        return model_info
    except Exception as e:
        logger.error(f"Error getting AI model info: {e}")
        raise HTTPException(status_code=500, detail="Erreur informations modèle IA")

@api_router.post("/ai/model/retrain")
async def retrain_ai_model():
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