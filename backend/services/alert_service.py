import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import logging

from models import WeatherAlert, UserSubscription, AlertType, RiskLevel

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, db: AsyncIOMotorClient):
        self.db = db
        # Configuration email (à adapter selon votre service)
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.from_email = os.environ.get('FROM_EMAIL', 'alerts@meteo-sentinelle.gp')
        
    async def get_subscribers_for_alert(self, alert: WeatherAlert) -> List[UserSubscription]:
        """Récupère les abonnés concernés par une alerte"""
        query = {
            "active": True,
            "verified_email": True,
            "preferences.communes": alert.commune,
            "preferences.alert_types": alert.alert_type,
            f"preferences.risk_threshold": {"$lte": self._risk_level_to_number(alert.severity)}
        }
        
        subscribers = await self.db.user_subscriptions.find(query).to_list(1000)
        return [UserSubscription(**sub) for sub in subscribers]
    
    def _risk_level_to_number(self, risk_level: RiskLevel) -> int:
        """Convertit le niveau de risque en nombre pour comparaison"""
        mapping = {
            RiskLevel.FAIBLE: 1,
            RiskLevel.MODERE: 2,
            RiskLevel.ELEVE: 3,
            RiskLevel.CRITIQUE: 4
        }
        return mapping.get(risk_level, 1)
    
    async def send_email_alert(self, subscribers: List[UserSubscription], alert: WeatherAlert) -> Dict[str, int]:
        """Envoie une alerte par email"""
        sent_count = 0
        failed_count = 0
        
        if not self.smtp_username or not self.smtp_password:
            logger.error("SMTP credentials not configured")
            return {"sent": 0, "failed": len(subscribers)}
        
        # Template email
        email_template = self._create_email_template(alert)
        
        try:
            # Connexion SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            for subscriber in subscribers:
                try:
                    # Personnalise l'email
                    msg = MIMEMultipart()
                    msg['From'] = self.from_email
                    msg['To'] = subscriber.email
                    msg['Subject'] = f"🚨 MÉTÉO SENTINELLE - {alert.title}"
                    
                    # Corps du message personnalisé
                    body = email_template.format(
                        commune=alert.commune,
                        severity_emoji=self._get_severity_emoji(alert.severity),
                        title=alert.title,
                        message=alert.message,
                        recommendations=self._format_recommendations(alert.recommendations),
                        unsubscribe_url=f"https://meteo-sentinelle.gp/unsubscribe?email={subscriber.email}"
                    )
                    
                    msg.attach(MIMEText(body, 'html', 'utf-8'))
                    
                    # Envoi
                    server.send_message(msg)
                    sent_count += 1
                    
                    # Met à jour les statistiques utilisateur
                    await self.db.user_subscriptions.update_one(
                        {"_id": subscriber.id},
                        {
                            "$set": {"last_notification": datetime.utcnow()},
                            "$inc": {"notifications_sent": 1}
                        }
                    )
                    
                    # Délai pour éviter spam
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to send email to {subscriber.email}: {e}")
                    failed_count += 1
            
            server.quit()
            
        except Exception as e:
            logger.error(f"SMTP server error: {e}")
            failed_count = len(subscribers)
        
        # Met à jour les statistiques de l'alerte
        await self.db.weather_alerts.update_one(
            {"id": alert.id},
            {"$inc": {"sent_notifications": sent_count}}
        )
        
        logger.info(f"Email alert sent: {sent_count} success, {failed_count} failed")
        return {"sent": sent_count, "failed": failed_count}
    
    def _create_email_template(self, alert: WeatherAlert) -> str:
        """Crée le template HTML pour les emails d'alerte"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8fafc; padding: 20px; border-radius: 0 0 8px 8px; }}
                .alert-box {{ background: #fef3c7; border: 2px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .critical {{ background: #fee2e2; border-color: #dc2626; }}
                .high {{ background: #fed7aa; border-color: #ea580c; }}
                .moderate {{ background: #fef3c7; border-color: #f59e0b; }}
                .low {{ background: #dcfce7; border-color: #22c55e; }}
                .recommendations {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .footer {{ text-align: center; font-size: 12px; color: #666; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛡️ MÉTÉO SENTINELLE</h1>
                    <p>Alerte météorologique - {commune}</p>
                </div>
                <div class="content">
                    <div class="alert-box {severity_class}">
                        <h2>{severity_emoji} {title}</h2>
                        <p><strong>{message}</strong></p>
                    </div>
                    
                    <div class="recommendations">
                        <h3>🎯 Recommandations de sécurité :</h3>
                        {recommendations}
                    </div>
                    
                    <p>Cette alerte a été générée automatiquement par Météo Sentinelle basée sur les données météorologiques les plus récentes.</p>
                    
                    <div class="footer">
                        <p>Météo Sentinelle - Protection météorologique pour la Guadeloupe</p>
                        <p><a href="{unsubscribe_url}">Se désabonner</a> | <a href="https://meteo-sentinelle.gp">Site web</a></p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_severity_emoji(self, severity: RiskLevel) -> str:
        """Retourne l'emoji correspondant au niveau de sévérité"""
        mapping = {
            RiskLevel.FAIBLE: "🟢",
            RiskLevel.MODERE: "🟡", 
            RiskLevel.ELEVE: "🟠",
            RiskLevel.CRITIQUE: "🔴"
        }
        return mapping.get(severity, "⚪")
    
    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Formate les recommandations en HTML"""
        if not recommendations:
            return "<p>Suivez les consignes de sécurité habituelles.</p>"
        
        html = "<ul>"
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        html += "</ul>"
        return html
    
    async def send_sms_alert(self, phone_numbers: List[str], alert: WeatherAlert) -> Dict[str, int]:
        """Envoie une alerte par SMS (à implémenter avec Twilio/AWS SNS)"""
        # TODO: Implémenter l'envoi SMS
        # Pour la demo, on simule l'envoi
        logger.info(f"SMS alert simulation: would send to {len(phone_numbers)} numbers")
        
        sms_message = f"🚨 {alert.commune}: {alert.title} - {alert.message[:100]}..."
        
        # Simulation
        sent_count = len(phone_numbers)
        failed_count = 0
        
        logger.info(f"SMS would send: {sms_message}")
        
        return {"sent": sent_count, "failed": failed_count}
    
    async def process_new_alert(self, alert: WeatherAlert) -> Dict[str, Any]:
        """Traite une nouvelle alerte (envoi notifications)"""
        logger.info(f"Processing new alert: {alert.title} for {alert.commune}")
        
        # Récupère les abonnés concernés
        subscribers = await self.get_subscribers_for_alert(alert)
        
        if not subscribers:
            logger.info(f"No subscribers found for alert in {alert.commune}")
            return {"email_sent": 0, "sms_sent": 0, "total_subscribers": 0}
        
        results = {}
        
        # Envoi emails
        email_subscribers = [s for s in subscribers if s.preferences.notification_email]
        if email_subscribers:
            email_results = await self.send_email_alert(email_subscribers, alert)
            results["email"] = email_results
        
        # Envoi SMS
        sms_subscribers = [s for s in subscribers if s.preferences.notification_sms and s.phone]
        if sms_subscribers:
            phone_numbers = [s.phone for s in sms_subscribers]
            sms_results = await self.send_sms_alert(phone_numbers, alert)
            results["sms"] = sms_results
        
        # Statistiques globales
        total_notifications = (results.get("email", {}).get("sent", 0) + 
                             results.get("sms", {}).get("sent", 0))
        
        # Met à jour les stats API
        await self.db.api_usage.update_one(
            {"date": datetime.now().date().isoformat()},
            {"$inc": {"alerts_sent": total_notifications}},
            upsert=True
        )
        
        logger.info(f"Alert processed: {total_notifications} notifications sent to {len(subscribers)} subscribers")
        
        return {
            "total_subscribers": len(subscribers),
            "notifications_sent": total_notifications,
            "details": results
        }
    
    async def cleanup_expired_alerts(self) -> int:
        """Nettoie les alertes expirées"""
        now = datetime.utcnow()
        
        result = await self.db.weather_alerts.delete_many({
            "active_until": {"$lt": now}
        })
        
        deleted_count = result.deleted_count
        logger.info(f"Cleaned up {deleted_count} expired alerts")
        
        return deleted_count