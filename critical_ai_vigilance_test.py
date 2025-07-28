#!/usr/bin/env python3
"""
Test critique spécifique pour la correction IA vigilance verte
Focus sur les exigences exactes de la demande de révision
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, List

# Configuration
BACKEND_URL = "https://7cc3db80-543d-4833-ab38-94990a7b2d12.preview.emergentagent.com/api"
TIMEOUT = 30.0

# Communes à tester (selon la demande spécifique)
TEST_COMMUNES = [
    "Pointe-à-Pitre",
    "Basse-Terre", 
    "Sainte-Anne"
]

class CriticalAIVigilanceTest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "critical_failures": [],
            "detailed_results": {}
        }
        self.vigilance_level = None
        
    async def close(self):
        await self.client.aclose()
    
    def log_result(self, test_name: str, success: bool, details: str = "", is_critical: bool = False):
        """Enregistre le résultat d'un test"""
        self.results["total_tests"] += 1
        if success:
            self.results["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["failed"] += 1
            print(f"❌ {test_name}: {details}")
            if is_critical:
                self.results["critical_failures"].append(f"{test_name}: {details}")
        
        self.results["detailed_results"][test_name] = {
            "success": success,
            "details": details,
            "is_critical": is_critical,
            "timestamp": datetime.now().isoformat()
        }
    
    async def test_vigilance_data(self) -> bool:
        """Test endpoint vigilance pour confirmer vigilance verte"""
        try:
            # Try different possible vigilance endpoints
            possible_endpoints = [
                "/vigilance/data",
                "/vigilance/guadeloupe", 
                "/vigilance/theme"
            ]
            
            vigilance_data = None
            working_endpoint = None
            
            for endpoint in possible_endpoints:
                try:
                    url = f"{BACKEND_URL}{endpoint}"
                    response = await self.client.get(url)
                    
                    if response.status_code == 200:
                        vigilance_data = response.json()
                        working_endpoint = endpoint
                        break
                except:
                    continue
            
            if not vigilance_data:
                self.log_result("Vigilance Data", False, 
                              "Aucun endpoint vigilance accessible", is_critical=True)
                return False
            
            # Extract vigilance level
            vigilance_level = None
            if 'color_level' in vigilance_data:
                vigilance_level = vigilance_data['color_level']
            elif 'level' in vigilance_data:
                vigilance_level = vigilance_data['level']
            elif 'vigilance_level' in vigilance_data:
                vigilance_level = vigilance_data['vigilance_level']
            
            if not vigilance_level:
                self.log_result("Vigilance Data", False, 
                              "Niveau de vigilance non trouvé dans la réponse", is_critical=True)
                return False
            
            self.vigilance_level = vigilance_level.lower()
            
            self.log_result("Vigilance Data", True, 
                          f"Endpoint: {working_endpoint}, Niveau: {vigilance_level}")
            return True
            
        except Exception as e:
            self.log_result("Vigilance Data", False, f"Exception: {str(e)}", is_critical=True)
            return False
    
    async def test_ai_critical_vigilance_green_requirements(self, commune: str) -> bool:
        """Test critique: IA ne doit PAS générer de risques élevés en vigilance VERTE"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"IA Critique Vigilance Verte - {commune}", False, 
                              f"Status {response.status_code}: {response.text}", is_critical=True)
                return False
            
            data = response.json()
            
            # EXIGENCE 1: risk_level doit être TOUJOURS "faible" en vigilance verte
            risk_level = data.get("risk_level", "").lower()
            if self.vigilance_level == "vert" and risk_level != "faible":
                self.log_result(f"IA Critique Vigilance Verte - {commune}", False, 
                              f"CRITIQUE: risk_level='{risk_level}' au lieu de 'faible' en vigilance VERTE", 
                              is_critical=True)
                return False
            
            # EXIGENCE 2: weather_risk_score <= 12 maximum en vigilance verte
            risk_score = data.get("risk_score", 0)
            weather_risk_score = data.get("weather_risk_score", risk_score)  # Fallback to risk_score
            
            if self.vigilance_level == "vert" and weather_risk_score > 12:
                self.log_result(f"IA Critique Vigilance Verte - {commune}", False, 
                              f"CRITIQUE: weather_risk_score={weather_risk_score} > 12 en vigilance VERTE", 
                              is_critical=True)
                return False
            
            # EXIGENCE 3: Pas de mentions de "vents destructeurs"
            recommendations = data.get("recommendations", [])
            weather_context = data.get("weather_context", {})
            
            # Chercher dans toutes les chaînes de texte
            all_text = " ".join(recommendations).lower()
            if isinstance(weather_context, dict):
                for key, value in weather_context.items():
                    if isinstance(value, str):
                        all_text += " " + value.lower()
            
            destructive_terms = ["vents destructeurs", "vent destructeur", "destructive winds", "destructive wind"]
            for term in destructive_terms:
                if term in all_text:
                    self.log_result(f"IA Critique Vigilance Verte - {commune}", False, 
                                  f"CRITIQUE: Mention de '{term}' trouvée en vigilance VERTE", 
                                  is_critical=True)
                    return False
            
            # EXIGENCE 4: Conditions météo décrites comme "normales"
            if self.vigilance_level == "vert":
                # Vérifier que les recommandations ne sont pas alarmistes
                alarmist_terms = ["évacuation", "urgence", "danger imminent", "critique", "alerte rouge"]
                for term in alarmist_terms:
                    if term in all_text:
                        self.log_result(f"IA Critique Vigilance Verte - {commune}", False, 
                                      f"CRITIQUE: Terme alarmiste '{term}' en vigilance VERTE", 
                                      is_critical=True)
                        return False
            
            self.log_result(f"IA Critique Vigilance Verte - {commune}", True, 
                          f"✅ Vigilance: {self.vigilance_level}, Risk: {risk_level}, Score: {weather_risk_score}")
            return True
            
        except Exception as e:
            self.log_result(f"IA Critique Vigilance Verte - {commune}", False, 
                          f"Exception: {str(e)}", is_critical=True)
            return False
    
    async def test_ai_coherence_with_vigilance(self, commune: str) -> bool:
        """Test cohérence entre prédictions IA et vigilance officielle"""
        try:
            # Récupérer prédiction IA
            ai_url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            ai_response = await self.client.get(ai_url)
            
            if ai_response.status_code != 200:
                self.log_result(f"Cohérence IA-Vigilance - {commune}", False, 
                              f"Erreur IA: {ai_response.status_code}")
                return False
            
            ai_data = ai_response.json()
            ai_risk_level = ai_data.get("risk_level", "").lower()
            ai_risk_score = ai_data.get("risk_score", 0)
            
            # Vérifier cohérence avec vigilance
            if self.vigilance_level == "vert":
                # En vigilance verte, l'IA ne devrait pas prédire de risques élevés
                if ai_risk_level in ["élevé", "critique"]:
                    self.log_result(f"Cohérence IA-Vigilance - {commune}", False, 
                                  f"INCOHÉRENCE: IA prédit '{ai_risk_level}' mais vigilance '{self.vigilance_level}'", 
                                  is_critical=True)
                    return False
                
                # Score de risque cohérent
                if ai_risk_score > 25:  # Seuil plus permissif que 12 pour cohérence générale
                    self.log_result(f"Cohérence IA-Vigilance - {commune}", False, 
                                  f"INCOHÉRENCE: Score IA {ai_risk_score} trop élevé pour vigilance verte")
                    return False
            
            self.log_result(f"Cohérence IA-Vigilance - {commune}", True, 
                          f"Cohérent: Vigilance {self.vigilance_level} ↔ IA {ai_risk_level} (score: {ai_risk_score})")
            return True
            
        except Exception as e:
            self.log_result(f"Cohérence IA-Vigilance - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def test_ai_recommendations_appropriate(self, commune: str) -> bool:
        """Test que les recommandations IA sont appropriées au niveau de vigilance"""
        try:
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                self.log_result(f"Recommandations IA - {commune}", False, 
                              f"Status {response.status_code}")
                return False
            
            data = response.json()
            recommendations = data.get("recommendations", [])
            
            if not recommendations:
                self.log_result(f"Recommandations IA - {commune}", False, 
                              "Aucune recommandation fournie")
                return False
            
            # En vigilance verte, les recommandations doivent être normales/préventives
            if self.vigilance_level == "vert":
                emergency_terms = [
                    "évacuation immédiate", "danger de mort", "alerte rouge", 
                    "urgence absolue", "fuyez", "évacuez maintenant"
                ]
                
                all_recommendations = " ".join(recommendations).lower()
                
                for term in emergency_terms:
                    if term in all_recommendations:
                        self.log_result(f"Recommandations IA - {commune}", False, 
                                      f"CRITIQUE: Recommandation d'urgence '{term}' en vigilance VERTE", 
                                      is_critical=True)
                        return False
                
                # Vérifier présence de recommandations préventives appropriées
                preventive_terms = ["surveiller", "préparer", "vérifier", "préventif", "normal"]
                has_preventive = any(term in all_recommendations for term in preventive_terms)
                
                if not has_preventive:
                    self.log_result(f"Recommandations IA - {commune}", False, 
                                  "Manque de recommandations préventives appropriées")
                    return False
            
            self.log_result(f"Recommandations IA - {commune}", True, 
                          f"Recommandations appropriées pour vigilance {self.vigilance_level}")
            return True
            
        except Exception as e:
            self.log_result(f"Recommandations IA - {commune}", False, f"Exception: {str(e)}")
            return False
    
    async def run_critical_tests(self):
        """Exécute les tests critiques pour la vigilance verte IA"""
        print("🚨 TESTS CRITIQUES - IA VIGILANCE VERTE")
        print("=" * 60)
        print("PRIORITÉ ABSOLUE: Vérifier que l'IA ne génère plus de 'vents destructeurs'")
        print("ou risques élevés en vigilance VERTE")
        print("=" * 60)
        
        # 1. Test vigilance data d'abord
        print("\n🟢 Test 1: Récupération données vigilance...")
        vigilance_ok = await self.test_vigilance_data()
        
        if not vigilance_ok:
            print("❌ ÉCHEC CRITIQUE: Impossible de récupérer les données de vigilance")
            return False
        
        print(f"📊 Niveau de vigilance détecté: {self.vigilance_level.upper()}")
        
        # 2. Tests critiques IA pour chaque commune
        print(f"\n🤖 Test 2: Exigences critiques IA (vigilance {self.vigilance_level})...")
        for commune in TEST_COMMUNES:
            await self.test_ai_critical_vigilance_green_requirements(commune)
        
        # 3. Tests cohérence IA-vigilance
        print(f"\n🔄 Test 3: Cohérence IA ↔ Vigilance...")
        for commune in TEST_COMMUNES:
            await self.test_ai_coherence_with_vigilance(commune)
        
        # 4. Tests recommandations appropriées
        print(f"\n📋 Test 4: Recommandations appropriées...")
        for commune in TEST_COMMUNES:
            await self.test_ai_recommendations_appropriate(commune)
        
        # Résumé critique
        print("\n" + "=" * 60)
        print("🚨 RÉSUMÉ TESTS CRITIQUES IA VIGILANCE VERTE")
        print("=" * 60)
        print(f"✅ Tests réussis: {self.results['passed']}")
        print(f"❌ Tests échoués: {self.results['failed']}")
        print(f"📈 Total tests: {self.results['total_tests']}")
        
        if self.results["critical_failures"]:
            print(f"\n🚨 ÉCHECS CRITIQUES ({len(self.results['critical_failures'])}):")
            for failure in self.results["critical_failures"]:
                print(f"   💥 {failure}")
            print("\n⚠️  CES ÉCHECS DOIVENT ÊTRE CORRIGÉS IMMÉDIATEMENT")
        else:
            print(f"\n🎉 AUCUN ÉCHEC CRITIQUE - IA CONFORME AUX EXIGENCES VIGILANCE VERTE")
        
        # Validation spécifique selon la demande
        if self.vigilance_level == "vert":
            print(f"\n✅ VALIDATION VIGILANCE VERTE:")
            print(f"   • risk_level = 'faible' OBLIGATOIRE: {'✅' if not any('risk_level' in f for f in self.results['critical_failures']) else '❌'}")
            print(f"   • weather_risk_score <= 12: {'✅' if not any('weather_risk_score' in f for f in self.results['critical_failures']) else '❌'}")
            print(f"   • Pas de 'vents destructeurs': {'✅' if not any('vents destructeurs' in f for f in self.results['critical_failures']) else '❌'}")
            print(f"   • Recommandations normales: {'✅' if not any('alarmiste' in f for f in self.results['critical_failures']) else '❌'}")
        
        # Sauvegarde résultats
        with open("/app/critical_ai_vigilance_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Résultats sauvegardés: /app/critical_ai_vigilance_test_results.json")
        
        return len(self.results["critical_failures"]) == 0

async def main():
    """Fonction principale"""
    tester = CriticalAIVigilanceTest()
    
    try:
        success = await tester.run_critical_tests()
        return 0 if success else 1
    finally:
        await tester.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)