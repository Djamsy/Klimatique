import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class CycloneDamagePredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = '/app/backend/ai_models/cyclone_model.joblib'
        self.scaler_path = '/app/backend/ai_models/scaler.joblib'
        
        # Facteurs de risque par type de commune
        self.commune_vulnerability = {
            'urbaine': {'infrastructure': 0.8, 'population': 1.0, 'economic': 0.9},
            'côtière': {'infrastructure': 0.9, 'population': 0.7, 'economic': 0.8},
            'montagne': {'infrastructure': 0.6, 'population': 0.5, 'economic': 0.6},
            'rurale': {'infrastructure': 0.5, 'population': 0.4, 'economic': 0.5},
            'insulaire': {'infrastructure': 0.7, 'population': 0.6, 'economic': 0.4}
        }
        
        # Charger le modèle si il existe
        self._load_model()
    
    def generate_training_data(self, n_samples=5000):
        """Génère des données d'entraînement basées sur des cyclones historiques réalistes"""
        logger.info("Generating realistic training data based on Caribbean cyclone patterns")
        
        # Cyclones historiques Antilles (données simplifiées mais réalistes)
        historical_patterns = [
            # Hugo 1989 - Catégorie 4
            {'wind_speed': 250, 'pressure': 920, 'damage_infrastructure': 90, 'damage_agriculture': 85, 'damage_population': 30},
            # Marilyn 1995 - Catégorie 2
            {'wind_speed': 165, 'pressure': 960, 'damage_infrastructure': 65, 'damage_agriculture': 70, 'damage_population': 15},
            # Irma 2017 - Catégorie 5
            {'wind_speed': 295, 'pressure': 914, 'damage_infrastructure': 95, 'damage_agriculture': 90, 'damage_population': 35},
            # Maria 2017 - Catégorie 5  
            {'wind_speed': 280, 'pressure': 908, 'damage_infrastructure': 90, 'damage_agriculture': 95, 'damage_population': 40},
            # Fiona 2022 - Catégorie 1-2
            {'wind_speed': 130, 'pressure': 980, 'damage_infrastructure': 45, 'damage_agriculture': 60, 'damage_population': 8}
        ]
        
        data = []
        
        for i in range(n_samples):
            # Sélection pattern aléatoire avec variations
            pattern = np.random.choice(historical_patterns)
            
            # Variables météorologiques avec variations réalistes
            wind_speed = max(80, pattern['wind_speed'] + np.random.normal(0, 30))  # km/h
            pressure = max(950, pattern['pressure'] + np.random.normal(0, 15))    # hPa
            temperature = np.random.normal(28, 3)  # °C
            humidity = np.random.uniform(75, 98)   # %
            precipitation = np.random.exponential(25) # mm/h
            
            # Topographie (0=plaine, 1=colline, 2=montagne)
            topography = np.random.choice([0, 1, 2], p=[0.4, 0.4, 0.2])
            
            # Type de commune
            commune_type = np.random.choice(['urbaine', 'côtière', 'montagne', 'rurale', 'insulaire'], 
                                          p=[0.25, 0.3, 0.2, 0.2, 0.05])
            
            # Densité population (habitants/km²)
            if commune_type == 'urbaine':
                population_density = np.random.normal(2000, 500)
            elif commune_type == 'côtière':
                population_density = np.random.normal(800, 300)
            else:
                population_density = np.random.normal(150, 100)
            
            population_density = max(50, population_density)
            
            # Distance côte (km)
            if commune_type == 'côtière':
                distance_coast = np.random.uniform(0, 2)
            elif commune_type == 'insulaire':
                distance_coast = 0
            else:
                distance_coast = np.random.uniform(1, 15)
            
            # Variables infrastructure
            building_age = np.random.uniform(10, 80)  # années
            building_quality = np.random.uniform(0.3, 1.0)  # 0-1
            
            # Vulnérabilité selon type
            vuln = self.commune_vulnerability[commune_type]
            
            # Calcul dégâts (% destruction)
            # Formule basée sur échelle Saffir-Simpson modifiée
            wind_factor = min(1.0, (wind_speed - 80) / 200)  # Normalisation
            pressure_factor = max(0, (1000 - pressure) / 100)
            
            base_damage_infra = (
                wind_factor * 0.6 + 
                pressure_factor * 0.3 + 
                (1/building_quality) * 0.1
            ) * vuln['infrastructure'] * 100
            
            base_damage_agri = (
                wind_factor * 0.7 + 
                (precipitation / 50) * 0.2 + 
                pressure_factor * 0.1
            ) * 100
            
            # Ajustements selon topographie
            if topography == 2:  # montagne
                base_damage_infra *= 0.8  # Plus protégé
                base_damage_agri *= 1.2   # Plus exposé aux glissements
            elif topography == 0:  # plaine côtière
                base_damage_infra *= 1.1  # Plus exposé
            
            # Distance côte impact
            coast_factor = max(0.5, 1 - (distance_coast / 20))
            base_damage_infra *= coast_factor
            
            # Normalisation et bruit réaliste
            damage_infrastructure = np.clip(base_damage_infra + np.random.normal(0, 10), 0, 100)
            damage_agriculture = np.clip(base_damage_agri + np.random.normal(0, 15), 0, 100)
            
            # Dégâts population (corrélés mais plus faibles)
            damage_population = np.clip(
                (damage_infrastructure * 0.3 + np.random.normal(0, 5)) * vuln['population'], 
                0, 50
            )
            
            # Encodage catégoriel
            commune_encoded = self._encode_commune_type(commune_type)
            
            data.append([
                wind_speed, pressure, temperature, humidity, precipitation,
                topography, population_density, distance_coast,
                building_age, building_quality, *commune_encoded,
                damage_infrastructure, damage_agriculture, damage_population
            ])
        
        columns = [
            'wind_speed', 'pressure', 'temperature', 'humidity', 'precipitation',
            'topography', 'population_density', 'distance_coast', 
            'building_age', 'building_quality',
            'commune_urbaine', 'commune_cotiere', 'commune_montagne', 'commune_rurale', 'commune_insulaire',
            'damage_infrastructure', 'damage_agriculture', 'damage_population'
        ]
        
        df = pd.DataFrame(data, columns=columns)
        logger.info(f"Generated {len(df)} training samples with realistic damage patterns")
        
        return df
    
    def _encode_commune_type(self, commune_type):
        """One-hot encoding pour type de commune"""
        encoding = [0, 0, 0, 0, 0]  # urbaine, côtière, montagne, rurale, insulaire
        
        type_map = {
            'urbaine': 0, 'côtière': 1, 'montagne': 2, 'rurale': 3, 'insulaire': 4
        }
        
        if commune_type in type_map:
            encoding[type_map[commune_type]] = 1
        
        return encoding
    
    def train_model(self, retrain=False):
        """Entraîne le modèle IA de prédiction cyclonique"""
        if self.is_trained and not retrain:
            logger.info("Model already trained and loaded")
            return
            
        logger.info("Training cyclone damage prediction AI model...")
        
        # Génération données d'entraînement
        df = self.generate_training_data(n_samples=8000)
        
        # Features et targets
        feature_columns = [
            'wind_speed', 'pressure', 'temperature', 'humidity', 'precipitation',
            'topography', 'population_density', 'distance_coast', 
            'building_age', 'building_quality',
            'commune_urbaine', 'commune_cotiere', 'commune_montagne', 'commune_rurale', 'commune_insulaire'
        ]
        
        target_columns = ['damage_infrastructure', 'damage_agriculture', 'damage_population']
        
        X = df[feature_columns]
        y = df[target_columns]
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Normalisation
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Modèle Random Forest (performant pour ce type de problème)
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        # Entraînement
        logger.info("Training Random Forest model...")
        self.model.fit(X_train_scaled, y_train)
        
        # Évaluation
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        logger.info(f"Model training completed:")
        logger.info(f"Training R² score: {train_score:.3f}")
        logger.info(f"Test R² score: {test_score:.3f}")
        
        # Sauvegarde
        self._save_model()
        self.is_trained = True
        
        return {
            'train_score': train_score,
            'test_score': test_score,
            'feature_importance': dict(zip(feature_columns, self.model.feature_importances_))
        }
    
    def predict_damage(self, weather_data, commune_info):
        """Prédit les dégâts cycloniques pour une commune"""
        if not self.is_trained:
            logger.warning("Model not trained, training now...")
            self.train_model()
        
        try:
            # Calcul du score de risque amélioré
            enhanced_risk_score, risk_factors = self._calculate_enhanced_risk_score(weather_data, commune_info)
            
            # Préparation features pour le modèle ML
            features = self._prepare_features(weather_data, commune_info)
            
            # Prédiction ML
            features_scaled = self.scaler.transform([features])
            predictions = self.model.predict(features_scaled)[0]
            
            # Post-traitement des prédictions
            base_damage_infrastructure = max(0, min(100, predictions[0]))
            base_damage_agriculture = max(0, min(100, predictions[1])) 
            base_damage_population = max(0, min(50, predictions[2]))
            
            # Ajustement avec le score de risque météorologique
            weather_factor = enhanced_risk_score / 100
            
            damage_infrastructure = min(100, base_damage_infrastructure * (1 + weather_factor * 0.3))
            damage_agriculture = min(100, base_damage_agriculture * (1 + weather_factor * 0.2))
            damage_population = min(50, base_damage_population * (1 + weather_factor * 0.4))
            
            # Calcul niveau de risque basé sur le score amélioré
            final_risk_score = max(enhanced_risk_score, 
                                 (damage_infrastructure * 0.4 + 
                                  damage_agriculture * 0.3 + 
                                  damage_population * 0.3))
            
            risk_level = self._calculate_risk_level(final_risk_score)
            
            # Génération recommandations améliorées
            recommendations = self._generate_enhanced_recommendations(
                damage_infrastructure, damage_agriculture, damage_population, 
                commune_info, weather_data, risk_factors
            )
            
            result = {
                'damage_predictions': {
                    'infrastructure': round(damage_infrastructure, 1),
                    'agriculture': round(damage_agriculture, 1),
                    'population_impact': round(damage_population, 1)
                },
                'risk_level': risk_level,
                'risk_score': round(final_risk_score, 1),
                'confidence': self._calculate_confidence(features, weather_data),
                'recommendations': recommendations,
                'weather_risk_factors': risk_factors,
                'enhanced_analysis': {
                    'weather_risk_score': enhanced_risk_score,
                    'ml_predictions': {
                        'infrastructure': round(base_damage_infrastructure, 1),
                        'agriculture': round(base_damage_agriculture, 1),
                        'population': round(base_damage_population, 1)
                    },
                    'weather_adjustment': round(weather_factor * 100, 1)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting damage: {e}")
            return self._generate_fallback_prediction(weather_data, commune_info)
    
    def predict_timeline_damage(self, weather_timeline, commune_info):
        """Prédit l'évolution des dégâts dans le temps (H+6, H+12, H+24)"""
        timeline_predictions = {}
        
        for time_key, weather_data in weather_timeline.items():
            prediction = self.predict_damage(weather_data, commune_info)
            timeline_predictions[time_key] = prediction
        
        return timeline_predictions
    
    def _prepare_features(self, weather_data, commune_info):
        """Prépare les features pour la prédiction"""
        # Données météo
        wind_speed = weather_data.get('wind_speed', 120)  # km/h
        pressure = weather_data.get('pressure', 980)      # hPa
        temperature = weather_data.get('temperature', 28) # °C
        humidity = weather_data.get('humidity', 85)       # %
        precipitation = weather_data.get('precipitation', 10) # mm/h
        
        # Données commune
        commune_type = commune_info.get('type', 'urbaine')
        population = commune_info.get('population', 10000)
        coordinates = commune_info.get('coordinates', [16.25, -61.55])
        
        # Calculs dérivés
        population_density = self._estimate_population_density(population, commune_type)
        distance_coast = self._estimate_distance_coast(coordinates, commune_type)
        topography = self._estimate_topography(coordinates, commune_type)
        
        # Valeurs par défaut infrastructure
        building_age = 35  # Moyenne Guadeloupe
        building_quality = 0.6  # Qualité moyenne
        
        # Encodage type commune
        commune_encoded = self._encode_commune_type(commune_type)
        
        features = [
            wind_speed, pressure, temperature, humidity, precipitation,
            topography, population_density, distance_coast,
            building_age, building_quality, *commune_encoded
        ]
        
        return features
    
    def _estimate_population_density(self, population, commune_type):
        """Estime la densité de population"""
        # Surface moyenne par type (km²)
        surface_estimates = {
            'urbaine': 15, 'côtière': 25, 'montagne': 40, 'rurale': 60, 'insulaire': 20
        }
        
        pop_num = float(population.replace(',', '').replace('k', '000')) if isinstance(population, str) else population
        surface = surface_estimates.get(commune_type, 30)
        
        return pop_num / surface
    
    def _estimate_distance_coast(self, coordinates, commune_type):
        """Estime la distance à la côte"""
        if commune_type in ['côtière', 'insulaire']:
            return np.random.uniform(0, 2)
        elif commune_type == 'urbaine':
            return np.random.uniform(1, 5)
        else:
            return np.random.uniform(3, 15)
    
    def _estimate_topography(self, coordinates, commune_type):
        """Estime la topographie (0=plaine, 1=colline, 2=montagne)"""
        if commune_type == 'montagne':
            return 2
        elif commune_type in ['côtière', 'insulaire']:
            return 0
        else:
            return 1
    
    def _calculate_enhanced_risk_score(self, weather_data, commune_info):
        """Calcule un score de risque amélioré basé sur les conditions météorologiques réelles"""
        
        # Données météorologiques
        wind_speed = weather_data.get('wind_speed', 0)
        pressure = weather_data.get('pressure', 1013)
        temperature = weather_data.get('temperature', 25)
        humidity = weather_data.get('humidity', 75)
        precipitation = weather_data.get('precipitation', 0)
        
        risk_score = 0
        risk_factors = []
        
        # 1. Analyse vitesse du vent (facteur principal)
        if wind_speed > 200:  # Ouragan majeur
            risk_score += 40
            risk_factors.append(f"Vents extrêmes: {wind_speed:.0f} km/h")
        elif wind_speed > 150:  # Ouragan
            risk_score += 30
            risk_factors.append(f"Vents d'ouragan: {wind_speed:.0f} km/h")
        elif wind_speed > 88:  # Tempête tropicale
            risk_score += 20
            risk_factors.append(f"Tempête tropicale: {wind_speed:.0f} km/h")
        elif wind_speed > 62:  # Vents forts
            risk_score += 10
            risk_factors.append(f"Vents forts: {wind_speed:.0f} km/h")
        
        # 2. Analyse pression atmosphérique
        if pressure < 950:  # Dépression très intense
            risk_score += 25
            risk_factors.append(f"Pression très basse: {pressure:.0f} hPa")
        elif pressure < 980:  # Dépression intense
            risk_score += 15
            risk_factors.append(f"Pression basse: {pressure:.0f} hPa")
        elif pressure < 1000:  # Dépression modérée
            risk_score += 5
            risk_factors.append(f"Pression sous normale: {pressure:.0f} hPa")
        
        # 3. Analyse température (cyclogenèse tropicale)
        if temperature > 29 and humidity > 85:  # Conditions très favorables
            risk_score += 15
            risk_factors.append(f"Conditions cyclogenèse: {temperature:.0f}°C, {humidity}% humidité")
        elif temperature > 27 and humidity > 80:  # Conditions favorables
            risk_score += 8
            risk_factors.append(f"Conditions favorables développement: {temperature:.0f}°C")
        elif temperature > 32:  # Chaleur extrême
            risk_score += 5
            risk_factors.append(f"Chaleur extrême: {temperature:.0f}°C")
        
        # 4. Analyse humidité
        if humidity > 90:
            risk_score += 8
            risk_factors.append(f"Humidité très élevée: {humidity}%")
        elif humidity > 85:
            risk_score += 5
            risk_factors.append(f"Humidité élevée: {humidity}%")
        
        # 5. Analyse précipitations
        if precipitation > 50:  # Pluies torrentielles
            risk_score += 15
            risk_factors.append(f"Pluies torrentielles: {precipitation:.0f} mm/h")
        elif precipitation > 25:  # Fortes pluies
            risk_score += 10
            risk_factors.append(f"Fortes pluies: {precipitation:.0f} mm/h")
        elif precipitation > 10:  # Pluies modérées
            risk_score += 5
            risk_factors.append(f"Pluies modérées: {precipitation:.0f} mm/h")
        
        # 6. Facteurs géographiques de la commune
        commune_type = commune_info.get('type', 'urbaine')
        if commune_type == 'côtière':
            risk_score += 8
            risk_factors.append("Zone côtière exposée")
        elif commune_type == 'insulaire':
            risk_score += 12
            risk_factors.append("Île isolée - évacuation difficile")
        elif commune_type == 'urbaine':
            risk_score += 5
            risk_factors.append("Zone urbaine dense")
        
        # 7. Analyse combinée (conditions synergiques)
        if wind_speed > 100 and pressure < 990 and precipitation > 20:
            risk_score += 10
            risk_factors.append("Conditions synergiques critiques")
        
        if temperature > 28 and humidity > 85 and wind_speed > 60:
            risk_score += 8
            risk_factors.append("Renforcement cyclonique possible")
        
        # Normalisation du score (0-100)
        risk_score = min(100, max(0, risk_score))
        
        return risk_score, risk_factors
    
    def _calculate_confidence(self, features, weather_data):
        """Calcule le niveau de confiance de la prédiction"""
        # Confiance basée sur la proximité aux données d'entraînement
        wind_speed = weather_data.get('wind_speed', 120)
        
        if 80 <= wind_speed <= 300:  # Plage d'entraînement
            return min(95, 70 + (25 * (250 - abs(wind_speed - 165)) / 165))
        else:
            return 60  # Confiance réduite hors plage
    
    def _calculate_risk_level(self, risk_score):
        """Calcule le niveau de risque basé sur le score - adapté aux conditions normales"""
        # Seuils ajustés pour les conditions météo normales (non-cycloniques)
        if risk_score >= 45:  # Était 80
            return 'critique'
        elif risk_score >= 25:  # Était 60
            return 'élevé'
        elif risk_score >= 10:  # Était 30
            return 'modéré'
        else:
            return 'faible'
    
    def _generate_enhanced_recommendations(self, damage_infra, damage_agri, damage_pop, commune_info, weather_data, risk_factors):
        """Génère des recommandations améliorées basées sur les conditions météorologiques"""
        recommendations = []
        commune_type = commune_info.get('type', 'urbaine')
        
        # Données météo
        wind_speed = weather_data.get('wind_speed', 0)
        pressure = weather_data.get('pressure', 1013)
        temperature = weather_data.get('temperature', 25)
        humidity = weather_data.get('humidity', 75)
        precipitation = weather_data.get('precipitation', 0)
        
        # Recommandations selon l'intensité du vent
        if wind_speed > 200:
            recommendations.extend([
                "🚨 ÉVACUATION IMMÉDIATE OBLIGATOIRE",
                "Fermeture totale des services et commerces",
                "Confinement en abri renforcé uniquement"
            ])
        elif wind_speed > 150:
            recommendations.extend([
                "⚠️ Évacuation préventive recommandée",
                "Éviter tout déplacement extérieur",
                "Sécuriser portes et fenêtres"
            ])
        elif wind_speed > 88:
            recommendations.extend([
                "Préparer un plan d'évacuation",
                "Éviter les zones exposées au vent",
                "Vérifier les amarrages et fixations"
            ])
        
        # Recommandations selon la pression
        if pressure < 950:
            recommendations.append("Surveillance météo continue - système très actif")
        elif pressure < 980:
            recommendations.append("Conditions météo dégradées - restez vigilants")
        
        # Recommandations selon température et humidité
        if temperature > 29 and humidity > 85:
            recommendations.extend([
                "Conditions favorables au renforcement cyclonique",
                "Préparer 72h d'autonomie (eau, nourriture, médicaments)"
            ])
        elif temperature > 32:
            recommendations.extend([
                "Chaleur extrême - hydratation renforcée",
                "Éviter efforts physiques aux heures chaudes"
            ])
        
        # Recommandations selon les précipitations
        if precipitation > 50:
            recommendations.extend([
                "🌊 RISQUE INONDATION MAJEUR",
                "Évacuer les zones basses et cours d'eau",
                "Couper électricité/gaz dans zones inondables"
            ])
        elif precipitation > 25:
            recommendations.extend([
                "Risque d'inondation - éviter déplacements",
                "Surveiller montée des eaux",
                "Préparer kit d'urgence étanche"
            ])
        
        # Recommandations spécifiques par type de commune
        if commune_type == 'côtière':
            if wind_speed > 100 or damage_infra > 50:
                recommendations.extend([
                    "🌊 Risque submersion marine - évacuer le littoral",
                    "Surveiller coefficient de marée",
                    "Éloigner véhicules de la côte"
                ])
        elif commune_type == 'insulaire':
            if damage_pop > 20 or wind_speed > 120:
                recommendations.extend([
                    "🚁 Coordination évacuation inter-îles urgente",
                    "Vérifier liaisons de communication",
                    "Stocks d'urgence pour isolement prolongé"
                ])
        elif commune_type == 'montagne':
            if precipitation > 30:
                recommendations.extend([
                    "⛰️ Vigilance glissements de terrain",
                    "Éviter routes de montagne",
                    "Surveiller stabilité des pentes"
                ])
        elif commune_type == 'urbaine':
            if wind_speed > 80:
                recommendations.extend([
                    "🏙️ Attention chutes d'objets urbains",
                    "Éviter centres-villes et parkings",
                    "Vérifier réseaux eau/électricité"
                ])
        
        # Recommandations selon dégâts prévus
        if damage_infra > 80:
            recommendations.extend([
                "🏠 Infrastructure critique - évacuation massive",
                "Activation cellule de crise préfectorale",
                "Préparer relogement d'urgence"
            ])
        elif damage_infra > 50:
            recommendations.extend([
                "Renforcement préventif des structures",
                "Vérification installations électriques",
                "Plan de continuité d'activité"
            ])
        
        if damage_agri > 70:
            recommendations.extend([
                "🌾 Protection urgente du bétail",
                "Récolte anticipée si possible",
                "Sécuriser équipements agricoles"
            ])
        
        if damage_pop > 30:
            recommendations.extend([
                "👥 Mise en place cellule psychologique",
                "Renforcement services de secours",
                "Communication d'urgence aux familles"
            ])
        
        # Recommandations générales de préparation
        if len([r for r in risk_factors if 'favorables' in r or 'cyclogenèse' in r]) > 0:
            recommendations.extend([
                "📱 Vérifier moyens de communication",
                "⚡ Charger appareils électroniques",
                "💊 Préparer trousse de premiers secours"
            ])
        
        # Recommandations selon conditions synergiques
        if "Conditions synergiques critiques" in risk_factors:
            recommendations.extend([
                "🔴 ALERTE MAXIMALE - Conditions exceptionnelles",
                "Suivre uniquement consignes officielles",
                "Éviter toute prise de risque"
            ])
        
        # Limiter à 8 recommandations les plus pertinentes
        return recommendations[:8]
    
    def _generate_fallback_prediction(self, weather_data, commune_info):
        """Génère une prédiction de fallback en cas d'erreur"""
        wind_speed = weather_data.get('wind_speed', 120)
        
        # Prédiction simple basée sur vitesse vent
        if wind_speed > 200:
            risk_level = 'critique'
            damage_infra = 80
        elif wind_speed > 150:
            risk_level = 'élevé'  
            damage_infra = 60
        elif wind_speed > 100:
            risk_level = 'modéré'
            damage_infra = 35
        else:
            risk_level = 'faible'
            damage_infra = 15
        
        return {
            'damage_predictions': {
                'infrastructure': damage_infra,
                'agriculture': min(100, damage_infra * 1.2),
                'population_impact': max(5, damage_infra * 0.3)
            },
            'risk_level': risk_level,
            'risk_score': damage_infra,
            'confidence': 60,
            'recommendations': ["Suivre les consignes préfectorales", "Préparer kit d'urgence"]
        }
    
    def _save_model(self):
        """Sauvegarde le modèle entraîné"""
        try:
            os.makedirs('/app/backend/ai_models', exist_ok=True)
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Model and scaler saved successfully")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def _load_model(self):
        """Charge le modèle pré-entraîné"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                logger.info("Pre-trained model loaded successfully")
            else:
                logger.info("No pre-trained model found, will train on first use")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.is_trained = False
    
    def get_model_info(self):
        """Retourne les informations du modèle"""
        return {
            'is_trained': self.is_trained,
            'model_type': 'Random Forest Regressor',
            'features': 15,
            'targets': ['Infrastructure', 'Agriculture', 'Population'],
            'training_samples': 8000,
            'last_trained': datetime.now().isoformat() if self.is_trained else None
        }

# Instance globale
cyclone_predictor = CycloneDamagePredictor()