/**
 * Service de backup pour les overlays météo
 * Gère le fallback et retry des couches météo en cas d'échec
 */

class OverlayBackupService {
  constructor() {
    this.overlayStatus = new Map();
    this.backupData = new Map();
    this.retryTimers = new Map();
    this.retryInterval = 60 * 60 * 1000; // 1 heure en ms
    this.maxRetries = 3;
  }

  /**
   * Initialise le statut d'un overlay
   */
  initOverlay(overlayType) {
    if (!this.overlayStatus.has(overlayType)) {
      this.overlayStatus.set(overlayType, {
        status: 'inactive',
        lastSuccess: null,
        failureCount: 0,
        lastAttempt: null,
        fallbackActive: false
      });
    }
  }

  /**
   * Enregistre une tentative de chargement d'overlay
   */
  recordAttempt(overlayType, success, data = null) {
    this.initOverlay(overlayType);
    const status = this.overlayStatus.get(overlayType);
    
    status.lastAttempt = new Date();
    
    if (success) {
      status.status = 'active';
      status.lastSuccess = new Date();
      status.failureCount = 0;
      status.fallbackActive = false;
      
      // Sauvegarder les données comme backup
      if (data) {
        this.backupData.set(overlayType, {
          data: data,
          timestamp: new Date(),
          source: 'primary'
        });
      }
      
      // Annuler les timers de retry
      this.clearRetryTimer(overlayType);
      
      console.log(`✅ Overlay ${overlayType} loaded successfully`);
      
    } else {
      status.status = 'failed';
      status.failureCount += 1;
      
      console.warn(`❌ Overlay ${overlayType} failed (attempt ${status.failureCount})`);
      
      // Activer le fallback si disponible
      this.activateFallback(overlayType);
      
      // Programmer un retry si pas trop d'échecs
      if (status.failureCount < this.maxRetries) {
        this.scheduleRetry(overlayType);
      }
    }
    
    this.overlayStatus.set(overlayType, status);
  }

  /**
   * Active le fallback d'un overlay
   */
  activateFallback(overlayType) {
    const backup = this.backupData.get(overlayType);
    
    if (backup) {
      const age = Date.now() - backup.timestamp.getTime();
      const maxAge = 6 * 60 * 60 * 1000; // 6 heures max pour backup
      
      if (age < maxAge) {
        const status = this.overlayStatus.get(overlayType);
        status.fallbackActive = true;
        status.status = 'fallback';
        
        console.log(`🔄 Using fallback for ${overlayType} (${Math.round(age/1000/60)} minutes old)`);
        return backup;
      } else {
        console.warn(`⚠️ Backup too old for ${overlayType} (${Math.round(age/1000/60/60)} hours)`);
      }
    }
    
    return null;
  }

  /**
   * Programme un retry automatique
   */
  scheduleRetry(overlayType) {
    this.clearRetryTimer(overlayType);
    
    const timer = setTimeout(() => {
      console.log(`🔄 Retrying overlay ${overlayType}...`);
      this.triggerRetry(overlayType);
    }, this.retryInterval);
    
    this.retryTimers.set(overlayType, timer);
    
    console.log(`⏰ Retry scheduled for ${overlayType} in 1 hour`);
  }

  /**
   * Annule le timer de retry
   */
  clearRetryTimer(overlayType) {
    const timer = this.retryTimers.get(overlayType);
    if (timer) {
      clearTimeout(timer);
      this.retryTimers.delete(overlayType);
    }
  }

  /**
   * Déclenche un retry (à connecter avec le composant)
   */
  triggerRetry(overlayType) {
    // Émet un événement personnalisé pour notifier le composant
    const event = new CustomEvent('overlayRetry', {
      detail: { overlayType }
    });
    window.dispatchEvent(event);
  }

  /**
   * Obtient le statut d'un overlay
   */
  getOverlayStatus(overlayType) {
    return this.overlayStatus.get(overlayType) || null;
  }

  /**
   * Obtient les données de backup d'un overlay
   */
  getBackupData(overlayType) {
    return this.backupData.get(overlayType) || null;
  }

  /**
   * Vérifie si un overlay doit utiliser le fallback
   */
  shouldUseFallback(overlayType) {
    const status = this.overlayStatus.get(overlayType);
    return status && status.fallbackActive;
  }

  /**
   * Génère une URL de fallback pour OpenWeatherMap
   */
  generateFallbackUrl(overlayType) {
    const apiKey = process.env.REACT_APP_OPENWEATHER_API_KEY;
    
    const fallbackLayers = {
      'clouds': 'clouds_new',
      'precipitation': 'precipitation_new', 
      'radar': 'radar'
    };
    
    const layerName = fallbackLayers[overlayType];
    if (!layerName || !apiKey) return null;
    
    // URL alternative avec serveur de backup
    return `https://maps.openweathermap.org/maps/2.0/weather/${layerName}/{z}/{x}/{y}?appid=${apiKey}`;
  }

  /**
   * Nettoie les données anciennes
   */
  cleanup() {
    const maxAge = 24 * 60 * 60 * 1000; // 24 heures
    const now = Date.now();
    
    for (const [overlayType, backup] of this.backupData.entries()) {
      const age = now - backup.timestamp.getTime();
      if (age > maxAge) {
        this.backupData.delete(overlayType);
        console.log(`🧹 Cleaned old backup for ${overlayType}`);
      }
    }
  }

  /**
   * Obtient les statistiques des overlays
   */
  getStats() {
    const stats = {
      total: this.overlayStatus.size,
      active: 0,
      failed: 0,
      fallback: 0,
      withBackup: this.backupData.size
    };
    
    for (const [_, status] of this.overlayStatus.entries()) {
      switch (status.status) {
        case 'active':
          stats.active++;
          break;
        case 'failed':
          stats.failed++;
          break;
        case 'fallback':
          stats.fallback++;
          break;
      }
    }
    
    return stats;
  }
}

// Instance singleton
export const overlayBackupService = new OverlayBackupService();

// Nettoyage automatique toutes les heures
setInterval(() => {
  overlayBackupService.cleanup();
}, 60 * 60 * 1000);