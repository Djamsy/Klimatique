#!/usr/bin/env python3
"""
Test complémentaire pour analyser le comportement de l'IA avec différentes conditions météo
et vérifier l'adaptation selon la vigilance
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime

BACKEND_URL = "https://6c0658c1-f5e4-4a08-98c7-406d205120ea.preview.emergentagent.com/api"
TIMEOUT = 30.0

class WeatherScenarioTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.results = []
    
    async def close(self):
        await self.client.aclose()
    
    async def test_multiple_scenarios(self):
        """Test plusieurs scénarios pour comprendre le comportement de l'IA"""
        print("🧪 TEST SCÉNARIOS MULTIPLES - COMPORTEMENT IA")
        print("=" * 60)
        
        communes = ["Pointe-à-Pitre", "Basse-Terre", "Sainte-Anne"]
        
        # Test plusieurs fois pour voir la variabilité
        for i in range(3):
            print(f"\n🔄 SÉRIE DE TESTS #{i+1}")
            print("-" * 40)
            
            for commune in communes:
                await self.test_commune_scenario(commune, i+1)
        
        # Analyser les résultats
        await self.analyze_results()
    
    async def test_commune_scenario(self, commune: str, series: int):
        """Test un scénario pour une commune"""
        try:
            # Test prédiction normale
            url = f"{BACKEND_URL}/ai/cyclone/predict/{commune}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Test debug pour voir l'adaptation
                debug_url = f"{BACKEND_URL}/ai/test/{commune}"
                debug_response = await self.client.get(debug_url)
                debug_data = debug_response.json() if debug_response.status_code == 200 else {}
                
                result = {
                    "series": series,
                    "commune": commune,
                    "risk_level": data.get("risk_level"),
                    "risk_score": data.get("risk_score"),
                    "confidence": data.get("confidence"),
                    "weather": data.get("weather_context", {}),
                    "debug_original_risk": debug_data.get("original_risk"),
                    "debug_adapted_risk": debug_data.get("adapted_risk"),
                    "vigilance_level": debug_data.get("vigilance_level"),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.results.append(result)
                
                print(f"   {commune}: {data.get('risk_level')} (score: {data.get('risk_score')}) - Vent: {data.get('weather_context', {}).get('wind_speed', 'N/A'):.1f} km/h")
            
        except Exception as e:
            print(f"   ❌ Erreur {commune}: {str(e)}")
    
    async def analyze_results(self):
        """Analyse les résultats collectés"""
        print(f"\n📊 ANALYSE DES RÉSULTATS ({len(self.results)} tests)")
        print("=" * 60)
        
        # Grouper par commune
        by_commune = {}
        for result in self.results:
            commune = result["commune"]
            if commune not in by_commune:
                by_commune[commune] = []
            by_commune[commune].append(result)
        
        # Analyser chaque commune
        for commune, results in by_commune.items():
            print(f"\n🏘️ {commune}:")
            
            risk_levels = [r["risk_level"] for r in results]
            risk_scores = [r["risk_score"] for r in results if r["risk_score"]]
            wind_speeds = [r["weather"]["wind_speed"] for r in results if r["weather"].get("wind_speed")]
            
            print(f"   • Niveaux de risque: {', '.join(risk_levels)}")
            if risk_scores:
                print(f"   • Scores de risque: {min(risk_scores):.1f} - {max(risk_scores):.1f}")
            if wind_speeds:
                print(f"   • Vitesses vent: {min(wind_speeds):.1f} - {max(wind_speeds):.1f} km/h")
            
            # Vérifier la cohérence
            unique_risks = set(risk_levels)
            if len(unique_risks) == 1:
                print(f"   ✅ Cohérent: toujours '{list(unique_risks)[0]}'")
            else:
                print(f"   🔄 Variable: {len(unique_risks)} niveaux différents")
        
        # Vérifier l'adaptation vigilance
        adaptations = [r for r in self.results if r.get("debug_original_risk") and r.get("debug_adapted_risk")]
        if adaptations:
            print(f"\n🔄 ADAPTATIONS VIGILANCE:")
            adapted_count = len([a for a in adaptations if a["debug_original_risk"] != a["debug_adapted_risk"]])
            print(f"   • Adaptations effectuées: {adapted_count}/{len(adaptations)}")
            
            vigilance_levels = set([a["vigilance_level"] for a in adaptations if a.get("vigilance_level")])
            print(f"   • Niveaux vigilance observés: {', '.join(vigilance_levels)}")
        
        # Sauvegarder
        with open("/app/weather_scenarios_analysis.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Résultats sauvegardés: /app/weather_scenarios_analysis.json")

async def main():
    tester = WeatherScenarioTester()
    try:
        await tester.test_multiple_scenarios()
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())