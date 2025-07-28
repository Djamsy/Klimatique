import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  Sun, 
  Cloud, 
  CloudRain, 
  CloudLightning, 
  Tornado,
  Wind,
  Play,
  Pause
} from 'lucide-react';

const WeatherAnimationDemo = () => {
  const [activeAnimation, setActiveAnimation] = useState('weather-sun');
  const [isPlaying, setIsPlaying] = useState(true);

  const animations = [
    {
      id: 'weather-sun',
      name: 'Soleil',
      icon: Sun,
      condition: 'Vigilance Verte',
      description: 'Conditions normales, temps ensoleillé',
      color: 'text-yellow-500',
      bgColor: 'bg-gradient-to-br from-yellow-400 to-orange-500'
    },
    {
      id: 'weather-clouds',
      name: 'Nuages',
      icon: Cloud,
      condition: 'Temps nuageux',
      description: 'Couverture nuageuse, conditions stables',
      color: 'text-gray-500',
      bgColor: 'bg-gradient-to-br from-gray-400 to-gray-600'
    },
    {
      id: 'weather-rain',
      name: 'Pluie',
      icon: CloudRain,
      condition: 'Vigilance Jaune',
      description: 'Risque modéré, précipitations',
      color: 'text-blue-500',
      bgColor: 'bg-gradient-to-br from-blue-600 to-blue-800'
    },
    {
      id: 'weather-lightning',
      name: 'Orage',
      icon: CloudLightning,
      condition: 'Vigilance Orange',
      description: 'Risque élevé, orages violents',
      color: 'text-orange-500',
      bgColor: 'bg-gradient-to-br from-orange-600 to-red-600'
    },
    {
      id: 'weather-hurricane',
      name: 'Ouragan',
      icon: Tornado,
      condition: 'Vigilance Rouge',
      description: 'Risque critique, cyclone',
      color: 'text-red-500',
      bgColor: 'bg-gradient-to-br from-red-600 to-red-800'
    },
    {
      id: 'weather-wind',
      name: 'Vent',
      icon: Wind,
      condition: 'Vents forts',
      description: 'Vents violents, rafales',
      color: 'text-cyan-500',
      bgColor: 'bg-gradient-to-br from-cyan-600 to-cyan-800'
    }
  ];

  const toggleAnimation = () => {
    setIsPlaying(!isPlaying);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Démonstration des Animations Météo Klimaclique
          </h1>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Les animations changent automatiquement selon l'analyse IA et les niveaux de vigilance Météo France
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Panneau de contrôle */}
          <div className="lg:col-span-1">
            <Card className="sticky top-8">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Play className="w-5 h-5" />
                  Contrôles d'Animation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Animation</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={toggleAnimation}
                      className="flex items-center gap-2"
                    >
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      {isPlaying ? 'Pause' : 'Play'}
                    </Button>
                  </div>
                  
                  <div className="space-y-3">
                    <h3 className="font-medium text-gray-900">Scénarios Météo</h3>
                    {animations.map((animation) => {
                      const IconComponent = animation.icon;
                      return (
                        <button
                          key={animation.id}
                          onClick={() => setActiveAnimation(animation.id)}
                          className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                            activeAnimation === animation.id
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <IconComponent className={`w-5 h-5 ${animation.color}`} />
                            <div>
                              <div className="font-medium">{animation.name}</div>
                              <div className="text-sm text-gray-600">{animation.condition}</div>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  <div className="pt-4 border-t">
                    <h3 className="font-medium text-gray-900 mb-2">Animation Active</h3>
                    {animations.find(a => a.id === activeAnimation) && (
                      <div className="space-y-2">
                        <Badge variant="secondary" className="w-full justify-center">
                          {animations.find(a => a.id === activeAnimation).condition}
                        </Badge>
                        <p className="text-sm text-gray-600">
                          {animations.find(a => a.id === activeAnimation).description}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Démonstration d'animation */}
          <div className="lg:col-span-2">
            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle>Aperçu en Temps Réel</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className={`relative h-96 ${activeAnimation} ${isPlaying ? '' : 'animation-paused'}`}>
                  {/* Background adaptatif */}
                  <div className={`absolute inset-0 ${
                    animations.find(a => a.id === activeAnimation)?.bgColor || 'bg-gradient-to-br from-blue-900 to-purple-900'
                  }`}></div>
                  
                  {/* Conteneur d'animations météorologiques */}
                  <div className="weather-animation-container">
                    {/* Animation de pluie */}
                    <div className="rain-animation">
                      {[...Array(25)].map((_, i) => (
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
                      <div className="text-4xl font-bold mb-2">
                        {animations.find(a => a.id === activeAnimation)?.name}
                      </div>
                      <div className="text-xl opacity-90">
                        {animations.find(a => a.id === activeAnimation)?.condition}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <div className="mt-6 grid md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Comment ça marche ?</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-start gap-2">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                      <span>L'IA analyse les données météo en temps réel</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                      <span>Vigilance Météo France intégrée</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                      <span>Animation adaptée automatiquement</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Niveaux de Vigilance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span>Vert: Conditions normales</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <span>Jaune: Risque modéré</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                      <span>Orange: Risque élevé</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                      <span>Rouge: Risque critique</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WeatherAnimationDemo;