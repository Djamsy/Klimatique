import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft,
  MapPin,
  Thermometer,
  Wind,
  CloudRain,
  Droplets,
  Clock,
  Shield,
  AlertTriangle,
  Users,
  Calendar,
  Info,
  Gauge
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { CachedWeatherService } from '../services/weatherService';

// Communes data (même que MapPage)
const COMMUNES_DATA = {
  "pointe-a-pitre": { 
    name: "Pointe-à-Pitre", 
    coordinates: [16.2415, -61.5328], 
    population: "16,000",
    type: "urbaine",
    riskFactors: ["Inondation urbaine", "Cyclones"],
    description: "Principal port et centre économique de la Guadeloupe"
  },
  "basse-terre": { 
    name: "Basse-Terre", 
    coordinates: [16.0074, -61.7056], 
    population: "10,800",
    type: "montagne",
    riskFactors: ["Glissements terrain", "Fortes pluies", "Cyclones"],
    description: "Préfecture située au pied de la Soufrière"
  },
  "sainte-anne": { 
    name: "Sainte-Anne", 
    coordinates: [16.2276, -61.3825], 
    population: "24,000",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Submersion marine"],
    description: "Station balnéaire réputée pour ses plages"
  },
  "le-moule": { 
    name: "Le Moule", 
    coordinates: [16.3336, -61.3503], 
    population: "22,000",
    type: "côtière",
    riskFactors: ["Vents violents", "Houle", "Sécheresse"],
    description: "Commune côtière exposée aux vents d'est"
  },
  "saint-francois": { 
    name: "Saint-François", 
    coordinates: [16.2500, -61.2667], 
    population: "13,500",
    type: "côtière",
    riskFactors: ["Cyclones", "Submersion marine"],
    description: "Port de plaisance et centre touristique"
  },
  "gosier": { 
    name: "Gosier", 
    coordinates: [16.1833, -61.5167], 
    population: "28,000",
    type: "urbaine",
    riskFactors: ["Inondation", "Cyclones"],
    description: "Zone urbaine densément peuplée"
  },
  "petit-bourg": { 
    name: "Petit-Bourg", 
    coordinates: [16.1833, -61.5833], 
    population: "25,000",
    type: "rurale",
    riskFactors: ["Inondation rivières", "Glissements terrain"],
    description: "Commune rurale traversée par plusieurs rivières"
  },
  "lamentin": { 
    name: "Lamentin", 
    coordinates: [16.2500, -61.6000], 
    population: "16,500",
    type: "urbaine",
    riskFactors: ["Inondation", "Vents forts"],
    description: "Zone aéroportuaire et commerciale"
  },
  "capesterre-belle-eau": { 
    name: "Capesterre-Belle-Eau", 
    coordinates: [16.0450, -61.5675], 
    population: "19,000",
    type: "montagne",
    riskFactors: ["Cyclones", "Pluies torrentielles", "Coulées boue"],
    description: "Commune montagneuse au relief accidenté"
  },
  "bouillante": { 
    name: "Bouillante", 
    coordinates: [16.1333, -61.7667], 
    population: "7,300",
    type: "côtière",
    riskFactors: ["Houle cyclonique", "Vents violents"],
    description: "Côte ouest exposée aux vents"
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

const getRiskProgress = (riskLevel) => {
  const values = {
    'faible': 25,
    'modéré': 50,
    'élevé': 75,
    'critique': 100
  };
  return values[riskLevel] || 25;
};

const CommunePage = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const commune = COMMUNES_DATA[slug];

  useEffect(() => {
    if (commune) {
      loadWeatherData();
    } else {
      setError("Commune non trouvée");
      setLoading(false);
    }
  }, [slug, commune]);

  const loadWeatherData = async () => {
    setLoading(true);
    try {
      const data = await CachedWeatherService.getWeatherWithCache(commune.name);
      setWeatherData(data);
    } catch (error) {
      console.error('Error loading weather data:', error);
      setError("Erreur lors du chargement des données météo");
    } finally {
      setLoading(false);
    }
  };

  const handleBackToMap = () => {
    navigate('/map');
  };

  const handleBackToHome = () => {
    navigate('/');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Chargement des données météo NASA...</p>
        </div>
      </div>
    );
  }

  if (error || !commune) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Commune non trouvée</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <Button onClick={handleBackToMap}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Retour à la carte
          </Button>
        </div>
      </div>
    );
  }

  const currentRisk = weatherData?.forecast?.[0]?.risk_level || 'faible';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                onClick={handleBackToMap}
                className="hover:bg-gray-100"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Carte
              </Button>
              <div className="hidden sm:block w-px h-6 bg-gray-300"></div>
              <Button
                variant="ghost"
                onClick={handleBackToHome}
                className="hover:bg-gray-100 text-sm"
              >
                Accueil
              </Button>
            </div>
            <div className="flex items-center">
              <Shield className="h-6 w-6 text-blue-800 mr-2" />
              <span className="font-semibold text-blue-800">Météo Sentinelle</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
                {commune.name}
              </h1>
              <p className="text-lg text-gray-600 mb-3">{commune.description}</p>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <div className="flex items-center">
                  <Users className="w-4 h-4 mr-1" />
                  {commune.population} habitants
                </div>
                <div className="flex items-center">
                  <MapPin className="w-4 h-4 mr-1" />
                  {commune.coordinates[0].toFixed(3)}, {commune.coordinates[1].toFixed(3)}
                </div>
                <Badge variant="outline" className="capitalize">
                  Zone {commune.type}
                </Badge>
              </div>
            </div>
            <div className="text-center">
              <div className="mb-2">
                <Badge 
                  className="text-sm px-4 py-2"
                  style={{ 
                    backgroundColor: getRiskColor(currentRisk) + '20',
                    color: getRiskColor(currentRisk),
                    border: `1px solid ${getRiskColor(currentRisk)}60`
                  }}
                >
                  <AlertTriangle className="w-4 h-4 mr-1" />
                  Risque {currentRisk}
                </Badge>
              </div>
              <Progress 
                value={getRiskProgress(currentRisk)} 
                className="w-24"
                style={{ 
                  color: getRiskColor(currentRisk)
                }}
              />
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Météo actuelle */}
          <div className="lg:col-span-2">
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Thermometer className="w-6 h-6 text-blue-600" />
                  Conditions météorologiques actuelles
                </CardTitle>
              </CardHeader>
              <CardContent>
                {weatherData ? (
                  <div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-blue-600 mb-2">
                          {Math.round(weatherData.current.temperature_current || weatherData.current.temperature_max)}°C
                        </div>
                        <p className="text-sm text-gray-600">Température</p>
                        <p className="text-xs text-gray-500 mt-1">
                          Min: {Math.round(weatherData.current.temperature_min)}° 
                          Max: {Math.round(weatherData.current.temperature_max)}°
                        </p>
                      </div>
                      <div className="text-center">
                        <div className="text-3xl font-bold text-green-600 mb-2 flex items-center justify-center gap-1">
                          <Wind className="w-6 h-6" />
                          {Math.round(weatherData.current.wind_speed)}
                        </div>
                        <p className="text-sm text-gray-600">Vent (km/h)</p>
                      </div>
                      <div className="text-center">
                        <div className="text-3xl font-bold text-blue-500 mb-2 flex items-center justify-center gap-1">
                          <CloudRain className="w-6 h-6" />
                          {weatherData.current.precipitation_probability}%
                        </div>
                        <p className="text-sm text-gray-600">Pluie</p>
                      </div>
                      <div className="text-center">
                        <div className="text-3xl font-bold text-cyan-600 mb-2 flex items-center justify-center gap-1">
                          <Droplets className="w-6 h-6" />
                          {weatherData.current.humidity}%
                        </div>
                        <p className="text-sm text-gray-600">Humidité</p>
                      </div>
                    </div>

                    <div className="text-center bg-gray-50 rounded-lg p-4">
                      <p className="text-lg font-medium text-gray-900 mb-2">
                        {weatherData.current.weather_description}
                      </p>
                      <p className="text-sm text-gray-600">
                        <Calendar className="inline w-4 h-4 mr-1" />
                        Dernière mise à jour: {new Date(weatherData.last_updated).toLocaleString('fr-FR')}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-gray-500">Données météo non disponibles</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Prévisions 5 jours */}
            {weatherData?.forecast && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-6 h-6 text-blue-600" />
                    Prévisions 5 jours
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {weatherData.forecast.slice(0, 5).map((day, index) => (
                      <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        <div className="flex items-center gap-4 flex-1">
                          <div className="w-16 text-sm font-medium text-gray-700">
                            {day.day_name}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">{day.weather_data.weather_description}</p>
                            <p className="text-sm text-gray-600">
                              Vent: {Math.round(day.weather_data.wind_speed)} km/h • 
                              Pluie: {day.weather_data.precipitation_probability}%
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="font-semibold text-lg">
                            {Math.round(day.weather_data.temperature_max)}° / {Math.round(day.weather_data.temperature_min)}°
                          </span>
                          <Badge 
                            size="sm"
                            style={{ 
                              backgroundColor: getRiskColor(day.risk_level) + '20',
                              color: getRiskColor(day.risk_level),
                              border: `1px solid ${getRiskColor(day.risk_level)}40`
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
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Risques spécifiques */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-orange-700">
                  <AlertTriangle className="w-5 h-5" />
                  Risques spécifiques
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {commune.riskFactors.map((risk, index) => (
                    <div key={index} className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
                      <div className="w-2 h-2 bg-orange-500 rounded-full flex-shrink-0"></div>
                      <span className="text-sm font-medium text-orange-800">{risk}</span>
                    </div>
                  ))}
                </div>
                
                {weatherData?.forecast?.[0]?.risk_factors && weatherData.forecast[0].risk_factors.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-orange-200">
                    <h4 className="font-semibold text-orange-800 mb-2 text-sm">Risques météorologiques actuels :</h4>
                    <div className="space-y-2">
                      {weatherData.forecast[0].risk_factors.map((factor, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm">
                          <Gauge className="w-3 h-3 text-red-600" />
                          <span className="text-red-700">{factor}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Alertes actives */}
            {weatherData?.alerts && weatherData.alerts.length > 0 && (
              <Card className="border-red-200">
                <CardHeader className="bg-red-50">
                  <CardTitle className="text-red-800 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    🚨 Alertes actives
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  <div className="space-y-3">
                    {weatherData.alerts.map((alert, index) => (
                      <div key={index} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                        <h4 className="font-semibold text-red-800 mb-1">{alert.title}</h4>
                        <p className="text-red-700 text-sm">{alert.message}</p>
                        {alert.recommendations && (
                          <div className="mt-2">
                            <p className="text-xs font-medium text-red-800 mb-1">Recommandations :</p>
                            <ul className="text-xs text-red-700 space-y-1">
                              {alert.recommendations.map((rec, i) => (
                                <li key={i} className="flex items-start gap-1">
                                  <span>•</span>
                                  <span>{rec}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Informations générales */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="w-5 h-5 text-blue-600" />
                  Informations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Type de zone:</span>
                    <span className="font-medium capitalize">{commune.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Population:</span>
                    <span className="font-medium">{commune.population}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Latitude:</span>
                    <span className="font-medium">{commune.coordinates[0].toFixed(4)}°</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Longitude:</span>
                    <span className="font-medium">{commune.coordinates[1].toFixed(4)}°</span>
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-xs text-gray-500 flex items-center gap-1">
                    <Shield className="w-3 h-3" />
                    Données fournies par NASA • Météo Sentinelle
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <Button className="w-full" onClick={handleBackToMap}>
                    <MapPin className="w-4 h-4 mr-2" />
                    Retour à la carte
                  </Button>
                  <Button variant="outline" className="w-full" onClick={() => window.location.reload()}>
                    <Clock className="w-4 h-4 mr-2" />
                    Actualiser les données
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommunePage;