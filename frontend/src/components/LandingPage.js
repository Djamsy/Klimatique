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
  Globe,
  Calendar,
  Wind,
  Droplets,
  ExternalLink
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { CachedWeatherService, SubscriptionService, ConfigService, CycloneAIService } from '../services/weatherService';
import { useToast } from '../hooks/use-toast';
import { useVigilanceTheme } from '../hooks/useVigilanceTheme';
import VigilanceAlert from './VigilanceAlert';

const LandingPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [weatherData, setWeatherData] = useState(null);
  const [isLoadingWeather, setIsLoadingWeather] = useState(true);
  const [communes, setCommunes] = useState([]);
  const [globalRisk, setGlobalRisk] = useState(null);
  const [vigilanceData, setVigilanceData] = useState(null);
  const [stats, setStats] = useState({
    total: 32,
    precision: 94,
    response_time: 15,
    users: '2.5k'
  });
  const { toast } = useToast();
  const { theme: vigilanceTheme, loading: themeLoading } = useVigilanceTheme();

  // Communes principales pour l'affichage
  const mainCommunes = ['Pointe-à-Pitre', 'Basse-Terre', 'Sainte-Anne', 'Le Moule', 'Saint-François'];

  useEffect(() => {
    loadInitialData();
    // Nettoie le cache expiré au chargement
    const { CacheUtils } = require('../services/weatherService');
    CacheUtils.cleanExpiredCache();
  }, []);

  useEffect(() => {
    // Appliquer le thème de vigilance dynamiquement
    if (vigilanceTheme && !themeLoading) {
      document.body.className = `vigilance-${vigilanceTheme.level}`;
      document.body.style.setProperty('--current-vigilance-primary', vigilanceTheme.primary_color);
      document.body.style.setProperty('--current-vigilance-level', vigilanceTheme.level);
    }
  }, [vigilanceTheme, themeLoading]);

  const loadInitialData = async () => {
    try {
      // Charge la configuration et la météo en parallèle
      const [communesData, weatherResults, globalRiskData, vigilanceResponse] = await Promise.all([
        ConfigService.getCommunes(),
        CachedWeatherService.getMultipleWeatherWithCache(mainCommunes),
        CycloneAIService.getGlobalCycloneRisk().catch(error => {
          console.error('Error loading global risk:', error);
          return null;
        }),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/vigilance/guadeloupe`).catch(error => {
          console.error('Error loading vigilance:', error);
          return null;
        })
      ]);
      
      setCommunes(communesData.communes || []);
      setGlobalRisk(globalRiskData);
      
      // Traitement des données de vigilance
      if (vigilanceResponse && vigilanceResponse.ok) {
        const vigilanceData = await vigilanceResponse.json();
        setVigilanceData(vigilanceData);
      }
      
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
      content: "Grâce à Klimaclique, nous anticipons mieux les risques d'inondation. Un outil indispensable pour protéger nos citoyens.",
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

  // Composant d'encart publicitaire
  const AdBanner = ({ position, className = '', children }) => (
    <div className={`ad-banner ad-${position} ${className}`}>
      <div className="ad-content bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 text-center">
        <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Publicité</div>
        {children}
      </div>
    </div>
  );

  // Différents types d'encarts publicitaires
  const AdContent = {
    topBanner: (
      <div className="flex items-center justify-center space-x-4">
        <div className="text-sm text-gray-700">
          <strong className="text-blue-700">Protégez votre maison</strong> - Assurance Météo Antilles
        </div>
        <Button variant="outline" size="sm" className="text-xs">
          En savoir plus
        </Button>
      </div>
    ),
    
    sidebarWeather: (
      <div className="space-y-2">
        <div className="font-semibold text-blue-800">Équipement Météo Pro</div>
        <p className="text-xs text-gray-600">Stations météo connectées pour particuliers et professionnels</p>
        <Button variant="outline" size="sm" className="w-full text-xs">
          Découvrir
        </Button>
      </div>
    ),
    
    betweenSections: (
      <div className="py-2">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="font-semibold text-green-800">Agriculture Connectée</div>
            <p className="text-xs text-gray-600">Solutions IoT pour l'agriculture tropicale</p>
          </div>
          <Button variant="outline" size="sm" className="ml-4">
            <ExternalLink className="w-3 h-3 mr-1" />
            Voir
          </Button>
        </div>
      </div>
    ),
    
    footerSponsored: (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="text-center p-3 bg-white rounded border">
          <div className="font-semibold text-indigo-700">Météo Services Pro</div>
          <p className="text-xs text-gray-600">API météo pour développeurs</p>
        </div>
        <div className="text-center p-3 bg-white rounded border">
          <div className="font-semibold text-orange-700">Formation Sécurité</div>
          <p className="text-xs text-gray-600">Gestion de crise météorologique</p>
        </div>
        <div className="text-center p-3 bg-white rounded border">
          <div className="font-semibold text-teal-700">EcoTech Caraïbes</div>
          <p className="text-xs text-gray-600">Technologies environnementales</p>
        </div>
      </div>
    )
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Alert Banner - Vigilance dynamique */}
      {vigilanceTheme && !themeLoading && vigilanceTheme.level !== 'vert' && (
        <div 
          className="vigilance-alert-banner text-white py-2 px-4 text-center text-sm font-medium transition-all duration-300"
          style={{
            backgroundColor: vigilanceTheme.primary_color
          }}
        >
          <AlertTriangle className="inline w-4 h-4 mr-2 alert-icon" />
          <span className="hidden sm:inline">Vigilance {vigilanceTheme.level.toUpperCase()} : </span>
          <span className="sm:hidden">⚠️ {vigilanceTheme.level.toUpperCase()} : </span>
          {vigilanceTheme.risks && vigilanceTheme.risks.length > 0 
            ? vigilanceTheme.risks[0].description || `Conditions météorologiques ${vigilanceTheme.level}`
            : `Vigilance ${vigilanceTheme.level} en cours`
          }
        </div>
      )}

      {/* Navigation */}
      <nav className="navbar sticky top-0 z-50 bg-white/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center animate-fade-in-left">
              <Shield className="h-8 w-8 text-blue-800 mr-3" />
              <span className="text-xl font-bold text-blue-800">Klimaclique</span>
            </div>
            <div className="hidden md:flex space-x-8 animate-fade-in-down">
              <a href="#features" className="text-gray-700 hover:text-blue-800 transition-colors duration-300">Fonctionnalités</a>
              <a href="#previsions" className="text-gray-700 hover:text-blue-800 transition-colors duration-300">Prévisions</a>
              <Button 
                variant="ghost" 
                onClick={handleNavigateToMap}
                className="text-gray-700 hover:text-blue-800 transition-colors duration-300 btn-animated"
              >
                Carte Interactive
              </Button>
              <a href="#temoignages" className="text-gray-700 hover:text-blue-800 transition-colors duration-300">Témoignages</a>
              <a href="#contact" className="text-gray-700 hover:text-blue-800 transition-colors duration-300">Contact</a>
            </div>
          </div>
        </div>
      </nav>

      {/* Encart Publicitaire Principal - Top Banner */}
      <div className="bg-gray-50 border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
          <AdBanner position="top">
            {AdContent.topBanner}
          </AdBanner>
        </div>
      </div>

      {/* Hero Section avec vigilance adaptative */}
      <section className="relative overflow-hidden">
        {/* Background avec gradient adaptatif selon vigilance */}
        <div className={`absolute inset-0 ${
          vigilanceData ? 
            `bg-gradient-to-br ${vigilanceTheme?.helpers?.getVigilanceGradient(vigilanceData.color_level) || 'from-blue-900 via-blue-800 to-purple-900'}` :
            'bg-gradient-to-br from-blue-900 via-blue-800 to-purple-900'
        }`}></div>
        <div className="absolute inset-0 bg-black opacity-20"></div>
        
        {/* Animation de particules météo */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-4 -right-4 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
          <div className="absolute -bottom-8 -left-4 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse delay-1000"></div>
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-cyan-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-500"></div>
        </div>
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
          <div className="text-center">
            {/* Alerte de vigilance en header */}
            {vigilanceData && (
              <div className="mb-8 max-w-2xl mx-auto">
                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/20">
                  <div className="flex items-center justify-center space-x-3 mb-2">
                    <Shield className="w-6 h-6 text-yellow-300" />
                    <span className="text-white font-bold text-lg">
                      VIGILANCE {vigilanceData.color_level.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-white/90 text-sm">
                    {vigilanceData.recommendations[0] || 'Consultez les recommandations officielles'}
                  </p>
                </div>
              </div>
            )}
            
            {/* Badge innovant */}
            <div className="inline-flex items-center bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 mb-8 border border-white/20">
              <Shield className="w-4 h-4 text-cyan-400 mr-2" />
              <span className="text-cyan-100 text-sm font-medium">
                {vigilanceData ? 'Vigilance Officielle' : 'Météo France'} • NASA • IA
              </span>
            </div>
            
            {/* Titre principal avec adaptation */}
            <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold mb-6 text-white leading-tight animate-fade-in-up">
              <span className="block">
                {vigilanceData && vigilanceData.color_level !== 'vert' ? 
                  'Restez informés,' : 
                  'Anticipez les risques,'
                }
              </span>
            </h1>
            
            {/* Sous-titre adaptatif */}
            <p className="text-xl sm:text-2xl lg:text-3xl mb-12 text-blue-100 leading-relaxed max-w-4xl mx-auto animate-fade-in-up animate-delay-200">
              {vigilanceData && vigilanceData.color_level !== 'vert' ? 
                'Suivez les recommandations officielles Météo France et restez informés.' :
                'Recommandations officielles et analyse IA pour votre sécurité en Guadeloupe.'
              }
              <span className="block mt-2 text-lg sm:text-xl lg:text-2xl text-cyan-200">
                Vigilances officielles • Données NASA • IA prédictive
              </span>
            </p>
            
            {/* Boutons d'action modernisés */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16 animate-fade-in-up animate-delay-400">
              <Button 
                size="lg" 
                className="group relative overflow-hidden bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white font-semibold text-lg px-8 py-4 rounded-2xl border-0 shadow-xl shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 btn-animated"
                onClick={handleNavigateToMap}
              >
                <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <Map className="w-6 h-6 mr-3" />
                Carte des Vigilances
                <ChevronRight className="w-5 h-5 ml-3 group-hover:translate-x-1 transition-transform duration-300" />
              </Button>
              
              <Button 
                variant="outline" 
                size="lg" 
                className="group border-2 border-white/30 text-white bg-white/10 hover:bg-white/20 backdrop-blur-sm font-semibold text-lg px-8 py-4 rounded-2xl transition-all duration-300 transform hover:scale-105 btn-animated"
                onClick={() => document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })}
              >
                <Bell className="w-5 h-5 mr-3" />
                Alertes Bêta
              </Button>
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

      {/* Section Vigilance Détaillée */}
      <section className="py-12 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <VigilanceAlert showDetails={true} showIA={true} />
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Performances en temps réel
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Notre IA analyse 24h/24 les conditions météorologiques pour vous offrir la meilleure protection
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center group">
              <div className="relative">
                <div className="text-4xl md:text-5xl font-bold text-blue-600 mb-2 group-hover:scale-110 transition-transform duration-300">
                  {stats.total}<span className="text-2xl text-blue-400">/32</span>
                </div>
                <div className="absolute -top-2 -right-2 w-4 h-4 bg-green-500 rounded-full animate-pulse"></div>
              </div>
              <div className="text-gray-600 text-sm md:text-base font-medium">Communes Surveillées</div>
              <div className="text-xs text-gray-500 mt-1">En temps réel</div>
            </div>
            
            <div className="text-center group">
              <div className="text-4xl md:text-5xl font-bold text-green-600 mb-2 group-hover:scale-110 transition-transform duration-300">
                {stats.precision}<span className="text-2xl text-green-400">%</span>
              </div>
              <div className="text-gray-600 text-sm md:text-base font-medium">Précision IA</div>
              <div className="text-xs text-gray-500 mt-1">Prédictions cycloniques</div>
            </div>
            
            <div className="text-center group">
              <div className="text-4xl md:text-5xl font-bold text-purple-600 mb-2 group-hover:scale-110 transition-transform duration-300">
                {stats.response_time}<span className="text-2xl text-purple-400">s</span>
              </div>
              <div className="text-gray-600 text-sm md:text-base font-medium">Temps de Réponse</div>
              <div className="text-xs text-gray-500 mt-1">Alertes instantanées</div>
            </div>
            
            <div className="text-center group">
              <div className="text-4xl md:text-5xl font-bold text-orange-600 mb-2 group-hover:scale-110 transition-transform duration-300">
                {stats.users}
              </div>
              <div className="text-gray-600 text-sm md:text-base font-medium">Utilisateurs Actifs</div>
              <div className="text-xs text-gray-500 mt-1">Communauté protégée</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-gradient-to-br from-gray-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fade-in-up">
            <div className="inline-flex items-center bg-blue-100 rounded-full px-4 py-2 mb-6 animate-bounce">
              <Brain className="w-5 h-5 text-blue-600 mr-2" />
              <span className="text-blue-800 font-medium">Intelligence Artificielle</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 animate-fade-in-up animate-delay-200">
              Technologie de pointe au service de votre sécurité
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto animate-fade-in-up animate-delay-300">
              Klimaclique combine données satellitaires NASA, intelligence artificielle et 
              connaissance du terrain pour vous offrir des prédictions d'une précision inégalée.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const IconComponent = getFeatureIcon(feature.icon);
              return (
                <Card key={feature.id} className={`group relative overflow-hidden bg-white hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 border-0 shadow-lg animate-fade-in-up animate-delay-${(index + 1) * 100} shimmer-effect`}>
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
                  
                  <CardHeader className="pb-4 text-center">
                    <div className="relative">
                      <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center mb-4 shadow-lg group-hover:shadow-xl transition-shadow duration-300">
                        <IconComponent className="w-8 h-8 text-white" />
                      </div>
                      <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                        <div className="w-2 h-2 bg-white rounded-full"></div>
                      </div>
                    </div>
                    <CardTitle className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors duration-300">
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Nouvelle section IA */}
          <div className="mt-20 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-8 md:p-12 text-white">
            <div className="text-center">
              <div className="inline-flex items-center bg-white/20 rounded-full px-4 py-2 mb-6">
                <Brain className="w-5 h-5 mr-2" />
                <span className="font-medium">IA Prédictive</span>
              </div>
              <h3 className="text-2xl md:text-3xl font-bold mb-4">
                Analyse prédictive des dégâts cycloniques
              </h3>
              <p className="text-lg text-blue-100 mb-8 max-w-2xl mx-auto">
                Notre modèle d'IA analyse humidité, température, pression et vents pour prédire avec précision les dégâts potentiels sur les infrastructures, l'agriculture et la population.
              </p>
              <div className="grid md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-cyan-300 mb-2">🏗️</div>
                  <div className="font-semibold">Infrastructure</div>
                  <div className="text-sm text-blue-200">Bâtiments, routes, réseaux</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-300 mb-2">🌾</div>
                  <div className="font-semibold">Agriculture</div>
                  <div className="text-sm text-blue-200">Cultures, élevage, équipements</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-yellow-300 mb-2">👥</div>
                  <div className="font-semibold">Population</div>
                  <div className="text-sm text-blue-200">Sécurité, évacuation, secours</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Global Risk Section */}
      {globalRisk && (
        <section className="py-20 bg-gradient-to-br from-slate-900 via-blue-900 to-purple-900 text-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <div className="inline-flex items-center bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 mb-6">
                <Brain className="w-5 h-5 mr-2" />
                <span className="font-medium">Analyse IA Temps Réel</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Risque Cyclonique Actuel
              </h2>
              <p className="text-lg text-blue-100 max-w-2xl mx-auto">
                Notre intelligence artificielle analyse en continu les conditions météorologiques pour évaluer le risque cyclonique
              </p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-8 mb-12">
              {/* Risque Global */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 text-center border border-white/20">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-400 to-cyan-400 rounded-full flex items-center justify-center">
                    <Globe className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h3 className="text-xl font-semibold mb-4">Niveau Régional</h3>
                <div className={`text-4xl font-bold mb-4 ${
                  globalRisk.global_risk_level === 'critique' ? 'text-red-400' :
                  globalRisk.global_risk_level === 'élevé' ? 'text-orange-400' :
                  globalRisk.global_risk_level === 'modéré' ? 'text-yellow-400' :
                  'text-green-400'
                }`}>
                  {globalRisk.global_risk_level.toUpperCase()}
                </div>
                <p className="text-blue-100">
                  Analyse globale Guadeloupe
                </p>
              </div>
              
              {/* Communes à risque */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 text-center border border-white/20">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 bg-gradient-to-br from-orange-400 to-red-400 rounded-full flex items-center justify-center">
                    <AlertTriangle className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h3 className="text-xl font-semibold mb-4">Zones d'Alerte</h3>
                <div className="text-4xl font-bold text-orange-400 mb-4">
                  {globalRisk.high_risk_count + globalRisk.critical_risk_count}
                </div>
                <p className="text-blue-100">
                  Communes en surveillance
                </p>
                <div className="mt-4 text-sm text-blue-200">
                  {globalRisk.critical_risk_count > 0 && (
                    <div className="bg-red-500/20 px-3 py-1 rounded-full mb-2">
                      {globalRisk.critical_risk_count} critiques
                    </div>
                  )}
                  {globalRisk.high_risk_count > 0 && (
                    <div className="bg-orange-500/20 px-3 py-1 rounded-full">
                      {globalRisk.high_risk_count} élevées
                    </div>
                  )}
                </div>
              </div>
              
              {/* Recommandations */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-teal-400 rounded-full flex items-center justify-center">
                    <Shield className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h3 className="text-xl font-semibold mb-4">Recommandations</h3>
                <div className="space-y-3 text-sm text-left">
                  {globalRisk.regional_recommendations.length > 0 ? (
                    globalRisk.regional_recommendations.slice(0, 3).map((rec, index) => (
                      <div key={index} className="flex items-start space-x-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full mt-2 flex-shrink-0"></div>
                        <span className="text-blue-100">{rec}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-center">
                      <span className="text-green-400 text-3xl">✓</span>
                      <p className="mt-2 text-blue-100">Conditions normales</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Communes affectées */}
            {globalRisk.affected_communes.length > 0 && (
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
                <h4 className="text-lg font-semibold mb-6 flex items-center justify-center gap-2">
                  <MapPin className="w-5 h-5" />
                  Communes sous surveillance IA
                </h4>
                <div className="flex flex-wrap gap-3 justify-center">
                  {globalRisk.affected_communes.map((commune, index) => (
                    <div
                      key={index}
                      className="bg-orange-500/20 border border-orange-400/30 px-4 py-2 rounded-full text-sm font-medium hover:bg-orange-500/30 transition-colors cursor-pointer"
                    >
                      {commune}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="mt-12 text-center">
              <p className="text-xs text-blue-300 flex items-center justify-center gap-2">
                <Brain className="w-4 h-4" />
                Analyse IA mise à jour: {new Date(globalRisk.last_analysis).toLocaleString('fr-FR')}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Weather Forecast Section */}
      <section id="previsions" className="py-20 bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center bg-blue-100 rounded-full px-4 py-2 mb-6">
              <Cloud className="w-5 h-5 text-blue-600 mr-2" />
              <span className="text-blue-800 font-medium">Données NASA + IA</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Prévisions Intelligentes pour la Guadeloupe
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Météo détaillée avec prédictions de risques cycloniques alimentée par l'IA et les données satellitaires NASA
            </p>
          </div>
          
          {isLoadingWeather ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center bg-white rounded-2xl px-6 py-4 shadow-lg">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600 mr-3" />
                <span className="text-gray-700 font-medium">Analyse IA en cours des conditions météorologiques...</span>
              </div>
            </div>
          ) : weatherData && weatherData.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-6">
              {weatherData.map((weather, index) => (
                <Card key={weather.id} className="group relative overflow-hidden bg-white hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-3 border-0 shadow-lg">
                  {/* Gradient de risque en header */}
                  <div className={`absolute top-0 left-0 w-full h-2 ${
                    weather.riskLevel === 'critique' ? 'bg-gradient-to-r from-red-500 to-red-600' :
                    weather.riskLevel === 'élevé' ? 'bg-gradient-to-r from-orange-500 to-orange-600' :
                    weather.riskLevel === 'modéré' ? 'bg-gradient-to-r from-yellow-500 to-yellow-600' :
                    'bg-gradient-to-r from-green-500 to-green-600'
                  }`}></div>
                  
                  <CardHeader className="pb-3 pt-6">
                    <div className="flex items-center justify-between mb-2">
                      <CardTitle className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                        {weather.commune}
                      </CardTitle>
                      <Badge 
                        className={`text-xs px-2 py-1 font-medium ${
                          weather.riskLevel === 'critique' ? 'bg-red-100 text-red-800 border-red-200' :
                          weather.riskLevel === 'élevé' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                          weather.riskLevel === 'modéré' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
                          'bg-green-100 text-green-800 border-green-200'
                        }`}
                      >
                        {weather.riskLevel}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500 flex items-center">
                      <Calendar className="w-4 h-4 mr-1" />
                      {weather.day}
                    </p>
                  </CardHeader>
                  
                  <CardContent>
                    {/* Icône météo et température */}
                    <div className="text-center mb-4">
                      <div className="text-4xl mb-2 group-hover:scale-110 transition-transform duration-300">
                        {weather.icon}
                      </div>
                      <div className="text-2xl font-bold text-gray-900 mb-1">
                        {Math.round(weather.temperature.max)}°
                      </div>
                      <div className="text-sm text-gray-600">
                        Min: {Math.round(weather.temperature.min)}°
                      </div>
                    </div>
                    
                    {/* Description météo */}
                    <div className="text-center mb-4">
                      <p className="text-sm text-gray-700 font-medium">
                        {weather.weather}
                      </p>
                    </div>
                    
                    {/* Détails météo */}
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="flex items-center text-gray-600">
                          <Wind className="w-3 h-3 mr-1" />
                          Vent
                        </span>
                        <span className="font-medium text-gray-900">
                          {Math.round(weather.windSpeed)} km/h
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="flex items-center text-gray-600">
                          <CloudRain className="w-3 h-3 mr-1" />
                          Pluie
                        </span>
                        <span className="font-medium text-gray-900">
                          {weather.precipitation}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="flex items-center text-gray-600">
                          <Droplets className="w-3 h-3 mr-1" />
                          Humidité
                        </span>
                        <span className="font-medium text-gray-900">
                          {weather.humidity}%
                        </span>
                      </div>
                    </div>
                    
                    {/* Indicateur IA */}
                    <div className="mt-4 pt-3 border-t border-gray-100">
                      <div className="flex items-center justify-center text-xs text-gray-500">
                        <Brain className="w-3 h-3 mr-1" />
                        <span>Analyse IA • NASA</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="bg-white rounded-2xl p-8 shadow-lg max-w-md mx-auto">
                <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Données temporairement indisponibles
                </h3>
                <p className="text-gray-600">
                  Nos systèmes analysent les conditions actuelles. Veuillez patienter...
                </p>
              </div>
            </div>
          )}
          
          {/* Call to action */}
          <div className="text-center mt-16">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-8 text-white">
              <h3 className="text-2xl font-bold mb-4">
                Explorez toutes les communes en détail
              </h3>
              <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
                Accédez à la carte interactive avec prédictions IA pour chacune des 32 communes de Guadeloupe
              </p>
              <Button 
                size="lg" 
                className="bg-white text-blue-600 hover:bg-blue-50 font-semibold px-8 py-3 rounded-2xl shadow-xl transform hover:scale-105 transition-all duration-300"
                onClick={handleNavigateToMap}
              >
                <Map className="w-5 h-5 mr-2" />
                Voir la Carte Interactive
                <ChevronRight className="w-5 h-5 ml-2" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Encart Publicitaire - Entre Sections */}
      <div className="py-8 bg-gradient-to-r from-gray-50 to-blue-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <AdBanner position="between-sections">
            {AdContent.betweenSections}
          </AdBanner>
        </div>
      </div>

      {/* Testimonials Section */}
      <section id="temoignages" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Ils nous font confiance
            </h2>
            <p className="text-xl text-gray-600">
              Découvrez comment Klimaclique accompagne déjà les acteurs locaux
            </p>
          </div>
          
          <div className="grid lg:grid-cols-4 gap-8">
            {/* Témoignages */}
            <div className="lg:col-span-3">
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
            
            {/* Encart Publicitaire Sidebar */}
            <div className="lg:col-span-1">
              <div className="sticky top-24">
                <AdBanner position="sidebar" className="mb-4">
                  {AdContent.sidebarWeather}
                </AdBanner>
                
                {/* Statistiques additionnelles */}
                <Card className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50">
                  <CardContent className="text-center">
                    <div className="text-2xl font-bold text-blue-800 mb-2">{stats.users}</div>
                    <p className="text-sm text-gray-600 mb-3">Utilisateurs actifs</p>
                    <div className="text-lg font-semibold text-green-700 mb-1">{stats.precision}%</div>
                    <p className="text-xs text-gray-500">Précision des alertes</p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section id="contact" className="cta-gradient text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Rejoignez la communauté Klimaclique
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

      {/* Encart Publicitaire Sponsorisé - Avant Footer */}
      <div className="py-12 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h3 className="text-xl font-semibold text-gray-800 mb-2">Nos partenaires technologiques</h3>
            <p className="text-gray-600">Solutions professionnelles pour la météorologie tropicale</p>
          </div>
          <AdBanner position="footer-sponsored">
            {AdContent.footerSponsored}
          </AdBanner>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center mb-4">
                <Shield className="h-8 w-8 text-blue-400 mr-3" />
                <span className="text-xl font-bold">Klimaclique</span>
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
              © 2025 Klimaclique. Tous droits réservés. Données météorologiques NASA.
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