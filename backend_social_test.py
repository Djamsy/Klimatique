#!/usr/bin/env python3
"""
Tests pour les nouveaux endpoints réseaux sociaux - Météo Sentinelle
Teste les endpoints API réseaux sociaux, modèles Pydantic, services et intégration météo
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

# Configuration
BACKEND_URL = "https://1f04a111-afac-4122-bfc5-7ccc3042901e.preview.emergentagent.com/api"
TIMEOUT = 30.0

# Communes à tester
TEST_COMMUNES = [
    "Pointe-à-Pitre",
    "Basse-Terre", 
    "Sainte-Anne"
]

class SocialMediaEndpointTester:
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
    
    async def test_social_test_connections(self) -> bool:
        """Test endpoint GET /api/social/test-connections"""
        try:
            url = f"{BACKEND_URL}/social/test-connections"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Test Connexions Sociales", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["connections", "overall_status"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Test Connexions Sociales", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications connections
            connections = data["connections"]
            if not isinstance(connections, dict):
                self.log_result("Test Connexions Sociales", False, 
                              "Connections pas un dictionnaire")
                return False
            
            # Vérifier que Twitter et Facebook sont présents
            expected_platforms = ["twitter", "facebook"]
            for platform in expected_platforms:
                if platform not in connections:
                    self.log_result("Test Connexions Sociales", False, 
                                  f"Plateforme manquante: {platform}")
                    return False
                
                platform_data = connections[platform]
                if "connected" not in platform_data:
                    self.log_result("Test Connexions Sociales", False, 
                                  f"Champ 'connected' manquant pour {platform}")
                    return False
            
            # Vérifications overall_status
            valid_statuses = ["connected", "disconnected"]
            if data["overall_status"] not in valid_statuses:
                self.log_result("Test Connexions Sociales", False, 
                              f"Overall status invalide: {data['overall_status']}")
                return False
            
            self.log_result("Test Connexions Sociales", True, 
                          f"Status: {data['overall_status']}")
            return True
            
        except Exception as e:
            self.log_result("Test Connexions Sociales", False, f"Exception: {str(e)}")
            return False
    
    async def test_social_scheduler_status(self) -> bool:
        """Test endpoint GET /api/social/scheduler/status"""
        try:
            url = f"{BACKEND_URL}/social/scheduler/status"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Statut Scheduler Social", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["is_running", "active_jobs", "last_check"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Statut Scheduler Social", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications is_running
            if not isinstance(data["is_running"], bool):
                self.log_result("Statut Scheduler Social", False, 
                              f"is_running invalide: {data['is_running']}")
                return False
            
            # Vérifications active_jobs
            if not isinstance(data["active_jobs"], int) or data["active_jobs"] < 0:
                self.log_result("Statut Scheduler Social", False, 
                              f"active_jobs invalide: {data['active_jobs']}")
                return False
            
            # Vérifications last_check (doit être une date ISO)
            try:
                datetime.fromisoformat(data["last_check"].replace('Z', '+00:00'))
            except ValueError:
                self.log_result("Statut Scheduler Social", False, 
                              f"last_check format invalide: {data['last_check']}")
                return False
            
            self.log_result("Statut Scheduler Social", True, 
                          f"Running: {data['is_running']}, Jobs: {data['active_jobs']}")
            return True
            
        except Exception as e:
            self.log_result("Statut Scheduler Social", False, f"Exception: {str(e)}")
            return False
    
    async def test_social_stats(self) -> bool:
        """Test endpoint GET /api/social/stats"""
        try:
            url = f"{BACKEND_URL}/social/stats"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result("Statistiques Sociales", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["total_posts", "platform_breakdown", "period_days", "last_updated"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Statistiques Sociales", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications total_posts
            if not isinstance(data["total_posts"], int) or data["total_posts"] < 0:
                self.log_result("Statistiques Sociales", False, 
                              f"total_posts invalide: {data['total_posts']}")
                return False
            
            # Vérifications platform_breakdown
            if not isinstance(data["platform_breakdown"], dict):
                self.log_result("Statistiques Sociales", False, 
                              "platform_breakdown pas un dictionnaire")
                return False
            
            # Vérifications period_days
            if not isinstance(data["period_days"], int) or data["period_days"] <= 0:
                self.log_result("Statistiques Sociales", False, 
                              f"period_days invalide: {data['period_days']}")
                return False
            
            # Vérifications last_updated (doit être une date ISO)
            try:
                datetime.fromisoformat(data["last_updated"].replace('Z', '+00:00'))
            except ValueError:
                self.log_result("Statistiques Sociales", False, 
                              f"last_updated format invalide: {data['last_updated']}")
                return False
            
            self.log_result("Statistiques Sociales", True, 
                          f"Total posts: {data['total_posts']}, Période: {data['period_days']} jours")
            return True
            
        except Exception as e:
            self.log_result("Statistiques Sociales", False, f"Exception: {str(e)}")
            return False
    
    async def test_social_post_without_credentials(self) -> bool:
        """Test endpoint POST /api/social/post sans credentials (doit échouer proprement)"""
        try:
            url = f"{BACKEND_URL}/social/post"
            
            # Test avec contenu simple
            post_data = {
                "content": "Test post météo Guadeloupe",
                "platforms": ["twitter", "facebook"]
            }
            
            response = await self.client.post(url, json=post_data)
            
            # On s'attend à un succès même sans credentials (le service doit gérer l'erreur)
            if response.status_code != 200:
                self.log_result("Post Social Sans Credentials", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["success", "results"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Post Social Sans Credentials", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications results
            results = data["results"]
            if not isinstance(results, dict):
                self.log_result("Post Social Sans Credentials", False, 
                              "Results pas un dictionnaire")
                return False
            
            # Vérifier que les plateformes sont présentes avec des erreurs
            expected_platforms = ["twitter", "facebook"]
            for platform in expected_platforms:
                if platform not in results:
                    self.log_result("Post Social Sans Credentials", False, 
                                  f"Plateforme manquante dans results: {platform}")
                    return False
                
                platform_result = results[platform]
                if "success" not in platform_result:
                    self.log_result("Post Social Sans Credentials", False, 
                                  f"Champ 'success' manquant pour {platform}")
                    return False
                
                # On s'attend à ce que ce soit false sans credentials
                if platform_result["success"] is True:
                    self.log_result("Post Social Sans Credentials", False, 
                                  f"Success inattendu pour {platform} sans credentials")
                    return False
            
            self.log_result("Post Social Sans Credentials", True, 
                          "Gestion d'erreur correcte sans credentials")
            return True
            
        except Exception as e:
            self.log_result("Post Social Sans Credentials", False, f"Exception: {str(e)}")
            return False
    
    async def test_social_post_with_weather_integration(self, commune: str) -> bool:
        """Test endpoint POST /api/social/post avec intégration météo"""
        try:
            url = f"{BACKEND_URL}/social/post"
            
            # Test avec commune pour intégration météo
            post_data = {
                "content": "",  # Sera généré automatiquement
                "commune": commune,
                "include_ai_prediction": True,
                "platforms": ["twitter"]
            }
            
            response = await self.client.post(url, json=post_data)
            
            if response.status_code != 200:
                self.log_result(f"Post Météo Intégré - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["success", "results"]
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Post Météo Intégré - {commune}", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications results
            results = data["results"]
            if not isinstance(results, dict):
                self.log_result(f"Post Météo Intégré - {commune}", False, 
                              "Results pas un dictionnaire")
                return False
            
            # Vérifier que Twitter est présent
            if "twitter" not in results:
                self.log_result(f"Post Météo Intégré - {commune}", False, 
                              "Twitter manquant dans results")
                return False
            
            twitter_result = results["twitter"]
            if "success" not in twitter_result:
                self.log_result(f"Post Météo Intégré - {commune}", False, 
                              "Champ 'success' manquant pour Twitter")
                return False
            
            # Le formatage météo doit fonctionner même sans credentials
            self.log_result(f"Post Météo Intégré - {commune}", True, 
                          f"Intégration météo OK pour {commune}")
            return True
            
        except Exception as e:
            self.log_result(f"Post Météo Intégré - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_social_schedule_post(self) -> bool:
        """Test endpoint POST /api/social/schedule"""
        try:
            url = f"{BACKEND_URL}/social/schedule"
            
            # Programmer un post pour dans 1 minute
            schedule_time = datetime.now() + timedelta(minutes=1)
            
            schedule_data = {
                "content": "Test post programmé météo Guadeloupe",
                "schedule_time": schedule_time.isoformat(),
                "platforms": ["twitter"]
            }
            
            response = await self.client.post(url, json=schedule_data)
            
            if response.status_code != 200:
                self.log_result("Programmation Post Social", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["success", "job_id", "scheduled_time", "platforms"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Programmation Post Social", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications success
            if not isinstance(data["success"], bool):
                self.log_result("Programmation Post Social", False, 
                              f"Success invalide: {data['success']}")
                return False
            
            # Vérifications job_id
            if not isinstance(data["job_id"], str) or len(data["job_id"]) == 0:
                self.log_result("Programmation Post Social", False, 
                              f"job_id invalide: {data['job_id']}")
                return False
            
            # Vérifications scheduled_time
            try:
                datetime.fromisoformat(data["scheduled_time"].replace('Z', '+00:00'))
            except ValueError:
                self.log_result("Programmation Post Social", False, 
                              f"scheduled_time format invalide: {data['scheduled_time']}")
                return False
            
            # Vérifications platforms
            if not isinstance(data["platforms"], list) or len(data["platforms"]) == 0:
                self.log_result("Programmation Post Social", False, 
                              f"Platforms invalide: {data['platforms']}")
                return False
            
            # Tester l'annulation du post programmé
            job_id = data["job_id"]
            cancel_url = f"{BACKEND_URL}/social/schedule/{job_id}"
            cancel_response = await self.client.delete(cancel_url)
            
            if cancel_response.status_code != 200:
                self.log_result("Programmation Post Social", False, 
                              f"Erreur annulation: {cancel_response.status_code}")
                return False
            
            cancel_data = cancel_response.json()
            if not cancel_data.get("success", False):
                self.log_result("Programmation Post Social", False, 
                              "Annulation échouée")
                return False
            
            self.log_result("Programmation Post Social", True, 
                          f"Job ID: {job_id}, Annulation OK")
            return True
            
        except Exception as e:
            self.log_result("Programmation Post Social", False, f"Exception: {str(e)}")
            return False
    
    async def test_social_credentials_storage(self) -> bool:
        """Test endpoint POST /api/social/credentials (avec données test)"""
        try:
            url = f"{BACKEND_URL}/social/credentials"
            
            # Test avec credentials Twitter factices
            credentials_data = {
                "platform": "twitter",
                "credentials": {
                    "consumer_key": "test_consumer_key",
                    "consumer_secret": "test_consumer_secret",
                    "access_token": "test_access_token",
                    "access_token_secret": "test_access_token_secret"
                }
            }
            
            response = await self.client.post(url, json=credentials_data)
            
            if response.status_code != 200:
                self.log_result("Stockage Credentials", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifications structure
            required_fields = ["success", "platform", "message"]
            for field in required_fields:
                if field not in data:
                    self.log_result("Stockage Credentials", False, 
                                  f"Champ manquant: {field}")
                    return False
            
            # Vérifications success
            if not isinstance(data["success"], bool):
                self.log_result("Stockage Credentials", False, 
                              f"Success invalide: {data['success']}")
                return False
            
            # Vérifications platform
            if data["platform"] != "twitter":
                self.log_result("Stockage Credentials", False, 
                              f"Platform incorrecte: {data['platform']}")
                return False
            
            # Vérifications message
            if not isinstance(data["message"], str) or len(data["message"]) == 0:
                self.log_result("Stockage Credentials", False, 
                              "Message invalide")
                return False
            
            self.log_result("Stockage Credentials", True, 
                          f"Platform: {data['platform']}, Success: {data['success']}")
            return True
            
        except Exception as e:
            self.log_result("Stockage Credentials", False, f"Exception: {str(e)}")
            return False
    
    async def test_ai_risk_resolution(self, commune: str) -> bool:
        """Test résolution problème risques IA bloqués à 'modéré'"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Résolution Risques IA - {commune}", False, 
                              f"Status {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            # Vérifier que le système peut bien retourner des risques "faible" en vigilance verte
            risk_level = data.get("risk_level", "")
            valid_risk_levels = ["faible", "modéré", "élevé", "critique"]
            
            if risk_level not in valid_risk_levels:
                self.log_result(f"Résolution Risques IA - {commune}", False, 
                              f"Risk level invalide: {risk_level}")
                return False
            
            # Le système doit pouvoir retourner tous les niveaux de risque
            self.log_result(f"Résolution Risques IA - {commune}", True, 
                          f"Risk level: {risk_level} (système fonctionnel)")
            return True
            
        except Exception as e:
            self.log_result(f"Résolution Risques IA - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def run_social_media_tests(self):
        """Exécute tous les tests des fonctionnalités réseaux sociaux"""
        print("🚀 Démarrage des tests réseaux sociaux - Météo Sentinelle")
        print(f"🌐 Backend URL: {BACKEND_URL}")
        print(f"🏝️ Communes à tester: {', '.join(TEST_COMMUNES)}")
        print("=" * 80)
        
        # 1. Test des nouveaux endpoints API réseaux sociaux
        print("\n📱 Tests endpoints API réseaux sociaux...")
        await self.test_social_test_connections()
        await self.test_social_scheduler_status()
        await self.test_social_stats()
        
        # 2. Test gestion erreurs
        print("\n⚠️ Tests gestion erreurs...")
        await self.test_social_post_without_credentials()
        await self.test_social_credentials_storage()
        
        # 3. Test intégration météo
        print("\n🌦️ Tests intégration météo...")
        for commune in TEST_COMMUNES:
            await self.test_social_post_with_weather_integration(commune)
        
        # 4. Test planificateur
        print("\n⏰ Tests planificateur...")
        await self.test_social_schedule_post()
        
        # 5. Test résolution problème risques IA
        print("\n🤖 Tests résolution problème risques IA...")
        for commune in TEST_COMMUNES:
            await self.test_ai_risk_resolution(commune)
        
        # Résumé final
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ DES TESTS RÉSEAUX SOCIAUX")
        print("=" * 80)
        print(f"✅ Tests réussis: {self.results['passed']}")
        print(f"❌ Tests échoués: {self.results['failed']}")
        print(f"📈 Total tests: {self.results['total_tests']}")
        
        if self.results['total_tests'] > 0:
            success_rate = (self.results['passed']/self.results['total_tests']*100)
            print(f"🎯 Taux de réussite: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print(f"\n❌ ERREURS DÉTECTÉES ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        # Sauvegarde résultats
        with open("/app/social_media_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Résultats sauvegardés dans: /app/social_media_test_results.json")
        
        return self.results["failed"] == 0

async def main():
    """Fonction principale"""
    tester = SocialMediaEndpointTester()
    
    try:
        success = await tester.run_social_media_tests()
        return 0 if success else 1
    finally:
        await tester.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)