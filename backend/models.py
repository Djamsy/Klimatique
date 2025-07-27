from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# Enums pour les types
class RiskLevel(str, Enum):
    FAIBLE = "faible"
    MODERE = "modéré" 
    ELEVE = "élevé"
    CRITIQUE = "critique"

class AlertType(str, Enum):
    CYCLONE = "cyclone"
    INONDATION = "inondation"
    FORTE_PLUIE = "forte_pluie"
    VENT_FORT = "vent_fort"
    HOULE = "houle"

class WeatherSource(str, Enum):
    OPENWEATHERMAP = "openweathermap"
    NASA = "nasa"
    CACHE = "cache"

# Modèles Weather Cache
class WeatherData(BaseModel):
    temperature_min: float
    temperature_max: float
    temperature_current: Optional[float] = None
    humidity: int
    wind_speed: float
    wind_direction: Optional[int] = None
    precipitation: float
    precipitation_probability: int
    pressure: Optional[float] = None
    visibility: Optional[float] = None
    uv_index: Optional[int] = None
    weather_description: str
    weather_icon: str

class WeatherForecastDay(BaseModel):
    date: str
    day_name: str
    weather_data: WeatherData
    risk_level: RiskLevel
    risk_factors: List[str] = []

class WeatherCache(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    commune: str
    coordinates: List[float]  # [lat, lon]
    current_weather: WeatherData
    forecast_5_days: List[WeatherForecastDay]
    source: WeatherSource
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    call_count_today: int = 0
    last_api_call: Optional[datetime] = None

# Modèles Alertes
class WeatherAlert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    commune: str
    coordinates: List[float]
    alert_type: AlertType
    severity: RiskLevel
    title: str
    message: str
    active_from: datetime
    active_until: datetime
    affected_zones: List[str] = []
    recommendations: List[str] = []
    source: WeatherSource
    auto_generated: bool = True
    sent_notifications: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Modèles Utilisateurs & Abonnements
class UserPreferences(BaseModel):
    communes: List[str]
    alert_types: List[AlertType]
    notification_email: bool = True
    notification_sms: bool = False
    risk_threshold: RiskLevel = RiskLevel.MODERE

class UserSubscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    phone: Optional[str] = None
    preferences: UserPreferences
    verified_email: bool = False
    verified_phone: bool = False
    active: bool = True
    subscription_date: datetime = Field(default_factory=datetime.utcnow)
    last_notification: Optional[datetime] = None
    notifications_sent: int = 0

# Modèles API Responses
class WeatherResponse(BaseModel):
    commune: str
    coordinates: List[float]
    current: WeatherData
    forecast: List[WeatherForecastDay]
    alerts: List[WeatherAlert] = []
    last_updated: datetime
    source: WeatherSource
    cached: bool = True

class AlertResponse(BaseModel):
    alerts: List[WeatherAlert]
    total_active: int
    by_severity: Dict[RiskLevel, int]
    last_updated: datetime

# Modèles NASA Satellite
class SatelliteLayer(str, Enum):
    TRUE_COLOR = "MODIS_Terra_CorrectedReflectance_TrueColor"
    CLOUD_TOP_TEMP = "MODIS_Terra_Cloud_Top_Temp"
    PRECIPITATION = "GPM_3IMERGHH_06_precipitation"

class SatelliteImageRequest(BaseModel):
    bbox: str  # "lon_min,lat_min,lon_max,lat_max"
    date: str  # "YYYY-MM-DD"
    layer: SatelliteLayer
    width: int = 512
    height: int = 512

class SatelliteResponse(BaseModel):
    image_url: str
    layer: SatelliteLayer
    bbox: str
    date: str
    resolution: str
    source: str = "NASA_GIBS"

# Modèles Statistiques & Monitoring
class APIUsageStats(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str  # YYYY-MM-DD
    openweather_calls: int = 0
    nasa_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    alerts_sent: int = 0
    new_subscriptions: int = 0
    active_users: int = 0
    
class CommuneStats(BaseModel):
    commune: str
    coordinates: List[float]
    total_subscribers: int
    alerts_this_month: int
    avg_risk_level: float
    last_critical_alert: Optional[datetime] = None

# Modèles Configuration
class WeatherConfig(BaseModel):
    communes_guadeloupe: List[str] = [
        "Pointe-à-Pitre", "Basse-Terre", "Sainte-Anne", "Le Moule",
        "Saint-François", "Gosier", "Petit-Bourg", "Lamentin",
        "Capesterre-Belle-Eau", "Bouillante", "Deshaies", "Saint-Claude",
        "Gourbeyre", "Trois-Rivières", "Vieux-Habitants", "Bailiff",
        "Baillif", "Vieux-Fort", "Goyave", "Petit-Canal",
        "Port-Louis", "Anse-Bertrand", "Morne-à-l'Eau", "Abymes",
        "Baie-Mahault", "Saint-Rose", "Sainte-Rose", "Pointe-Noire",
        "Terre-de-Bas", "Terre-de-Haut", "La Désirade", "Marie-Galante"
    ]
    
    guadeloupe_bbox: str = "-61.8,15.8,-61.0,16.5"  # Lon min, Lat min, Lon max, Lat max
    
    update_frequencies: Dict[RiskLevel, int] = {
        RiskLevel.FAIBLE: 60,      # minutes
        RiskLevel.MODERE: 30,
        RiskLevel.ELEVE: 10, 
        RiskLevel.CRITIQUE: 5
    }
    
    daily_call_limit: int = 1000
    cache_expiry_hours: int = 2

# Validation et utilitaires
class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []

# Modèles pour les formulaires frontend
class SubscriptionRequest(BaseModel):
    email: str
    phone: Optional[str] = None
    communes: List[str]
    alert_types: List[AlertType] = [AlertType.CYCLONE, AlertType.FORTE_PLUIE]
    message: Optional[str] = None

class ContactRequest(BaseModel):
    email: str
    message: str
    type: str = "beta_access"  # beta_access, support, feedback
    
class UnsubscribeRequest(BaseModel):
    email: str
    reason: Optional[str] = None