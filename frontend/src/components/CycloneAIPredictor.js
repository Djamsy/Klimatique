import React, { useState, useEffect } from 'react';
import { CycloneAIService } from '../services/weatherService';
import { AlertTriangle, TrendingUp, Clock, Shield, Brain, History, Globe } from 'lucide-react';

const CycloneAIPredictor = ({ commune, showTimeline = false, showHistorical = false }) => {
  const [prediction, setPrediction] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [historical, setHistorical] = useState(null);
  const [globalRisk, setGlobalRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('prediction');

  useEffect(() => {
    fetchPredictions();
  }, [commune]);

  const fetchPredictions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const predictionData = await CycloneAIService.getCyclonePrediction(commune);
      setPrediction(predictionData);
      
      if (showTimeline) {
        const timelineData = await CycloneAIService.getCycloneTimeline(commune);
        setTimeline(timelineData);
      }
      
      if (showHistorical) {
        const historicalData = await CycloneAIService.getHistoricalDamage(commune);
        setHistorical(historicalData);
      }
      
      // Récupère le risque global une seule fois
      if (!globalRisk) {
        const globalData = await CycloneAIService.getGlobalCycloneRisk();
        setGlobalRisk(globalData);
      }
      
    } catch (err) {
      console.error('Error fetching AI predictions:', err);
      setError('Erreur lors du chargement des prédictions IA');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'critique': return 'text-red-600 bg-red-100';
      case 'élevé': return 'text-orange-600 bg-orange-100';
      case 'modéré': return 'text-yellow-600 bg-yellow-100';
      case 'faible': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getDamageIcon = (percentage) => {
    if (percentage >= 70) return '🔴';
    if (percentage >= 40) return '🟠';
    if (percentage >= 20) return '🟡';
    return '🟢';
  };

  const formatConfidence = (confidence) => {
    if (confidence >= 90) return { text: 'Très haute', color: 'text-green-600' };
    if (confidence >= 70) return { text: 'Haute', color: 'text-blue-600' };
    if (confidence >= 50) return { text: 'Moyenne', color: 'text-yellow-600' };
    return { text: 'Faible', color: 'text-red-600' };
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="flex items-center space-x-2">
          <Brain className="h-5 w-5 text-blue-600 animate-spin" />
          <span className="text-gray-600">Analyse IA en cours...</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <span className="text-red-700">{error}</span>
        </div>
        <button
          onClick={fetchPredictions}
          className="mt-2 text-red-600 hover:text-red-800 underline"
        >
          Réessayer
        </button>
      </div>
    );
  }

  if (!prediction) {
    return (
      <div className="text-center py-8">
        <Brain className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600">Aucune prédiction IA disponible</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* En-tête avec risque global */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center">
              <Brain className="h-6 w-6 mr-2" />
              IA Prédictive Cyclonique
            </h2>
            <p className="text-blue-100 mt-1">Analyse avancée pour {commune}</p>
          </div>
          <div className="text-right">
            <div className={`px-4 py-2 rounded-full text-sm font-medium ${getRiskColor(prediction.risk_level)}`}>
              {prediction.risk_level.toUpperCase()}
            </div>
            <div className="text-blue-100 text-sm mt-1">
              Score: {prediction.risk_score}/100
            </div>
          </div>
        </div>
      </div>

      {/* Onglets */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('prediction')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'prediction'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Prédiction Actuelle
          </button>
          {showTimeline && (
            <button
              onClick={() => setActiveTab('timeline')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'timeline'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Évolution
            </button>
          )}
          {showHistorical && (
            <button
              onClick={() => setActiveTab('historical')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'historical'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Historique
            </button>
          )}
          {globalRisk && (
            <button
              onClick={() => setActiveTab('global')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'global'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Vue Globale
            </button>
          )}
        </nav>
      </div>

      {/* Contenu des onglets */}
      {activeTab === 'prediction' && (
        <div className="space-y-6">
          {/* Prédictions de dégâts */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-700">Infrastructure</h3>
                <span className="text-2xl">{getDamageIcon(prediction.damage_predictions.infrastructure)}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {prediction.damage_predictions.infrastructure}%
              </div>
              <div className="text-sm text-gray-600">Dégâts prévus</div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-700">Agriculture</h3>
                <span className="text-2xl">{getDamageIcon(prediction.damage_predictions.agriculture)}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {prediction.damage_predictions.agriculture}%
              </div>
              <div className="text-sm text-gray-600">Cultures affectées</div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-700">Population</h3>
                <span className="text-2xl">{getDamageIcon(prediction.damage_predictions.population_impact)}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {prediction.damage_predictions.population_impact}%
              </div>
              <div className="text-sm text-gray-600">Impact population</div>
            </div>
          </div>

          {/* Niveau de confiance */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="h-5 w-5 text-blue-600" />
                <span className="font-medium">Niveau de confiance</span>
              </div>
              <div className={`font-bold ${formatConfidence(prediction.confidence).color}`}>
                {formatConfidence(prediction.confidence).text} ({prediction.confidence}%)
              </div>
            </div>
          </div>

          {/* Recommandations */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <AlertTriangle className="h-5 w-5 mr-2 text-orange-600" />
              Recommandations
            </h3>
            <ul className="space-y-2">
              {prediction.recommendations.map((rec, index) => (
                <li key={index} className="flex items-start space-x-2">
                  <span className="text-orange-600 mt-1">•</span>
                  <span className="text-gray-700">{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {activeTab === 'timeline' && timeline && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center">
            <Clock className="h-5 w-5 mr-2 text-blue-600" />
            Évolution des Prédictions
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(timeline.timeline_predictions).map(([timeKey, timePrediction]) => (
              <div key={timeKey} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="text-center mb-3">
                  <div className="text-lg font-bold text-gray-900">{timeKey}</div>
                  <div className={`px-2 py-1 rounded text-xs font-medium ${getRiskColor(timePrediction.risk_level)}`}>
                    {timePrediction.risk_level}
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Infrastructure:</span>
                    <span className="font-medium">{timePrediction.damage_predictions.infrastructure}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Agriculture:</span>
                    <span className="font-medium">{timePrediction.damage_predictions.agriculture}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Population:</span>
                    <span className="font-medium">{timePrediction.damage_predictions.population_impact}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'historical' && historical && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center">
            <History className="h-5 w-5 mr-2 text-blue-600" />
            Historique des Dégâts
          </h3>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Année
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Événement
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Impact
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Dégâts
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {historical.historical_events.map((event, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {event.year}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {event.event_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {event.damage_type}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskColor(event.impact_level)}`}>
                          {event.impact_level}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {event.estimated_damage_percent}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'global' && globalRisk && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center">
            <Globe className="h-5 w-5 mr-2 text-blue-600" />
            Vue Globale - Guadeloupe
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h4 className="text-md font-medium mb-3">Niveau de Risque Régional</h4>
              <div className={`px-4 py-2 rounded-lg text-center ${getRiskColor(globalRisk.global_risk_level)}`}>
                <div className="text-2xl font-bold">{globalRisk.global_risk_level.toUpperCase()}</div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">{globalRisk.high_risk_count}</div>
                  <div className="text-gray-600">Risque élevé</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{globalRisk.critical_risk_count}</div>
                  <div className="text-gray-600">Risque critique</div>
                </div>
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h4 className="text-md font-medium mb-3">Recommandations Régionales</h4>
              <ul className="space-y-2">
                {globalRisk.regional_recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <span className="text-blue-600 mt-1">•</span>
                    <span className="text-gray-700 text-sm">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {globalRisk.affected_communes.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h4 className="text-md font-medium mb-3">Communes à Risque</h4>
              <div className="flex flex-wrap gap-2">
                {globalRisk.affected_communes.map((commune, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm"
                  >
                    {commune}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CycloneAIPredictor;