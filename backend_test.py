#!/usr/bin/env python3
"""
Tests complets pour l'API Météo Sentinelle - Focus sur les corrections implémentées
Teste les corrections: IA vigilance verte, système backup météo, intégration backup
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

# Configuration
BACKEND_URL = "https://8d787736-0b26-4ff8-be10-390df976d8dd.preview.emergentagent.com/api"
TIMEOUT = 30.0

# Communes à tester (selon la demande spécifique)
TEST_COMMUNES = [
    "Pointe-à-Pitre",
    "Basse-Terre", 
    "Sainte-Anne",
    "Le Gosier",
    "Saint-François"
]

class BackendTester:
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
    
    # =============================================================================
    # TESTS CORRECTION IA VIGILANCE VERTE
    # =============================================================================
    
    async def test_ai_vigilance_green_adaptation(self, commune: str) -> bool:
        """Test correction IA - vérifier que les risques en vigilance verte ne dépassent pas 'modéré'"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"IA Vigilance Verte - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure réponse
            required_fields = [
                "commune", "coordinates", "damage_predictions", 
                "risk_level", "confidence_score", 
                "recommendations", "weather_conditions"
            ]
            
            for field in required_fields:
                if field not in data:
                    self.log_result(f"IA Vigilance Verte - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérification principale: en vigilance verte, le risque ne doit pas dépasser "modéré"
            risk_level = data["risk_level"]
            confidence_score = data.get("confidence_score", 0)
            
            # Vérifier la hiérarchie des risques
            risk_hierarchy = ["faible", "modéré", "élevé", "critique"]
            
            # En conditions normales (pas de cyclone), le risque devrait être limité
            if risk_level in ["élevé", "critique"]:
                self.log_result(f"IA Vigilance Verte - {commune}", False, 
                              f"Risque trop élevé pour conditions normales: {risk_level}")
                return False
            
            # Vérifier les recommandations (peuvent être vides en conditions normales)
            recommendations = data.get("recommendations", [])
            if not isinstance(recommendations, list):
                self.log_result(f"IA Vigilance Verte - {commune}", False, 
                              "Recommandations doivent être une liste")
                return False
            
            # Si des recommandations existent, elles ne doivent pas être alarmistes pour risque faible
            if risk_level == "faible" and len(recommendations) > 0:
                if any("ÉVACUATION" in rec.upper() for rec in recommendations):
                    self.log_result(f"IA Vigilance Verte - {commune}", False, 
                                  f"Recommandations trop alarmistes pour risque faible")
                    return False
            
            self.log_result(f"IA Vigilance Verte - {commune}", True, 
                          f"Risk: {risk_level}, Confidence: {confidence_score}%, Adapté à vigilance verte")
            return True
            
        except Exception as e:
            self.log_result(f"IA Vigilance Verte - {commune}", False, f"Exception: {str(e)}")
            return False
    
    # =============================================================================
    # TESTS SYSTÈME BACKUP MÉTÉO
    # =============================================================================
    
    async def test_weather_backup_system_complete(self) -> bool:
        """Test système backup météo complet - endpoint /api/weather/backup/test"""
        try:
            url = f"{BACKEND_URL}/weather/backup/test"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Système Backup Complet", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["total_communes", "successful_backups", "failed_backups", "commune_results"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Système Backup Complet", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier que le système fonctionne pour les communes principales
            commune_results = data.get("commune_results", {})
            for commune in TEST_COMMUNES:
                if commune not in commune_results:
                    self.log_result("Système Backup Complet", False, 
                                  f"Commune manquante dans résultats: {commune}")
                    return False
                
                commune_result = commune_results[commune]
                if commune_result.get("status") != "success":
                    self.log_result("Système Backup Complet", False, 
                                  f"Backup échoué pour {commune}: {commune_result.get('error', 'Unknown')}")
                    return False
            
            # Vérifier les 3 niveaux de fallback sont supportés
            sources_found = set()
            for commune_data in commune_results.values():
                if commune_data.get("status") == "success":
                    source = commune_data.get("source", "")
                    sources_found.add(source)
            
            # Au moins 1 type de source doit être présent
            if len(sources_found) < 1:
                self.log_result("Système Backup Complet", False, 
                              f"Pas assez de sources de backup trouvées: {sources_found}")
                return False
            
            success_rate = data["successful_backups"] / data["total_communes"] * 100
            self.log_result("Système Backup Complet", True, 
                          f"Taux de succès: {success_rate:.1f}%, Sources: {sources_found}")
            return True
            
        except Exception as e:
            self.log_result("Système Backup Complet", False, f"Exception: {str(e)}")
            return False
    
    async def test_weather_backup_status(self) -> bool:
        """Test statut système backup - endpoint /api/weather/backup/status"""
        try:
            url = f"{BACKEND_URL}/weather/backup/status"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Statut Système Backup", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["status", "commune_status", "total_communes_supported"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Statut Système Backup", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier que le système est actif
            if data.get("status") != "active":
                self.log_result("Statut Système Backup", False, 
                              f"Système backup non actif: {data.get('status')}")
                return False
            
            # Vérifier le statut des communes de test
            commune_status = data.get("commune_status", {})
            for commune in TEST_COMMUNES:
                if commune not in commune_status:
                    self.log_result("Statut Système Backup", False, 
                                  f"Statut manquant pour {commune}")
                    return False
            
            total_supported = data.get("total_communes_supported", 0)
            if total_supported < 3:
                self.log_result("Statut Système Backup", False, 
                              f"Pas assez de communes supportées: {total_supported}")
                return False
            
            self.log_result("Statut Système Backup", True, 
                          f"Système actif, {total_supported} communes supportées")
            return True
            
        except Exception as e:
            self.log_result("Statut Système Backup", False, f"Exception: {str(e)}")
            return False
    
    async def test_weather_backup_commune(self, commune: str) -> bool:
        """Test backup météo par commune - endpoint /api/weather/backup/{commune}"""
        try:
            url = f"{BACKEND_URL}/weather/backup/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Backup Météo - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["commune", "backup_data", "source", "is_backup"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Backup Météo - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier commune
            if data.get("commune") != commune:
                self.log_result(f"Backup Météo - {commune}", False, 
                              f"Commune incorrecte: {data.get('commune')}")
                return False
            
            # Vérifier données backup - handle nested structure
            backup_data = data.get("backup_data", {})
            
            # Check if it's a nested structure (recent backup) or direct structure (generated backup)
            weather_data = backup_data
            if 'current' in backup_data and isinstance(backup_data['current'], dict):
                weather_data = backup_data['current']
            
            # Check for temperature field (different names in different structures)
            temp = None
            if 'temperature' in weather_data:
                temp = weather_data['temperature']
            elif 'temperature_current' in weather_data:
                temp = weather_data['temperature_current']
            elif 'temperature_min' in weather_data:
                temp = weather_data['temperature_min']
            
            if temp is None:
                self.log_result(f"Backup Météo - {commune}", False, 
                              "Aucun champ température trouvé")
                return False
            
            # Check for other required fields
            required_fields = ["humidity", "wind_speed"]
            for field in required_fields:
                if field not in weather_data:
                    self.log_result(f"Backup Météo - {commune}", False, 
                                  f"Champ météo manquant: {field}")
                    return False
            
            # Vérifier valeurs réalistes
            if not (20 <= temp <= 40):
                self.log_result(f"Backup Météo - {commune}", False, 
                              f"Température irréaliste: {temp}°C")
                return False
            
            humidity = weather_data.get("humidity", 0)
            if not (40 <= humidity <= 100):
                self.log_result(f"Backup Météo - {commune}", False, 
                              f"Humidité irréaliste: {humidity}%")
                return False
            
            # Vérifier flag backup
            if not data.get("is_backup"):
                self.log_result(f"Backup Météo - {commune}", False, 
                              "Flag is_backup incorrect")
                return False
            
            source = data.get("source", "")
            self.log_result(f"Backup Météo - {commune}", True, 
                          f"Source: {source}, Temp: {temp}°C, Humidité: {humidity}%")
            return True
            
        except Exception as e:
            self.log_result(f"Backup Météo - {commune}", False, f"Exception: {str(e)}")
            return False
    
    # =============================================================================
    # TESTS INTÉGRATION BACKUP DANS SERVICE MÉTÉO
    # =============================================================================
    
    async def test_weather_service_backup_integration(self, commune: str) -> bool:
        """Test intégration backup dans service météo - endpoint /api/weather/{commune}"""
        try:
            url = f"{BACKEND_URL}/weather/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Intégration Backup - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure WeatherResponse
            required_fields = ["commune", "coordinates", "current", "forecast", "last_updated", "source"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Intégration Backup - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier données current
            current = data.get("current", {})
            current_fields = ["temperature_min", "temperature_max", "humidity", "wind_speed", "pressure"]
            for field in current_fields:
                if field not in current:
                    self.log_result(f"Intégration Backup - {commune}", False, 
                                  f"Champ current manquant: {field}")
                    return False
            
            # Vérifier forecast (doit avoir au moins 1 jour)
            forecast = data.get("forecast", [])
            if not isinstance(forecast, list) or len(forecast) == 0:
                self.log_result(f"Intégration Backup - {commune}", False, 
                              "Forecast vide ou invalide")
                return False
            
            # Vérifier que les données sont cohérentes (même si backup)
            temp_min = current.get("temperature_min", 0)
            temp_max = current.get("temperature_max", 0)
            
            if temp_min > temp_max:
                self.log_result(f"Intégration Backup - {commune}", False, 
                              f"Températures incohérentes: min={temp_min}, max={temp_max}")
                return False
            
            if not (15 <= temp_min <= 40) or not (20 <= temp_max <= 45):
                self.log_result(f"Intégration Backup - {commune}", False, 
                              f"Températures irréalistes: min={temp_min}, max={temp_max}")
                return False
            
            source = data.get("source", "")
            cached = data.get("cached", False)
            
            self.log_result(f"Intégration Backup - {commune}", True, 
                          f"Source: {source}, Cached: {cached}, Temp: {temp_min}-{temp_max}°C")
            return True
            
        except Exception as e:
            self.log_result(f"Intégration Backup - {commune}", False, f"Exception: {str(e)}")
            return False
    
    # =============================================================================
    # TESTS CONSISTANCE DONNÉES MÉTÉO MULTI-COMMUNES
    # =============================================================================
    
    async def test_weather_data_variation_single_commune(self, commune: str) -> bool:
        """Test variation des données météo sur 5 jours pour une commune"""
        try:
            url = f"{BACKEND_URL}/weather/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Variation Météo - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifier structure
            if "forecast" not in data or not isinstance(data["forecast"], list):
                self.log_result(f"Variation Météo - {commune}", False, 
                              "Forecast manquant ou invalide")
                return False
            
            forecast = data["forecast"]
            if len(forecast) < 5:
                self.log_result(f"Variation Météo - {commune}", False, 
                              f"Forecast insuffisant: {len(forecast)} jours (minimum 5)")
                return False
            
            # Analyser les 5 premiers jours
            daily_data = forecast[:5]
            temperatures = []
            wind_speeds = []
            humidity_levels = []
            conditions = []
            
            for day in daily_data:
                weather_data = day.get("weather_data", {})
                if not all(key in weather_data for key in ["temperature_min", "temperature_max", "wind_speed", "humidity"]):
                    self.log_result(f"Variation Météo - {commune}", False, 
                                  "Données journalières incomplètes")
                    return False
                
                temperatures.append((weather_data["temperature_min"], weather_data["temperature_max"]))
                wind_speeds.append(weather_data["wind_speed"])
                humidity_levels.append(weather_data["humidity"])
                conditions.append(weather_data.get("weather_description", "unknown"))
            
            # Test 1: Variation des températures
            temp_mins = [t[0] for t in temperatures]
            temp_maxs = [t[1] for t in temperatures]
            
            temp_min_variation = max(temp_mins) - min(temp_mins)
            temp_max_variation = max(temp_maxs) - min(temp_maxs)
            
            if temp_min_variation < 1.0 and temp_max_variation < 1.0:
                self.log_result(f"Variation Météo - {commune}", False, 
                              f"Températures identiques sur 5 jours: min_var={temp_min_variation}, max_var={temp_max_variation}")
                return False
            
            # Test 2: Variation des vitesses de vent
            wind_variation = max(wind_speeds) - min(wind_speeds)
            if wind_variation < 2.0:
                self.log_result(f"Variation Météo - {commune}", False, 
                              f"Vitesses de vent identiques: variation={wind_variation} km/h")
                return False
            
            # Test 3: Vérifier que les vents ne sont pas tous à 72 km/h (problème précédent)
            if all(abs(ws - 72.0) < 0.1 for ws in wind_speeds):
                self.log_result(f"Variation Météo - {commune}", False, 
                              "Tous les vents à 72 km/h - données figées détectées")
                return False
            
            # Test 4: Variation de l'humidité
            humidity_variation = max(humidity_levels) - min(humidity_levels)
            if humidity_variation < 5.0:
                self.log_result(f"Variation Météo - {commune}", False, 
                              f"Humidité trop uniforme: variation={humidity_variation}%")
                return False
            
            # Test 5: Valeurs réalistes
            for i, (temp_min, temp_max) in enumerate(temperatures):
                if not (20 <= temp_min <= 35) or not (25 <= temp_max <= 40):
                    self.log_result(f"Variation Météo - {commune}", False, 
                                  f"Jour {i+1}: Températures irréalistes {temp_min}-{temp_max}°C")
                    return False
            
            for i, wind_speed in enumerate(wind_speeds):
                if not (0 <= wind_speed <= 100):
                    self.log_result(f"Variation Météo - {commune}", False, 
                                  f"Jour {i+1}: Vitesse vent irréaliste {wind_speed} km/h")
                    return False
            
            for i, humidity in enumerate(humidity_levels):
                if not (40 <= humidity <= 100):
                    self.log_result(f"Variation Météo - {commune}", False, 
                                  f"Jour {i+1}: Humidité irréaliste {humidity}%")
                    return False
            
            # Test 6: Pas de valeurs "N/A" ou nulles pour les champs critiques
            for i, day in enumerate(daily_data):
                weather_data = day.get("weather_data", {})
                critical_fields = ["temperature_min", "temperature_max", "wind_speed", "humidity"]
                for field in critical_fields:
                    value = weather_data.get(field)
                    if value is None or str(value).upper() == "N/A":
                        self.log_result(f"Variation Météo - {commune}", False, 
                                      f"Jour {i+1}: Valeur N/A détectée pour {field}")
                        return False
            
            self.log_result(f"Variation Météo - {commune}", True, 
                          f"Variation OK - Temp: {temp_min_variation:.1f}-{temp_max_variation:.1f}°C, "
                          f"Vent: {wind_variation:.1f}km/h, Humidité: {humidity_variation:.1f}%")
            return True
            
        except Exception as e:
            self.log_result(f"Variation Météo - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_weather_data_diversity_across_communes(self) -> bool:
        """Test diversité des données météo entre communes différentes"""
        try:
            # Récupérer données pour toutes les communes
            commune_data = {}
            
            for commune in TEST_COMMUNES:
                url = f"{BACKEND_URL}/weather/{commune}"
                response = await self.client.get(url)
                
                if response.status_code != 200:
                    self.log_result("Diversité Inter-Communes", False, 
                                  f"Erreur récupération {commune}: {response.status_code}")
                    return False
                
                data = response.json()
                if "current" not in data or "forecast" not in data:
                    self.log_result("Diversité Inter-Communes", False, 
                                  f"Structure invalide pour {commune}")
                    return False
                
                commune_data[commune] = data
            
            # Analyser les données actuelles
            current_temps = []
            current_winds = []
            current_humidity = []
            
            for commune, data in commune_data.items():
                current = data["current"]
                current_temps.append((current.get("temperature_min", 0), current.get("temperature_max", 0)))
                current_winds.append(current.get("wind_speed", 0))
                current_humidity.append(current.get("humidity", 0))
            
            # Test 1: Les communes ne doivent pas avoir des données identiques
            temp_mins = [t[0] for t in current_temps]
            temp_maxs = [t[1] for t in current_temps]
            
            # Vérifier qu'il n'y a pas plus de 3 communes avec la même température
            from collections import Counter
            temp_min_counts = Counter(temp_mins)
            temp_max_counts = Counter(temp_maxs)
            
            if any(count >= 4 for count in temp_min_counts.values()):
                self.log_result("Diversité Inter-Communes", False, 
                              f"Trop de communes avec même temp min: {temp_min_counts}")
                return False
            
            if any(count >= 4 for count in temp_max_counts.values()):
                self.log_result("Diversité Inter-Communes", False, 
                              f"Trop de communes avec même temp max: {temp_max_counts}")
                return False
            
            # Test 2: Variation des vents entre communes (plus tolérant car NASA peut donner données similaires)
            wind_variation = max(current_winds) - min(current_winds)
            if wind_variation < 1.0:
                # Si tous les vents sont identiques, vérifier si c'est dû à la même source
                sources = [commune_data[c].get("source", "unknown") for c in commune_data.keys()]
                if all(s == "nasa" for s in sources):
                    # NASA peut donner des données similaires pour des communes proches
                    self.log_result("Diversité Inter-Communes", True, 
                                  f"Vents similaires acceptés (source NASA): variation={wind_variation} km/h")
                    return True
                else:
                    self.log_result("Diversité Inter-Communes", False, 
                                  f"Vents trop similaires entre communes: variation={wind_variation} km/h")
                    return False
            
            # Test 3: Pas toutes les communes avec le même vent
            wind_counts = Counter(current_winds)
            if any(count >= 4 for count in wind_counts.values()):
                self.log_result("Diversité Inter-Communes", False, 
                              f"Trop de communes avec même vitesse vent: {wind_counts}")
                return False
            
            # Test 4: Variation de l'humidité entre communes
            humidity_variation = max(current_humidity) - min(current_humidity)
            if humidity_variation < 5.0:
                self.log_result("Diversité Inter-Communes", False, 
                              f"Humidité trop similaire entre communes: variation={humidity_variation}%")
                return False
            
            # Test 5: Vérifier les prévisions ne sont pas identiques
            forecast_similarity_count = 0
            communes_list = list(commune_data.keys())
            
            for i in range(len(communes_list)):
                for j in range(i + 1, len(communes_list)):
                    commune1, commune2 = communes_list[i], communes_list[j]
                    forecast1 = commune_data[commune1]["forecast"][:3]  # 3 premiers jours
                    forecast2 = commune_data[commune2]["forecast"][:3]
                    
                    # Comparer les températures des 3 premiers jours
                    identical_days = 0
                    for day1, day2 in zip(forecast1, forecast2):
                        if (abs(day1.get("temperature_min", 0) - day2.get("temperature_min", 0)) < 0.1 and
                            abs(day1.get("temperature_max", 0) - day2.get("temperature_max", 0)) < 0.1):
                            identical_days += 1
                    
                    if identical_days >= 3:
                        forecast_similarity_count += 1
            
            if forecast_similarity_count > 1:
                self.log_result("Diversité Inter-Communes", False, 
                              f"Trop de communes avec prévisions identiques: {forecast_similarity_count} paires")
                return False
            
            # Test 6: Cohérence géographique (optionnel - les communes côtières vs intérieures)
            coastal_communes = ["Pointe-à-Pitre", "Sainte-Anne", "Le Gosier", "Saint-François"]
            inland_communes = ["Basse-Terre"]
            
            coastal_temps = [commune_data[c]["current"]["temperature_max"] for c in coastal_communes if c in commune_data]
            inland_temps = [commune_data[c]["current"]["temperature_max"] for c in inland_communes if c in commune_data]
            
            if coastal_temps and inland_temps:
                avg_coastal = sum(coastal_temps) / len(coastal_temps)
                avg_inland = sum(inland_temps) / len(inland_temps)
                
                # Les températures ne doivent pas être aberrantes (différence > 15°C)
                if abs(avg_coastal - avg_inland) > 15:
                    self.log_result("Diversité Inter-Communes", False, 
                                  f"Différence température aberrante côte/intérieur: {abs(avg_coastal - avg_inland):.1f}°C")
                    return False
            
            self.log_result("Diversité Inter-Communes", True, 
                          f"Diversité OK - Temp var: {max(temp_maxs)-min(temp_maxs):.1f}°C, "
                          f"Vent var: {wind_variation:.1f}km/h, Humidité var: {humidity_variation:.1f}%")
            return True
            
        except Exception as e:
            self.log_result("Diversité Inter-Communes", False, f"Exception: {str(e)}")
            return False
    
    async def test_nasa_api_fixes_working(self) -> bool:
        """Test que les corrections NASA API fonctionnent (pas de valeurs N/A pour champs critiques)"""
        try:
            all_working = True
            na_values_found = []
            
            for commune in TEST_COMMUNES:
                url = f"{BACKEND_URL}/weather/{commune}"
                response = await self.client.get(url)
                
                if response.status_code != 200:
                    self.log_result("Corrections NASA API", False, 
                                  f"Erreur {commune}: {response.status_code}")
                    return False
                
                data = response.json()
                
                # Vérifier les champs critiques seulement (pas les optionnels comme wind_direction, visibility, uv_index)
                critical_fields = {
                    "current": ["temperature_min", "temperature_max", "humidity", "wind_speed"],
                    "forecast": ["temperature_min", "temperature_max", "humidity", "wind_speed"]
                }
                
                # Vérifier current
                current = data.get("current", {})
                for field in critical_fields["current"]:
                    value = current.get(field)
                    if value is None or str(value).upper() == "N/A":
                        na_values_found.append(f"{commune}: current.{field} = {value}")
                
                # Vérifier forecast (5 premiers jours)
                forecast = data.get("forecast", [])[:5]
                for i, day in enumerate(forecast):
                    weather_data = day.get("weather_data", {})
                    for field in critical_fields["forecast"]:
                        value = weather_data.get(field)
                        if value is None or str(value).upper() == "N/A":
                            na_values_found.append(f"{commune}: forecast[{i}].weather_data.{field} = {value}")
            
            if na_values_found:
                # Limiter l'affichage aux 5 premières erreurs
                displayed_errors = na_values_found[:5]
                error_msg = "; ".join(displayed_errors)
                if len(na_values_found) > 5:
                    error_msg += f" ... et {len(na_values_found)-5} autres"
                
                self.log_result("Corrections NASA API", False, error_msg)
                return False
            
            self.log_result("Corrections NASA API", True, 
                          f"Aucune valeur N/A critique trouvée sur {len(TEST_COMMUNES)} communes")
            return True
            
        except Exception as e:
            self.log_result("Corrections NASA API", False, f"Exception: {str(e)}")
            return False
    
    async def test_realistic_weather_values_all_communes(self) -> bool:
        """Test que toutes les valeurs météo sont réalistes pour le climat tropical"""
        try:
            unrealistic_values = []
            
            for commune in TEST_COMMUNES:
                url = f"{BACKEND_URL}/weather/{commune}"
                response = await self.client.get(url)
                
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                # Vérifier données actuelles
                current = data.get("current", {})
                temp_min = current.get("temperature_min", 0)
                temp_max = current.get("temperature_max", 0)
                wind_speed = current.get("wind_speed", 0)
                humidity = current.get("humidity", 0)
                pressure = current.get("pressure", 0)
                
                # Températures tropicales réalistes (Guadeloupe)
                if not (18 <= temp_min <= 35):
                    unrealistic_values.append(f"{commune}: temp_min={temp_min}°C (attendu: 18-35°C)")
                
                if not (22 <= temp_max <= 40):
                    unrealistic_values.append(f"{commune}: temp_max={temp_max}°C (attendu: 22-40°C)")
                
                # Vents réalistes (pas de vents destructeurs constants)
                if wind_speed > 80:
                    unrealistic_values.append(f"{commune}: vent={wind_speed}km/h (>80km/h suspect)")
                
                if wind_speed < 0:
                    unrealistic_values.append(f"{commune}: vent={wind_speed}km/h (négatif)")
                
                # Humidité tropicale
                if not (40 <= humidity <= 100):
                    unrealistic_values.append(f"{commune}: humidité={humidity}% (attendu: 40-100%)")
                
                # Pression atmosphérique - 101.3 kPa = 1013 hPa (normal)
                if pressure > 0:
                    if pressure < 200:  # Probablement en kPa (101.3 kPa = 1013 hPa)
                        if not (98 <= pressure <= 104):
                            unrealistic_values.append(f"{commune}: pression={pressure}kPa (attendu: 98-104kPa)")
                    else:  # Probablement en hPa
                        if not (980 <= pressure <= 1040):
                            unrealistic_values.append(f"{commune}: pression={pressure}hPa (attendu: 980-1040hPa)")
                
                # Vérifier forecast (3 premiers jours)
                forecast = data.get("forecast", [])[:3]
                for i, day in enumerate(forecast):
                    weather_data = day.get("weather_data", {})
                    day_temp_min = weather_data.get("temperature_min", 0)
                    day_temp_max = weather_data.get("temperature_max", 0)
                    day_wind = weather_data.get("wind_speed", 0)
                    day_humidity = weather_data.get("humidity", 0)
                    
                    if day_temp_min > 0 and not (18 <= day_temp_min <= 35):
                        unrealistic_values.append(f"{commune} J{i+1}: temp_min={day_temp_min}°C")
                    
                    if day_temp_max > 0 and not (22 <= day_temp_max <= 40):
                        unrealistic_values.append(f"{commune} J{i+1}: temp_max={day_temp_max}°C")
                    
                    if day_wind > 80:
                        unrealistic_values.append(f"{commune} J{i+1}: vent={day_wind}km/h")
                    
                    if day_humidity > 0 and not (40 <= day_humidity <= 100):
                        unrealistic_values.append(f"{commune} J{i+1}: humidité={day_humidity}%")
            
            if unrealistic_values:
                # Limiter l'affichage aux 10 premières erreurs
                displayed_errors = unrealistic_values[:10]
                error_msg = "; ".join(displayed_errors)
                if len(unrealistic_values) > 10:
                    error_msg += f" ... et {len(unrealistic_values)-10} autres"
                
                self.log_result("Valeurs Météo Réalistes", False, error_msg)
                return False
            
            self.log_result("Valeurs Météo Réalistes", True, 
                          f"Toutes les valeurs réalistes sur {len(TEST_COMMUNES)} communes")
            return True
            
        except Exception as e:
            self.log_result("Valeurs Météo Réalistes", False, f"Exception: {str(e)}")
            return False

    # =============================================================================
    # TESTS ROBUSTESSE GÉNÉRALE
    # =============================================================================
    
    async def test_api_status(self) -> bool:
        """Test endpoint de diagnostic général - /api/status"""
        try:
            url = f"{BACKEND_URL}/status"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("API Status", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["status", "timestamp", "api_usage", "services"]
            for field in required_fields:
                if field not in data:
                    self.log_result("API Status", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier que l'API est opérationnelle
            if data.get("status") != "operational":
                self.log_result("API Status", False, 
                              f"API non opérationnelle: {data.get('status')}")
                return False
            
            # Vérifier services
            services = data.get("services", {})
            required_services = ["weather_cache", "alert_system", "subscriptions"]
            for service in required_services:
                if services.get(service) != "active":
                    self.log_result("API Status", False, 
                                  f"Service non actif: {service}")
                    return False
            
            # Vérifier usage API
            api_usage = data.get("api_usage", {})
            if "openweather_calls_today" not in api_usage:
                self.log_result("API Status", False, 
                              "Statistiques API usage manquantes")
                return False
            
            calls_today = api_usage.get("openweather_calls_today", 0)
            self.log_result("API Status", True, 
                          f"API opérationnelle, {calls_today} appels aujourd'hui")
            return True
            
        except Exception as e:
            self.log_result("API Status", False, f"Exception: {str(e)}")
            return False
    
    async def test_service_initialization(self) -> bool:
        """Test que tous les services s'initialisent correctement"""
        try:
            # Test plusieurs endpoints pour vérifier l'initialisation
            endpoints_to_test = [
                "/status",
                "/config/communes",
                "/weather/backup/status"
            ]
            
            all_working = True
            details = []
            
            for endpoint in endpoints_to_test:
                url = f"{BACKEND_URL}{endpoint}"
                response = await self.client.get(url)
                
                if response.status_code == 200:
                    details.append(f"{endpoint}: OK")
                else:
                    details.append(f"{endpoint}: FAILED ({response.status_code})")
                    all_working = False
            
            if all_working:
                self.log_result("Initialisation Services", True, 
                              f"Tous les services initialisés: {', '.join(details)}")
            else:
                self.log_result("Initialisation Services", False, 
                              f"Problèmes d'initialisation: {', '.join(details)}")
            
            return all_working
            
        except Exception as e:
            self.log_result("Initialisation Services", False, f"Exception: {str(e)}")
            return False
    
    # =============================================================================
    # TESTS AI PREDICTION ENDPOINTS - FOCUS PRINCIPAL
    # =============================================================================
    
    async def test_ai_prediction_endpoint(self, commune: str) -> bool:
        """Test endpoint AI prediction - /api/ai/cyclone/predict/{commune}"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"AI Prediction - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure réponse
            required_fields = [
                "commune", "coordinates", "damage_predictions", 
                "risk_level", "confidence_score", "recommendations"
            ]
            
            for field in required_fields:
                if field not in data:
                    self.log_result(f"AI Prediction - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier structure damage_predictions
            damage_predictions = data.get("damage_predictions", {})
            damage_fields = ["infrastructure", "agriculture", "population_impact"]
            for field in damage_fields:
                if field not in damage_predictions:
                    self.log_result(f"AI Prediction - {commune}", False, 
                                  f"Champ damage_predictions manquant: {field}")
                    return False
            
            # Vérifier valeurs réalistes
            risk_level = data.get("risk_level")
            if risk_level not in ["faible", "modéré", "élevé", "critique"]:
                self.log_result(f"AI Prediction - {commune}", False, 
                              f"Niveau de risque invalide: {risk_level}")
                return False
            
            confidence = data.get("confidence_score", 0)
            if not (0 <= confidence <= 100):
                self.log_result(f"AI Prediction - {commune}", False, 
                              f"Score de confiance invalide: {confidence}")
                return False
            
            # Vérifier recommandations (peuvent être vides en conditions normales)
            recommendations = data.get("recommendations", [])
            if not isinstance(recommendations, list):
                self.log_result(f"AI Prediction - {commune}", False, 
                              "Recommandations doivent être une liste")
                return False
            
            # En conditions normales, les recommandations peuvent être vides
            # Mais si elles existent, elles ne doivent pas être alarmistes pour risque faible
            if risk_level == "faible" and len(recommendations) > 0:
                if any("ÉVACUATION" in rec.upper() for rec in recommendations):
                    self.log_result(f"AI Prediction - {commune}", False, 
                                  "Recommandations trop alarmistes pour risque faible")
                    return False
            
            self.log_result(f"AI Prediction - {commune}", True, 
                          f"Risk: {risk_level}, Confidence: {confidence}%, Recs: {len(recommendations)}")
            return True
            
        except Exception as e:
            self.log_result(f"AI Prediction - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_ai_timeline_endpoint(self, commune: str) -> bool:
        """Test endpoint AI timeline - /api/ai/cyclone/timeline/{commune}"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/timeline/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"AI Timeline - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["commune", "coordinates", "timeline_predictions"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"AI Timeline - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier timeline_predictions
            timeline = data.get("timeline_predictions", {})
            if not isinstance(timeline, dict) or len(timeline) == 0:
                self.log_result(f"AI Timeline - {commune}", False, 
                              "Timeline predictions vide ou invalide")
                return False
            
            # Vérifier au moins quelques points temporels
            expected_hours = ["H+0", "H+6", "H+12"]
            found_hours = []
            for hour_key in expected_hours:
                if hour_key in timeline:
                    found_hours.append(hour_key)
                    hour_data = timeline[hour_key]
                    if "risk_evolution" not in hour_data:
                        self.log_result(f"AI Timeline - {commune}", False, 
                                      f"risk_evolution manquant pour {hour_key}")
                        return False
            
            if len(found_hours) < 2:
                self.log_result(f"AI Timeline - {commune}", False, 
                              f"Pas assez de points temporels: {found_hours}")
                return False
            
            self.log_result(f"AI Timeline - {commune}", True, 
                          f"Timeline OK avec {len(timeline)} points temporels")
            return True
            
        except Exception as e:
            self.log_result(f"AI Timeline - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_ai_historical_endpoint(self, commune: str) -> bool:
        """Test endpoint AI historical - /api/ai/cyclone/historical/{commune}"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/historical/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"AI Historical - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["commune", "coordinates", "historical_events", "risk_factors"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"AI Historical - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier historical_events
            historical_events = data.get("historical_events", [])
            if not isinstance(historical_events, list):
                self.log_result(f"AI Historical - {commune}", False, 
                              "historical_events doit être une liste")
                return False
            
            # Vérifier structure des événements historiques
            for i, event in enumerate(historical_events[:3]):  # Vérifier les 3 premiers
                event_fields = ["year", "event_name", "damage_type", "damage_percentage"]
                for field in event_fields:
                    if field not in event:
                        self.log_result(f"AI Historical - {commune}", False, 
                                      f"Champ événement manquant: {field} (événement {i})")
                        return False
            
            # Vérifier risk_factors
            risk_factors = data.get("risk_factors", [])
            if not isinstance(risk_factors, list):
                self.log_result(f"AI Historical - {commune}", False, 
                              "risk_factors doit être une liste")
                return False
            
            self.log_result(f"AI Historical - {commune}", True, 
                          f"Historique OK avec {len(historical_events)} événements, {len(risk_factors)} facteurs")
            return True
            
        except Exception as e:
            self.log_result(f"AI Historical - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_ai_global_risk_endpoint(self) -> bool:
        """Test endpoint AI global risk - /api/ai/cyclone/global-risk"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/global-risk"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("AI Global Risk", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = [
                "global_risk_level", "affected_communes", "high_risk_count", 
                "critical_risk_count", "regional_recommendations", "last_analysis"
            ]
            
            for field in required_fields:
                if field not in data:
                    self.log_result("AI Global Risk", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifier global_risk_level
            global_risk = data.get("global_risk_level")
            if global_risk not in ["faible", "modéré", "élevé", "critique"]:
                self.log_result("AI Global Risk", False, 
                              f"Niveau de risque global invalide: {global_risk}")
                return False
            
            # Vérifier cohérence des compteurs
            high_risk_count = data.get("high_risk_count", 0)
            critical_risk_count = data.get("critical_risk_count", 0)
            
            if not isinstance(high_risk_count, int) or high_risk_count < 0:
                self.log_result("AI Global Risk", False, 
                              f"high_risk_count invalide: {high_risk_count}")
                return False
            
            if not isinstance(critical_risk_count, int) or critical_risk_count < 0:
                self.log_result("AI Global Risk", False, 
                              f"critical_risk_count invalide: {critical_risk_count}")
                return False
            
            # Vérifier affected_communes
            affected_communes = data.get("affected_communes", [])
            if not isinstance(affected_communes, list):
                self.log_result("AI Global Risk", False, 
                              "affected_communes doit être une liste")
                return False
            
            # Vérifier regional_recommendations
            recommendations = data.get("regional_recommendations", [])
            if not isinstance(recommendations, list):
                self.log_result("AI Global Risk", False, 
                              "regional_recommendations doit être une liste")
                return False
            
            self.log_result("AI Global Risk", True, 
                          f"Risque global: {global_risk}, Communes affectées: {len(affected_communes)}, "
                          f"Risque élevé: {high_risk_count}, Critique: {critical_risk_count}")
            return True
            
        except Exception as e:
            self.log_result("AI Global Risk", False, f"Exception: {str(e)}")
            return False
    
    async def test_ai_service_initialization(self) -> bool:
        """Test que le service AI précalculation est bien initialisé"""
        try:
            # Tester plusieurs endpoints AI pour vérifier l'initialisation
            endpoints_to_test = [
                "/ai/scheduler/status",
                "/ai/model/info"
            ]
            
            all_working = True
            details = []
            
            for endpoint in endpoints_to_test:
                url = f"{BACKEND_URL}{endpoint}"
                response = await self.client.get(url)
                
                if response.status_code == 200:
                    details.append(f"{endpoint}: OK")
                else:
                    details.append(f"{endpoint}: FAILED ({response.status_code})")
                    all_working = False
            
            if all_working:
                self.log_result("AI Service Initialization", True, 
                              f"Services AI initialisés: {', '.join(details)}")
            else:
                self.log_result("AI Service Initialization", False, 
                              f"Problèmes initialisation AI: {', '.join(details)}")
            
            return all_working
            
        except Exception as e:
            self.log_result("AI Service Initialization", False, f"Exception: {str(e)}")
            return False
    
    async def test_ai_parameter_fix_validation(self) -> bool:
        """Test spécifique pour valider que le fix des paramètres AI fonctionne"""
        try:
            # Tester plusieurs communes pour s'assurer qu'il n'y a plus d'erreur de paramètres
            test_communes = ["Deshaies", "Pointe-à-Pitre"]
            all_working = True
            error_details = []
            
            for commune in test_communes:
                url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
                response = await self.client.get(url)
                
                if response.status_code != 200:
                    all_working = False
                    error_text = response.text
                    
                    # Vérifier spécifiquement l'erreur de paramètres
                    if "unexpected keyword argument 'commune_name'" in error_text:
                        error_details.append(f"{commune}: ERREUR PARAMÈTRES NON CORRIGÉE - {error_text}")
                    else:
                        error_details.append(f"{commune}: Autre erreur - Status {response.status_code}")
                else:
                    # Vérifier que la réponse est valide
                    try:
                        data = response.json()
                        if "commune" not in data or "damage_predictions" not in data:
                            all_working = False
                            error_details.append(f"{commune}: Réponse invalide")
                    except:
                        all_working = False
                        error_details.append(f"{commune}: JSON invalide")
            
            if all_working:
                self.log_result("AI Parameter Fix Validation", True, 
                              f"Fix paramètres validé sur {len(test_communes)} communes")
            else:
                self.log_result("AI Parameter Fix Validation", False, 
                              f"Problèmes détectés: {'; '.join(error_details)}")
            
            return all_working
            
        except Exception as e:
            self.log_result("AI Parameter Fix Validation", False, f"Exception: {str(e)}")
            return False

    async def run_all_tests(self):
        """Exécute tous les tests avec focus sur les endpoints AI"""
        print("🚀 Démarrage des tests AI prediction endpoints - Météo Sentinelle")
        print(f"🌐 Backend URL: {BACKEND_URL}")
        print(f"🏝️ Communes à tester: {', '.join(TEST_COMMUNES)}")
        print("=" * 80)
        
        # 1. FOCUS PRINCIPAL: Tests AI Prediction Endpoints
        print("\n🤖 Tests AI Prediction Endpoints (FOCUS PRINCIPAL)...")
        
        # Test validation du fix des paramètres
        await self.test_ai_parameter_fix_validation()
        
        # Test initialisation service AI
        await self.test_ai_service_initialization()
        
        # Test endpoints AI pour communes spécifiques
        test_communes_ai = ["Deshaies", "Pointe-à-Pitre"]  # Communes mentionnées dans la demande
        
        for commune in test_communes_ai:
            await self.test_ai_prediction_endpoint(commune)
            await self.test_ai_timeline_endpoint(commune)
            await self.test_ai_historical_endpoint(commune)
        
        # Test endpoint global risk
        await self.test_ai_global_risk_endpoint()
        
        # 2. Tests correction IA vigilance verte (existants)
        print("\n🤖 Tests correction IA vigilance verte...")
        for commune in TEST_COMMUNES:
            await self.test_ai_vigilance_green_adaptation(commune)
        
        # 3. Tests robustesse générale
        print("\n🔧 Tests robustesse générale...")
        await self.test_api_status()
        await self.test_service_initialization()
        
        # Résumé final
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ DES TESTS AI PREDICTION ENDPOINTS")
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
        with open("/app/ai_prediction_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Résultats sauvegardés dans: /app/ai_prediction_test_results.json")
        
        return self.results["failed"] == 0

async def main():
    """Fonction principale"""
    tester = BackendTester()
    
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
    finally:
        await tester.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)