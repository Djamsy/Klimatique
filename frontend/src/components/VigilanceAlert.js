import React, { useState, useEffect } from 'react';
import { Alert, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { 
  AlertTriangle, 
  Shield, 
  Wind, 
  CloudRain, 
  Thermometer, 
  Clock,
  ExternalLink,
  Brain
} from 'lucide-react';

const VigilanceAlert = ({ showDetails = true, showIA = true, className = "" }) => {
  const [vigilanceData, setVigilanceData] = useState(null);
  const [theme, setTheme] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchVigilanceData();
    // Mise à jour toutes les 30 minutes
    const interval = setInterval(fetchVigilanceData, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchVigilanceData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [vigilanceResponse, themeResponse] = await Promise.all([
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/vigilance/guadeloupe`),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/vigilance/theme`)
      ]);
      
      if (!vigilanceResponse.ok || !themeResponse.ok) {
        throw new Error('Erreur lors de la récupération des données');
      }
      
      const vigilanceData = await vigilanceResponse.json();
      const themeData = await themeResponse.json();
      
      setVigilanceData(vigilanceData);
      setTheme(themeData);
      
    } catch (err) {
      console.error('Error fetching vigilance data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getVigilanceIcon = (level) => {
    switch (level) {
      case 'rouge':
        return <AlertTriangle className="h-5 w-5 text-red-600" />;
      case 'orange':
        return <AlertTriangle className="h-5 w-5 text-orange-600" />;
      case 'jaune':
        return <Shield className="h-5 w-5 text-yellow-600" />;
      default:
        return <Shield className="h-5 w-5 text-green-600" />;
    }
  };

  const getVigilanceBackground = (level) => {
    switch (level) {
      case 'rouge':
        return 'bg-gradient-to-r from-red-600 to-red-800';
      case 'orange':
        return 'bg-gradient-to-r from-orange-600 to-orange-800';
      case 'jaune':
        return 'bg-gradient-to-r from-yellow-500 to-yellow-700';
      default:
        return 'bg-gradient-to-r from-green-600 to-green-800';
    }
  };

  const getVigilanceBorder = (level) => {
    switch (level) {
      case 'rouge':
        return 'border-red-500';
      case 'orange':
        return 'border-orange-500';
      case 'jaune':
        return 'border-yellow-500';
      default:
        return 'border-green-500';
    }
  };

  const getRiskIcon = (riskCode) => {
    switch (riskCode) {
      case 'VENT':
        return <Wind className="h-4 w-4" />;
      case 'PLUIE':
        return <CloudRain className="h-4 w-4" />;
      case 'CANICULE':
        return <Thermometer className="h-4 w-4" />;
      default:
        return <AlertTriangle className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="bg-gray-200 h-20 rounded-lg"></div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className={`border-yellow-500 ${className}`}>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Service de vigilance temporairement indisponible. 
          Consultez <a href="https://meteofrance.fr" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">meteofrance.fr</a>
        </AlertDescription>
      </Alert>
    );
  }

  if (!vigilanceData) {
    return null;
  }

  return (
    <div className={className}>
      {/* Alerte principale */}
      <div className={`${getVigilanceBackground(vigilanceData.color_level)} text-white rounded-lg p-4 mb-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getVigilanceIcon(vigilanceData.color_level)}
            <div>
              <h3 className="font-bold text-lg">
                VIGILANCE {vigilanceData.color_level.toUpperCase()}
              </h3>
              <p className="text-sm opacity-90">
                Météo France • Guadeloupe
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold">
              {vigilanceData.global_risk_score}/100
            </div>
            <div className="text-xs opacity-75">
              Score officiel
            </div>
          </div>
        </div>
        
        {/* Heure de mise à jour */}
        <div className="mt-3 flex items-center justify-between text-xs opacity-75">
          <div className="flex items-center space-x-1">
            <Clock className="h-3 w-3" />
            <span>Mis à jour: {new Date(vigilanceData.last_updated).toLocaleTimeString('fr-FR')}</span>
          </div>
          <div className="flex items-center space-x-1">
            <span>Valide jusqu'à: {new Date(vigilanceData.valid_until).toLocaleTimeString('fr-FR')}</span>
          </div>
        </div>
      </div>

      {/* Risques identifiés */}
      {vigilanceData.risks && vigilanceData.risks.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-gray-900 mb-2">Risques identifiés</h4>
          <div className="flex flex-wrap gap-2">
            {vigilanceData.risks.map((risk, index) => (
              <Badge
                key={index}
                variant="outline"
                className={`flex items-center space-x-1 ${getVigilanceBorder(risk.level)} text-${risk.level === 'rouge' ? 'red' : risk.level === 'orange' ? 'orange' : risk.level === 'jaune' ? 'yellow' : 'green'}-700`}
              >
                {getRiskIcon(risk.code)}
                <span>{risk.name}</span>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Recommandations officielles */}
      {showDetails && (
        <Card className={`border-l-4 ${getVigilanceBorder(vigilanceData.color_level)}`}>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center space-x-2 text-lg">
              <Shield className="h-5 w-5 text-blue-600" />
              <span>Recommandations Officielles</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {vigilanceData.recommendations.map((rec, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
                  <span className="text-gray-700">{rec}</span>
                </div>
              ))}
            </div>
            
            {/* Lien vers source officielle */}
            <div className="mt-4 pt-3 border-t border-gray-200">
              <a 
                href="https://meteofrance.fr/vigilance" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 text-sm"
              >
                <ExternalLink className="h-3 w-3" />
                <span>Consulter la source officielle</span>
              </a>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Section IA en complément */}
      {showIA && (
        <Card className="mt-4 bg-gray-50">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center space-x-2 text-base text-gray-700">
              <Brain className="h-4 w-4" />
              <span>Analyse IA Complémentaire</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600 mb-3">
              Notre IA analyse les conditions locales pour fournir des prédictions spécifiques par commune.
            </p>
            <div className="text-xs text-gray-500">
              Les prédictions IA complètent les vigilances officielles et ne les remplacent pas.
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default VigilanceAlert;