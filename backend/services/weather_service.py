import os
import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

from models import (
    WeatherResponse, SatelliteImageRequest, SatelliteResponse, 
    SatelliteLayer, WeatherAlert, AlertType, RiskLevel,
    WeatherSource, WeatherConfig
)
from services.weather_cache_service import WeatherCacheService

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self, db: AsyncIOMotorClient, cache_service: WeatherCacheService, config: WeatherConfig):
        self.db = db
        self.cache_service = cache_service
        self.config = config
        self.nasa_base_url = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
        
    async def get_weather_for_commune(self, commune: str) -> Optional[WeatherResponse]:
        """Récupère la météo d'une commune (priorité cache)"""
        try:
            # Récupère depuis le cache ou met à jour
            weather_cache = await self.cache_service.get_or_update_weather(commune)
            
            if not weather_cache:
                logger.error(f"Unable to get weather data for {commune}")
                return None
            
            # Récupère les alertes actives pour cette commune
            alerts = await self.get_active_alerts_for_commune(commune)
            
            return WeatherResponse(
                commune=commune,
                coordinates=weather_cache.coordinates,
                current=weather_cache.current_weather,
                forecast=weather_cache.forecast_5_days,
                alerts=alerts,
                last_updated=weather_cache.updated_at,
                source=weather_cache.source,
                cached=True
            )
            
        except Exception as e:
            logger.error(f"Error getting weather for {commune}: {e}")
            return None
    
    async def get_weather_for_multiple_communes(self, communes: List[str]) -> Dict[str, WeatherResponse]:
        """Récupère la météo pour plusieurs communes"""
        results = {}
        
        for commune in communes:
            weather = await self.get_weather_for_commune(commune)
            if weather:
                results[commune] = weather
                
        return results
    
    async def get_satellite_image(self, request: SatelliteImageRequest) -> Optional[SatelliteResponse]:
        """Récupère une image satellite depuis NASA GIBS"""
        try:
            # Construction de l'URL NASA GIBS
            layer_url = f"{self.nasa_base_url}/{request.layer.value}/default/{request.date}/EPSG4326_250m/{{}}/{{}}/{{}}.jpg"
            
            # Calcul des tuiles pour la bbox Guadeloupe
            # Simplifié pour demo - à améliorer avec calcul de tuiles réel
            tile_x, tile_y, zoom = self._calculate_tile_coordinates(request.bbox, request.width, request.height)
            
            image_url = layer_url.format(zoom, tile_y, tile_x)
            
            # Vérifie que l'image existe
            async with httpx.AsyncClient() as client:
                response = await client.head(image_url)
                
                if response.status_code == 200:
                    return SatelliteResponse(
                        image_url=image_url,
                        layer=request.layer,
                        bbox=request.bbox,
                        date=request.date,
                        resolution=f"{request.width}x{request.height}",
                        source="NASA_GIBS"
                    )
                else:
                    logger.warning(f"NASA GIBS image not available: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting satellite image: {e}")
            return None
    
    def _calculate_tile_coordinates(self, bbox: str, width: int, height: int) -> tuple:
        """Calcule les coordonnées de tuile pour NASA GIBS (simplifié)"""
        # Parse bbox: "lon_min,lat_min,lon_max,lat_max"
        lon_min, lat_min, lon_max, lat_max = map(float, bbox.split(','))
        
        # Centre de la Guadeloupe
        center_lon = (lon_min + lon_max) / 2
        center_lat = (lat_min + lat_max) / 2
        
        # Calcul simplifié pour zoom level 6 (région Antilles)
        zoom = 6
        
        # Conversion coordonnées géographiques -> tuiles Web Mercator
        tile_x = int((center_lon + 180.0) / 360.0 * (2 ** zoom))
        tile_y = int((1.0 - (center_lat + 90.0) / 180.0) * (2 ** zoom))
        
        return tile_x, tile_y, zoom
    
    async def get_satellite_layers_available(self) -> List[Dict[str, Any]]:
        """Retourne les couches satellite disponibles"""
        return [
            {
                "layer": SatelliteLayer.TRUE_COLOR,
                "name": "Couleurs naturelles",
                "description": "Image satellite en couleurs naturelles",
                "type": "optical"
            },
            {
                "layer": SatelliteLayer.CLOUD_TOP_TEMP,
                "name": "Température sommet nuages",
                "description": "Température des sommets nuageux (détection cyclones)",
                "type": "thermal"
            },
            {
                "layer": SatelliteLayer.PRECIPITATION,
                "name": "Précipitations",
                "description": "Intensité des précipitations mesurées par satellite",
                "type": "precipitation"
            }
        ]
    
    async def get_active_alerts_for_commune(self, commune: str) -> List[WeatherAlert]:
        """Récupère les alertes météo actives pour une commune"""
        now = datetime.utcnow()
        
        alerts = await self.db.weather_alerts.find({
            "commune": commune,
            "active_from": {"$lte": now},
            "active_until": {"$gte": now}
        }).to_list(100)
        
        return [WeatherAlert(**alert) for alert in alerts]
    
    async def get_regional_alerts(self) -> List[WeatherAlert]:
        """Récupère toutes les alertes météo actives en Guadeloupe"""
        now = datetime.utcnow()
        
        alerts = await self.db.weather_alerts.find({
            "active_from": {"$lte": now},
            "active_until": {"$gte": now}
        }).sort("severity", -1).to_list(100)
        
        return [WeatherAlert(**alert) for alert in alerts]
    
    async def process_weather_alerts_from_cache(self):
        """Analyse les données du cache pour générer des alertes automatiques"""
        logger.info("Processing automatic weather alerts from cache data")
        
        alerts_generated = 0
        
        for commune in self.config.communes_guadeloupe:
            try:
                # Récupère les données du cache
                weather_cache = await self.cache_service.get_cached_weather(commune)
                
                if not weather_cache:
                    continue
                
                # Analyse les prévisions pour détecter les risques
                for day_forecast in weather_cache.forecast_5_days:
                    alerts = await self._generate_alerts_from_forecast(commune, day_forecast)
                    
                    for alert in alerts:
                        # Vérifie si une alerte similaire existe déjà
                        existing = await self.db.weather_alerts.find_one({
                            "commune": commune,
                            "alert_type": alert.alert_type,
                            "active_until": {"$gte": datetime.utcnow()}
                        })
                        
                        if not existing:
                            await self.db.weather_alerts.insert_one(alert.dict())
                            alerts_generated += 1
                            logger.info(f"Generated alert for {commune}: {alert.title}")
                            
            except Exception as e:
                logger.error(f"Error processing alerts for {commune}: {e}")
                continue
        
        logger.info(f"Generated {alerts_generated} automatic weather alerts")
        return alerts_generated
    
    async def _generate_alerts_from_forecast(self, commune: str, forecast) -> List[WeatherAlert]:
        """Génère des alertes basées sur les données de prévision"""
        alerts = []
        weather = forecast.weather_data
        coordinates = self.cache_service._get_commune_coordinates(commune) or [0, 0]
        
        # Alerte cyclone/vent fort
        if weather.wind_speed > 80:
            alerts.append(WeatherAlert(
                commune=commune,
                coordinates=coordinates,
                alert_type=AlertType.CYCLONE,
                severity=RiskLevel.CRITIQUE,
                title="ALERTE CYCLONE - Vents destructeurs",
                message=f"Vents violents prévus: {weather.wind_speed:.0f} km/h. Restez à l'abri!",
                active_from=datetime.utcnow(),
                active_until=datetime.utcnow() + timedelta(days=1),
                recommendations=[
                    "Restez à l'intérieur",
                    "Éloignez-vous des fenêtres",
                    "Préparez eau et nourriture",
                    "Chargez vos appareils électroniques"
                ]
            ))
        elif weather.wind_speed > 60:
            alerts.append(WeatherAlert(
                commune=commune,
                coordinates=coordinates,
                alert_type=AlertType.VENT_FORT,
                severity=RiskLevel.ELEVE,
                title="Vents violents attendus",
                message=f"Vents forts prévus: {weather.wind_speed:.0f} km/h. Soyez prudents!",
                active_from=datetime.utcnow(),
                active_until=datetime.utcnow() + timedelta(hours=12)
            ))
        
        # Alerte fortes pluies/inondation
        if weather.precipitation > 30 and weather.precipitation_probability > 80:
            alerts.append(WeatherAlert(
                commune=commune,
                coordinates=coordinates,
                alert_type=AlertType.INONDATION,
                severity=RiskLevel.ELEVE,
                title="Risque d'inondation majeur",
                message=f"Pluies diluviennes prévues: {weather.precipitation:.1f}mm/h. Évitez les zones basses!",
                active_from=datetime.utcnow(),
                active_until=datetime.utcnow() + timedelta(hours=8),
                recommendations=[
                    "Évitez les zones inondables",
                    "Ne traversez pas les cours d'eau en crue",
                    "Surveillez les enfants",
                    "Préparez-vous à évacuer si nécessaire"
                ]
            ))
        elif weather.precipitation > 15:
            alerts.append(WeatherAlert(
                commune=commune,
                coordinates=coordinates,
                alert_type=AlertType.FORTE_PLUIE,
                severity=RiskLevel.MODERE,
                title="Fortes pluies attendues",
                message=f"Précipitations importantes prévues: {weather.precipitation:.1f}mm/h",
                active_from=datetime.utcnow(),
                active_until=datetime.utcnow() + timedelta(hours=6)
            ))
        
        return alerts
    
    async def get_weather_statistics(self) -> Dict[str, Any]:
        """Génère des statistiques météorologiques"""
        stats = {}
        
        # Statistiques par niveau de risque
        risk_counts = {level.value: 0 for level in RiskLevel}
        
        for commune in self.config.communes_guadeloupe:
            weather_cache = await self.cache_service.get_cached_weather(commune)
            if weather_cache and weather_cache.forecast_5_days:
                max_risk = max([day.risk_level for day in weather_cache.forecast_5_days])
                risk_counts[max_risk.value] += 1
        
        stats["risk_distribution"] = risk_counts
        
        # Alertes actives
        active_alerts = await self.get_regional_alerts()
        stats["active_alerts"] = len(active_alerts)
        stats["alerts_by_type"] = {}
        
        for alert in active_alerts:
            alert_type = alert.alert_type.value
            stats["alerts_by_type"][alert_type] = stats["alerts_by_type"].get(alert_type, 0) + 1
        
        # Usage API
        api_stats = await self.cache_service.get_daily_usage_stats()
        stats["api_usage"] = {
            "openweather_calls": api_stats.openweather_calls,
            "cache_hits": api_stats.cache_hits,
            "cache_misses": api_stats.cache_misses,
            "efficiency": round(api_stats.cache_hits / max(api_stats.cache_hits + api_stats.cache_misses, 1) * 100, 1)
        }
        
        return stats