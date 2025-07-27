#!/usr/bin/env python3
"""
Tests complets pour l'API IA prédictive cyclonique - Météo Sentinelle
Teste tous les endpoints IA avec différentes communes de Guadeloupe
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime
from typing import Dict, List

# Configuration
BACKEND_URL = "https://27295348-593a-48c2-aea4-043c0efd2678.preview.emergentagent.com/api"
TIMEOUT = 30.0

# Communes à tester (selon la demande)
TEST_COMMUNES = [
    "Pointe-à-Pitre",
    "Basse-Terre", 
    "Sainte-Anne",
    "Le Moule",
    "Marie-Galante"
]

class AIEndpointTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "detailed_results": {}
        }
        
    async def close(self):
        await self.client.aclose()
    
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Enregistre le résultat d'un test"""
        self.results["total_tests"] += 1
        if success:
            self.results["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["failed"] += 1
            print(f"❌ {test_name}: {details}")
            self.results["errors"].append(f"{test_name}: {details}")
        
        self.results["detailed_results"][test_name] = {
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
    
    async def test_cyclone_prediction(self, commune: str) -> bool:
        """Test endpoint GET /api/ai/cyclone/predict/{commune}"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Prédiction IA - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure réponse
            required_fields = [
                "commune", "coordinates", "damage_predictions", 
                "risk_level", "risk_score", "confidence", 
                "recommendations", "weather_context"
            ]
            
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Prédiction IA - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications damage_predictions
            damage_pred = data["damage_predictions"]
            damage_fields = ["infrastructure", "agriculture", "population_impact"]
            
            for field in damage_fields:
                if field not in damage_pred:
                    self.log_result(f"Prédiction IA - {commune}", False, 
                                  f"Champ damage manquant: {field}")
                    return False
                
                value = damage_pred[field]
                if not isinstance(value, (int, float)) or value < 0 or value > 100:
                    self.log_result(f"Prédiction IA - {commune}", False, 
                                  f"Valeur damage invalide {field}: {value}")
                    return False
            
            # Vérifications risk_level
            valid_risk_levels = ["faible", "modéré", "élevé", "critique"]
            if data["risk_level"] not in valid_risk_levels:
                self.log_result(f"Prédiction IA - {commune}", False, 
                              f"Risk level invalide: {data['risk_level']}")
                return False
            
            # Vérifications confidence
            confidence = data["confidence"]
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 100:
                self.log_result(f"Prédiction IA - {commune}", False, 
                              f"Confidence invalide: {confidence}")
                return False
            
            # Vérifications recommendations (allow empty for low risk)
            recommendations = data["recommendations"]
            if not isinstance(recommendations, list):
                self.log_result(f"Prédiction IA - {commune}", False, 
                              "Recommendations pas une liste")
                return False
            
            # Allow empty recommendations for very low risk scenarios
            risk_level = data["risk_level"]
            if len(recommendations) == 0 and risk_level not in ["faible"]:
                self.log_result(f"Prédiction IA - {commune}", False, 
                              f"Recommendations vides pour risque {risk_level}")
                return False
            
            self.log_result(f"Prédiction IA - {commune}", True, 
                          f"Risk: {data['risk_level']}, Score: {data['risk_score']}")
            return True
            
        except Exception as e:
            self.log_result(f"Prédiction IA - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_cyclone_timeline(self, commune: str) -> bool:
        """Test endpoint GET /api/ai/cyclone/timeline/{commune}"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/timeline/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Timeline IA - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["commune", "coordinates", "timeline_predictions"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Timeline IA - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications timeline_predictions
            timeline = data["timeline_predictions"]
            if not isinstance(timeline, dict) or len(timeline) == 0:
                self.log_result(f"Timeline IA - {commune}", False, 
                              "Timeline predictions vide")
                return False
            
            # Vérifier au moins une prédiction temporelle
            for time_key, prediction in timeline.items():
                if not isinstance(prediction, dict):
                    self.log_result(f"Timeline IA - {commune}", False, 
                                  f"Prédiction {time_key} invalide")
                    return False
                
                # Vérifier structure prédiction
                if "damage_predictions" not in prediction or "risk_level" not in prediction:
                    self.log_result(f"Timeline IA - {commune}", False, 
                                  f"Structure prédiction {time_key} invalide")
                    return False
                
                break  # Test juste la première
            
            self.log_result(f"Timeline IA - {commune}", True, 
                          f"Timeline avec {len(timeline)} prédictions")
            return True
            
        except Exception as e:
            self.log_result(f"Timeline IA - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_historical_damage(self, commune: str) -> bool:
        """Test endpoint GET /api/ai/cyclone/historical/{commune}"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/historical/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Historique - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["commune", "coordinates", "historical_events", "vulnerability_analysis"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Historique - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications historical_events
            events = data["historical_events"]
            if not isinstance(events, list):
                self.log_result(f"Historique - {commune}", False, 
                              "Historical events pas une liste")
                return False
            
            # Vérifier structure des événements
            for event in events:
                required_event_fields = ["year", "event_name", "damage_type", "impact_level"]
                for field in required_event_fields:
                    if field not in event:
                        self.log_result(f"Historique - {commune}", False, 
                                      f"Champ événement manquant: {field}")
                        return False
            
            # Vérifications vulnerability_analysis
            vuln = data["vulnerability_analysis"]
            if not isinstance(vuln, dict):
                self.log_result(f"Historique - {commune}", False, 
                              "Vulnerability analysis invalide")
                return False
            
            self.log_result(f"Historique - {commune}", True, 
                          f"{len(events)} événements historiques")
            return True
            
        except Exception as e:
            self.log_result(f"Historique - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_global_risk(self) -> bool:
        """Test endpoint GET /api/ai/cyclone/global-risk"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/global-risk"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Risque Global", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = [
                "global_risk_level", "affected_communes", 
                "high_risk_count", "critical_risk_count", 
                "regional_recommendations"
            ]
            
            for field in required_fields:
                if field not in data:
                    self.log_result("Risque Global", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications risk_level
            valid_risk_levels = ["faible", "modéré", "élevé", "critique"]
            if data["global_risk_level"] not in valid_risk_levels:
                self.log_result("Risque Global", False, 
                              f"Risk level global invalide: {data['global_risk_level']}")
                return False
            
            # Vérifications affected_communes
            if not isinstance(data["affected_communes"], list):
                self.log_result("Risque Global", False, 
                              "Affected communes pas une liste")
                return False
            
            # Vérifications counts
            high_count = data["high_risk_count"]
            critical_count = data["critical_risk_count"]
            
            if not isinstance(high_count, int) or high_count < 0:
                self.log_result("Risque Global", False, 
                              f"High risk count invalide: {high_count}")
                return False
            
            if not isinstance(critical_count, int) or critical_count < 0:
                self.log_result("Risque Global", False, 
                              f"Critical risk count invalide: {critical_count}")
                return False
            
            # Vérifications recommendations
            if not isinstance(data["regional_recommendations"], list):
                self.log_result("Risque Global", False, 
                              "Regional recommendations pas une liste")
                return False
            
            self.log_result("Risque Global", True, 
                          f"Risk: {data['global_risk_level']}, Communes affectées: {len(data['affected_communes'])}")
            return True
            
        except Exception as e:
            self.log_result("Risque Global", False, f"Exception: {str(e)}")
            return False
    
    async def test_model_info(self) -> bool:
        """Test endpoint GET /api/ai/model/info"""
        try:
            url = f"{BACKEND_URL}/ai/model/info"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Info Modèle IA", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["is_trained", "model_type", "features", "targets"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Info Modèle IA", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications is_trained
            if not isinstance(data["is_trained"], bool):
                self.log_result("Info Modèle IA", False, 
                              f"is_trained invalide: {data['is_trained']}")
                return False
            
            # Vérifications model_type
            if not isinstance(data["model_type"], str) or len(data["model_type"]) == 0:
                self.log_result("Info Modèle IA", False, 
                              "Model type invalide")
                return False
            
            self.log_result("Info Modèle IA", True, 
                          f"Type: {data['model_type']}, Entraîné: {data['is_trained']}")
            return True
            
        except Exception as e:
            self.log_result("Info Modèle IA", False, f"Exception: {str(e)}")
            return False
    
    async def test_model_retrain(self) -> bool:
        """Test endpoint POST /api/ai/model/retrain"""
        try:
            url = f"{BACKEND_URL}/ai/model/retrain"
            response = await self.client.post(url)
            
            if response.status_code != 200:
                self.log_result("Re-entraînement IA", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["message", "training_metrics"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Re-entraînement IA", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications message
            if not isinstance(data["message"], str) or len(data["message"]) == 0:
                self.log_result("Re-entraînement IA", False, 
                              "Message invalide")
                return False
            
            # Vérifications training_metrics
            metrics = data["training_metrics"]
            if not isinstance(metrics, dict):
                self.log_result("Re-entraînement IA", False, 
                              "Training metrics invalide")
                return False
            
            self.log_result("Re-entraînement IA", True, 
                          f"Message: {data['message']}")
            return True
            
        except Exception as e:
            self.log_result("Re-entraînement IA", False, f"Exception: {str(e)}")
            return False
    
    async def test_openweather_integration(self) -> bool:
        """Test intégration OpenWeatherMap via endpoint météo"""
        try:
            # Test avec une commune pour vérifier que l'API météo fonctionne
            url = f"{BACKEND_URL}/weather/Pointe-à-Pitre"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Intégration OpenWeatherMap", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure météo
            required_fields = ["commune", "coordinates", "current", "forecast"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Intégration OpenWeatherMap", False, 
                                  f"Champ météo manquant: {field}")
                    return False
            
            # Vérifications données actuelles
            current = data["current"]
            weather_fields = ["temperature_min", "temperature_max", "humidity", "wind_speed"]
            for field in weather_fields:
                if field not in current:
                    self.log_result("Intégration OpenWeatherMap", False, 
                                  f"Champ météo current manquant: {field}")
                    return False
            
            self.log_result("Intégration OpenWeatherMap", True, 
                          f"Données météo OK pour {data['commune']}")
            return True
            
        except Exception as e:
            self.log_result("Intégration OpenWeatherMap", False, f"Exception: {str(e)}")
            return False

    async def test_cache_stats(self) -> bool:
        """Test endpoint GET /api/cache/stats"""
        try:
            url = f"{BACKEND_URL}/cache/stats"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Cache Stats", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["cache_stats", "cache_efficiency", "status"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Cache Stats", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications cache_efficiency
            efficiency = data["cache_efficiency"]
            efficiency_fields = ["daily_limit", "today_usage", "efficiency_percent", "remaining_calls"]
            for field in efficiency_fields:
                if field not in efficiency:
                    self.log_result("Cache Stats", False, 
                                  f"Champ efficiency manquant: {field}")
                    return False
            
            # Vérifications valeurs
            if not isinstance(efficiency["daily_limit"], int) or efficiency["daily_limit"] <= 0:
                self.log_result("Cache Stats", False, 
                              f"Daily limit invalide: {efficiency['daily_limit']}")
                return False
            
            if data["status"] != "active":
                self.log_result("Cache Stats", False, 
                              f"Status cache invalide: {data['status']}")
                return False
            
            self.log_result("Cache Stats", True, 
                          f"Usage: {efficiency['today_usage']}/{efficiency['daily_limit']}, Efficiency: {efficiency['efficiency_percent']}%")
            return True
            
        except Exception as e:
            self.log_result("Cache Stats", False, f"Exception: {str(e)}")
            return False

    async def test_cached_weather(self, commune: str) -> bool:
        """Test endpoint GET /api/weather/cached/{commune}"""
        try:
            url = f"{BACKEND_URL}/weather/cached/{commune}"
            response = await self.client.get(url)
            
            # Accepter 404 si pas en cache
            if response.status_code == 404:
                self.log_result(f"Cache Météo - {commune}", True, 
                              "Pas en cache (normal)")
                return True
            
            if response.status_code != 200:
                self.log_result(f"Cache Météo - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["commune", "data", "source", "cached"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Cache Météo - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications valeurs
            if data["commune"] != commune:
                self.log_result(f"Cache Météo - {commune}", False, 
                              f"Commune incorrecte: {data['commune']}")
                return False
            
            if data["source"] != "cache":
                self.log_result(f"Cache Météo - {commune}", False, 
                              f"Source incorrecte: {data['source']}")
                return False
            
            if not data["cached"]:
                self.log_result(f"Cache Météo - {commune}", False, 
                              "Cached flag incorrect")
                return False
            
            self.log_result(f"Cache Météo - {commune}", True, 
                          f"Données en cache pour {commune}")
            return True
            
        except Exception as e:
            self.log_result(f"Cache Météo - {commune}", False, f"Exception: {str(e)}")
            return False

    async def test_clouds_overlay(self) -> bool:
        """Test endpoint GET /api/weather/overlay/clouds"""
        try:
            url = f"{BACKEND_URL}/weather/overlay/clouds"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Overlay Nuages", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["overlay_type", "data", "source"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Overlay Nuages", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications valeurs
            if data["overlay_type"] != "clouds":
                self.log_result("Overlay Nuages", False, 
                              f"Type overlay incorrect: {data['overlay_type']}")
                return False
            
            if data["source"] not in ["cache", "api"]:
                self.log_result("Overlay Nuages", False, 
                              f"Source invalide: {data['source']}")
                return False
            
            # Vérifier que data n'est pas vide
            if not data["data"]:
                self.log_result("Overlay Nuages", False, 
                              "Données overlay vides")
                return False
            
            self.log_result("Overlay Nuages", True, 
                          f"Source: {data['source']}")
            return True
            
        except Exception as e:
            self.log_result("Overlay Nuages", False, f"Exception: {str(e)}")
            return False

    async def test_precipitation_overlay(self) -> bool:
        """Test endpoint GET /api/weather/overlay/precipitation"""
        try:
            url = f"{BACKEND_URL}/weather/overlay/precipitation"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Overlay Précipitations", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["overlay_type", "data", "source"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Overlay Précipitations", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications valeurs
            if data["overlay_type"] != "precipitation":
                self.log_result("Overlay Précipitations", False, 
                              f"Type overlay incorrect: {data['overlay_type']}")
                return False
            
            if data["source"] not in ["cache", "api"]:
                self.log_result("Overlay Précipitations", False, 
                              f"Source invalide: {data['source']}")
                return False
            
            # Vérifier que data n'est pas vide
            if not data["data"]:
                self.log_result("Overlay Précipitations", False, 
                              "Données overlay vides")
                return False
            
            self.log_result("Overlay Précipitations", True, 
                          f"Source: {data['source']}")
            return True
            
        except Exception as e:
            self.log_result("Overlay Précipitations", False, f"Exception: {str(e)}")
            return False

    async def test_radar_overlay(self) -> bool:
        """Test endpoint GET /api/weather/overlay/radar"""
        try:
            url = f"{BACKEND_URL}/weather/overlay/radar"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Overlay Radar", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["overlay_type", "data", "source"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Overlay Radar", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications valeurs
            if data["overlay_type"] != "radar":
                self.log_result("Overlay Radar", False, 
                              f"Type overlay incorrect: {data['overlay_type']}")
                return False
            
            if data["source"] not in ["cache", "api"]:
                self.log_result("Overlay Radar", False, 
                              f"Source invalide: {data['source']}")
                return False
            
            # Vérifier que data n'est pas vide
            if not data["data"]:
                self.log_result("Overlay Radar", False, 
                              "Données overlay vides")
                return False
            
            self.log_result("Overlay Radar", True, 
                          f"Source: {data['source']}")
            return True
            
        except Exception as e:
            self.log_result("Overlay Radar", False, f"Exception: {str(e)}")
            return False

    async def test_precipitation_forecast(self) -> bool:
        """Test endpoint GET /api/weather/precipitation/forecast"""
        try:
            url = f"{BACKEND_URL}/weather/precipitation/forecast"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Prévisions Précipitations", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["location", "forecast", "type"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Prévisions Précipitations", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications valeurs
            if data["location"] != "Guadeloupe":
                self.log_result("Prévisions Précipitations", False, 
                              f"Location incorrecte: {data['location']}")
                return False
            
            if data["type"] != "precipitation":
                self.log_result("Prévisions Précipitations", False, 
                              f"Type incorrect: {data['type']}")
                return False
            
            # Vérifier que forecast n'est pas vide
            if not data["forecast"]:
                self.log_result("Prévisions Précipitations", False, 
                              "Prévisions vides")
                return False
            
            self.log_result("Prévisions Précipitations", True, 
                          f"Prévisions pour {data['location']}")
            return True
            
        except Exception as e:
            self.log_result("Prévisions Précipitations", False, f"Exception: {str(e)}")
            return False

    async def test_pluviometer_data(self, commune: str) -> bool:
        """Test endpoint GET /api/weather/pluviometer/{commune}"""
        try:
            url = f"{BACKEND_URL}/weather/pluviometer/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Pluviomètre - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["commune", "coordinates", "current", "forecast", "daily_total", "peak_hour", "last_updated"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Pluviomètre - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications commune
            if data["commune"] != commune:
                self.log_result(f"Pluviomètre - {commune}", False, 
                              f"Commune incorrecte: {data['commune']}")
                return False
            
            # Vérifications coordinates
            coords = data["coordinates"]
            if not isinstance(coords, list) or len(coords) != 2:
                self.log_result(f"Pluviomètre - {commune}", False, 
                              f"Coordonnées invalides: {coords}")
                return False
            
            # Vérifications current
            current = data["current"]
            current_fields = ["precipitation", "intensity", "description"]
            for field in current_fields:
                if field not in current:
                    self.log_result(f"Pluviomètre - {commune}", False, 
                                  f"Champ current manquant: {field}")
                    return False
            
            # Vérifications precipitation value
            precip = current["precipitation"]
            if not isinstance(precip, (int, float)) or precip < 0:
                self.log_result(f"Pluviomètre - {commune}", False, 
                              f"Précipitation invalide: {precip}")
                return False
            
            # Vérifications intensity
            valid_intensities = ["nulle", "faible", "modérée", "forte", "très forte"]
            if current["intensity"] not in valid_intensities:
                self.log_result(f"Pluviomètre - {commune}", False, 
                              f"Intensité invalide: {current['intensity']}")
                return False
            
            # Vérifications forecast
            forecast = data["forecast"]
            if not isinstance(forecast, list):
                self.log_result(f"Pluviomètre - {commune}", False, 
                              "Forecast pas une liste")
                return False
            
            # Vérifications daily_total
            daily_total = data["daily_total"]
            if not isinstance(daily_total, (int, float)) or daily_total < 0:
                self.log_result(f"Pluviomètre - {commune}", False, 
                              f"Daily total invalide: {daily_total}")
                return False
            
            self.log_result(f"Pluviomètre - {commune}", True, 
                          f"Précip: {precip}mm, Intensité: {current['intensity']}, Total jour: {daily_total}mm")
            return True
            
        except Exception as e:
            self.log_result(f"Pluviomètre - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Exécute tous les tests IA et nouveaux endpoints météo"""
        print("🚀 Démarrage des tests complets - Météo Sentinelle")
        print(f"🌐 Backend URL: {BACKEND_URL}")
        print(f"🏝️ Communes à tester: {', '.join(TEST_COMMUNES)}")
        print("=" * 80)
        
        # Test intégration OpenWeatherMap
        await self.test_openweather_integration()
        
        # Tests nouveaux endpoints météo (demande spécifique)
        print("\n🌦️ Tests nouveaux endpoints météo...")
        await self.test_cache_stats()
        await self.test_clouds_overlay()
        await self.test_precipitation_overlay()
        await self.test_radar_overlay()
        await self.test_precipitation_forecast()
        
        # Tests cache météo par commune
        print(f"\n💾 Tests cache météo par commune...")
        for commune in ["Pointe-à-Pitre", "Basse-Terre", "Sainte-Anne"]:
            await self.test_cached_weather(commune)
        
        # Tests pluviomètre par commune
        print(f"\n🌧️ Tests pluviomètre par commune...")
        for commune in ["Pointe-à-Pitre", "Basse-Terre", "Sainte-Anne"]:
            await self.test_pluviometer_data(commune)
        
        # Test info modèle IA
        print("\n🤖 Tests IA prédictive...")
        await self.test_model_info()
        
        # Test re-entraînement modèle (peut être long)
        print("\n⚠️ Test re-entraînement (peut prendre du temps)...")
        await self.test_model_retrain()
        
        # Test risque global
        await self.test_global_risk()
        
        # Tests par commune
        print(f"\n🏘️ Tests IA par commune ({len(TEST_COMMUNES)} communes)...")
        for commune in TEST_COMMUNES:
            print(f"\n--- Tests IA pour {commune} ---")
            
            # Test prédiction IA
            await self.test_cyclone_prediction(commune)
            
            # Test timeline
            await self.test_cyclone_timeline(commune)
            
            # Test historique
            await self.test_historical_damage(commune)
        
        # Résumé final
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ DES TESTS COMPLETS")
        print("=" * 80)
        print(f"✅ Tests réussis: {self.results['passed']}")
        print(f"❌ Tests échoués: {self.results['failed']}")
        print(f"📈 Total tests: {self.results['total_tests']}")
        print(f"🎯 Taux de réussite: {(self.results['passed']/self.results['total_tests']*100):.1f}%")
        
        if self.results["errors"]:
            print(f"\n❌ ERREURS DÉTECTÉES ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        # Sauvegarde résultats
        with open("/app/weather_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Résultats sauvegardés dans: /app/weather_test_results.json")
        
        return self.results["failed"] == 0

async def main():
    """Fonction principale"""
    tester = AIEndpointTester()
    
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
    finally:
        await tester.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)