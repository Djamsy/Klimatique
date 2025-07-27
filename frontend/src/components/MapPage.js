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
  Loader2
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { CachedWeatherService } from '../services/weatherService';
import { GUADELOUPE_COMMUNES } from '../data/communesData';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in react-leaflet
import L from 'leaflet';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

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

  useEffect(() => {
    loadWeatherForCommunes();
  }, []);

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

  // Centre de la Guadeloupe pour vue d'ensemble
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
                {GUADELOUPE_COMMUNES.length} communes • Données NASA
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
                  maxWidth={300}
                  minWidth={260}
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
                        
                        <div className="text-xs text-gray-500 mt-2">
                          <div className="grid grid-cols-2 gap-1">
                            {commune.riskFactors.slice(0, 2).map((risk, i) => (
                              <div key={i} className="truncate">• {risk}</div>
                            ))}
                          </div>
                        </div>
                        
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
            <p className="text-xs text-gray-500 mt-1">
              {GUADELOUPE_COMMUNES.length} communes de Guadeloupe
            </p>
          </div>
        </div>

        {/* Stats flottantes */}
        <div className="absolute top-6 right-6 bg-white rounded-lg shadow-lg p-4 z-50">
          <h4 className="font-semibold text-gray-900 mb-2">Couverture</h4>
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
        </div>

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