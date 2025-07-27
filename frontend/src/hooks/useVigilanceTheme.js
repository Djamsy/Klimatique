import { useState, useEffect } from 'react';

export const useVigilanceTheme = () => {
  const [theme, setTheme] = useState({
    primary_color: '#00FF00',
    level: 'vert',
    level_name: 'Vert',
    risk_score: 10,
    header_class: 'bg-green-gradient',
    badge_class: 'badge-vert',
    alert_class: 'alert-vert',
    risks: [],
    recommendations: []
  });
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchVigilanceTheme();
    
    // Mise à jour toutes les 30 minutes
    const interval = setInterval(fetchVigilanceTheme, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchVigilanceTheme = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/vigilance/theme`);
      
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération du thème');
      }
      
      const themeData = await response.json();
      setTheme(themeData);
      
      // Appliquer le thème aux variables CSS
      applyThemeToCSS(themeData);
      
    } catch (err) {
      console.error('Error fetching vigilance theme:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const applyThemeToCSS = (themeData) => {
    const root = document.documentElement;
    
    // Définir les variables CSS selon le niveau de vigilance
    const colors = getVigilanceColors(themeData.level);
    
    root.style.setProperty('--vigilance-primary', colors.primary);
    root.style.setProperty('--vigilance-secondary', colors.secondary);
    root.style.setProperty('--vigilance-accent', colors.accent);
    root.style.setProperty('--vigilance-background', colors.background);
    root.style.setProperty('--vigilance-text', colors.text);
    root.style.setProperty('--vigilance-border', colors.border);
  };

  const getVigilanceColors = (level) => {
    switch (level) {
      case 'rouge':
        return {
          primary: '#DC2626',
          secondary: '#EF4444',
          accent: '#FCA5A5',
          background: '#FEF2F2',
          text: '#7F1D1D',
          border: '#F87171'
        };
      case 'orange':
        return {
          primary: '#EA580C',
          secondary: '#F97316',
          accent: '#FED7AA',
          background: '#FFF7ED',
          text: '#9A3412',
          border: '#FB923C'
        };
      case 'jaune':
        return {
          primary: '#D97706',
          secondary: '#F59E0B',
          accent: '#FDE68A',
          background: '#FFFBEB',
          text: '#92400E',
          border: '#FBBF24'
        };
      default: // vert
        return {
          primary: '#059669',
          secondary: '#10B981',
          accent: '#A7F3D0',
          background: '#ECFDF5',
          text: '#064E3B',
          border: '#34D399'
        };
    }
  };

  const getVigilanceGradient = (level) => {
    switch (level) {
      case 'rouge':
        return 'from-red-600 to-red-800';
      case 'orange':
        return 'from-orange-600 to-orange-800';
      case 'jaune':
        return 'from-yellow-500 to-yellow-700';
      default:
        return 'from-green-600 to-green-800';
    }
  };

  const getVigilanceBadgeClass = (level) => {
    switch (level) {
      case 'rouge':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'orange':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'jaune':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-green-100 text-green-800 border-green-200';
    }
  };

  const getVigilanceAlertClass = (level) => {
    switch (level) {
      case 'rouge':
        return 'border-red-500 bg-red-50';
      case 'orange':
        return 'border-orange-500 bg-orange-50';
      case 'jaune':
        return 'border-yellow-500 bg-yellow-50';
      default:
        return 'border-green-500 bg-green-50';
    }
  };

  return {
    theme,
    loading,
    error,
    refreshTheme: fetchVigilanceTheme,
    helpers: {
      getVigilanceColors,
      getVigilanceGradient,
      getVigilanceBadgeClass,
      getVigilanceAlertClass
    }
  };
};