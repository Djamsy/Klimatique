import React, { useState, useEffect } from 'react';
import { TileLayer, useMap } from 'react-leaflet';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Switch } from './ui/switch';
import { WeatherOverlayService } from '../services/weatherService';
import { 
  Cloud, 
  CloudRain, 
  Radar, 
  Layers, 
  Eye, 
  EyeOff,
  RefreshCw,
  Loader2,
  AlertTriangle
} from 'lucide-react';

const WeatherOverlays = ({ onOverlayChange }) => {
  const [overlays, setOverlays] = useState({
    clouds: { active: false, data: null, loading: false },
    precipitation: { active: false, data: null, loading: false },
    radar: { active: false, data: null, loading: false }
  });
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(Date.now());

  const map = useMap();

  useEffect(() => {
    // Rafraîchir automatiquement toutes les 10 minutes
    const interval = setInterval(() => {
      refreshActiveOverlays();
    }, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const refreshActiveOverlays = async () => {
    const activeOverlays = Object.entries(overlays).filter(([_, overlay]) => overlay.active);
    
    for (const [type, _] of activeOverlays) {
      await loadOverlay(type);
    }
  };

  const loadOverlay = async (type) => {
    try {
      setOverlays(prev => ({
        ...prev,
        [type]: { ...prev[type], loading: true }
      }));
      setError(null);

      let data;
      switch (type) {
        case 'clouds':
          data = await WeatherOverlayService.getCloudsOverlay();
          break;
        case 'precipitation':
          data = await WeatherOverlayService.getPrecipitationOverlay();
          break;
        case 'radar':
          data = await WeatherOverlayService.getRadarOverlay();
          break;
        default:
          throw new Error(`Type d'overlay non supporté: ${type}`);
      }
      
      setOverlays(prev => ({
        ...prev,
        [type]: {
          ...prev[type],
          data: data.data,
          loading: false
        }
      }));

      setLastRefresh(Date.now());

    } catch (err) {
      console.error(`Error loading ${type} overlay:`, err);
      setError(err.message);
      
      setOverlays(prev => ({
        ...prev,
        [type]: { ...prev[type], loading: false }
      }));
    }
  };

  const toggleOverlay = async (type) => {
    const isCurrentlyActive = overlays[type].active;
    
    // Activer/désactiver immédiatement
    setOverlays(prev => ({
      ...prev,
      [type]: {
        ...prev[type],
        active: !isCurrentlyActive
      }
    }));
    
    // Notifier le parent du changement
    if (onOverlayChange) {
      onOverlayChange(type, !isCurrentlyActive);
    }
    
    // Optionnel : charger les données en arrière-plan
    if (!isCurrentlyActive) {
      loadOverlay(type);
    }
  };

  const getOverlayIcon = (type) => {
    switch (type) {
      case 'clouds':
        return <Cloud className="h-4 w-4" />;
      case 'precipitation':
        return <CloudRain className="h-4 w-4" />;
      case 'radar':
        return <Radar className="h-4 w-4" />;
      default:
        return <Layers className="h-4 w-4" />;
    }
  };

  const getOverlayLabel = (type) => {
    switch (type) {
      case 'clouds':
        return 'Nuages';
      case 'precipitation':
        return 'Précipitations';
      case 'radar':
        return 'Radar';
      default:
        return type;
    }
  };

  const getOverlayColor = (type) => {
    switch (type) {
      case 'clouds':
        return 'text-gray-600';
      case 'precipitation':
        return 'text-blue-600';
      case 'radar':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  const renderTileOverlay = (type) => {
    const overlay = overlays[type];
    
    if (!overlay.active) {
      return null;
    }

    // Construire l'URL correcte pour les tiles OpenWeatherMap
    const apiKey = process.env.REACT_APP_OPENWEATHER_API_KEY;
    
    if (!apiKey) {
      console.error('OpenWeatherMap API key not found');
      return null;
    }
    
    let layerName;
    switch (type) {
      case 'clouds':
        layerName = 'clouds_new';
        break;
      case 'precipitation':
        layerName = 'precipitation_new';
        break;
      case 'radar':
        layerName = 'radar';
        break;
      default:
        return null;
    }
    
    const tileUrl = `https://tile.openweathermap.org/map/${layerName}/{z}/{x}/{y}.png?appid=${apiKey}`;
    
    console.log(`Rendering overlay ${type} with URL: ${tileUrl}`);
    
    return (
      <TileLayer
        key={`${type}-${lastRefresh}`}
        url={tileUrl}
        opacity={getOverlayOpacity(type)}
        zIndex={getOverlayZIndex(type)}
        attribution={`OpenWeatherMap ${type}`}
      />
    );
  };

  const getOverlayOpacity = (type) => {
    switch (type) {
      case 'clouds':
        return 0.6;
      case 'precipitation':
        return 0.7;
      case 'radar':
        return 0.8;
      default:
        return 0.5;
    }
  };

  const getOverlayZIndex = (type) => {
    switch (type) {
      case 'clouds':
        return 200;
      case 'precipitation':
        return 300;
      case 'radar':
        return 400;
      default:
        return 100;
    }
  };

  return (
    <>
      {/* Rendu des overlays sur la carte */}
      {Object.keys(overlays).map(type => renderTileOverlay(type))}
      
      {/* Panneau de contrôle */}
      <Card className="absolute top-20 left-6 bg-white/95 backdrop-blur-sm shadow-xl border z-[1010] w-64">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center space-x-2 text-sm">
            <Layers className="h-4 w-4 text-blue-600" />
            <span>Overlays Météo</span>
            <Badge variant="outline" className="ml-auto text-xs">
              {Object.values(overlays).filter(o => o.active).length}
            </Badge>
          </CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Contrôles des overlays */}
          <div className="space-y-3">
            {Object.entries(overlays).map(([type, overlay]) => (
              <div key={type} className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex items-center space-x-2">
                  <div className={getOverlayColor(type)}>
                    {getOverlayIcon(type)}
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    {getOverlayLabel(type)}
                  </span>
                  {overlay.loading && (
                    <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
                  )}
                  {overlay.active && (
                    <div className="w-2 h-2 bg-green-500 rounded-full" />
                  )}
                </div>
                
                <Switch
                  checked={overlay.active}
                  onCheckedChange={() => toggleOverlay(type)}
                  disabled={overlay.loading}
                />
              </div>
            ))}
          </div>

          {/* Informations */}
          <div className="pt-3 border-t border-gray-200">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center space-x-1">
                <RefreshCw className="h-3 w-3" />
                <span>Auto-refresh 10min</span>
              </div>
              <div>
                {new Date(lastRefresh).toLocaleTimeString('fr-FR', {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </div>
            </div>
          </div>

          {/* Légende */}
          <div className="space-y-2">
            <div className="text-xs font-medium text-gray-700">Légende</div>
            <div className="grid grid-cols-1 gap-1 text-xs">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-white border border-gray-300 rounded opacity-60"></div>
                <span className="text-gray-600">Nuages</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded opacity-70"></div>
                <span className="text-gray-600">Précipitations</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded opacity-80"></div>
                <span className="text-gray-600">Radar</span>
              </div>
            </div>
          </div>

          {/* Erreur */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-2">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                <span className="text-xs text-red-700">{error}</span>
              </div>
            </div>
          )}

          {/* Bouton de rafraîchissement manuel */}
          <Button
            variant="outline"
            size="sm"
            onClick={refreshActiveOverlays}
            className="w-full"
            disabled={Object.values(overlays).some(overlay => overlay.loading)}
          >
            <RefreshCw className="h-3 w-3 mr-2" />
            Rafraîchir
          </Button>
        </CardContent>
      </Card>
    </>
  );
};

export default WeatherOverlays;