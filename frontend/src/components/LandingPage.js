import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Cloud, 
  Sun, 
  CloudRain, 
  CloudLightning, 
  CloudRainWind, 
  Tornado,
  Bell, 
  Map, 
  Database, 
  MapPin,
  Phone,
  Mail,
  Shield,
  AlertTriangle,
  ChevronRight,
  Star,
  Users,
  Clock,
  Target,
  Loader2,
  Brain,
  Globe
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { CachedWeatherService, SubscriptionService, ConfigService, CycloneAIService } from '../services/weatherService';
import { useToast } from '../hooks/use-toast';

const LandingPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [weatherData, setWeatherData] = useState(null);
  const [isLoadingWeather, setIsLoadingWeather] = useState(true);
  const [communes, setCommunes] = useState([]);
  const [globalRisk, setGlobalRisk] = useState(null);
  const [stats, setStats] = useState({
    total: 32,
    precision: 94,
    response_time: 15,
    users: '2.5k'
  });
  const { toast } = useToast();

  // Communes principales pour l'affichage
  const mainCommunes = ['Pointe-à-Pitre', 'Basse-Terre', 'Sainte-Anne', 'Le Moule', 'Saint-François'];

  useEffect(() => {
    loadInitialData();
    // Nettoie le cache expiré au chargement
    const { CacheUtils } = require('../services/weatherService');
    CacheUtils.cleanExpiredCache();
  }, []);

  const loadInitialData = async () => {
    try {
      // Charge la configuration et la météo en parallèle
      const [communesData, weatherResults, globalRiskData] = await Promise.all([
        ConfigService.getCommunes(),
        CachedWeatherService.getMultipleWeatherWithCache(mainCommunes),
        CycloneAIService.getGlobalCycloneRisk().catch(error => {
          console.error('Error loading global risk:', error);
          return null;
        })
      ]);
      
      setCommunes(communesData.communes || []);
      setGlobalRisk(globalRiskData);
      
      // Transforme les données météo pour l'affichage
      const transformedWeather = Object.entries(weatherResults).map(([commune, data]) => {
        if (!data || !data.forecast || !data.forecast[0]) return null;
        
        const todayForecast = data.forecast[0];
        return {
          id: commune,
          commune,
          date: todayForecast.date,
          day: todayForecast.day_name,
          temperature: {
            min: todayForecast.weather_data.temperature_min,
            max: todayForecast.weather_data.temperature_max
          },
          weather: todayForecast.weather_data.weather_description,
          icon: todayForecast.weather_data.weather_icon,
          riskLevel: todayForecast.risk_level,
          windSpeed: todayForecast.weather_data.wind_speed,
          precipitation: todayForecast.weather_data.precipitation_probability,
          humidity: todayForecast.weather_data.humidity
        };
      }).filter(Boolean);
      
      setWeatherData(transformedWeather);
      setIsLoadingWeather(false);
      
    } catch (error) {
      console.error('Error loading initial data:', error);
      setIsLoadingWeather(false);
      toast({
        title: "Erreur de chargement",
        description: "Impossible de charger les données météo. Utilisation des données de démonstration.",
        variant: "destructive"
      });
      
      // Fallback avec données mockées
      loadMockData();
    }
  };

  const loadMockData = () => {
    const mockWeather = [
      {
        id: 'pointe-a-pitre',
        commune: 'Pointe-à-Pitre',
        date: new Date().toISOString().split('T')[0],
        day: "Aujourd'hui",
        temperature: { min: 24, max: 29 },
        weather: "Ensoleillé",
        icon: "sun",
        riskLevel: "faible",
        windSpeed: 15,
        precipitation: 10,
        humidity: 65
      }
    ];
    setWeatherData(mockWeather);
  };

  const getWeatherIcon = (iconName) => {
    const icons = {
      'sun': Sun,
      'cloud': Cloud,
      'cloud-rain': CloudRain,
      'cloud-lightning': CloudLightning,
      'cloud-rain-wind': CloudRainWind,
      'tornado': Tornado
    };
    return icons[iconName] || Sun;
  };

  const getFeatureIcon = (iconName) => {
    const icons = {
      'cloud-sun': Cloud,
      'bell': Bell,
      'map': Map,
      'database': Database
    };
    return icons[iconName] || Cloud;
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const contactData = {
        email: email.trim(),
        message: message.trim(),
        type: 'beta_access'
      };

      const result = await SubscriptionService.sendContactRequest(contactData);
      
      if (result.success) {
        toast({
          title: "Demande envoyée !",
          description: result.message,
          variant: "default"
        });
        
        setEmail('');
        setMessage('');
      } else {
        throw new Error(result.error || 'Erreur lors de l\'envoi');
      }
      
    } catch (error) {
      console.error('Contact form error:', error);
      toast({
        title: "Erreur",
        description: error.message || "Erreur lors de l'envoi. Veuillez réessayer.",
        variant: "destructive"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNavigateToMap = () => {
    navigate('/map');
  };

  // Features statiques (ne nécessitent pas d'API)
  const features = [
    {
      id: 1,
      icon: 'cloud-sun',
      title: "Prédictions à 5 jours",
      description: "Météo détaillée avec indicateurs de risque spécifiques à chaque commune de Guadeloupe"
    },
    {
      id: 2,
      icon: 'bell',
      title: "Alertes en temps réel", 
      description: "Notifications SMS et email automatiques en cas d'événement météorologique extrême"
    },
    {
      id: 3,
      icon: 'map',
      title: "Cartes interactives",
      description: "Visualisation en temps réel des vents, précipitations et zones à risque"
    },
    {
      id: 4,
      icon: 'database',
      title: "Données NASA",
      description: "Croisement données satellitaires NASA et modèles météorologiques avancés"
    }
  ];

  const testimonials = [
    {
      id: 1,
      name: "Marie Dubois",
      role: "Maire de Sainte-Anne",
      content: "Grâce à Météo Sentinelle, nous anticipons mieux les risques d'inondation. Un outil indispensable pour protéger nos citoyens.",
      avatar: "MD"
    },
    {
      id: 2,
      name: "Jean-Claude Martin",
      role: "Agriculteur, Basse-Terre",
      content: "Les alertes précises m'ont permis de protéger mes cultures à plusieurs reprises. La précision locale fait toute la différence.",
      avatar: "JM"
    },
    {
      id: 3,
      name: "Dr. Sophie Laurent",
      role: "Médecin urgentiste, CHU",
      content: "L'anticipation des événements extrêmes nous aide à mieux organiser les services d'urgence. Un gain de temps vital.",
      avatar: "SL"
    }
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Alert Banner */}
      <div className="alert-banner text-white py-2 px-4 text-center text-sm font-medium">
        <AlertTriangle className="inline w-4 h-4 mr-2" />
        Vigilance orange : Fortes pluies attendues ce weekend sur la Basse-Terre
      </div>

      {/* Navigation */}
      <nav className="navbar sticky top-0 z-50 bg-white/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-800 mr-3" />
              <span className="text-xl font-bold text-blue-800">Météo Sentinelle</span>
            </div>
            <div className="hidden md:flex space-x-8">
              <a href="#features" className="text-gray-700 hover:text-blue-800 transition-colors">Fonctionnalités</a>
              <a href="#previsions" className="text-gray-700 hover:text-blue-800 transition-colors">Prévisions</a>
              <Button 
                variant="ghost" 
                onClick={handleNavigateToMap}
                className="text-gray-700 hover:text-blue-800 transition-colors"
              >
                Carte Interactive
              </Button>
              <a href="#temoignages" className="text-gray-700 hover:text-blue-800 transition-colors">Témoignages</a>
              <a href="#contact" className="text-gray-700 hover:text-blue-800 transition-colors">Contact</a>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Background avec gradient animé */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900 via-blue-800 to-purple-900"></div>
        <div className="absolute inset-0 bg-black opacity-20"></div>
        
        {/* Animation de particules météo */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-4 -right-4 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
          <div className="absolute -bottom-8 -left-4 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse delay-1000"></div>
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-cyan-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-500"></div>
        </div>
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
          <div className="text-center">
            {/* Badge innovant */}
            <div className="inline-flex items-center bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 mb-8 border border-white/20">
              <Brain className="w-4 h-4 text-cyan-400 mr-2" />
              <span className="text-cyan-100 text-sm font-medium">IA Prédictive • Temps Réel • NASA</span>
            </div>
            
            {/* Titre principal avec animation */}
            <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold mb-6 text-white leading-tight">
              <span className="block">Anticipez les risques,</span>
              <span className="block bg-gradient-to-r from-cyan-400 to-blue-300 bg-clip-text text-transparent">
                protégez les vôtres
              </span>
            </h1>
            
            {/* Sous-titre amélioré */}
            <p className="text-xl sm:text-2xl lg:text-3xl mb-12 text-blue-100 leading-relaxed max-w-4xl mx-auto">
              Intelligence artificielle de pointe pour la prédiction cyclonique en Guadeloupe.
              <span className="block mt-2 text-lg sm:text-xl lg:text-2xl text-cyan-200">
                Données NASA • Alertes temps réel • Conçu pour sauver des vies
              </span>
            </p>
            
            {/* Boutons d'action modernisés */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <Button 
                size="lg" 
                className="group relative overflow-hidden bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white font-semibold text-lg px-8 py-4 rounded-2xl border-0 shadow-xl shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105"
                onClick={handleNavigateToMap}
              >
                <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <Map className="w-6 h-6 mr-3" />
                Accéder à la Carte IA
                <ChevronRight className="w-5 h-5 ml-3 group-hover:translate-x-1 transition-transform duration-300" />
              </Button>
              
              <Button 
                variant="outline" 
                size="lg" 
                className="group border-2 border-white/30 text-white bg-white/10 hover:bg-white/20 backdrop-blur-sm font-semibold text-lg px-8 py-4 rounded-2xl transition-all duration-300 transform hover:scale-105"
                onClick={() => document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })}
              >
                <Bell className="w-5 h-5 mr-3" />
                Alertes Bêta
              </Button>
            </div>
            
            {/* Stats en temps réel */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-8 max-w-4xl mx-auto">
              <div className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-white/20">
                <div className="text-2xl sm:text-3xl font-bold text-cyan-400 mb-2">
                  {stats.total}<span className="text-sm text-cyan-300">/32</span>
                </div>
                <div className="text-white text-sm sm:text-base">Communes</div>
              </div>
              <div className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-white/20">
                <div className="text-2xl sm:text-3xl font-bold text-green-400 mb-2">
                  {stats.precision}<span className="text-sm text-green-300">%</span>
                </div>
                <div className="text-white text-sm sm:text-base">Précision</div>
              </div>
              <div className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-white/20">
                <div className="text-2xl sm:text-3xl font-bold text-purple-400 mb-2">
                  {stats.response_time}<span className="text-sm text-purple-300">s</span>
                </div>
                <div className="text-white text-sm sm:text-base">Temps réel</div>
              </div>
              <div className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-white/20">
                <div className="text-2xl sm:text-3xl font-bold text-yellow-400 mb-2">
                  {stats.users}
                </div>
                <div className="text-white text-sm sm:text-base">Utilisateurs</div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Vague de transition */}
        <div className="absolute bottom-0 left-0 w-full">
          <svg viewBox="0 0 1200 120" preserveAspectRatio="none" className="relative block w-full h-16 sm:h-20 lg:h-24">
            <path d="M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z" fill="#ffffff" opacity="0.1"></path>
            <path d="M0,0V15.81C13,36.92,27.64,56.86,47.69,72.05,99.41,111.27,165,111,224.58,91.58c31.15-10.15,60.09-26.07,89.67-39.8,40.92-19,84.73-46,130.83-49.67,36.26-2.85,70.9,9.42,98.6,31.56,31.77,25.39,62.32,62,103.63,73,40.44,10.79,81.35-6.69,119.13-24.28s75.16-39,116.92-43.05c59.73-5.85,113.28,22.88,168.9,38.84,30.2,8.66,59,6.17,87.09-7.5,22.43-10.89,48-26.93,60.65-49.24V0Z" fill="#ffffff" opacity="0.05"></path>
            <path d="M0,0V5.63C149.93,59,314.09,71.32,475.83,42.57c43-7.64,84.23-20.12,127.61-26.46,59-8.63,112.48,12.24,165.56,35.4C827.93,77.22,886,95.24,951.2,90c86.53-7,172.46-45.71,248.8-84.81V0Z" fill="#ffffff"></path>
          </svg>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="stat-number text-3xl md:text-4xl font-bold mb-2">
                {stats.total}<span className="text-lg">/32</span>
              </div>
              <div className="text-gray-600 text-sm md:text-base">Communes couvertes</div>
            </div>
            <div className="text-center">
              <div className="stat-number text-3xl md:text-4xl font-bold mb-2">
                {stats.precision}<span className="text-lg">%</span>
              </div>
              <div className="text-gray-600 text-sm md:text-base">Précision des alertes</div>
            </div>
            <div className="text-center">
              <div className="stat-number text-3xl md:text-4xl font-bold mb-2">
                {stats.response_time}<span className="text-lg">min</span>
              </div>
              <div className="text-gray-600 text-sm md:text-base">Temps de réaction</div>
            </div>
            <div className="text-center">
              <div className="stat-number text-3xl md:text-4xl font-bold mb-2">
                {stats.users}<span className="text-lg">+</span>
              </div>
              <div className="text-gray-600 text-sm md:text-base">Utilisateurs actifs</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Une technologie au service de votre sécurité
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Météo Sentinelle combine données satellitaires NASA, intelligence artificielle et 
              connaissance du terrain pour vous offrir des prédictions d'une précision inégalée.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature) => {
              const IconComponent = getFeatureIcon(feature.icon);
              return (
                <Card key={feature.id} className="feature-card p-6 text-center">
                  <CardHeader className="pb-4">
                    <div className="feature-icon w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4">
                      <IconComponent className="w-8 h-8 text-blue-800" />
                    </div>
                    <CardTitle className="text-lg font-semibold text-gray-900">
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-600">{feature.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Global Risk Section */}
      {globalRisk && (
        <section className="py-16 bg-gradient-to-br from-blue-50 to-purple-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 flex items-center justify-center gap-3">
                <Brain className="w-8 h-8 text-blue-600" />
                Analyse IA - Risque Cyclonique
              </h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                Notre intelligence artificielle analyse en temps réel les conditions météorologiques pour prédire les risques cycloniques
              </p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-8">
              {/* Risque Global */}
              <div className="bg-white rounded-lg shadow-lg p-6 text-center">
                <div className="flex items-center justify-center mb-4">
                  <Globe className="w-8 h-8 text-blue-600 mr-2" />
                  <h3 className="text-xl font-semibold text-gray-900">Risque Régional</h3>
                </div>
                <div className={`text-3xl font-bold mb-2 ${
                  globalRisk.global_risk_level === 'critique' ? 'text-red-600' :
                  globalRisk.global_risk_level === 'élevé' ? 'text-orange-600' :
                  globalRisk.global_risk_level === 'modéré' ? 'text-yellow-600' :
                  'text-green-600'
                }`}>
                  {globalRisk.global_risk_level.toUpperCase()}
                </div>
                <p className="text-gray-600 text-sm">
                  Analyse globale Guadeloupe
                </p>
              </div>
              
              {/* Communes à risque */}
              <div className="bg-white rounded-lg shadow-lg p-6 text-center">
                <div className="flex items-center justify-center mb-4">
                  <AlertTriangle className="w-8 h-8 text-orange-600 mr-2" />
                  <h3 className="text-xl font-semibold text-gray-900">Zones d'Alerte</h3>
                </div>
                <div className="text-3xl font-bold text-orange-600 mb-2">
                  {globalRisk.high_risk_count + globalRisk.critical_risk_count}
                </div>
                <p className="text-gray-600 text-sm">
                  Communes en vigilance
                </p>
                <div className="mt-3 text-xs text-gray-500">
                  {globalRisk.critical_risk_count > 0 && (
                    <span className="text-red-600 font-medium">
                      {globalRisk.critical_risk_count} critiques
                    </span>
                  )}
                  {globalRisk.high_risk_count > 0 && (
                    <span className="text-orange-600 font-medium">
                      {globalRisk.critical_risk_count > 0 ? ' • ' : ''}
                      {globalRisk.high_risk_count} élevées
                    </span>
                  )}
                </div>
              </div>
              
              {/* Recommandations */}
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-center mb-4">
                  <Shield className="w-8 h-8 text-green-600 mr-2" />
                  <h3 className="text-xl font-semibold text-gray-900">Recommandations</h3>
                </div>
                <div className="space-y-2 text-sm">
                  {globalRisk.regional_recommendations.length > 0 ? (
                    globalRisk.regional_recommendations.slice(0, 3).map((rec, index) => (
                      <div key={index} className="flex items-start space-x-2">
                        <span className="text-green-600 mt-1">•</span>
                        <span className="text-gray-700">{rec}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-gray-500">
                      <span className="text-green-600 text-2xl">✓</span>
                      <p className="mt-2">Conditions normales</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Communes affectées */}
            {globalRisk.affected_communes.length > 0 && (
              <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
                <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-blue-600" />
                  Communes sous surveillance
                </h4>
                <div className="flex flex-wrap gap-2">
                  {globalRisk.affected_communes.map((commune, index) => (
                    <Badge
                      key={index}
                      variant="outline"
                      className="px-3 py-1 text-sm border-orange-200 text-orange-800 bg-orange-50"
                    >
                      {commune}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            
            <div className="mt-8 text-center">
              <p className="text-xs text-gray-500 flex items-center justify-center gap-1">
                <Brain className="w-3 h-3" />
                Analyse IA mise à jour: {new Date(globalRisk.last_analysis).toLocaleString('fr-FR')}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Weather Forecast Section */}
      <section id="previsions" className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Prévisions pour la Guadeloupe
            </h2>
            <p className="text-lg text-gray-600">
              Météo détaillée avec indicateurs de risque alimentée par les données NASA
            </p>
          </div>
          
          {isLoadingWeather ? (
            <div className="flex justify-center items-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              <span className="ml-3 text-lg text-gray-600">Chargement des données météo NASA...</span>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8">
              {weatherData && weatherData.map((day) => {
                const IconComponent = getWeatherIcon(day.icon);
                return (
                  <Card key={day.id} className="weather-card p-4">
                    <CardContent className="text-center space-y-3">
                      <div className="font-semibold text-gray-900">{day.commune}</div>
                      <IconComponent className="w-12 h-12 mx-auto text-blue-600" />
                      <div className="text-sm text-gray-600">{day.weather}</div>
                      <div className="text-lg font-bold text-gray-900">
                        {Math.round(day.temperature.max)}° / {Math.round(day.temperature.min)}°
                      </div>
                      <Badge 
                        className={`risk-indicator risk-${day.riskLevel}`}
                        style={{ 
                          backgroundColor: getRiskColor(day.riskLevel) + '20', 
                          color: getRiskColor(day.riskLevel),
                          border: `1px solid ${getRiskColor(day.riskLevel)}40`
                        }}
                      >
                        Risque {day.riskLevel}
                      </Badge>
                      <div className="text-xs text-gray-500 space-y-1">
                        <div>Vent: {Math.round(day.windSpeed)} km/h</div>
                        <div>Pluie: {day.precipitation}%</div>
                        <div>Humidité: {day.humidity}%</div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
          
          <div className="text-center">
            <Button 
              size="lg" 
              onClick={handleNavigateToMap}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4"
            >
              <Map className="w-5 h-5 mr-2" />
              Explorer toutes les communes sur la carte
              <ChevronRight className="w-5 h-5 ml-2" />
            </Button>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="temoignages" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Ils nous font confiance
            </h2>
            <p className="text-xl text-gray-600">
              Découvrez comment Météo Sentinelle accompagne déjà les acteurs locaux
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial) => (
              <Card key={testimonial.id} className="testimonial-card p-6">
                <CardContent>
                  <div className="flex mb-4">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="w-4 h-4 text-yellow-400 fill-current" />
                    ))}
                  </div>
                  <p className="text-gray-700 mb-6 italic">"{testimonial.content}"</p>
                  <div className="flex items-center">
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mr-4">
                      <span className="text-blue-800 font-semibold">{testimonial.avatar}</span>
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900">{testimonial.name}</div>
                      <div className="text-sm text-gray-600">{testimonial.role}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section id="contact" className="cta-gradient text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Rejoignez la communauté Météo Sentinelle
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Soyez parmi les premiers à bénéficier de notre service d'alerte météo nouvelle génération alimenté par la NASA
          </p>
          
          <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
            <div className="grid md:grid-cols-2 gap-4 mb-6">
              <Input
                type="email"
                placeholder="Votre adresse email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isSubmitting}
                className="bg-white/10 border-white/20 text-white placeholder-white/70"
              />
              <Button 
                type="submit" 
                disabled={isSubmitting}
                className="bg-white text-blue-800 hover:bg-blue-50 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Envoi...
                  </>
                ) : (
                  'Demander un accès'
                )}
              </Button>
            </div>
            <Textarea
              placeholder="Message (optionnel) - Parlez-nous de vos besoins spécifiques"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={isSubmitting}
              className="bg-white/10 border-white/20 text-white placeholder-white/70 mb-4"
              rows={3}
            />
          </form>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center mb-4">
                <Shield className="h-8 w-8 text-blue-400 mr-3" />
                <span className="text-xl font-bold">Météo Sentinelle</span>
              </div>
              <p className="text-gray-300 text-sm">
                Protection météorologique avancée pour la Guadeloupe alimentée par les données NASA.
              </p>
            </div>
            
            <div>
              <h3 className="font-semibold mb-4">Services</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><a href="#" className="hover:text-white">Prévisions météo</a></li>
                <li><a href="#" className="hover:text-white">Alertes SMS</a></li>
                <li><a href="#" className="hover:text-white">API professionnelle</a></li>
                <li><Button variant="link" className="p-0 h-auto text-sm text-gray-300 hover:text-white" onClick={handleNavigateToMap}>Carte interactive</Button></li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-semibold mb-4">Support</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><a href="#" className="hover:text-white">Documentation</a></li>
                <li><a href="#" className="hover:text-white">FAQ</a></li>
                <li><a href="#" className="hover:text-white">Contact</a></li>
                <li><a href="#" className="hover:text-white">Statut service</a></li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-semibold mb-4">Contact</h3>
              <div className="space-y-2 text-sm text-gray-300">
                <div className="flex items-center">
                  <Phone className="w-4 h-4 mr-2" />
                  <span>+590 590 XX XX XX</span>
                </div>
                <div className="flex items-center">
                  <Mail className="w-4 h-4 mr-2" />
                  <span>contact@meteo-sentinelle.gp</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center">
            <p className="text-gray-400 text-sm">
              © 2025 Météo Sentinelle. Tous droits réservés. Données météorologiques NASA.
            </p>
            <div className="flex space-x-4 mt-4 md:mt-0">
              <a href="#" className="text-gray-400 hover:text-white text-sm">Mentions légales</a>
              <a href="#" className="text-gray-400 hover:text-white text-sm">Confidentialité</a>
              <a href="#" className="text-gray-400 hover:text-white text-sm">CGU</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;