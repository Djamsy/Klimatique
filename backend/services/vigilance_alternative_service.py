import os
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
import asyncio
from bs4 import BeautifulSoup
import re
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class VigilanceAlternativeService:
    def __init__(self):
        self.openweather_api_key = os.environ.get('OPENWEATHER_API_KEY')
        
        # URLs publiques Météo France (pas d'API key requise)
        self.meteofrance_public_urls = {
            'vigilance': 'https://vigilance.meteofrance.fr/fr/vigilance-meteo',
            'vigilance_data': 'https://vigilance.meteofrance.fr/vigilance_ws/get_vigilance_data',
            'antilles': 'https://vigilance.meteofrance.fr/fr/antilles-guyane'
        }
        
        # OpenWeatherMap alerts endpoint
        self.openweather_alerts_url = "https://api.openweathermap.org/data/3.0/onecall"
        
        # Guadeloupe coordinates
        self.guadeloupe_coords = {
            'lat': 16.2650,
            'lon': -61.5510
        }
        
        self.vigilance_colors = {
            'vert': {'level': 1, 'color': '#00FF00', 'name': 'Vert'},
            'jaune': {'level': 2, 'color': '#FFFF00', 'name': 'Jaune'},
            'orange': {'level': 3, 'color': '#FFA500', 'name': 'Orange'},
            'rouge': {'level': 4, 'color': '#FF0000', 'name': 'Rouge'}
        }
        
        self.risk_types = {
            'RAIN': 'Pluie-inondation',
            'WIND': 'Vent violent',
            'THUNDERSTORM': 'Orages',
            'HURRICANE': 'Cyclone',
            'HEAT': 'Canicule',
            'COASTAL': 'Phénomène côtier'
        }

    async def get_openweather_alerts(self) -> Dict:
        """Récupère les alertes météo depuis OpenWeatherMap"""
        try:
            if not self.openweather_api_key:
                logger.warning("OpenWeatherMap API key not configured")
                return None
                
            params = {
                'lat': self.guadeloupe_coords['lat'],
                'lon': self.guadeloupe_coords['lon'],
                'appid': self.openweather_api_key,
                'units': 'metric',
                'lang': 'fr'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.openweather_alerts_url,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._process_openweather_alerts(data)
                else:
                    logger.error(f"OpenWeatherMap alerts request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching OpenWeatherMap alerts: {e}")
            return None

    def _process_openweather_alerts(self, data: Dict) -> Dict:
        """Traite les alertes OpenWeatherMap en format vigilance"""
        try:
            alerts = data.get('alerts', [])
            current_weather = data.get('current', {})
            
            # Analyse des conditions météo actuelles
            weather_main = current_weather.get('weather', [{}])[0].get('main', '')
            wind_speed = current_weather.get('wind_speed', 0) * 3.6  # m/s to km/h
            rain_1h = current_weather.get('rain', {}).get('1h', 0)
            
            # Détermination du niveau de vigilance basé sur les conditions
            vigilance_level = self._determine_vigilance_level(weather_main, wind_speed, rain_1h, alerts)
            
            risks = []
            recommendations = []
            
            # Traitement des alertes OpenWeatherMap
            for alert in alerts:
                event = alert.get('event', '')
                description = alert.get('description', '')
                
                risk_type = self._map_openweather_event_to_risk(event)
                if risk_type:
                    risks.append({
                        'code': risk_type,
                        'name': self.risk_types.get(risk_type, event),
                        'level': vigilance_level,
                        'description': description
                    })
            
            # Si pas d'alertes spécifiques, analyser les conditions actuelles
            if not risks:
                if rain_1h > 5:
                    risks.append({
                        'code': 'RAIN',
                        'name': 'Pluie-inondation',
                        'level': 'jaune' if rain_1h < 10 else 'orange',
                        'description': f"Précipitations intenses détectées: {rain_1h:.1f}mm/h"
                    })
                
                if wind_speed > 50:
                    risks.append({
                        'code': 'WIND',
                        'name': 'Vent violent',
                        'level': 'jaune' if wind_speed < 80 else 'orange',
                        'description': f"Vents forts détectés: {wind_speed:.1f} km/h"
                    })
            
            # Génération des recommandations
            recommendations = self._generate_recommendations(vigilance_level, risks)
            
            return {
                'departement': 'GUA',
                'color_level': vigilance_level,
                'color_info': self.vigilance_colors[vigilance_level],
                'risks': risks,
                'global_risk_score': self._calculate_risk_score(vigilance_level, risks),
                'recommendations': recommendations,
                'valid_from': datetime.now().isoformat(),
                'valid_until': (datetime.now() + timedelta(hours=24)).isoformat(),
                'last_updated': datetime.now().isoformat(),
                'source': 'OpenWeatherMap',
                'is_fallback': False
            }
            
        except Exception as e:
            logger.error(f"Error processing OpenWeatherMap alerts: {e}")
            return None

    def _determine_vigilance_level(self, weather_main: str, wind_speed: float, rain_1h: float, alerts: List) -> str:
        """Détermine le niveau de vigilance basé sur les conditions"""
        # Alertes critiques
        if any('hurricane' in alert.get('event', '').lower() or 
               'cyclone' in alert.get('event', '').lower() 
               for alert in alerts):
            return 'rouge'
        
        # Conditions dangereuses
        if (wind_speed > 80 or rain_1h > 20 or 
            any('severe' in alert.get('event', '').lower() for alert in alerts)):
            return 'orange'
        
        # Conditions modérées
        if (wind_speed > 50 or rain_1h > 5 or 
            'thunderstorm' in weather_main.lower() or
            any('warning' in alert.get('event', '').lower() for alert in alerts)):
            return 'jaune'
        
        return 'vert'

    def _map_openweather_event_to_risk(self, event: str) -> Optional[str]:
        """Mappe les événements OpenWeatherMap aux codes de risque"""
        event_lower = event.lower()
        
        if any(term in event_lower for term in ['rain', 'flood', 'precipitation']):
            return 'RAIN'
        elif any(term in event_lower for term in ['wind', 'gust', 'gale']):
            return 'WIND'
        elif any(term in event_lower for term in ['thunder', 'storm', 'lightning']):
            return 'THUNDERSTORM'
        elif any(term in event_lower for term in ['hurricane', 'cyclone', 'typhoon']):
            return 'HURRICANE'
        elif any(term in event_lower for term in ['heat', 'hot', 'temperature']):
            return 'HEAT'
        elif any(term in event_lower for term in ['coastal', 'tide', 'wave']):
            return 'COASTAL'
        
        return None

    def _generate_recommendations(self, vigilance_level: str, risks: List) -> List[str]:
        """Génère des recommandations selon le niveau de vigilance"""
        recommendations = []
        
        if vigilance_level == 'rouge':
            recommendations.extend([
                "🚨 VIGILANCE ROUGE - Phénomène météorologique exceptionnel",
                "Restez absolument chez vous",
                "Évitez tout déplacement",
                "Suivez les consignes des autorités locales"
            ])
        elif vigilance_level == 'orange':
            recommendations.extend([
                "⚠️ VIGILANCE ORANGE - Phénomène météorologique dangereux",
                "Limitez vos déplacements aux trajets indispensables",
                "Évitez les activités extérieures et de loisirs",
                "Renforcez vos équipements (volets, amarrages)",
                "Tenez-vous informé de l'évolution"
            ])
        elif vigilance_level == 'jaune':
            recommendations.extend([
                "⚡ VIGILANCE JAUNE - Conditions météorologiques à surveiller",
                "Soyez prudent lors de vos déplacements",
                "Évitez les activités extérieures sensibles",
                "Restez informé de l'évolution météorologique"
            ])
        else:
            recommendations.extend([
                "✅ Conditions météorologiques normales",
                "Aucune vigilance particulière requise",
                "Profitez des conditions favorables"
            ])
        
        # Recommandations spécifiques par type de risque
        for risk in risks:
            if risk['code'] == 'RAIN':
                recommendations.extend([
                    "🌧️ Risque d'inondation",
                    "Évitez les zones inondables",
                    "Ne traversez pas les cours d'eau en crue"
                ])
            elif risk['code'] == 'WIND':
                recommendations.extend([
                    "💨 Risque de vent violent",
                    "Évitez les zones exposées",
                    "Sécurisez les objets mobiles"
                ])
            elif risk['code'] == 'THUNDERSTORM':
                recommendations.extend([
                    "⚡ Risque d'orages",
                    "Évitez les espaces ouverts",
                    "Débranchez les appareils électriques"
                ])
        
        return recommendations

    def _calculate_risk_score(self, vigilance_level: str, risks: List) -> int:
        """Calcule un score de risque global"""
        base_scores = {
            'vert': 10,
            'jaune': 40,
            'orange': 70,
            'rouge': 95
        }
        
        base_score = base_scores.get(vigilance_level, 10)
        
        # Ajustement selon le nombre et type de risques
        risk_bonus = len(risks) * 5
        
        for risk in risks:
            if risk['code'] == 'HURRICANE':
                risk_bonus += 20
            elif risk['code'] in ['WIND', 'RAIN']:
                risk_bonus += 10
            else:
                risk_bonus += 5
        
        return min(100, base_score + risk_bonus)

    async def get_enhanced_vigilance_data(self, departement: str = 'guadeloupe') -> Dict:
        """Récupère les données de vigilance avec sources alternatives"""
        try:
            # Essayer d'abord OpenWeatherMap
            openweather_data = await self.get_openweather_alerts()
            if openweather_data:
                logger.info("Using OpenWeatherMap alerts data")
                return openweather_data
            
            # Fallback vers données simulées mais intelligentes
            logger.info("Using enhanced fallback vigilance data")
            return self._generate_enhanced_fallback_data()
            
        except Exception as e:
            logger.error(f"Error in get_enhanced_vigilance_data: {e}")
            return self._generate_enhanced_fallback_data()

    def _generate_enhanced_fallback_data(self) -> Dict:
        """Génère des données de fallback plus réalistes et dynamiques"""
        import random
        from datetime import datetime, timedelta
        
        # Probabilités saisonnières pour la Guadeloupe
        current_month = datetime.now().month
        
        # Saison cyclonique (juin-novembre)
        if 6 <= current_month <= 11:
            vigilance_probs = {'vert': 0.4, 'jaune': 0.3, 'orange': 0.2, 'rouge': 0.1}
        else:
            vigilance_probs = {'vert': 0.7, 'jaune': 0.2, 'orange': 0.1, 'rouge': 0.0}
        
        # Sélection aléatoire pondérée du niveau de vigilance
        vigilance_level = random.choices(
            list(vigilance_probs.keys()), 
            weights=list(vigilance_probs.values())
        )[0]
        
        # Génération des risques selon le niveau
        risks = []
        if vigilance_level != 'vert':
            risk_scenarios = {
                'jaune': [
                    {'code': 'RAIN', 'name': 'Pluie-inondation', 'desc': 'Averses modérées attendues'},
                    {'code': 'WIND', 'name': 'Vent violent', 'desc': 'Rafales jusqu\'à 60 km/h'},
                    {'code': 'THUNDERSTORM', 'name': 'Orages', 'desc': 'Orages isolés possibles'}
                ],
                'orange': [
                    {'code': 'RAIN', 'name': 'Pluie-inondation', 'desc': 'Fortes pluies attendues ce weekend sur la Basse-Terre'},
                    {'code': 'WIND', 'name': 'Vent violent', 'desc': 'Rafales jusqu\'à 100 km/h'},
                    {'code': 'THUNDERSTORM', 'name': 'Orages', 'desc': 'Orages violents avec grêle possible'}
                ],
                'rouge': [
                    {'code': 'HURRICANE', 'name': 'Cyclone', 'desc': 'Cyclone tropical approchant'},
                    {'code': 'WIND', 'name': 'Vent violent', 'desc': 'Vents cycloniques > 120 km/h'},
                    {'code': 'RAIN', 'name': 'Pluie-inondation', 'desc': 'Pluies diluviennes et inondations majeures'}
                ]
            }
            
            scenario_risks = risk_scenarios.get(vigilance_level, [])
            selected_risks = random.sample(scenario_risks, min(2, len(scenario_risks)))
            
            for risk_data in selected_risks:
                risks.append({
                    'code': risk_data['code'],
                    'name': risk_data['name'],
                    'level': vigilance_level,
                    'description': risk_data['desc']
                })
        
        recommendations = self._generate_recommendations(vigilance_level, risks)
        
        return {
            'departement': 'GUA',
            'color_level': vigilance_level,
            'color_info': self.vigilance_colors[vigilance_level],
            'risks': risks,
            'global_risk_score': self._calculate_risk_score(vigilance_level, risks),
            'recommendations': recommendations,
            'valid_from': datetime.now().isoformat(),
            'valid_until': (datetime.now() + timedelta(hours=24)).isoformat(),
            'last_updated': datetime.now().isoformat(),
            'source': 'Enhanced Fallback',
            'is_fallback': True
        }

# Instance globale
vigilance_alternative_service = VigilanceAlternativeService()