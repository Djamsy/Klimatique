import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  AlertTriangle, 
  AlertCircle, 
  CheckCircle, 
  XCircle,
  Cloud,
  CloudRain,
  CloudLightning,
  Tornado,
  Sun,
  ArrowLeft
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const VigilancePreview = () => {
  const [currentVigilance, setCurrentVigilance] = useState('orange');
  const navigate = useNavigate();

  const vigilanceLevels = {
    vert: {
      color: 'green',
      animation: 'weather-sun',
      icon: CheckCircle,
      title: 'Vigilance Verte',
      description: 'Pas de vigilance particulière requise',
      bgGradient: 'from-green-400 to-green-600',
      textColor: 'text-green-800',
      bgColor: 'bg-green-50',
      recommendations: [
        'Conditions météorologiques normales',
        'Aucune précaution particulière nécessaire',
        'Activités extérieures possibles'
      ]
    },
    jaune: {
      color: 'yellow',
      animation: 'weather-rain',
      icon: AlertTriangle,
      title: 'Vigilance Jaune',
      description: 'Soyez attentifs si vous pratiquez des activités sensibles au risque météorologique',
      bgGradient: 'from-yellow-400 to-yellow-600',
      textColor: 'text-yellow-800',
      bgColor: 'bg-yellow-50',
      recommendations: [
        'Conditions météorologiques à surveiller',
        'Prudence lors des activités extérieures',
        'Informez-vous régulièrement'
      ]
    },
    orange: {
      color: 'orange',
      animation: 'weather-lightning',
      icon: AlertCircle,
      title: 'Vigilance Orange',
      description: 'Soyez très vigilants. Des phénomènes dangereux sont prévus',
      bgGradient: 'from-orange-500 to-red-500',
      textColor: 'text-orange-800',
      bgColor: 'bg-orange-50',
      recommendations: [
        'Évitez les déplacements non nécessaires',
        'Restez informés de l\'évolution météorologique',
        'Prenez des précautions particulières'
      ]
    },
    rouge: {
      color: 'red',
      animation: 'weather-hurricane',
      icon: XCircle,
      title: 'Vigilance Rouge',
      description: 'Une vigilance absolue s\'impose. Phénomènes dangereux d\'intensité exceptionnelle',
      bgGradient: 'from-red-600 to-red-800',
      textColor: 'text-red-800',
      bgColor: 'bg-red-50',
      recommendations: [
        'Évitez absolument tout déplacement',
        'Restez chez vous en sécurité',
        'Suivez les consignes des autorités'
      ]
    }
  };

  const currentLevel = vigilanceLevels[currentVigilance];
  const IconComponent = currentLevel.icon;

  const getWeatherIcon = (level) => {
    switch (level) {
      case 'vert': return Sun;
      case 'jaune': return CloudRain;
      case 'orange': return CloudLightning;
      case 'rouge': return Tornado;
      default: return Cloud;
    }
  };

  const handleBackToHome = () => {
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                onClick={handleBackToHome}
                className="hover:bg-gray-100"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Retour
              </Button>
              <h1 className="text-2xl font-bold text-gray-900">
                Klimaclique - Aperçu Vigilances
              </h1>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Contrôles de vigilance */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Sélectionner un niveau de vigilance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(vigilanceLevels).map(([level, config]) => {
                const WeatherIcon = getWeatherIcon(level);
                return (
                  <button
                    key={level}
                    onClick={() => setCurrentVigilance(level)}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      currentVigilance === level
                        ? `border-${config.color}-500 ${config.bgColor}`
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex flex-col items-center space-y-2">
                      <WeatherIcon className={`w-8 h-8 ${config.textColor}`} />
                      <span className="font-medium">{config.title}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Aperçu de la vigilance */}
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Animation Hero */}
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IconComponent className={`w-6 h-6 ${currentLevel.textColor}`} />
                {currentLevel.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className={`relative h-96 ${currentLevel.animation}`}>
                {/* Background avec gradient de vigilance */}
                <div className={`absolute inset-0 bg-gradient-to-br ${currentLevel.bgGradient}`}></div>
                
                {/* Conteneur d'animations météorologiques */}
                <div className="weather-animation-container">
                  {/* Animation de pluie */}
                  <div className="rain-animation">
                    {[...Array(20)].map((_, i) => (
                      <div key={i} className="rain-drop"></div>
                    ))}
                  </div>
                  
                  {/* Animation de foudre */}
                  <div className="lightning-animation">
                    <div className="lightning-flash"></div>
                    <div className="lightning-flash"></div>
                    <div className="lightning-flash"></div>
                  </div>
                  
                  {/* Animation d'ouragan */}
                  <div className="hurricane-animation">
                    <div className="hurricane-spiral"></div>
                    <div className="hurricane-spiral"></div>
                    <div className="hurricane-eye"></div>
                  </div>
                  
                  {/* Animation de soleil */}
                  <div className="sun-animation"></div>
                  
                  {/* Animation de nuages */}
                  <div className="clouds-animation">
                    <div className="cloud"></div>
                    <div className="cloud"></div>
                    <div className="cloud"></div>
                    <div className="cloud"></div>
                    <div className="cloud"></div>
                  </div>
                  
                  {/* Animation de vent */}
                  <div className="wind-animation">
                    <div className="wind-line"></div>
                    <div className="wind-line"></div>
                    <div className="wind-line"></div>
                    <div className="wind-line"></div>
                    <div className="wind-line"></div>
                  </div>
                </div>
                
                {/* Overlay d'information */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center text-white">
                    <Badge 
                      variant="secondary" 
                      className={`mb-4 ${currentLevel.bgColor} ${currentLevel.textColor} text-lg px-4 py-2`}
                    >
                      {currentLevel.title}
                    </Badge>
                    <div className="text-xl font-medium opacity-90">
                      Animation: {currentLevel.animation.replace('weather-', '')}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Informations de vigilance */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <IconComponent className={`w-6 h-6 ${currentLevel.textColor}`} />
                  Détails de la vigilance
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className={`p-4 rounded-lg ${currentLevel.bgColor}`}>
                  <p className={`${currentLevel.textColor} font-medium`}>
                    {currentLevel.description}
                  </p>
                </div>
                
                <div>
                  <h3 className="font-semibold mb-2">Recommandations :</h3>
                  <ul className="space-y-2">
                    {currentLevel.recommendations.map((rec, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                        <span className="text-gray-700">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Correspondance IA</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Niveau de vigilance</span>
                    <Badge variant="outline">{currentLevel.title}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Animation déclenchée</span>
                    <Badge variant="secondary">{currentLevel.animation}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Logique IA</span>
                    <span className="text-sm text-gray-600">
                      {currentVigilance === 'rouge' ? 'Risque critique' :
                       currentVigilance === 'orange' ? 'Risque élevé' :
                       currentVigilance === 'jaune' ? 'Risque modéré' : 'Conditions normales'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Comment ça fonctionne</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                    <span>L'IA analyse les données Météo France en temps réel</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                    <span>Le niveau de vigilance détermine l'animation affichée</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                    <span>L'expérience utilisateur s'adapte automatiquement</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VigilancePreview;