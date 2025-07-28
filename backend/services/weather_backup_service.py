import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class WeatherBackupService:
    def __init__(self, db):
        self.db = db
        self.backup_dir = Path('/app/backend/data/weather_backup')
        self.backup_dir.mkdir(exist_ok=True)
        
        # Données de backup pré-générées pour chaque commune
        self.communes_backup = {
            'Pointe-à-Pitre': {
                'coordinates': [16.24, -61.53],
                'type': 'urbaine',
                'weather_patterns': {
                    'normal': {'temp': 28, 'humidity': 75, 'wind': 15, 'pressure': 1013},
                    'rainy': {'temp': 26, 'humidity': 85, 'wind': 20, 'pressure': 1008},
                    'dry': {'temp': 30, 'humidity': 65, 'wind': 12, 'pressure': 1015}
                }
            },
            'Basse-Terre': {
                'coordinates': [15.99, -61.73],
                'type': 'montagne',
                'weather_patterns': {
                    'normal': {'temp': 26, 'humidity': 80, 'wind': 12, 'pressure': 1010},
                    'rainy': {'temp': 24, 'humidity': 90, 'wind': 18, 'pressure': 1005},
                    'dry': {'temp': 28, 'humidity': 70, 'wind': 10, 'pressure': 1014}
                }
            },
            'Sainte-Anne': {
                'coordinates': [16.23, -61.38],
                'type': 'côtière',
                'weather_patterns': {
                    'normal': {'temp': 29, 'humidity': 78, 'wind': 18, 'pressure': 1012},
                    'rainy': {'temp': 27, 'humidity': 88, 'wind': 22, 'pressure': 1007},
                    'dry': {'temp': 31, 'humidity': 68, 'wind': 15, 'pressure': 1016}
                }
            },
            'Les Abymes': {
                'coordinates': [16.27, -61.51],
                'type': 'urbaine',
                'weather_patterns': {
                    'normal': {'temp': 28, 'humidity': 76, 'wind': 16, 'pressure': 1013},
                    'rainy': {'temp': 26, 'humidity': 86, 'wind': 21, 'pressure': 1008},
                    'dry': {'temp': 30, 'humidity': 66, 'pressure': 1015}
                }
            },
            'Baie-Mahault': {
                'coordinates': [16.27, -61.59],
                'type': 'urbaine',
                'weather_patterns': {
                    'normal': {'temp': 28, 'humidity': 77, 'wind': 17, 'pressure': 1012},
                    'rainy': {'temp': 26, 'humidity': 87, 'wind': 22, 'pressure': 1007},
                    'dry': {'temp': 30, 'humidity': 67, 'wind': 14, 'pressure': 1015}
                }
            },
            'Le Gosier': {
                'coordinates': [16.21, -61.50],
                'type': 'côtière',
                'weather_patterns': {
                    'normal': {'temp': 29, 'humidity': 79, 'wind': 19, 'pressure': 1012},
                    'rainy': {'temp': 27, 'humidity': 89, 'wind': 23, 'pressure': 1006},
                    'dry': {'temp': 31, 'humidity': 69, 'wind': 16, 'pressure': 1016}
                }
            }
        }
    
    async def store_weather_backup(self, commune: str, weather_data: Dict) -> bool:
        """Stocke une sauvegarde des données météo en MongoDB"""
        try:
            backup_data = {
                'commune': commune,
                'weather_data': weather_data,
                'timestamp': datetime.now(),
                'type': 'api_success'
            }
            
            # Insérer en base avec expiration après 24h
            await self.db.weather_backup.insert_one(backup_data)
            
            # Nettoyer les anciennes sauvegardes (garder seulement les 10 dernières)
            old_backups = await self.db.weather_backup.find({
                'commune': commune
            }).sort('timestamp', -1).skip(10).to_list(length=None)
            
            for backup in old_backups:
                await self.db.weather_backup.delete_one({'_id': backup['_id']})
            
            logger.info(f"Weather backup stored for {commune}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing weather backup for {commune}: {e}")
            return False
    
    async def get_latest_backup(self, commune: str) -> Optional[Dict]:
        """Récupère la dernière sauvegarde météo pour une commune"""
        try:
            # Chercher la dernière sauvegarde de moins de 24h
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            backup = await self.db.weather_backup.find_one({
                'commune': commune,
                'timestamp': {'$gte': cutoff_time}
            }, sort=[('timestamp', -1)])
            
            if backup:
                logger.info(f"Latest backup found for {commune}")
                return backup['weather_data']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest backup for {commune}: {e}")
            return None
    
    def generate_realistic_backup_weather(self, commune: str) -> Dict:
        """Génère des données météo réalistes de backup pour une commune"""
        try:
            commune_data = self.communes_backup.get(commune)
            if not commune_data:
                # Utiliser Pointe-à-Pitre comme défaut
                commune_data = self.communes_backup['Pointe-à-Pitre']
            
            # Sélectionner un pattern météo selon l'heure
            current_hour = datetime.now().hour
            if 6 <= current_hour <= 11:  # Matin
                pattern = 'normal'
            elif 12 <= current_hour <= 17:  # Après-midi
                pattern = 'normal' if current_hour % 2 == 0 else 'dry'
            else:  # Soir/nuit
                pattern = 'normal' if current_hour % 3 != 0 else 'rainy'
            
            base_weather = commune_data['weather_patterns'][pattern]
            
            # Ajouter de la variabilité réaliste
            import random
            
            weather_data = {
                'temperature': base_weather['temp'] + random.uniform(-2, 2),
                'humidity': max(50, min(95, base_weather['humidity'] + random.randint(-5, 5))),
                'wind_speed': max(5, base_weather['wind'] + random.uniform(-3, 5)),
                'pressure': base_weather['pressure'] + random.uniform(-5, 5),
                'precipitation': max(0, random.exponential(1) if pattern == 'rainy' else random.exponential(0.3)),
                'weather_description': self._get_weather_description(pattern),
                'weather_icon': self._get_weather_icon(pattern),
                'source': 'backup_generated',
                'commune': commune,
                'coordinates': commune_data['coordinates'],
                'timestamp': datetime.now().isoformat(),
                'is_backup': True
            }
            
            logger.info(f"Generated realistic backup weather for {commune}")
            return weather_data
            
        except Exception as e:
            logger.error(f"Error generating backup weather for {commune}: {e}")
            return self._get_emergency_fallback(commune)
    
    def _get_weather_description(self, pattern: str) -> str:
        """Retourne une description météo selon le pattern"""
        descriptions = {
            'normal': ['Partiellement nuageux', 'Nuages épars', 'Beau temps'],
            'rainy': ['Averses éparses', 'Pluie légère', 'Couvert avec pluie'],
            'dry': ['Ensoleillé', 'Ciel dégagé', 'Beau temps sec']
        }
        
        import random
        return random.choice(descriptions.get(pattern, descriptions['normal']))
    
    def _get_weather_icon(self, pattern: str) -> str:
        """Retourne une icône météo selon le pattern"""
        icons = {
            'normal': '02d',  # Partiellement nuageux
            'rainy': '10d',   # Pluie
            'dry': '01d'      # Ciel dégagé
        }
        return icons.get(pattern, '02d')
    
    def _get_emergency_fallback(self, commune: str) -> Dict:
        """Données d'urgence ultra-basiques"""
        return {
            'temperature': 28,
            'humidity': 75,
            'wind_speed': 15,
            'pressure': 1013,
            'precipitation': 0,
            'weather_description': 'Conditions tropicales normales',
            'weather_icon': '02d',
            'source': 'emergency_fallback',
            'commune': commune,
            'coordinates': [16.25, -61.55],  # Coordonnées Guadeloupe centre
            'timestamp': datetime.now().isoformat(),
            'is_backup': True,
            'is_emergency': True
        }
    
    async def get_backup_weather_with_fallback(self, commune: str) -> Dict:
        """
        Système complet de backup météo avec plusieurs niveaux de fallback:
        1. Dernière sauvegarde API (< 24h)
        2. Données réalistes générées
        3. Fallback d'urgence
        """
        try:
            # Niveau 1: Dernière sauvegarde API
            latest_backup = await self.get_latest_backup(commune)
            if latest_backup:
                latest_backup['source'] = 'backup_recent'
                latest_backup['is_backup'] = True
                return latest_backup
            
            # Niveau 2: Données réalistes générées
            realistic_data = self.generate_realistic_backup_weather(commune)
            return realistic_data
            
        except Exception as e:
            logger.error(f"Error in backup weather system for {commune}: {e}")
            # Niveau 3: Fallback d'urgence
            return self._get_emergency_fallback(commune)
    
    async def test_backup_system(self) -> Dict:
        """Teste le système de backup pour toutes les communes"""
        results = {
            'total_communes': 0,
            'successful_backups': 0,
            'failed_backups': 0,
            'commune_results': {}
        }
        
        for commune in self.communes_backup.keys():
            results['total_communes'] += 1
            
            try:
                backup_data = await self.get_backup_weather_with_fallback(commune)
                
                if backup_data and 'temperature' in backup_data:
                    results['successful_backups'] += 1
                    results['commune_results'][commune] = {
                        'status': 'success',
                        'source': backup_data.get('source', 'unknown'),
                        'temperature': backup_data.get('temperature'),
                        'timestamp': backup_data.get('timestamp')
                    }
                else:
                    results['failed_backups'] += 1
                    results['commune_results'][commune] = {
                        'status': 'failed',
                        'error': 'No valid data returned'
                    }
                    
            except Exception as e:
                results['failed_backups'] += 1
                results['commune_results'][commune] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return results
    
    async def cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes de plus de 7 jours"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            
            result = await self.db.weather_backup.delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old weather backups")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
            return 0

# Instance globale (sera initialisée dans server.py)
weather_backup_service = None