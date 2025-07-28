#!/usr/bin/env python3
"""
Test spécifique pour l'endpoint /api/ai/cyclone/predict/{commune}
Analyse détaillée de l'adaptation du risque IA selon la vigilance Météo France

Objectifs:
1. Tester le niveau de vigilance récupéré par Météo France
2. Analyser le niveau de risque AI calculé AVANT adaptation
3. Analyser le niveau de risque AI APRÈS adaptation selon vigilance
4. Vérifier que si vigilance = "vert", le risque peut être "faible"
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, List

# Configuration
BACKEND_URL = "https://6c0658c1-f5e4-4a08-98c7-406d205120ea.preview.emergentagent.com/api"
TIMEOUT = 30.0

# Communes à tester selon la demande
TEST_COMMUNES = ["Pointe-à-Pitre", "Basse-Terre", "Sainte-Anne"]

class CycloneVigilanceAnalyzer:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.results = {
            "vigilance_data": {},
            "commune_analyses": {},
            "summary": {},
            "timestamp": datetime.now().isoformat()
        }
    
    async def close(self):
        await self.client.aclose()
    
    async def test_vigilance_endpoint(self):
        """Test l'endpoint de vigilance Météo France"""
        print("🔍 Test endpoint vigilance Météo France...")
        
        try:
            # Test endpoint vigilance Guadeloupe
            url = f"{BACKEND_URL}/vigilance/guadeloupe"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                vigilance_data = response.json()
                self.results["vigilance_data"] = vigilance_data
                
                print(f"✅ Vigilance récupérée: {vigilance_data.get('color_level', 'unknown')}")
                print(f"   Couleur: {vigilance_data.get('color_info', {}).get('name', 'N/A')}")
                print(f"   Score risque global: {vigilance_data.get('global_risk_score', 'N/A')}")
                print(f"   Risques actifs: {len(vigilance_data.get('risks', []))}")
                print(f"   Mode fallback: {vigilance_data.get('is_fallback', False)}")
                
                return True
            else:
                print(f"❌ Erreur vigilance: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Exception vigilance: {str(e)}")
            return False
    
    async def analyze_commune_prediction(self, commune: str):
        """Analyse détaillée de la prédiction IA pour une commune"""
        print(f"\n🏘️ Analyse détaillée - {commune}")
        print("=" * 50)
        
        try:
            # 1. Récupérer la prédiction IA
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                print(f"❌ Erreur prédiction: {response.status_code} - {response.text}")
                return False
            
            prediction_data = response.json()
            
            # 2. Analyser les données météo utilisées
            weather_context = prediction_data.get("weather_context", {})
            print("🌤️ DONNÉES MÉTÉO UTILISÉES:")
            print(f"   • Vent: {weather_context.get('wind_speed', 'N/A')} km/h")
            print(f"   • Pression: {weather_context.get('pressure', 'N/A')} hPa")
            print(f"   • Température: {weather_context.get('temperature', 'N/A')}°C")
            print(f"   • Humidité: {weather_context.get('humidity', 'N/A')}%")
            print(f"   • Précipitations: {weather_context.get('precipitation', 'N/A')} mm/h")
            print(f"   • Source: {weather_context.get('source', 'N/A')}")
            
            # 3. Analyser le score de risque IA
            risk_score = prediction_data.get("risk_score", 0)
            risk_level = prediction_data.get("risk_level", "unknown")
            confidence = prediction_data.get("confidence", 0)
            
            print(f"\n🤖 ANALYSE IA:")
            print(f"   • Score de risque: {risk_score}/100")
            print(f"   • Niveau de risque FINAL: {risk_level}")
            print(f"   • Confiance: {confidence}%")
            
            # 4. Analyser les dégâts prédits
            damage_pred = prediction_data.get("damage_predictions", {})
            print(f"\n💥 DÉGÂTS PRÉDITS:")
            print(f"   • Infrastructure: {damage_pred.get('infrastructure', 'N/A')}%")
            print(f"   • Agriculture: {damage_pred.get('agriculture', 'N/A')}%")
            print(f"   • Impact population: {damage_pred.get('population_impact', 'N/A')}%")
            
            # 5. Analyser les recommandations
            recommendations = prediction_data.get("recommendations", [])
            print(f"\n📋 RECOMMANDATIONS ({len(recommendations)}):")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"   {i}. {rec}")
            
            # 6. Tester l'endpoint de debug pour voir l'adaptation vigilance
            await self.test_ai_debug_endpoint(commune)
            
            # Stocker les résultats
            self.results["commune_analyses"][commune] = {
                "weather_data": weather_context,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "confidence": confidence,
                "damage_predictions": damage_pred,
                "recommendations_count": len(recommendations),
                "success": True
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Exception analyse {commune}: {str(e)}")
            self.results["commune_analyses"][commune] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    async def test_ai_debug_endpoint(self, commune: str):
        """Test l'endpoint de debug IA pour voir l'adaptation vigilance"""
        try:
            url = f"{BACKEND_URL}/ai/test/{commune}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                debug_data = response.json()
                
                print(f"\n🔬 DEBUG IA - ADAPTATION VIGILANCE:")
                print(f"   • Risque IA ORIGINAL: {debug_data.get('original_risk', 'N/A')}")
                print(f"   • Risque IA ADAPTÉ: {debug_data.get('adapted_risk', 'N/A')}")
                print(f"   • Niveau vigilance: {debug_data.get('vigilance_level', 'N/A')}")
                print(f"   • Score risque: {debug_data.get('risk_score', 'N/A')}")
                print(f"   • Confiance: {debug_data.get('confidence', 'N/A')}%")
                print(f"   • Mode test: {debug_data.get('test_mode', False)}")
                
                # Stocker les données de debug
                if commune in self.results["commune_analyses"]:
                    self.results["commune_analyses"][commune]["debug_data"] = {
                        "original_risk": debug_data.get('original_risk'),
                        "adapted_risk": debug_data.get('adapted_risk'),
                        "vigilance_level": debug_data.get('vigilance_level'),
                        "adaptation_occurred": debug_data.get('original_risk') != debug_data.get('adapted_risk')
                    }
                
            else:
                print(f"   ⚠️ Debug endpoint non disponible: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ Erreur debug endpoint: {str(e)}")
    
    async def analyze_risk_adaptation_logic(self):
        """Analyse la logique d'adaptation du risque selon la vigilance"""
        print(f"\n🧠 ANALYSE LOGIQUE D'ADAPTATION")
        print("=" * 50)
        
        vigilance_level = self.results["vigilance_data"].get("color_level", "unknown")
        print(f"Niveau de vigilance actuel: {vigilance_level}")
        
        # Analyser les adaptations pour chaque commune
        adaptations = []
        for commune, data in self.results["commune_analyses"].items():
            if data.get("success") and "debug_data" in data:
                debug = data["debug_data"]
                adaptations.append({
                    "commune": commune,
                    "original": debug.get("original_risk"),
                    "adapted": debug.get("adapted_risk"),
                    "changed": debug.get("adaptation_occurred", False)
                })
        
        print(f"\nAdaptations observées:")
        for adapt in adaptations:
            status = "🔄 ADAPTÉ" if adapt["changed"] else "➡️ INCHANGÉ"
            print(f"   • {adapt['commune']}: {adapt['original']} → {adapt['adapted']} {status}")
        
        # Vérifier si vigilance verte permet risque faible
        if vigilance_level == "vert":
            faible_risks = [a for a in adaptations if a["adapted"] == "faible"]
            if faible_risks:
                print(f"\n✅ VIGILANCE VERTE → RISQUE FAIBLE confirmé pour:")
                for risk in faible_risks:
                    print(f"   • {risk['commune']}")
            else:
                print(f"\n⚠️ VIGILANCE VERTE mais aucun risque 'faible' observé")
                print("   Cela peut indiquer un problème dans la logique d'adaptation")
        
        return adaptations
    
    async def run_complete_analysis(self):
        """Exécute l'analyse complète"""
        print("🚀 ANALYSE COMPLÈTE - CYCLONE IA & VIGILANCE")
        print(f"🌐 Backend URL: {BACKEND_URL}")
        print(f"🏝️ Communes: {', '.join(TEST_COMMUNES)}")
        print("=" * 80)
        
        # 1. Test endpoint vigilance
        vigilance_ok = await self.test_vigilance_endpoint()
        
        if not vigilance_ok:
            print("❌ Impossible de continuer sans données de vigilance")
            return False
        
        # 2. Analyser chaque commune
        print(f"\n🏘️ ANALYSE PAR COMMUNE")
        print("=" * 50)
        
        success_count = 0
        for commune in TEST_COMMUNES:
            success = await self.analyze_commune_prediction(commune)
            if success:
                success_count += 1
        
        # 3. Analyser la logique d'adaptation
        adaptations = await self.analyze_risk_adaptation_logic()
        
        # 4. Générer le résumé
        await self.generate_summary(success_count, adaptations)
        
        # 5. Sauvegarder les résultats
        with open("/app/cyclone_vigilance_analysis.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Analyse sauvegardée: /app/cyclone_vigilance_analysis.json")
        
        return success_count == len(TEST_COMMUNES)
    
    async def generate_summary(self, success_count: int, adaptations: List[Dict]):
        """Génère le résumé de l'analyse"""
        print(f"\n📊 RÉSUMÉ DE L'ANALYSE")
        print("=" * 80)
        
        vigilance_level = self.results["vigilance_data"].get("color_level", "unknown")
        vigilance_score = self.results["vigilance_data"].get("global_risk_score", 0)
        is_fallback = self.results["vigilance_data"].get("is_fallback", False)
        
        print(f"✅ Communes analysées avec succès: {success_count}/{len(TEST_COMMUNES)}")
        print(f"🚦 Niveau de vigilance: {vigilance_level} (score: {vigilance_score})")
        print(f"🔄 Mode fallback vigilance: {is_fallback}")
        
        # Analyser les niveaux de risque obtenus
        risk_levels = {}
        for commune, data in self.results["commune_analyses"].items():
            if data.get("success"):
                level = data.get("risk_level", "unknown")
                risk_levels[level] = risk_levels.get(level, 0) + 1
        
        print(f"\n📈 DISTRIBUTION DES NIVEAUX DE RISQUE:")
        for level, count in risk_levels.items():
            print(f"   • {level}: {count} commune(s)")
        
        # Analyser les adaptations
        adapted_count = len([a for a in adaptations if a["changed"]])
        print(f"\n🔄 ADAPTATIONS VIGILANCE:")
        print(f"   • Communes adaptées: {adapted_count}/{len(adaptations)}")
        print(f"   • Communes inchangées: {len(adaptations) - adapted_count}/{len(adaptations)}")
        
        # Vérification spécifique vigilance verte → risque faible
        if vigilance_level == "vert":
            faible_count = risk_levels.get("faible", 0)
            if faible_count > 0:
                print(f"\n✅ VALIDATION: Vigilance VERTE permet risque FAIBLE ({faible_count} cas)")
            else:
                print(f"\n⚠️ PROBLÈME: Vigilance VERTE mais aucun risque FAIBLE détecté")
                print("   → Vérifier la logique d'adaptation dans cyclone_damage_predictor.py")
        
        # Stocker le résumé
        self.results["summary"] = {
            "success_rate": f"{success_count}/{len(TEST_COMMUNES)}",
            "vigilance_level": vigilance_level,
            "vigilance_score": vigilance_score,
            "is_fallback": is_fallback,
            "risk_distribution": risk_levels,
            "adaptations_count": adapted_count,
            "total_communes": len(TEST_COMMUNES),
            "green_vigilance_allows_low_risk": vigilance_level == "vert" and risk_levels.get("faible", 0) > 0
        }
        
        print(f"\n🎯 CONCLUSION:")
        if success_count == len(TEST_COMMUNES):
            print("✅ Tous les tests ont réussi")
            if vigilance_level == "vert" and risk_levels.get("faible", 0) > 0:
                print("✅ La logique vigilance verte → risque faible fonctionne correctement")
            elif vigilance_level == "vert":
                print("⚠️ Vigilance verte détectée mais pas de risque faible - à investiguer")
            else:
                print(f"ℹ️ Vigilance {vigilance_level} - comportement normal")
        else:
            print(f"❌ {len(TEST_COMMUNES) - success_count} test(s) ont échoué")

async def main():
    """Fonction principale"""
    analyzer = CycloneVigilanceAnalyzer()
    
    try:
        success = await analyzer.run_complete_analysis()
        return 0 if success else 1
    finally:
        await analyzer.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)