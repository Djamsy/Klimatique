import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { WeatherOverlayService } from '../services/weatherService';
import { 
  CloudRain, 
  Droplets, 
  TrendingUp, 
  Clock, 
  AlertTriangle,
  BarChart3,
  Activity
} from 'lucide-react';

const PluviometerWidget = ({ commune, className = "" }) => {
  const [pluvioData, setPluvioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (commune) {
      fetchPluviometerData();
      // Mise à jour toutes les 5 minutes
      const interval = setInterval(fetchPluviometerData, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [commune]);

  const fetchPluviometerData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/weather/pluviometer/${commune}`
      );
      
      if (!response.ok) {
        throw new Error('Erreur lors du chargement des données pluviométriques');
      }
      
      const data = await response.json();
      setPluvioData(data);
      
    } catch (err) {
      console.error('Error fetching pluviometer data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getIntensityColor = (intensity) => {
    switch (intensity) {
      case 'très forte':
        return 'text-red-600 bg-red-100';
      case 'forte':
        return 'text-orange-600 bg-orange-100';
      case 'modérée':
        return 'text-yellow-600 bg-yellow-100';
      case 'faible':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getIntensityIcon = (intensity) => {
    switch (intensity) {
      case 'très forte':
        return '🔴';
      case 'forte':
        return '🟠';
      case 'modérée':
        return '🟡';
      case 'faible':
        return '🔵';
      default:
        return '⚪';
    }
  };

  const getPrecipitationProgress = (precip) => {
    // Échelle: 0-20 mm/h pour la barre de progression
    return Math.min((precip / 20) * 100, 100);
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <Card>
          <CardHeader>
            <div className="h-6 bg-gray-200 rounded w-3/4"></div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              <div className="h-20 bg-gray-200 rounded"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <Card className={`border-yellow-500 ${className}`}>
        <CardContent className="p-4">
          <div className="flex items-center space-x-2 text-yellow-600">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!pluvioData) {
    return null;
  }

  return (
    <Card className={`overflow-hidden ${className}`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center space-x-2 text-lg">
          <CloudRain className="h-5 w-5 text-blue-600" />
          <span>Pluviomètre</span>
          <Badge variant="outline" className="ml-auto text-xs">
            {commune}
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Intensité actuelle */}
        <div className="text-center">
          <div className="flex items-center justify-center space-x-2 mb-3">
            <span className="text-3xl">
              {getIntensityIcon(pluvioData.current.intensity)}
            </span>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {pluvioData.current.precipitation.toFixed(1)} mm/h
              </div>
              <div className="text-sm text-gray-600">
                {pluvioData.current.description}
              </div>
            </div>
          </div>
          
          <Badge 
            className={`px-3 py-1 text-sm font-medium ${getIntensityColor(pluvioData.current.intensity)}`}
          >
            {pluvioData.current.intensity}
          </Badge>
        </div>

        {/* Barre de progression */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Intensité</span>
            <span className="font-medium">
              {getPrecipitationProgress(pluvioData.current.precipitation).toFixed(0)}%
            </span>
          </div>
          <Progress 
            value={getPrecipitationProgress(pluvioData.current.precipitation)} 
            className="h-3"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>Nulle</span>
            <span>Très forte</span>
          </div>
        </div>

        {/* Statistiques journalières */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center bg-blue-50 rounded-lg p-3">
            <div className="flex items-center justify-center mb-1">
              <Droplets className="h-4 w-4 text-blue-600 mr-1" />
              <span className="text-sm font-medium text-blue-900">Total jour</span>
            </div>
            <div className="text-xl font-bold text-blue-600">
              {pluvioData.daily_total.toFixed(1)} mm
            </div>
          </div>
          
          <div className="text-center bg-orange-50 rounded-lg p-3">
            <div className="flex items-center justify-center mb-1">
              <TrendingUp className="h-4 w-4 text-orange-600 mr-1" />
              <span className="text-sm font-medium text-orange-900">Pic prévu</span>
            </div>
            <div className="text-xl font-bold text-orange-600">
              {pluvioData.peak_hour.precipitation?.toFixed(1) || '0.0'} mm/h
            </div>
            {pluvioData.peak_hour.time && (
              <div className="text-xs text-orange-700 mt-1">
                à {formatTime(pluvioData.peak_hour.time)}
              </div>
            )}
          </div>
        </div>

        {/* Prévisions prochaines heures */}
        {pluvioData.forecast && pluvioData.forecast.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-900 flex items-center">
              <BarChart3 className="h-4 w-4 mr-2" />
              Prévisions 6h
            </h4>
            
            <div className="grid grid-cols-6 gap-2">
              {pluvioData.forecast.slice(0, 6).map((hour, index) => (
                <div key={index} className="text-center">
                  <div className="text-xs text-gray-600 mb-1">
                    {formatTime(hour.time)}
                  </div>
                  <div className="bg-gray-100 rounded-full h-8 flex items-center justify-center mb-1">
                    <div 
                      className="bg-blue-500 rounded-full transition-all duration-300"
                      style={{
                        width: `${Math.max(4, Math.min(24, (hour.precipitation / 10) * 24))}px`,
                        height: `${Math.max(4, Math.min(24, (hour.precipitation / 10) * 24))}px`
                      }}
                    ></div>
                  </div>
                  <div className="text-xs font-medium text-gray-900">
                    {hour.precipitation.toFixed(1)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {hour.precipitation_probability.toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Légende */}
        <div className="pt-3 border-t border-gray-200">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center space-x-1">
              <Activity className="h-3 w-3" />
              <span>Temps réel</span>
            </div>
            <div className="flex items-center space-x-1">
              <Clock className="h-3 w-3" />
              <span>Mis à jour: {formatTime(pluvioData.last_updated)}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PluviometerWidget;