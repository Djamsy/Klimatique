import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';
import { 
  MapPin, 
  Shield,
  ArrowLeft,
  Users,
  AlertTriangle,
  Info,
  Loader2,
  Layers,
  Cloud,
  CloudRain,
  Thermometer,
  Eye,
  EyeOff,
  Brain,
  Globe,
  Activity
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader } from './ui/card';
import { Switch } from './ui/switch';
import { CachedWeatherService, CycloneAIService } from '../services/weatherService';
import { GUADELOUPE_COMMUNES } from '../data/communesData';
import WeatherOverlays from './WeatherOverlays';
import PluviometerWidget from './PluviometerWidget';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in react-leaflet
import L from 'leaflet';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// NASA GIBS Overlay Layers
const NASA_GIBS_LAYERS = {
  clouds: {
    name: "Nuages",
    url: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/{time}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
    icon: Cloud,
    description: "Couverture nuageuse en temps réel"
  },
  cloudTemp: {
    name: "Température nuages",
    url: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Cloud_Top_Temp_Day/default/{time}/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png",
    icon: Thermometer,
    description: "Température au sommet des nuages"
  },
  precipitation: {
    name: "Précipitations",
    url: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/GPM_3IMERGHH_06_precipitation/default/{time}/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png",
    icon: CloudRain,
    description: "Précipitations satellite"
  }
};

// Composant pour gérer les couches NASA GIBS
const NASAOverlayController = ({ map, activeOverlays, setActiveOverlays }) => {
  const [overlayLayers, setOverlayLayers] = useState({});

  // Génère la date actuelle pour NASA GIBS (format YYYY-MM-DD)
  const getCurrentDate = () => {
    const now = new Date();
    // NASA GIBS a souvent 1-2 jours de retard
    now.setDate(now.getDate() - 1);
    return now.toISOString().split('T')[0];
  };

  useEffect(() => {
    if (!map) return;

    const currentDate = getCurrentDate();
    const layers = {};
    
    // Limites géographiques de la Guadeloupe
    const guadeloupeBounds = [
      [15.8, -61.9],  // Sud-Ouest
      [16.6, -61.0]   // Nord-Est
    ];

    // Crée les couches overlay pour chaque type
    Object.entries(NASA_GIBS_LAYERS).forEach(([key, config]) => {
      const url = config.url.replace('{time}', currentDate);
      
      const layer = L.tileLayer(url, {
        attribution: 'NASA GIBS',
        opacity: 0.7,
        maxZoom: 12,  // Augmenté de 9 à 12
        minZoom: 8,   // Ajout limite minimum
        tileSize: 256,
        bounds: guadeloupeBounds  // Limite à la Guadeloupe
      });
      
      layers[key] = layer;
    });

    setOverlayLayers(layers);

    return () => {
      // Nettoie les couches à la destruction
      Object.values(layers).forEach(layer => {
        if (map.hasLayer(layer)) {
          map.removeLayer(layer);
        }
      });
    };
  }, [map]);

  useEffect(() => {
    if (!map || !overlayLayers) return;

    // Gère l'affichage/masquage des couches selon l'état
    Object.entries(overlayLayers).forEach(([key, layer]) => {
      if (activeOverlays[key]) {
        if (!map.hasLayer(layer)) {
          map.addLayer(layer);
        }
      } else {
        if (map.hasLayer(layer)) {
          map.removeLayer(layer);
        }
      }
    });
  }, [map, overlayLayers, activeOverlays]);

  return null;
};

// Hook pour récupérer la référence de la carte
const MapController = ({ onMapReady }) => {
  const map = useMap();
  
  useEffect(() => {
    if (map && onMapReady) {
      onMapReady(map);
    }
  }, [map, onMapReady]);

  return null;
};

// Composant pour créer des icônes personnalisées selon le risque
const createCustomIcon = (riskLevel, isLarge = false) => {
  const colors = {
    'faible': '#22c55e',
    'modéré': '#f59e0b', 
    'élevé': '#ea580c',
    'critique': '#dc2626'
  };
  
  const color = colors[riskLevel] || '#22c55e';
  const size = isLarge ? 28 : 22;
  const innerSize = isLarge ? 10 : 8;
  
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
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [map, setMap] = useState(null);
  const [showLayerControls, setShowLayerControls] = useState(false);
  const [showPluviometer, setShowPluviometer] = useState(false);
  const [selectedCommune, setSelectedCommune] = useState(null);
  const [activeOverlays, setActiveOverlays] = useState({
    clouds: false,
    cloudTemp: false,
    precipitation: false
  });
  const [globalRisk, setGlobalRisk] = useState(null);
  const [showGlobalRisk, setShowGlobalRisk] = useState(false);
  const [cacheStats, setCacheStats] = useState(null);

  useEffect(() => {
    loadWeatherForCommunes();
    loadGlobalRisk();
    loadCacheStats();
  }, []);

  const loadCacheStats = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/cache/stats`);
      if (response.ok) {
        const stats = await response.json();
        setCacheStats(stats);
      }
    } catch (error) {
      console.error('Error loading cache stats:', error);
    }
  };

  const handleOverlayChange = (type, active) => {
    setActiveOverlays(prev => ({
      ...prev,
      [type]: active
    }));
  };

  const handleCommuneSelect = (commune) => {
    setSelectedCommune(commune);
    setShowPluviometer(true);
  };

  const loadGlobalRisk = async () => {
    try {
      const riskData = await CycloneAIService.getGlobalCycloneRisk();
      setGlobalRisk(riskData);
    } catch (error) {
      console.error('Error loading global risk:', error);
    }
  };

  const loadWeatherForCommunes = async () => {
    setLoading(true);
    setLoadingProgress(0);

    try {
      // Charge par lots pour optimiser les performances
      const batchSize = 6;
      const communes = GUADELOUPE_COMMUNES.map(c => c.name);
      const allWeatherData = {};
      
      for (let i = 0; i < communes.length; i += batchSize) {
        const batch = communes.slice(i, i + batchSize);
        
        try {
          const batchData = await CachedWeatherService.getMultipleWeatherWithCache(batch);
          Object.assign(allWeatherData, batchData);
          
          // Met à jour le progrès
          const progress = Math.min(((i + batchSize) / communes.length) * 100, 100);
          setLoadingProgress(progress);
        } catch (error) {
          console.error(`Error loading batch ${i}-${i + batchSize}:`, error);
        }
        
        // Petit délai entre les lots
        if (i + batchSize < communes.length) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      setWeatherByCommune(allWeatherData);
    } catch (error) {
      console.error('Error loading weather for communes:', error);
    } finally {
      setLoading(false);
      setLoadingProgress(100);
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

  const handleMapReady = (mapInstance) => {
    setMap(mapInstance);
  };

  const toggleOverlay = (overlayKey) => {
    setActiveOverlays(prev => ({
      ...prev,
      [overlayKey]: !prev[overlayKey]
    }));
  };

  const toggleAllOverlays = (enabled) => {
    const newState = {};
    Object.keys(activeOverlays).forEach(key => {
      newState[key] = enabled;
    });
    setActiveOverlays(newState);
  };

  // Centre et limites de la Guadeloupe pour vue d'ensemble
  const guadeloupeCenter = [16.25, -61.55];
  
  // Limites géographiques de l'archipel de Guadeloupe (optimisation données)
  const guadeloupeBounds = [
    [15.8, -61.9],  // Sud-Ouest (Basse-Terre sud)
    [16.6, -61.0]   // Nord-Est (Grande-Terre nord)
  ];

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header - Mobile optimized */}
      <header className="bg-white shadow-sm border-b z-50 relative">
        <div className="max-w-7xl mx-auto px-2 sm:px-4 lg:px-8">
          <div className="flex justify-between items-center py-2 sm:py-4">
            <div className="flex items-center space-x-2 sm:space-x-4">
              <Button
                variant="ghost"
                onClick={handleBackToHome}
                className="hover:bg-gray-100 p-2 sm:px-4"
                size="sm"
              >
                <ArrowLeft className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">Accueil</span>
              </Button>
              <div className="flex items-center">
                <Shield className="h-6 w-6 sm:h-8 sm:w-8 text-blue-800 mr-2 sm:mr-3" />
                <span className="text-sm sm:text-xl font-bold text-blue-800">
                  <span className="sm:hidden">Carte</span>
                  <span className="hidden sm:inline">Klimaclique - Carte Interactive</span>
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-2 sm:space-x-4">
              {/* Mobile controls */}
              <Button
                variant="outline"
                onClick={() => setShowLayerControls(!showLayerControls)}
                className="sm:hidden p-2"
                size="sm"
              >
                <Layers className="w-4 h-4" />
              </Button>
              {/* Desktop controls */}
              <Button
                variant="outline"
                onClick={() => setShowLayerControls(!showLayerControls)}
                className="hidden sm:flex"
              >
                <Layers className="w-4 h-4 mr-2" />
                Couches NASA
              </Button>
              <Badge variant="outline" className="hidden lg:flex text-xs">
                <AlertTriangle className="w-3 h-3 mr-1" />
                {GUADELOUPE_COMMUNES.length} communes • Données NASA
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Instruction Banner - Mobile optimized */}
      <div className="bg-blue-50 border-b border-blue-200 py-2 sm:py-3 px-2 sm:px-4 z-40 relative">
        <div className="max-w-7xl mx-auto flex items-center justify-center">
          <Info className="w-3 h-3 sm:w-4 sm:h-4 text-blue-600 mr-2 flex-shrink-0" />
          <span className="text-xs sm:text-sm text-blue-800 font-medium text-center">
            <span className="sm:hidden">Cliquez sur une commune</span>
            <span className="hidden sm:inline">Vue satellite Guadeloupe • Navigation limitée à l'archipel • Cliquez sur une commune pour les détails</span>
          </span>
        </div>
      </div>

      {/* Map Container - Mobile optimized */}
      <div className="flex-1 relative">
        <MapContainer
          center={guadeloupeCenter}
          zoom={window.innerWidth < 768 ? 8 : 9} // Zoom réduit sur mobile
          minZoom={8}
          maxZoom={12}
          maxBounds={guadeloupeBounds}
          maxBoundsViscosity={1.0}
          style={{ height: '100%', width: '100%' }}
          zoomControl={window.innerWidth >= 768} // Masquer les contrôles zoom sur mobile
          touchZoom={true} // Activer le zoom tactile
          doubleClickZoom={true}
          scrollWheelZoom={false} // Désactiver le zoom avec scroll pour éviter les conflits
          dragging={true}
        >
          {/* Couche de base satellite */}
          <TileLayer
            attribution='Satellite imagery © <a href="https://www.google.com/maps">Google</a> | <a href="https://klimaclique.gp">Klimaclique</a>'
            url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
          />
          
          {/* Contrôleur de carte pour obtenir la référence */}
          <MapController onMapReady={handleMapReady} />
          
          {/* Overlays météo OpenWeatherMap */}
          <WeatherOverlays onOverlayChange={handleOverlayChange} />
          
          {/* Contrôleur des couches NASA GIBS */}
          {map && (
            <NASAOverlayController 
              map={map} 
              activeOverlays={activeOverlays}
              setActiveOverlays={setActiveOverlays}
            />
          )}
          
          {/* Markers des communes */}
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
                  closeButton={false}
                  minWidth={window.innerWidth < 768 ? 200 : 250}
                  maxWidth={window.innerWidth < 768 ? 280 : 300}
                  autoPan={true}
                  keepInView={true}
                >
                  <Card className="border-0 shadow-none">
                    <CardHeader className="pb-2 sm:pb-3">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-sm sm:text-lg text-gray-900">
                          {commune.name}
                        </h3>
                        <Badge 
                          className="text-xs px-2 py-1"
                          style={{ 
                            backgroundColor: getRiskColor(riskLevel) + '20',
                            color: getRiskColor(riskLevel),
                            border: `1px solid ${getRiskColor(riskLevel)}40`
                          }}
                        >
                          {riskLevel}
                        </Badge>
                      </div>
                    </CardHeader>
                    
                    <CardContent className="pt-0">
                      {weather ? (
                        <div className="space-y-2 sm:space-y-3">
                          <div className="grid grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm">
                            <div className="flex items-center justify-between">
                              <span className="text-gray-600">Temp:</span>
                              <span className="font-medium">
                                {Math.round(weather.current?.temperature_max || 0)}°C
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-600">Vent:</span>
                              <span className="font-medium">
                                {Math.round(weather.current?.wind_speed || 0)} km/h
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-600">Humidité:</span>
                              <span className="font-medium">
                                {Math.round(weather.current?.humidity || 0)}%
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-600">Pluie:</span>
                              <span className="font-medium">
                                {Math.round(weather.current?.precipitation_probability || 0)}%
                              </span>
                            </div>
                          </div>
                          
                          <div className="flex flex-col sm:flex-row space-y-1 sm:space-y-0 sm:space-x-2 pt-2 sm:pt-3 border-t">
                            <Button 
                              size="sm"
                              className="w-full bg-blue-600 hover:bg-blue-700 text-xs sm:text-sm py-1 sm:py-2"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCommuneClick(commune);
                              }}
                            >
                              <MapPin className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                              Détails
                            </Button>
                            
                            <Button 
                              size="sm"
                              variant="outline"
                              className="w-full border-blue-200 text-blue-600 hover:bg-blue-50 text-xs sm:text-sm py-1 sm:py-2"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedCommune(commune);
                                setShowPluviometer(true);
                              }}
                            >
                              <Activity className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                              Pluie
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-4 sm:py-6">
                          <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin mx-auto text-blue-600 mb-2" />
                          <p className="text-xs sm:text-sm text-gray-600">Chargement...</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Contrôles des couches NASA GIBS - Mobile optimized */}
        {showLayerControls && (
          <div className="absolute top-4 left-2 right-2 sm:top-6 sm:left-6 sm:right-auto bg-white rounded-lg shadow-lg p-3 sm:p-4 z-50 sm:min-w-80">
            <div className="flex justify-between items-center mb-3 sm:mb-4">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2 text-sm sm:text-base">
                <Layers className="w-4 h-4 sm:w-5 sm:h-5" />
                <span className="sm:hidden">Couches NASA</span>
                <span className="hidden sm:inline">Couches NASA GIBS</span>
              </h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowLayerControls(false)}
                className="h-6 w-6 sm:h-8 sm:w-8 p-0"
              >
                ×
              </Button>
            </div>
            
            <div className="space-y-3 sm:space-y-4">
              <div className="flex justify-between items-center pb-2 border-b">
                <span className="text-xs sm:text-sm font-medium">Contrôles rapides</span>
                <div className="flex gap-1 sm:gap-2">
                  <Button size="sm" variant="outline" onClick={() => toggleAllOverlays(true)} className="px-2 py-1 text-xs sm:px-3 sm:py-2 sm:text-sm">
                    <Eye className="w-3 h-3 sm:mr-1" />
                    <span className="hidden sm:inline">Tout</span>
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => toggleAllOverlays(false)} className="px-2 py-1 text-xs sm:px-3 sm:py-2 sm:text-sm">
                    <EyeOff className="w-3 h-3 sm:mr-1" />
                    <span className="hidden sm:inline">Aucun</span>
                  </Button>
                </div>
              </div>
              
              {Object.entries(NASA_GIBS_LAYERS).map(([key, config]) => {
                const IconComponent = config.icon;
                return (
                  <div key={key} className="flex items-center justify-between py-1 sm:py-2">
                    <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                      <IconComponent className="w-3 h-3 sm:w-4 sm:h-4 text-blue-600 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-xs sm:text-sm truncate">{config.name}</div>
                        <div className="text-xs text-gray-500 truncate sm:block hidden">{config.description}</div>
                      </div>
                    </div>
                    <Switch
                      checked={activeOverlays[key]}
                      onCheckedChange={() => toggleOverlay(key)}
                      className="ml-2 flex-shrink-0"
                    />
                  </div>
                );
              })}
            </div>
            
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                <Shield className="inline w-3 h-3 mr-1" />
                Données satellite NASA GIBS • Mise à jour quotidienne
              </p>
            </div>
          </div>
        )}

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
              Vue satellite • Couches NASA GIBS • Temps réel
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {GUADELOUPE_COMMUNES.length} communes de Guadeloupe
            </p>
          </div>
        </div>

        {/* Bouton de test pluviomètre */}
        <div className="absolute bottom-6 left-6 z-[1010]">
          <Button
            onClick={() => {
              setSelectedCommune({ name: 'Pointe-à-Pitre' });
              setShowPluviometer(true);
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg"
            size="lg"
          >
            <Activity className="w-5 h-5 mr-2" />
            Test Pluviomètre
          </Button>
        </div>

        {/* Panneau de droite avec pluviomètre */}
        {showPluviometer && selectedCommune && (
          <div className="absolute top-6 right-6 w-80 z-[1020] space-y-4">
            <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-xl p-4 border">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-gray-900 flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-blue-600" />
                  Pluviomètre
                </h4>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPluviometer(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <EyeOff className="w-4 h-4" />
                </Button>
              </div>
              <p className="text-sm text-gray-600">{selectedCommune.name}</p>
            </div>
            <PluviometerWidget commune={selectedCommune.name} />
          </div>
        )}

        {/* Stats flottantes - affichage conditionnel */}
        {!showPluviometer && (
          <div className="absolute top-6 right-6 bg-white/95 backdrop-blur-sm rounded-lg shadow-xl p-4 z-[1000] border">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-gray-900">Tableau de bord</h4>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowGlobalRisk(!showGlobalRisk)}
                  className={showGlobalRisk ? 'text-blue-600' : ''}
                >
                  <Brain className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowLayerControls(!showLayerControls)}
                  className={showLayerControls ? 'text-blue-600' : ''}
                >
                  <Layers className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            {showGlobalRisk && globalRisk ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b">
                  <span className="text-sm font-medium">Risque Global</span>
                  <Badge 
                    className="text-xs px-2 py-1"
                    style={{ 
                      backgroundColor: getRiskColor(globalRisk.global_risk_level) + '20',
                      color: getRiskColor(globalRisk.global_risk_level),
                      border: `1px solid ${getRiskColor(globalRisk.global_risk_level)}60`
                    }}
                  >
                    {globalRisk.global_risk_level}
                  </Badge>
                </div>
                
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div>
                    <div className="text-xl font-bold text-orange-600">{globalRisk.high_risk_count}</div>
                    <div className="text-xs text-gray-600">Risque élevé</div>
                  </div>
                  <div>
                    <div className="text-xl font-bold text-red-600">{globalRisk.critical_risk_count}</div>
                    <div className="text-xs text-gray-600">Critique</div>
                  </div>
                </div>
                
                {globalRisk.affected_communes.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-xs font-medium text-gray-700 mb-1">Communes à risque:</p>
                    <div className="flex flex-wrap gap-1">
                      {globalRisk.affected_communes.slice(0, 3).map((commune, index) => (
                        <span key={index} className="text-xs bg-orange-100 text-orange-800 px-1 py-0.5 rounded">
                          {commune}
                        </span>
                      ))}
                      {globalRisk.affected_communes.length > 3 && (
                        <span className="text-xs text-gray-500">+{globalRisk.affected_communes.length - 3}</span>
                      )}
                    </div>
                  </div>
                )}
                
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-500 flex items-center gap-1">
                    <Brain className="w-3 h-3" />
                    IA Prédictive • {new Date(globalRisk.last_analysis).toLocaleTimeString('fr-FR')}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div>
                    <div className="text-2xl font-bold text-blue-600">{GUADELOUPE_COMMUNES.length}</div>
                    <div className="text-xs text-gray-600">Communes</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-green-600">{Object.keys(weatherByCommune).length}</div>
                    <div className="text-xs text-gray-600">Actives</div>
                  </div>
                </div>
                
                {/* Statistiques cache */}
                {cacheStats && (
                  <div className="grid grid-cols-2 gap-3 text-center">
                    <div>
                      <div className="text-lg font-bold text-purple-600">
                        {cacheStats.cache_efficiency?.today_usage || 0}
                      </div>
                      <div className="text-xs text-gray-600">Appels API</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-cyan-600">
                        {Math.round(cacheStats.cache_efficiency?.efficiency_percent || 0)}%
                      </div>
                      <div className="text-xs text-gray-600">Efficacité</div>
                    </div>
                  </div>
                )}
                
                {Object.values(activeOverlays).some(Boolean) && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-xs text-gray-500 flex items-center gap-1">
                      <Layers className="w-3 h-3" />
                      {Object.entries(activeOverlays).filter(([k, v]) => v).length} couches actives
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 shadow-xl min-w-80">
              <div className="text-center mb-4">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900">Chargement des données NASA</h3>
                <p className="text-sm text-gray-600">
                  Récupération météo pour {GUADELOUPE_COMMUNES.length} communes...
                </p>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${loadingProgress}%` }}
                ></div>
              </div>
              <p className="text-center text-xs text-gray-500 mt-2">
                {Math.round(loadingProgress)}% complété
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MapPage;