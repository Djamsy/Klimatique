import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { 
  MapPin, 
  AlertTriangle, 
  Wind, 
  CloudRain, 
  Thermometer, 
  Droplets,
  Clock,
  X
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { CachedWeatherService } from '../services/weatherService';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in react-leaflet
import L from 'leaflet';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Communes de Guadeloupe avec coordonnées précises
const GUADELOUPE_COMMUNES = [
  { 
    name: "Pointe-à-Pitre", 
    coordinates: [16.2415, -61.5328], 
    population: "16,000",
    type: "urbaine",
    riskFactors: ["Inondation urbaine", "Cyclones"]
  },
  { 
    name: "Basse-Terre", 
    coordinates: [16.0074, -61.7056], 
    population: "10,800",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Fortes pluies", "Cyclones"]
  },
  { 
    name: "Sainte-Anne", 
    coordinates: [16.2276, -61.3825], 
    population: "24,000",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Submersion marine"]
  },
  { 
    name: "Le Moule", 
    coordinates: [16.3336, -61.3503], 
    population: "22,000",
    type: "côtière",
    riskFactors: ["Vents violents", "Houle", "Sécheresse"]
  },
  { 
    name: "Saint-François", 
    coordinates: [16.2500, -61.2667], 
    population: "13,500",
    type: "côtière",
    riskFactors: ["Cyclones", "Submersion marine"]
  },
  { 
    name: "Gosier", 
    coordinates: [16.1833, -61.5167], 
    population: "28,000",
    type: "urbaine",
    riskFactors: ["Inondation", "Cyclones"]
  },
  { 
    name: "Petit-Bourg", 
    coordinates: [16.1833, -61.5833], 
    population: "25,000",
    type: "rurale",
    riskFactors: ["Inondation rivières", "Glissements terrain"]
  },
  { 
    name: "Lamentin", 
    coordinates: [16.2500, -61.6000], 
    population: "16,500",
    type: "urbaine",
    riskFactors: ["Inondation", "Vents forts"]
  },
  { 
    name: "Capesterre-Belle-Eau", 
    coordinates: [16.0450, -61.5675], 
    population: "19,000",
    type: "montagne",
    riskFactors: ["Cyclones", "Pluies torrentielles", "Coulées boue"]
  },
  { 
    name: "Bouillante", 
    coordinates: [16.1333, -61.7667], 
    population: "7,300",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Vents violents"]
  },
  { 
    name: "Deshaies", 
    coordinates: [16.2994, -61.7944], 
    population: "4,200",
    type: "côtière",
    riskFactors: ["Submersion marine", "Cyclones"]
  },
  { 
    name: "Saint-Claude", 
    coordinates: [16.0333, -61.6833], 
    population: "10,200",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Fortes pluies"]
  }
];

// Composant pour créer des icônes personnalisées selon le risque
const createCustomIcon = (riskLevel) => {
  const colors = {
    'faible': '#22c55e',
    'modéré': '#f59e0b', 
    'élevé': '#ea580c',
    'critique': '#dc2626'
  };
  
  const color = colors[riskLevel] || '#22c55e';
  
  return L.divIcon({
    html: `
      <div style="
        background-color: ${color}; 
        border: 3px solid white; 
        border-radius: 50%; 
        width: 20px; 
        height: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          width: 8px; 
          height: 8px; 
          background-color: white; 
          border-radius: 50%;
        "></div>
      </div>
    `,
    className: 'custom-marker',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });
};

const CommuneDetailModal = ({ commune, weatherData, isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [detailedWeather, setDetailedWeather] = useState(null);

  useEffect(() => {
    if (isOpen && commune) {
      loadDetailedWeather();
    }
  }, [isOpen, commune]);

  const loadDetailedWeather = async () => {
    setLoading(true);
    try {
      const data = await CachedWeatherService.getWeatherWithCache(commune.name);
      setDetailedWeather(data);
    } catch (error) {
      console.error('Error loading detailed weather:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (riskLevel) => {
    const colors = {
      'faible': '#22c55e',
      'modéré': '#f59e0b',
      'élevé': '#ea580c', 
      'critique': '#dc2626'
    };
    return colors[riskLevel] || '#22c55e';
  };

  if (!commune) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <MapPin className="w-6 h-6 text-blue-600" />
            {commune.name}
            <Badge variant="outline" className="ml-auto">
              {commune.type}
            </Badge>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* Informations générales */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Informations générales</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-gray-600">Population</span>
                  <p className="font-semibold">{commune.population} habitants</p>
                </div>
                <div>
                  <span className="text-sm text-gray-600">Coordonnées</span>
                  <p className="font-semibold">
                    {commune.coordinates[0].toFixed(3)}, {commune.coordinates[1].toFixed(3)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Météo actuelle */}
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : detailedWeather ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Thermometer className="w-5 h-5" />
                  Conditions météorologiques actuelles
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {Math.round(detailedWeather.current.temperature_current || detailedWeather.current.temperature_max)}°C
                    </div>
                    <p className="text-sm text-gray-600">Température</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600 flex items-center justify-center gap-1">
                      <Wind className="w-5 h-5" />
                      {Math.round(detailedWeather.current.wind_speed)}
                    </div>
                    <p className="text-sm text-gray-600">Vent (km/h)</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-500 flex items-center justify-center gap-1">
                      <CloudRain className="w-5 h-5" />
                      {detailedWeather.current.precipitation_probability}%
                    </div>
                    <p className="text-sm text-gray-600">Pluie</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-cyan-600 flex items-center justify-center gap-1">
                      <Droplets className="w-5 h-5" />
                      {detailedWeather.current.humidity}%
                    </div>
                    <p className="text-sm text-gray-600">Humidité</p>
                  </div>
                </div>

                <div className="text-center">
                  <p className="text-lg mb-2">{detailedWeather.current.weather_description}</p>
                  {detailedWeather.forecast && detailedWeather.forecast[0] && (
                    <Badge 
                      className="text-sm"
                      style={{ 
                        backgroundColor: getRiskColor(detailedWeather.forecast[0].risk_level) + '20',
                        color: getRiskColor(detailedWeather.forecast[0].risk_level),
                        border: `1px solid ${getRiskColor(detailedWeather.forecast[0].risk_level)}40`
                      }}
                    >
                      Risque {detailedWeather.forecast[0].risk_level}
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : null}

          {/* Prévisions 5 jours */}
          {detailedWeather && detailedWeather.forecast && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Prévisions 5 jours
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {detailedWeather.forecast.slice(0, 5).map((day, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="font-medium w-20">{day.day_name}</span>
                        <span className="text-sm text-gray-600">{day.weather_data.weather_description}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-semibold">
                          {Math.round(day.weather_data.temperature_max)}° / {Math.round(day.weather_data.temperature_min)}°
                        </span>
                        <Badge 
                          size="sm"
                          style={{ 
                            backgroundColor: getRiskColor(day.risk_level) + '20',
                            color: getRiskColor(day.risk_level)
                          }}
                        >
                          {day.risk_level}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Risques spécifiques */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-orange-500" />
                Risques spécifiques à la commune
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3">
                {commune.riskFactors.map((risk, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
                    <AlertTriangle className="w-4 h-4 text-orange-500 flex-shrink-0" />
                    <span>{risk}</span>
                  </div>
                ))}
              </div>
              
              {detailedWeather && detailedWeather.forecast && detailedWeather.forecast[0] && detailedWeather.forecast[0].risk_factors && (
                <div className="mt-4">
                  <h4 className="font-semibold mb-2">Risques météorologiques actuels :</h4>
                  <div className="grid gap-2">
                    {detailedWeather.forecast[0].risk_factors.map((factor, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm">
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span>{factor}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Alertes actives */}
          {detailedWeather && detailedWeather.alerts && detailedWeather.alerts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg text-red-600">🚨 Alertes actives</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {detailedWeather.alerts.map((alert, index) => (
                    <div key={index} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <h4 className="font-semibold text-red-800">{alert.title}</h4>
                      <p className="text-red-700 text-sm mt-1">{alert.message}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

const InteractiveMap = () => {
  const [selectedCommune, setSelectedCommune] = useState(null);
  const [weatherByCommune, setWeatherByCommune] = useState({});
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWeatherForCommunes();
  }, []);

  const loadWeatherForCommunes = async () => {
    setLoading(true);
    try {
      const communeNames = GUADELOUPE_COMMUNES.slice(0, 6).map(c => c.name); // Limite pour performance
      const weatherData = await CachedWeatherService.getMultipleWeatherWithCache(communeNames);
      setWeatherByCommune(weatherData);
    } catch (error) {
      console.error('Error loading weather for communes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCommuneClick = (commune) => {
    setSelectedCommune(commune);
    setIsModalOpen(true);
  };

  const getCommuneRiskLevel = (communeName) => {
    const weather = weatherByCommune[communeName];
    if (weather && weather.forecast && weather.forecast[0]) {
      return weather.forecast[0].risk_level;
    }
    return 'faible';
  };

  // Centre de la Guadeloupe
  const guadeloupeCenter = [16.25, -61.55];

  return (
    <div className="w-full">
      <div className="mb-4 text-center">
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          Carte interactive de la Guadeloupe
        </h3>
        <p className="text-gray-600">
          Cliquez sur une commune pour voir les détails météorologiques et les risques
        </p>
      </div>

      <div className="rounded-lg overflow-hidden border-2 border-gray-200" style={{ height: '500px' }}>
        <MapContainer
          center={guadeloupeCenter}
          zoom={10}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {GUADELOUPE_COMMUNES.map((commune, index) => {
            const riskLevel = getCommuneRiskLevel(commune.name);
            
            return (
              <Marker
                key={index}
                position={commune.coordinates}
                icon={createCustomIcon(riskLevel)}
                eventHandlers={{
                  click: () => handleCommuneClick(commune)
                }}
              >
                <Popup
                  closeButton={true}
                  minWidth={window.innerWidth < 768 ? 120 : 150}
                  maxWidth={window.innerWidth < 768 ? 180 : 200}
                  autoPan={true}
                  keepInView={true}
                  closeOnEscapeKey={true}
                  autoClose={true}
                  closeOnClick={true}
                >
                  <div className="text-center p-1">
                    <h4 className="font-semibold text-xs sm:text-sm">{commune.name}</h4>
                    <p className="text-xs text-gray-600 mb-1">{commune.population} hab.</p>
                    <Badge 
                      className="mb-2 text-xs px-1 py-0"
                      style={{ 
                        backgroundColor: getRiskColor(riskLevel) + '20',
                        color: getRiskColor(riskLevel)
                      }}
                    >
                      {riskLevel}
                    </Badge>
                    <br/>
                    <Button 
                      size="sm" 
                      className="text-xs py-1 px-2 h-6"
                      onClick={() => handleCommuneClick(commune)}
                    >
                      Détails
                    </Button>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Légende */}
      <div className="mt-4 flex flex-wrap gap-4 justify-center">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded-full"></div>
          <span className="text-sm">Risque faible</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-500 rounded-full"></div>
          <span className="text-sm">Risque modéré</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-500 rounded-full"></div>
          <span className="text-sm">Risque élevé</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded-full"></div>
          <span className="text-sm">Risque critique</span>
        </div>
      </div>

      {/* Modal de détails */}
      <CommuneDetailModal
        commune={selectedCommune}
        weatherData={weatherByCommune[selectedCommune?.name]}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};

// Fonction utilitaire pour les couleurs
const getRiskColor = (riskLevel) => {
  const colors = {
    'faible': '#22c55e',
    'modéré': '#f59e0b',
    'élevé': '#ea580c',
    'critique': '#dc2626'
  };
  return colors[riskLevel] || '#22c55e';
};

export default InteractiveMap;