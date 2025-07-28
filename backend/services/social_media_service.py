import os
import logging
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import asyncio
import tweepy
import facebook
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class SocialMediaService:
    def __init__(self, db):
        self.db = db
        
        # Configuration Twitter API v2
        self.twitter_bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')
        self.twitter_consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
        self.twitter_consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
        self.twitter_access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Configuration Facebook
        self.facebook_app_id = os.environ.get('FACEBOOK_APP_ID')
        self.facebook_app_secret = os.environ.get('FACEBOOK_APP_SECRET')
        self.facebook_access_token = os.environ.get('FACEBOOK_ACCESS_TOKEN')
        
        # Initialiser les clients
        self.twitter_client = None
        self.facebook_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialise les clients des API sociales"""
        try:
            # Client Twitter
            if self.twitter_consumer_key and self.twitter_consumer_secret:
                self.twitter_client = tweepy.Client(
                    bearer_token=self.twitter_bearer_token,
                    consumer_key=self.twitter_consumer_key,
                    consumer_secret=self.twitter_consumer_secret,
                    access_token=self.twitter_access_token,
                    access_token_secret=self.twitter_access_token_secret,
                    wait_on_rate_limit=True
                )
                logger.info("Twitter client initialized successfully")
            else:
                logger.warning("Twitter credentials not configured")
            
            # Client Facebook
            if self.facebook_access_token:
                self.facebook_client = facebook.GraphAPI(access_token=self.facebook_access_token)
                logger.info("Facebook client initialized successfully")
            else:
                logger.warning("Facebook credentials not configured")
                
        except Exception as e:
            logger.error(f"Error initializing social media clients: {e}")
    
    async def store_social_credentials(self, platform: str, credentials: Dict) -> bool:
        """Stocke les identifiants des réseaux sociaux en base"""
        try:
            credential_data = {
                'platform': platform,
                'credentials': credentials,
                'created_at': datetime.now(),
                'is_active': True
            }
            
            # Mise à jour ou insertion
            await self.db.social_credentials.update_one(
                {'platform': platform},
                {'$set': credential_data},
                upsert=True
            )
            
            logger.info(f"Social credentials stored for platform: {platform}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing social credentials: {e}")
            return False
    
    async def get_social_credentials(self, platform: str) -> Optional[Dict]:
        """Récupère les identifiants d'un réseau social"""
        try:
            credential = await self.db.social_credentials.find_one(
                {'platform': platform, 'is_active': True}
            )
            return credential.get('credentials') if credential else None
            
        except Exception as e:
            logger.error(f"Error getting social credentials: {e}")
            return None
    
    def format_weather_post(self, weather_data: Dict, vigilance_data: Dict, ai_prediction: Optional[Dict] = None) -> str:
        """Formate un post météorologique pour les réseaux sociaux"""
        try:
            commune = weather_data.get('commune', 'Guadeloupe')
            temp = weather_data.get('temperature', 'N/A')
            condition = weather_data.get('condition', 'temps variable')
            
            # Niveau de vigilance
            vigilance_level = vigilance_data.get('color_level', 'vert')
            vigilance_emoji = {
                'vert': '🟢',
                'jaune': '🟡', 
                'orange': '🟠',
                'rouge': '🔴'
            }.get(vigilance_level, '🟢')
            
            # Construction du post
            post_content = f"🌴 #MétéoGuadeloupe - {commune}\n\n"
            post_content += f"🌡️ Température: {temp}°C\n"
            post_content += f"☁️ Conditions: {condition}\n"
            post_content += f"{vigilance_emoji} Vigilance: {vigilance_level.upper()}\n\n"
            
            # Ajouter prédiction IA si disponible
            if ai_prediction:
                risk_level = ai_prediction.get('risk_level', 'faible')
                risk_emoji = {
                    'faible': '🟢',
                    'modéré': '🟡',
                    'élevé': '🟠', 
                    'critique': '🔴'
                }.get(risk_level, '🟢')
                
                post_content += f"🤖 IA Prédictive: {risk_emoji} Risque {risk_level}\n"
                
                # Recommandations principales
                recommendations = ai_prediction.get('recommendations', [])
                if recommendations:
                    post_content += f"📋 Conseil: {recommendations[0]}\n"
            
            post_content += f"\n#MétéoSentinelle #Antilles #Prévention\n"
            post_content += f"🕐 {datetime.now().strftime('%H:%M - %d/%m/%Y')}"
            
            return post_content
            
        except Exception as e:
            logger.error(f"Error formatting weather post: {e}")
            return f"🌴 Mise à jour météo Guadeloupe - {datetime.now().strftime('%H:%M')}"
    
    async def post_to_twitter(self, content: str) -> Dict:
        """Poste sur Twitter"""
        try:
            if not self.twitter_client:
                return {'success': False, 'error': 'Twitter client not initialized'}
            
            # Limiter à 280 caractères
            if len(content) > 280:
                content = content[:277] + "..."
            
            # Poster le tweet
            response = self.twitter_client.create_tweet(text=content)
            
            # Enregistrer en base
            await self._log_social_post('twitter', content, response.data['id'])
            
            logger.info(f"Tweet posted successfully: {response.data['id']}")
            return {
                'success': True,
                'post_id': response.data['id'],
                'platform': 'twitter'
            }
            
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}")
            return {'success': False, 'error': str(e)}
    
    async def post_to_facebook(self, content: str) -> Dict:
        """Poste sur Facebook"""
        try:
            if not self.facebook_client:
                return {'success': False, 'error': 'Facebook client not initialized'}
            
            # Poster sur Facebook (page ou profil selon le token)
            response = self.facebook_client.put_wall_post(message=content)
            
            # Enregistrer en base
            await self._log_social_post('facebook', content, response['id'])
            
            logger.info(f"Facebook post published successfully: {response['id']}")
            return {
                'success': True,
                'post_id': response['id'],
                'platform': 'facebook'
            }
            
        except Exception as e:
            logger.error(f"Error posting to Facebook: {e}")
            return {'success': False, 'error': str(e)}
    
    async def post_to_all_platforms(self, content: str) -> Dict:
        """Poste sur tous les réseaux sociaux configurés"""
        results = {}
        
        # Twitter
        if self.twitter_client:
            results['twitter'] = await self.post_to_twitter(content)
        else:
            results['twitter'] = {'success': False, 'error': 'Twitter not configured'}
        
        # Facebook
        if self.facebook_client:
            results['facebook'] = await self.post_to_facebook(content)
        else:
            results['facebook'] = {'success': False, 'error': 'Facebook not configured'}
        
        return results
    
    async def _log_social_post(self, platform: str, content: str, post_id: str):
        """Enregistre un post dans la base de données"""
        try:
            post_log = {
                'platform': platform,
                'content': content,
                'post_id': post_id,
                'posted_at': datetime.now(),
                'status': 'published'
            }
            
            await self.db.social_posts.insert_one(post_log)
            logger.info(f"Social post logged: {platform} - {post_id}")
            
        except Exception as e:
            logger.error(f"Error logging social post: {e}")
    
    async def schedule_weather_post(self, commune: str, schedule_time: datetime, platforms: List[str] = None) -> bool:
        """Programme un post météo"""
        try:
            if platforms is None:
                platforms = ['twitter', 'facebook']
            
            scheduled_post = {
                'commune': commune,
                'platforms': platforms,
                'scheduled_time': schedule_time,
                'status': 'scheduled',
                'created_at': datetime.now()
            }
            
            result = await self.db.scheduled_posts.insert_one(scheduled_post)
            
            logger.info(f"Weather post scheduled for {commune} at {schedule_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling weather post: {e}")
            return False
    
    async def get_scheduled_posts(self, status: str = 'scheduled') -> List[Dict]:
        """Récupère les posts programmés"""
        try:
            cursor = self.db.scheduled_posts.find({'status': status})
            return await cursor.to_list(length=100)
            
        except Exception as e:
            logger.error(f"Error getting scheduled posts: {e}")
            return []
    
    async def mark_post_as_sent(self, post_id: str):
        """Marque un post programmé comme envoyé"""
        try:
            await self.db.scheduled_posts.update_one(
                {'_id': post_id},
                {'$set': {'status': 'sent', 'sent_at': datetime.now()}}
            )
            
        except Exception as e:
            logger.error(f"Error marking post as sent: {e}")
    
    async def get_post_statistics(self, days: int = 30) -> Dict:
        """Récupère les statistiques des posts sur les réseaux sociaux"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Compter les posts par plateforme
            pipeline = [
                {'$match': {'posted_at': {'$gte': start_date}}},
                {'$group': {
                    '_id': '$platform',
                    'count': {'$sum': 1}
                }}
            ]
            
            cursor = self.db.social_posts.aggregate(pipeline)
            platform_stats = {doc['_id']: doc['count'] async for doc in cursor}
            
            # Total des posts
            total_posts = await self.db.social_posts.count_documents({
                'posted_at': {'$gte': start_date}
            })
            
            return {
                'total_posts': total_posts,
                'platform_breakdown': platform_stats,
                'period_days': days,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting post statistics: {e}")
            return {
                'total_posts': 0,
                'platform_breakdown': {},
                'period_days': days,
                'error': str(e)
            }
    
    def test_connections(self) -> Dict:
        """Teste les connexions aux API sociales"""
        results = {}
        
        # Test Twitter
        try:
            if self.twitter_client:
                me = self.twitter_client.get_me()
                results['twitter'] = {
                    'connected': True,
                    'username': me.data.username,
                    'user_id': me.data.id
                }
            else:
                results['twitter'] = {'connected': False, 'error': 'Client not initialized'}
                
        except Exception as e:
            results['twitter'] = {'connected': False, 'error': str(e)}
        
        # Test Facebook  
        try:
            if self.facebook_client:
                profile = self.facebook_client.get_object('me')
                results['facebook'] = {
                    'connected': True,
                    'name': profile.get('name', 'Unknown'),
                    'user_id': profile.get('id')
                }
            else:
                results['facebook'] = {'connected': False, 'error': 'Client not initialized'}
                
        except Exception as e:
            results['facebook'] = {'connected': False, 'error': str(e)}
        
        return results

# Instance globale (sera initialisée dans server.py)
social_media_service = None