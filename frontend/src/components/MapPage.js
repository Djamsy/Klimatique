import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';
import { 
  MapPin, 
  Shield,
  ArrowLeft,
  Users,
  AlertTriangle,
  Info
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
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
    riskFactors: ["Inondation urbaine", "Cyclones"],
    slug: "pointe-a-pitre"
  },
  { 
    name: "Basse-Terre", 
    coordinates: [16.0074, -61.7056], 
    population: "10,800",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Fortes pluies", "Cyclones"],
    slug: "basse-terre"
  },
  { 
    name: "Sainte-Anne", 
    coordinates: [16.2276, -61.3825], 
    population: "24,000",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Submersion marine"],
    slug: "sainte-anne"
  },
  { 
    name: "Le Moule", 
    coordinates: [16.3336, -61.3503], 
    population: "22,000",
    type: "côtière",
    riskFactors: ["Vents violents", "Houle", "Sécheresse"],
    slug: "le-moule"
  },
  { 
    name: "Saint-François", 
    coordinates: [16.2500, -61.2667], 
    population: "13,500",
    type: "côtière",
    riskFactors: ["Cyclones", "Submersion marine"],
    slug: "saint-francois"
  },
  { 
    name: "Gosier", 
    coordinates: [16.1833, -61.5167], 
    population: "28,000",
    type: "urbaine",
    riskFactors: ["Inondation", "Cyclones"],
    slug: "gosier"
  },
  { 
    name: "Petit-Bourg", 
    coordinates: [16.1833, -61.5833], 
    population: "25,000",
    type: "rurale",
    riskFactors: ["Inondation rivières", "Glissements terrain"],
    slug: "petit-bourg"
  },
  { 
    name: "Lamentin", 
    coordinates: [16.2500, -61.6000], 
    population: "16,500",
    type: "urbaine",
    riskFactors: ["Inondation", "Vents forts"],
    slug: "lamentin"
  },
  { 
    name: "Capesterre-Belle-Eau", 
    coordinates: [16.0450, -61.5675], 
    population: "19,000",
    type: "montagne",
    riskFactors: ["Cyclones", "Pluies torrentielles", "Coulées boue"],
    slug: "capesterre-belle-eau"
  },
  { 
    name: "Bouillante", 
    coordinates: [16.1333, -61.7667], 
    population: "7,300",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Vents violents"],
    slug: "bouillante"
  },
  { 
    name: "Deshaies", 
    coordinates: [16.2994, -61.7944], 
    population: "4,200",
    type: "côtière",
    riskFactors: ["Submersion marine", "Cyclones"],
    slug: "deshaies"
  },
  { 
    name: "Saint-Claude", 
    coordinates: [16.0333, -61.6833], 
    population: "10,200",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Fortes pluies"],
    slug: "saint-claude"
  }
];

// Composant pour créer des icônes personnalisées selon le risque
const createCustomIcon = (riskLevel, isLarge = false) => {
  const colors = {
    'faible': '#22c55e',
    'modéré': '#f59e0b', 
    'élevé': '#ea580c',
    'critique': '#dc2626'
  };
  
  const color = colors[riskLevel] || '#22c55e';
  const size = isLarge ? 30 : 24;
  const innerSize = isLarge ? 12 : 10;
  
  return L.divIcon({
    html: `
      <div style="
        background-color: ${color}; 
        border: 3px solid white; 
        border-radius: 50%; 
        width: ${size}px; 
        height: ${size}px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: transform 0.2s ease;
      " onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'">
        <div style="
          width: ${innerSize}px; 
          height: ${innerSize}px; 
          background-color: white; 
          border-radius: 50%;
        "></div>
      </div>
    `,
    className: 'custom-marker',
    iconSize: [size, size],
    iconAnchor: [size/2, size/2]
  });
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

const MapPage = () => {
  const navigate = useNavigate();
  const [weatherByCommune, setWeatherByCommune] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedInfo, setSelectedInfo] = useState(null);

  useEffect(() => {
    loadWeatherForCommunes();
  }, []);

  const loadWeatherForCommunes = async () => {
    setLoading(true);
    try {
      const communeNames = GUADELOUPE_COMMUNES.slice(0, 8).map(c => c.name);
      const weatherData = await CachedWeatherService.getMultipleWeatherWithCache(communeNames);
      setWeatherByCommune(weatherData);
    } catch (error) {
      console.error('Error loading weather for communes:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCommuneRiskLevel = (communeName) => {
    const weather = weatherByCommune[communeName];
    if (weather && weather.forecast && weather.forecast[0]) {
      return weather.forecast[0].risk_level;
    }
    return 'faible';
  };

  const handleCommuneClick = (commune) => {
    navigate(`/commune/${commune.slug}`);
  };

  const handleBackToHome = () => {
    navigate('/');
  };

  // Centre de la Guadeloupe
  const guadeloupeCenter = [16.25, -61.55];

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <header className="bg-white shadow-sm border-b z-50 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Button
                variant="ghost"
                onClick={handleBackToHome}
                className="mr-4 hover:bg-gray-100"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Accueil
              </Button>
              <Shield className="h-8 w-8 text-blue-800 mr-3" />
              <span className="text-xl font-bold text-blue-800">Météo Sentinelle - Carte Interactive</span>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="outline" className="hidden sm:flex">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Données NASA temps réel
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Instruction Banner */}
      <div className="bg-blue-50 border-b border-blue-200 py-3 px-4 z-40 relative">
        <div className="max-w-7xl mx-auto flex items-center justify-center">
          <Info className="w-4 h-4 text-blue-600 mr-2" />
          <span className="text-blue-800 font-medium">
            Vue satellite • Cliquez sur une commune pour voir les détails météorologiques et les risques
          </span>
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 relative">
        <MapContainer
          center={guadeloupeCenter}
          zoom={9}
          style={{ height: '100%', width: '100%' }}
          zoomControl={true}
        >
          <TileLayer
            attribution='Satellite imagery © <a href="https://www.google.com/maps">Google</a> | <a href="https://meteo-sentinelle.gp">Météo Sentinelle</a>'
            url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
          />
          
          {GUADELOUPE_COMMUNES.map((commune, index) => {
            const riskLevel = getCommuneRiskLevel(commune.name);
            const weather = weatherByCommune[commune.name];
            const currentTemp = weather?.current ? Math.round(weather.current.temperature_current || weather.current.temperature_max) : null;
            
            return (
              <Marker
                key={index}
                position={commune.coordinates}
                icon={createCustomIcon(riskLevel, true)}
                eventHandlers={{
                  click: () => handleCommuneClick(commune)
                }}
              >
                <Popup
                  className="custom-popup"
                  closeButton={true}
                  maxWidth={280}
                  minWidth={250}
                >
                  <Card className="border-0 shadow-none">
                    <CardContent className="p-4">
                      <div className="text-center space-y-3">
                        <div>
                          <h3 className="font-bold text-lg text-gray-900">{commune.name}</h3>
                          <p className="text-sm text-gray-600">
                            <Users className="inline w-3 h-3 mr-1" />
                            {commune.population} habitants • {commune.type}
                          </p>
                        </div>
                        
                        {currentTemp && (
                          <div className="bg-blue-50 rounded-lg p-3">
                            <div className="text-2xl font-bold text-blue-800">
                              {currentTemp}°C
                            </div>
                            <div className="text-sm text-blue-600">
                              {weather.current.weather_description}
                            </div>
                          </div>
                        )}
                        
                        <Badge 
                          className="text-sm px-3 py-1"
                          style={{ 
                            backgroundColor: getRiskColor(riskLevel) + '20',
                            color: getRiskColor(riskLevel),
                            border: `1px solid ${getRiskColor(riskLevel)}60`
                          }}
                        >
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          Risque {riskLevel}
                        </Badge>
                        
                        <Button 
                          className="w-full mt-3 bg-blue-600 hover:bg-blue-700"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCommuneClick(commune);
                          }}
                        >
                          <MapPin className="w-4 h-4 mr-2" />
                          Voir tous les détails
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Légende flottante */}
        <div className="absolute bottom-6 left-6 bg-white rounded-lg shadow-lg p-4 z-50 max-w-xs">
          <h4 className="font-semibold text-gray-900 mb-3">Légende des risques</h4>
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow"></div>
              <span className="text-sm">Risque faible</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-yellow-500 rounded-full border-2 border-white shadow"></div>
              <span className="text-sm">Risque modéré</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-orange-500 rounded-full border-2 border-white shadow"></div>
              <span className="text-sm">Risque élevé</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow"></div>
              <span className="text-sm">Risque critique</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-600">
              <Shield className="inline w-3 h-3 mr-1" />
              Vue satellite • Données NASA • Temps réel
            </p>
          </div>
        </div>

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 shadow-xl">
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <span className="text-gray-700">Chargement des données météo NASA...</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MapPage;