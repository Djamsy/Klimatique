import axios from 'axios';

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL || 'https://7cc3db80-543d-4833-ab38-94990a7b2d12.preview.emergentagent.com';
const API = `${BACKEND_URL}/api`;

console.log('🔧 Backend URL:', BACKEND_URL);
console.log('🔧 API URL:', API);

// Weather API Service
export class WeatherService {
  
  // Récupère la météo d'une commune
  static async getWeatherByCommune(commune) {
    try {
      const response = await axios.get(`${API}/weather/${encodeURIComponent(commune)}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching weather for ${commune}:`, error);
      throw error;
    }
  }
  
  // Récupère la météo de plusieurs communes
  static async getWeatherMultipleCommunes(communes) {
    try {
      const communesStr = communes.join(',');
      const response = await axios.get(`${API}/weather/multiple/${encodeURIComponent(communesStr)}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching weather for multiple communes:', error);
      throw error;
    }
  }
  
  // Récupère les statistiques météo globales
  static async getWeatherStats() {
    try {
      const response = await axios.get(`${API}/weather/stats`);
      return response.data;
    } catch (error) {
      console.error('Error fetching weather stats:', error);
      throw error;
    }
  }
  
  // Récupère les alertes actives
  static async getActiveAlerts() {
    try {
      const response = await axios.get(`${API}/alerts`);
      return response.data;
    } catch (error) {
      console.error('Error fetching alerts:', error);
      throw error;
    }
  }
  
  // Récupère les alertes d'une commune
  static async getAlertsByCommune(commune) {
    try {
      const response = await axios.get(`${API}/alerts/${encodeURIComponent(commune)}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching alerts for ${commune}:`, error);
      throw error;
    }
  }
  
  // Récupère une image satellite
  static async getSatelliteImage(request) {
    try {
      const response = await axios.post(`${API}/satellite/image`, request);
      return response.data;
    } catch (error) {
      console.error('Error fetching satellite image:', error);
      throw error;
    }
  }
  
  // Récupère les couches satellite disponibles
  static async getSatelliteLayers() {
    try {
      const response = await axios.get(`${API}/satellite/layers`);
      return response.data;
    } catch (error) {
      console.error('Error fetching satellite layers:', error);
      throw error;
    }
  }
}

// Subscription API Service  
export class SubscriptionService {
  
  // Inscription utilisateur
  static async subscribeUser(subscriptionData) {
    try {
      const response = await axios.post(`${API}/subscribe`, subscriptionData);
      return response.data;
    } catch (error) {
      console.error('Error subscribing user:', error);
      throw error;
    }
  }
  
  // Demande de contact
  static async sendContactRequest(contactData) {
    try {
      const response = await axios.post(`${API}/contact`, contactData);
      return response.data;
    } catch (error) {
      console.error('Error sending contact request:', error);
      throw error;
    }
  }
  
  // Désabonnement
  static async unsubscribeUser(unsubscribeData) {
    try {
      const response = await axios.post(`${API}/unsubscribe`, unsubscribeData);
      return response.data;
    } catch (error) {
      console.error('Error unsubscribing user:', error);
      throw error;
    }
  }
  
  // Statistiques abonnements
  static async getSubscriptionStats() {
    try {
      const response = await axios.get(`${API}/subscribers/stats`);
      return response.data;
    } catch (error) {
      console.error('Error fetching subscription stats:', error);
      throw error;
    }
  }
}

// Config API Service
export class ConfigService {
  
  // Récupère la liste des communes
  static async getCommunes() {
    try {
      const response = await axios.get(`${API}/config/communes`);
      return response.data;
    } catch (error) {
      console.error('Error fetching communes:', error);
      throw error;
    }
  }
  
  // Récupère les types d'alertes
  static async getAlertTypes() {
    try {
      const response = await axios.get(`${API}/config/alert-types`);
      return response.data;
    } catch (error) {
      console.error('Error fetching alert types:', error);
      throw error;
    }
  }
  
  // Status API
  static async getApiStatus() {
    try {
      const response = await axios.get(`${API}/status`);
      return response.data;
    } catch (error) {
      console.error('Error fetching API status:', error);
      throw error;
    }
  }
}

// Utilitaires pour le cache client
export class CacheUtils {
  
  static CACHE_DURATION = 5 * 60 * 1000; // 5 minutes en milliseconds
  
  // Sauvegarde en localStorage avec timestamp
  static setCache(key, data) {
    const cacheData = {
      data,
      timestamp: Date.now()
    };
    localStorage.setItem(`meteo_cache_${key}`, JSON.stringify(cacheData));
  }
  
  // Récupère depuis localStorage avec vérification expiration
  static getCache(key) {
    try {
      const cached = localStorage.getItem(`meteo_cache_${key}`);
      if (!cached) return null;
      
      const { data, timestamp } = JSON.parse(cached);
      
      // Vérifie si le cache a expiré
      if (Date.now() - timestamp > this.CACHE_DURATION) {
        localStorage.removeItem(`meteo_cache_${key}`);
        return null;
      }
      
      return data;
    } catch (error) {
      console.error('Cache retrieval error:', error);
      return null;
    }
  }
  
  // Nettoie le cache expiré
  static cleanExpiredCache() {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith('meteo_cache_')) {
        try {
          const cached = JSON.parse(localStorage.getItem(key));
          if (Date.now() - cached.timestamp > this.CACHE_DURATION) {
            localStorage.removeItem(key);
          }
        } catch (error) {
          localStorage.removeItem(key); // Supprime les entrées corrompues
        }
      }
    });
  }
}

// Service météo avec cache côté client
export class CachedWeatherService {
  
  // Récupère météo avec cache client pour améliorer performance
  static async getWeatherWithCache(commune) {
    const cacheKey = `weather_${commune}`;
    
    // Essaie d'abord le cache
    const cached = CacheUtils.getCache(cacheKey);
    if (cached) {
      console.log(`Weather served from client cache for ${commune}`);
      return cached;
    }
    
    // Sinon, appel API
    try {
      const data = await WeatherService.getWeatherByCommune(commune);
      CacheUtils.setCache(cacheKey, data);
      console.log(`Weather fetched from API and cached for ${commune}`);
      return data;
    } catch (error) {
      console.error(`Failed to fetch weather for ${commune}:`, error);
      throw error;
    }
  }
  
  // Récupère prévisions multiples avec cache
  static async getMultipleWeatherWithCache(communes) {
    const promises = communes.map(commune => this.getWeatherWithCache(commune));
    const results = await Promise.allSettled(promises);
    
    const successfulResults = {};
    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        successfulResults[communes[index]] = result.value;
      } else {
        console.error(`Failed to get weather for ${communes[index]}:`, result.reason);
      }
    });
    
    return successfulResults;
  }
  
  // Force refresh (bypass cache)
  static async forceRefreshWeather(commune) {
    const cacheKey = `weather_${commune}`;
    localStorage.removeItem(`meteo_cache_${cacheKey}`);
    return await this.getWeatherWithCache(commune);
  }
}

// Weather Overlay Service
export class WeatherOverlayService {
  
  // Services Overlays Météo
  static async getCloudsOverlay() {
    try {
      const response = await axios.get(`${API}/weather/overlay/clouds`);
      return response.data;
    } catch (error) {
      console.error('Error fetching clouds overlay:', error);
      throw error;
    }
  }

  static async getPrecipitationOverlay() {
    try {
      const response = await axios.get(`${API}/weather/overlay/precipitation`);
      return response.data;
    } catch (error) {
      console.error('Error fetching precipitation overlay:', error);
      throw error;
    }
  }

  static async getRadarOverlay() {
    try {
      const response = await axios.get(`${API}/weather/overlay/radar`);
      return response.data;
    } catch (error) {
      console.error('Error fetching radar overlay:', error);
      throw error;
    }
  }

  static async getPluviometerData(commune) {
    try {
      const response = await axios.get(`${API}/weather/pluviometer/${encodeURIComponent(commune)}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching pluviometer data:', error);
      throw error;
    }
  }

  static async getCacheStats() {
    try {
      const response = await axios.get(`${API}/cache/stats`);
      return response.data;
    } catch (error) {
      console.error('Error fetching cache stats:', error);
      throw error;
    }
  }
}

// AI Cyclone Prediction Service
export class CycloneAIService {
  
  // Services IA Prédictive Cyclonique
  static async getCyclonePrediction(commune) {
    try {
      const response = await axios.get(`${API}/ai/cyclone/predict/${encodeURIComponent(commune)}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching cyclone prediction:', error);
      throw error;
    }
  }

  static async getCycloneTimeline(commune) {
    try {
      const response = await axios.get(`${API}/ai/cyclone/timeline/${encodeURIComponent(commune)}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching cyclone timeline:', error);
      throw error;
    }
  }

  static async getHistoricalDamage(commune) {
    try {
      const response = await axios.get(`${API}/ai/cyclone/historical/${encodeURIComponent(commune)}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching historical damage:', error);
      throw error;
    }
  }

  static async getGlobalCycloneRisk() {
    try {
      const response = await axios.get(`${API}/ai/cyclone/global-risk`);
      return response.data;
    } catch (error) {
      console.error('Error fetching global cyclone risk:', error);
      throw error;
    }
  }

  static async getAIModelInfo() {
    try {
      const response = await axios.get(`${API}/ai/model/info`);
      return response.data;
    } catch (error) {
      console.error('Error fetching AI model info:', error);
      throw error;
    }
  }
}

// Export par défaut
export default {
  WeatherService,
  SubscriptionService,
  ConfigService,
  CachedWeatherService,
  CacheUtils,
  CycloneAIService
};