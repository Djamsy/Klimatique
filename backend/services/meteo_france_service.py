import os
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import base64

logger = logging.getLogger(__name__)

class MeteoFranceService:
    def __init__(self):
        # Configuration API Météo France
        self.base_url = "https://public-api.meteofrance.fr/public"
        self.token_url = "https://portail-api.meteofrance.fr/token"
        self.client_id = os.environ.get('METEOFRANCE_CLIENT_ID')
        self.client_secret = os.environ.get('METEOFRANCE_CLIENT_SECRET')
        
        # Codes départements Antilles
        self.departements = {
            'guadeloupe': 'GUA',
            'martinique': 'MAR',
            'guyane': 'GUY',
            'reunion': 'REU',
            'mayotte': 'MAY'
        }
        
        self.vigilance_colors = {
            'vert': {'level': 1, 'color': '#00FF00', 'name': 'Vert'},
            'jaune': {'level': 2, 'color': '#FFFF00', 'name': 'Jaune'},
            'orange': {'level': 3, 'color': '#FFA500', 'name': 'Orange'},
            'rouge': {'level': 4, 'color': '#FF0000', 'name': 'Rouge'}
        }
        
        self.risk_types = {
            'VENT': 'Vent violent',
            'PLUIE': 'Pluie-inondation',
            'ORAGE': 'Orages',
            'NEIGE': 'Neige-verglas',
            'CANICULE': 'Canicule',
            'FROID': 'Grand froid',
            'AVALANCHE': 'Avalanches',
            'TSUNAMI': 'Phénomène météorologique dangereux côtier',
            'CYCLONE': 'Cyclone'
        }
    
    async def get_access_token(self) -> Optional[str]:
        """Récupère un token d'accès pour l'API Météo France"""
        try:
            if not self.client_id or not self.client_secret:
                logger.error("Météo France credentials not configured")
                return None
            
            # Encodage en base64 pour l'authentification
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = 'grant_type=client_credentials'
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    headers=headers,
                    data=data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    return token_data.get('access_token')
                else:
                    logger.error(f"Token request failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    async def get_vigilance_data(self, departement: str = 'guadeloupe') -> Dict:
        """Récupère les données de vigilance pour un département"""
        try:
            token = await self.get_access_token()
            if not token:
                return self._fallback_vigilance_data()
            
            dept_code = self.departements.get(departement.lower(), 'GUA')
            
            # URL pour les vigilances
            vigilance_url = f"{self.base_url}/DPVigilance/v1/textesvigilance/encours"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    vigilance_url,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._process_vigilance_data(data, dept_code)
                else:
                    logger.error(f"Vigilance request failed: {response.status_code}")
                    return self._fallback_vigilance_data()
                    
        except Exception as e:
            logger.error(f"Error getting vigilance data: {e}")
            return self._fallback_vigilance_data()
    
    def _process_vigilance_data(self, data: Dict, dept_code: str) -> Dict:
        """Traite les données de vigilance de l'API Météo France"""
        try:
            # Recherche des informations pour le département
            vigilance_info = {
                'departement': dept_code,
                'color_level': 'vert',
                'color_info': self.vigilance_colors['vert'],
                'risks': [],
                'global_risk_score': 10,
                'recommendations': [],
                'valid_from': datetime.now().isoformat(),
                'valid_until': (datetime.now() + timedelta(hours=24)).isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            
            # Parsing des données (structure réelle API Météo France)
            if 'product' in data and 'text_bloc_items' in data['product']:
                for item in data['product']['text_bloc_items']:
                    if item.get('domain_id') == dept_code:
                        # Couleur de vigilance
                        color_max = item.get('color_max_id', 'vert')
                        vigilance_info['color_level'] = color_max
                        vigilance_info['color_info'] = self.vigilance_colors.get(color_max, self.vigilance_colors['vert'])
                        
                        # Calcul du score de risque global
                        vigilance_info['global_risk_score'] = self._calculate_global_risk_score(color_max)
                        
                        # Extraction des risques
                        if 'text_items' in item.get('bloc_items', {}):
                            risks = self._extract_risks(item['bloc_items']['text_items'])
                            vigilance_info['risks'] = risks
                        
                        # Génération des recommandations
                        vigilance_info['recommendations'] = self._generate_vigilance_recommendations(color_max, vigilance_info['risks'])
                        
                        # Dates de validité
                        vigilance_info['valid_from'] = item.get('valid_from', vigilance_info['valid_from'])
                        vigilance_info['valid_until'] = item.get('valid_until', vigilance_info['valid_until'])
                        
                        break
            
            return vigilance_info
            
        except Exception as e:
            logger.error(f"Error processing vigilance data: {e}")
            return self._fallback_vigilance_data()
    
    def _extract_risks(self, text_items: Dict) -> List[Dict]:
        """Extrait les risques depuis les données de vigilance"""
        risks = []
        
        try:
            if 'term_items' in text_items:
                for term_item in text_items['term_items']:
                    if 'risk_name' in term_item:
                        risk_code = term_item['risk_name']
                        risk_name = self.risk_types.get(risk_code, risk_code)
                        
                        risk_info = {
                            'code': risk_code,
                            'name': risk_name,
                            'level': term_item.get('color_id', 'vert'),
                            'description': term_item.get('text', '')
                        }
                        risks.append(risk_info)
        
        except Exception as e:
            logger.error(f"Error extracting risks: {e}")
        
        return risks
    
    def _calculate_global_risk_score(self, color_level: str) -> int:
        """Calcule un score de risque global basé sur la couleur de vigilance"""
        scores = {
            'vert': 10,
            'jaune': 40,
            'orange': 70,
            'rouge': 95
        }
        return scores.get(color_level, 10)
    
    def _generate_vigilance_recommendations(self, color_level: str, risks: List[Dict]) -> List[str]:
        """Génère des recommandations basées sur le niveau de vigilance officiel"""
        recommendations = []
        
        if color_level == 'rouge':
            recommendations.extend([
                "🚨 VIGILANCE ROUGE - Phénomène météorologique dangereux",
                "Évitez tout déplacement - Restez chez vous",
                "Tenez-vous informé de l'évolution de la situation",
                "Suivez les consignes des autorités locales",
                "Préparez vos provisions d'urgence (72h minimum)"
            ])
        
        elif color_level == 'orange':
            recommendations.extend([
                "⚠️ VIGILANCE ORANGE - Phénomène météorologique dangereux",
                "Limitez vos déplacements aux trajets indispensables",
                "Évitez les activités extérieures et de loisirs",
                "Renforcez vos équipements (volets, amarrages)",
                "Tenez-vous informé de l'évolution"
            ])
        
        elif color_level == 'jaune':
            recommendations.extend([
                "⚡ VIGILANCE JAUNE - Phénomène météorologique à surveiller",
                "Soyez attentif aux conditions météorologiques",
                "Évitez les activités sensibles aux conditions météo",
                "Restez informé de l'évolution de la situation"
            ])
        
        else:  # vert
            recommendations.extend([
                "✅ Pas de vigilance particulière",
                "Conditions météorologiques normales",
                "Profitez des activités extérieures en toute sécurité"
            ])
        
        # Recommandations spécifiques par type de risque
        for risk in risks:
            if risk['code'] == 'CYCLONE':
                recommendations.extend([
                    "🌀 ALERTE CYCLONE - Mesures d'urgence requises",
                    "Évacuation possible - Préparez un kit d'urgence",
                    "Sécurisez tout objet pouvant être emporté par le vent"
                ])
            elif risk['code'] == 'VENT':
                recommendations.extend([
                    "💨 Attention aux vents forts",
                    "Évitez les zones exposées et les arbres",
                    "Sécurisez les objets légers"
                ])
            elif risk['code'] == 'PLUIE':
                recommendations.extend([
                    "🌧️ Risque d'inondation",
                    "Évitez les zones inondables",
                    "Ne traversez pas les cours d'eau en crue"
                ])
        
        return recommendations[:8]  # Limiter à 8 recommandations
    
    def _fallback_vigilance_data(self) -> Dict:
        """Données de vigilance par défaut en cas d'erreur - simulation dynamique"""
        import random
        
        # Simulation d'un cycle de vigilance pour démo
        current_hour = datetime.now().hour
        
        # Logique de simulation basée sur l'heure pour tester les différents niveaux
        if current_hour % 6 == 0:  # Toutes les 6 heures, changement de niveau
            levels = ['vert', 'jaune', 'orange', 'rouge']
            # Rotation basée sur l'heure courante
            level_index = (current_hour // 6) % len(levels)
            current_level = levels[level_index]
        else:
            current_level = 'vert'  # Par défaut
        
        # Génération des risques selon le niveau
        risks = []
        if current_level in ['orange', 'rouge']:
            risks = [
                {
                    'code': 'PLUIE',
                    'name': 'Pluie-inondation',
                    'level': current_level,
                    'description': f'Fortes pluies attendues ce weekend sur la Basse-Terre'
                }
            ]
        elif current_level == 'jaune':
            risks = [
                {
                    'code': 'VENT',
                    'name': 'Vent violent',
                    'level': current_level,
                    'description': 'Vents soutenus attendus sur la côte'
                }
            ]
        
        return {
            'departement': 'GUA',
            'color_level': current_level,
            'color_info': self.vigilance_colors[current_level],
            'risks': risks,
            'global_risk_score': self._calculate_global_risk_score(current_level),
            'recommendations': self._generate_vigilance_recommendations(current_level, risks),
            'valid_from': datetime.now().isoformat(),
            'valid_until': (datetime.now() + timedelta(hours=24)).isoformat(),
            'last_updated': datetime.now().isoformat(),
            'is_fallback': True
        }
    
    async def get_detailed_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """Récupère les prévisions détaillées pour des coordonnées"""
        try:
            token = await self.get_access_token()
            if not token:
                return None
            
            forecast_url = f"{self.base_url}/DPPrevision/v1/chaineComplete"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            params = {
                'lat': lat,
                'lon': lon,
                'formatDate': 'iso'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    forecast_url,
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Forecast request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting forecast data: {e}")
            return None

# Instance globale
meteo_france_service = MeteoFranceService()