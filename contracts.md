# Météo Sentinelle - Contrats API & Architecture Backend

## 🏗️ Architecture Hybride NASA + OpenWeatherMap

### Concept Innovation
- **NASA GIBS API** : Vue satellite régionale, données scientifiques macro
- **OpenWeatherMap API** : Données météo locales précises par commune
- **Transition fluide** : Zoom progressif satellite → local

---

## 🛰️ NASA GIBS Integration

### Endpoints Backend à créer :
- `GET /api/satellite/region` - Image satellite Antilles-Guadeloupe
- `GET /api/satellite/layers` - Couches disponibles (nuages, température, etc.)
- `GET /api/satellite/animation` - Animation temporelle (24h)

### Données mockées actuellement :
```javascript
// Dans mock.js - à remplacer
export const riskZones = [
  { name: "Pointe-à-Pitre", riskLevel: "modéré", coordinates: [16.2415, -61.5328] },
  { name: "Basse-Terre", riskLevel: "élevé", coordinates: [16.0074, -61.7056] }
];
```

### Implémentation NASA :
```python
# Backend - À créer
NASA_GIBS_URL = "https://gibs.earthdata.nasa.gov/wmts/"
LAYERS = ["MODIS_Terra_CorrectedReflectance_TrueColor", "MODIS_Terra_Cloud_Top_Temp"]

async def get_satellite_image(bbox: str, date: str, layer: str):
    # Récupérer image satellite région Guadeloupe
    # Bbox: Lon min, Lat min, Lon max, Lat max
    # Exemple: "-62.0,15.5,-60.5,16.8" (Guadeloupe étendue)
```

---

## 🌦️ OpenWeatherMap Integration

### Endpoints Backend à créer :
- `GET /api/weather/current/{commune}` - Météo actuelle par commune
- `GET /api/weather/forecast/{commune}` - Prévisions 5 jours
- `GET /api/weather/alerts/{region}` - Alertes météo active
- `GET /api/weather/historical` - Données historiques

### Données mockées actuellement :
```javascript
// Dans mock.js - à remplacer
export const weatherForecast = [
  {
    date: "2025-01-15",
    temperature: { min: 24, max: 29 },
    riskLevel: "faible"
  }
];
```

### Implémentation OpenWeatherMap :
```python
# Backend - À créer
OPENWEATHER_API_KEY = os.environ['OPENWEATHER_API_KEY']
OPENWEATHER_URL = "https://api.openweathermap.org/data/3.0/"

async def get_local_weather(lat: float, lon: float):
    # One Call API 3.0 pour données complètes
    # Prévisions + alertes + données actuelles
```

---

## 📱 Interface Utilisateur - Intégration Frontend

### Composant Carte à modifier :
**Fichier : `/frontend/src/components/LandingPage.js`**

**Section actuelle (mockée) :**
```javascript
// Ligne ~280 - Section Interactive Map
<div className="map-container rounded-lg h-96 flex items-center justify-center relative">
  <Map className="w-16 h-16 mx-auto text-blue-600 mb-4" />
  <h3>Carte interactive</h3>
  // Données mockées des zones à risque
</div>
```

**À remplacer par :**
```javascript
// Intégration vraie carte avec niveaux de zoom
<WeatherMap 
  defaultView="satellite"  // NASA GIBS
  zoomTransition="local"   // OpenWeatherMap
  alertsEnabled={true}
/>
```

### Composant Prévisions à modifier :
**Section actuelle (mockée) :**
```javascript
// Ligne ~247 - Weather Forecast Section  
{weatherForecast.map((day) => {
  // Données mockées de mock.js
})}
```

**À remplacer par :**
```javascript
// API calls réelles
const [forecast, setForecast] = useState([]);
useEffect(() => {
  fetchWeatherForecast(); // Call backend API
}, []);
```

---

## 🗄️ Base de Données MongoDB

### Collections à créer :

#### 1. **weather_alerts**
```javascript
{
  _id: ObjectId,
  commune: "Pointe-à-Pitre",
  alert_type: "cyclone" | "inondation" | "forte_pluie",
  severity: "critique" | "élevé" | "modéré" | "faible", 
  message: "Vigilance rouge cyclone approche",
  active_from: DateTime,
  active_until: DateTime,
  coordinates: [lat, lon],
  created_at: DateTime
}
```

#### 2. **user_subscriptions**  
```javascript
{
  _id: ObjectId,
  email: "user@example.com",
  communes: ["Pointe-à-Pitre", "Basse-Terre"],
  alert_types: ["cyclone", "inondation"],
  phone: "+590590xxxxxx", // Optionnel SMS
  active: true,
  created_at: DateTime
}
```

#### 3. **weather_history**
```javascript
{
  _id: ObjectId,
  commune: "Basse-Terre",
  date: Date,
  temperature_max: 29,
  temperature_min: 24,
  precipitation: 15.5,
  wind_speed: 25,
  humidity: 85,
  source: "openweathermap" | "nasa"
}
```

---

## ⚡ STRATÉGIE CACHE INTELLIGENTE - 1000 CALLS OPTIMISÉS

### Architecture Cache Adaptative :
- **Backend** : 1000 calls OpenWeatherMap/jour répartis intelligemment
- **Cache MongoDB** : Stockage météo avec timestamps
- **Users** : Récupération instantanée depuis cache
- **Cron Jobs** : Fréquence adaptative selon risque météo

### Répartition des calls quotidiens :
```python
NORMAL_WEATHER = 60 minutes    # 24 calls/jour × 32 communes = 768 calls
MODERATE_RISK = 30 minutes     # Surveillance accrue
HIGH_RISK = 10 minutes         # Veille active  
CRITICAL = 5 minutes           # Urgence cyclone (232 calls réserve)
```

## 🔄 APIs Backend à Développer

### 1. Weather Cache Service (`/backend/services/weather_cache_service.py`)
```python
class WeatherCacheService:
    async def update_weather_data(self):
        # Call OpenWeatherMap → Cache MongoDB
        
    async def get_cached_forecast(self, commune: str):
        # Récupération instantanée depuis cache
        
    async def adaptive_update_frequency(self):
        # Fréquence adaptative selon niveau risque
        
    async def assess_weather_risk(self):
        # Analyse données → détermine fréquence mise à jour
```

### 2. Weather Service (`/backend/services/weather_service.py`)
```python
class WeatherService:
    async def get_satellite_view(self, bbox: str, zoom_level: int):
        # NASA GIBS integration (illimité gratuit)
        
    async def get_local_forecast_cached(self, commune: str):
        # Récupération depuis cache optimisé
        
    async def process_weather_alerts(self):
        # Analyse données cache → génère alertes automatiques
```

### 2. Alert Service (`/backend/services/alert_service.py`)
```python
class AlertService:
    async def send_email_alert(self, users: List[str], alert: dict):
        # Envoi email via service (SendGrid/AWS SES)
        
    async def send_sms_alert(self, phones: List[str], message: str):
        # Envoi SMS (Twilio/AWS SNS)
```

### 3. Subscription Service (`/backend/services/subscription_service.py`)
```python
class SubscriptionService:
    async def register_user(self, email: str, preferences: dict):
        # Inscription utilisateur
        
    async def get_subscribers_by_zone(self, commune: str, alert_type: str):
        # Récupérer abonnés pour alerte ciblée
```

---

## 🚀 Plan de Développement

### Phase 1 : APIs Backend
1. ✅ Créer modèles MongoDB
2. ✅ Intégration OpenWeatherMap (données locales)
3. ✅ Intégration NASA GIBS (vues satellite)
4. ✅ Endpoints API CRUD

### Phase 2 : Intégration Frontend  
1. ✅ Remplacer données mockées par appels API
2. ✅ Composant carte interactive hybride
3. ✅ Formulaires d'inscription fonctionnels
4. ✅ Système d'alertes temps réel

### Phase 3 : Services Avancés
1. ✅ Système d'envoi email/SMS
2. ✅ Cron jobs pour alertes automatiques
3. ✅ Analytics et monitoring
4. ✅ Optimisation performances

---

## 🔧 Variables d'Environnement Requises

```bash
# À ajouter dans backend/.env
OPENWEATHER_API_KEY=your_openweather_key
NASA_EARTHDATA_TOKEN=your_nasa_token  # Si nécessaire
SMTP_SERVER=your_email_service
SMS_API_KEY=your_sms_provider_key
```

---

## ✅ Checklist Intégration

- [ ] **NASA GIBS** : Images satellites région Antilles  
- [ ] **OpenWeatherMap** : Données météo 32 communes Guadeloupe
- [ ] **MongoDB** : Collections alertes, abonnements, historique
- [ ] **Frontend** : Remplacement mock.js par APIs réelles
- [ ] **Alertes** : Email/SMS automatiques par zone
- [ ] **Tests** : Validation intégration hybride

**L'approche hybride NASA + OpenWeatherMap offrira une expérience utilisateur exceptionnelle avec le meilleur des deux mondes : vision satellitaire globale et précision locale.**