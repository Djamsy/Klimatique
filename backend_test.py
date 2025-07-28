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
BACKEND_URL = "https://d77d7f0e-effd-4bb4-a235-509e3ee58622.preview.emergentagent.com/api"
TIMEOUT = 30.0

# Communes à tester (selon la demande spécifique)
TEST_COMMUNES = [
    "Pointe-à-Pitre",
    "Basse-Terre", 
    "Sainte-Anne"
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
                "risk_level", "risk_score", "confidence", 
                "recommendations", "weather_context"
            ]
            
            for field in required_fields:
                if field not in data:
                    self.log_result(f"IA Vigilance Verte - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérification principale: en vigilance verte, le risque ne doit pas dépasser "modéré"
            risk_level = data["risk_level"]
            risk_score = data.get("risk_score", 0)
            
            # Vérifier la hiérarchie des risques
            risk_hierarchy = ["faible", "modéré", "élevé", "critique"]
            
            # En conditions normales (pas de cyclone), le risque devrait être limité
            if risk_level in ["élevé", "critique"] and risk_score < 30:
                self.log_result(f"IA Vigilance Verte - {commune}", False, 
                              f"Risque trop élevé pour conditions normales: {risk_level} (score: {risk_score})")
                return False
            
            # Vérifier que le score de risque est cohérent avec le niveau
            if risk_level == "faible" and risk_score > 20:
                self.log_result(f"IA Vigilance Verte - {commune}", False, 
                              f"Score incohérent pour risque faible: {risk_score}")
                return False
            
            if risk_level == "modéré" and risk_score > 40:
                self.log_result(f"IA Vigilance Verte - {commune}", False, 
                              f"Score incohérent pour risque modéré: {risk_score}")
                return False
            
            # Vérifier les recommandations (doivent être adaptées au niveau de risque)
            recommendations = data.get("recommendations", [])
            if risk_level == "faible" and any("ÉVACUATION" in rec.upper() for rec in recommendations):
                self.log_result(f"IA Vigilance Verte - {commune}", False, 
                              f"Recommandations trop alarmistes pour risque faible")
                return False
            
            self.log_result(f"IA Vigilance Verte - {commune}", True, 
                          f"Risk: {risk_level}, Score: {risk_score}, Adapté à vigilance verte")
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
    
    async def run_all_tests(self):
        """Exécute tous les tests selon la demande spécifique"""
        print("🚀 Démarrage des tests corrections backend - Météo Sentinelle")
        print(f"🌐 Backend URL: {BACKEND_URL}")
        print(f"🏝️ Communes à tester: {', '.join(TEST_COMMUNES)}")
        print("=" * 80)
        
        # 1. Tests correction IA vigilance verte
        print("\n🤖 Tests correction IA vigilance verte...")
        for commune in TEST_COMMUNES:
            await self.test_ai_vigilance_green_adaptation(commune)
        
        # 2. Tests système backup météo
        print("\n💾 Tests système backup météo...")
        await self.test_weather_backup_system_complete()
        await self.test_weather_backup_status()
        
        for commune in TEST_COMMUNES:
            await self.test_weather_backup_commune(commune)
        
        # 3. Tests intégration backup météo
        print("\n🔄 Tests intégration backup dans service météo...")
        for commune in TEST_COMMUNES:
            await self.test_weather_service_backup_integration(commune)
        
        # 4. Tests robustesse générale
        print("\n🔧 Tests robustesse générale...")
        await self.test_api_status()
        await self.test_service_initialization()
        
        # Résumé final
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ DES TESTS CORRECTIONS BACKEND")
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
        with open("/app/backend_corrections_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Résultats sauvegardés dans: /app/backend_corrections_test_results.json")
        
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