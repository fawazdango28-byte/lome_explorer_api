"""
Utilitaires WebSocket et gestion des tâches périodiques
Fichier: websocket_utils.py
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from datetime import timedelta
from django.core.management.base import BaseCommand
from .models import Evenement, Utilisateur
from .serializers import EvenementListSerializer
import logging

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


class WebSocketManager:
    """Gestionnaire centralisé des notifications WebSocket"""
    
    @staticmethod
    def send_notification(group_name, notification_type, data):
        """Envoyer une notification à un groupe"""
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': notification_type,
                    **data
                }
            )
            logger.info(f"Notification envoyée à {group_name}: {notification_type}")
            return True
        except Exception as e:
            logger.error(f"Erreur envoi notification WebSocket: {e}")
            return False
    
    @staticmethod
    def broadcast_to_all(notification_type, data):
        """Diffuser à tous les clients connectés"""
        return WebSocketManager.send_notification(
            'events_notifications',
            notification_type,
            data
        )
    
    @staticmethod
    def send_personal_notification(user_id, notification_type, data):
        """Envoyer une notification personnelle"""
        return WebSocketManager.send_notification(
            f'user_{user_id}',
            notification_type,
            data
        )
    
    @staticmethod
    def send_location_notification(latitude, longitude, notification_type, data, radius=15):
        """Envoyer une notification basée sur la localisation"""
        # Zone principale
        lat_zone = int(float(latitude) * 100)
        lng_zone = int(float(longitude) * 100)
        
        success = WebSocketManager.send_notification(
            f'location_{lat_zone}_{lng_zone}',
            notification_type,
            data
        )
        
        # Zones adjacentes si nécessaire
        if radius > 10:
            for lat_offset in [-1, 0, 1]:
                for lng_offset in [-1, 0, 1]:
                    if lat_offset == 0 and lng_offset == 0:
                        continue
                    
                    adjacent_group = f'location_{lat_zone + lat_offset}_{lng_zone + lng_offset}'
                    WebSocketManager.send_notification(
                        adjacent_group,
                        notification_type,
                        {**data, 'is_adjacent_zone': True}
                    )
        
        return success
    
    @staticmethod
    def send_category_notification(category, notification_type, data):
        """Envoyer une notification par catégorie"""
        category_group = f"category_{category.lower().replace(' ', '_')}"
        return WebSocketManager.send_notification(
            category_group,
            notification_type,
            data
        )


class EventReminderService:
    """Service pour les rappels d'événements"""
    
    @staticmethod
    def send_upcoming_reminders():
        """Envoyer les rappels pour les événements à venir"""
        now = timezone.now()
        
        # Rappels à 24h
        tomorrow = now + timedelta(hours=24)
        events_24h = Evenement.objects.filter(
            date_debut__gte=now + timedelta(hours=23, minutes=30),
            date_debut__lte=tomorrow + timedelta(minutes=30)
        ).select_related('organisateur', 'lieu')
        
        for event in events_24h:
            EventReminderService.send_reminder(event, '24 heures')
        
        # Rappels à 1h
        one_hour = now + timedelta(hours=1)
        events_1h = Evenement.objects.filter(
            date_debut__gte=now + timedelta(minutes=30),
            date_debut__lte=one_hour + timedelta(minutes=30)
        ).select_related('organisateur', 'lieu')
        
        for event in events_1h:
            EventReminderService.send_reminder(event, '1 heure')
        
        logger.info(f"Rappels envoyés: {len(events_24h)} (24h), {len(events_1h)} (1h)")
    
    @staticmethod
    def send_reminder(event, time_until):
        """Envoyer un rappel pour un événement spécifique"""
        event_data = EvenementListSerializer(event).data
        
        # Rappel à l'organisateur
        WebSocketManager.send_personal_notification(
            event.organisateur.id,
            'event_reminder',
            {
                'event_data': event_data,
                'reminder_time': time_until,
                'is_organizer': True
            }
        )
        
        # Rappel géographique pour les utilisateurs de la zone
        WebSocketManager.send_location_notification(
            float(event.lieu.latitude),
            float(event.lieu.longitude),
            'proximity_event_reminder',
            {
                'event_data': event_data,
                'reminder_time': time_until
            }
        )


class WebSocketHealthCheck:
    """Vérification de l'état des WebSockets"""
    
    @staticmethod
    def test_connection():
        """Tester la connectivité WebSocket"""
        try:
            test_data = {
                'type': 'health_check',
                'timestamp': timezone.now().isoformat(),
                'message': 'Test de connectivité'
            }
            
            success = WebSocketManager.send_notification(
                'events_notifications',
                'health_check_notification',
                test_data
            )
            
            return success
        except Exception as e:
            logger.error(f"Test WebSocket échoué: {e}")
            return False
    
    @staticmethod
    def get_connection_stats():
        """Obtenir les statistiques de connexion (nécessite Redis)"""
        try:
            # Ici vous pouvez implémenter des statistiques via Redis
            # Par exemple, compter les connexions actives
            return {
                'status': 'healthy',
                'active_connections': 'N/A',
                'last_check': timezone.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': timezone.now().isoformat()
            }


# Commande de gestion Django pour les tâches périodiques
class Command(BaseCommand):
    """
    Commande Django pour envoyer les rappels d'événements
    Usage: python manage.py send_event_reminders
    """
    help = 'Envoie les rappels d\'événements via WebSocket'
    
    def handle(self, *args, **options):
        self.stdout.write('🔄 Envoi des rappels d\'événements...')
        
        try:
            EventReminderService.send_upcoming_reminders()
            self.stdout.write(
                self.style.SUCCESS('✅ Rappels envoyés avec succès')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur: {e}')
            )


# Décorateur pour faciliter l'envoi de notifications
def websocket_notification(notification_type, target='all'):
    """
    Décorateur pour envoyer automatiquement des notifications WebSocket
    
    Usage:
    @websocket_notification('new_event_notification')
    def create_event(request):
        # votre code
        return event
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Extraire les données pour la notification
            if hasattr(result, 'data'):  # Response DRF
                data = result.data
            elif isinstance(result, dict):
                data = result
            else:
                data = {'result': str(result)}
            
            # Envoyer la notification
            if target == 'all':
                WebSocketManager.broadcast_to_all(notification_type, data)
            elif target.startswith('user_'):
                user_id = target.split('_')[1]
                WebSocketManager.send_personal_notification(user_id, notification_type, data)
            
            return result
        return wrapper
    return decorator


# Utilitaires pour les vues API
def notify_new_event(event):
    """Notifier la création d'un nouvel événement"""
    event_data = EvenementListSerializer(event).data
    
    # Notification globale
    WebSocketManager.broadcast_to_all(
        'new_event_notification',
        {'event_data': event_data}
    )
    
    # Notification géographique
    WebSocketManager.send_location_notification(
        float(event.lieu.latitude),
        float(event.lieu.longitude),
        'proximity_event_notification',
        {'event_data': event_data}
    )
    
    # Notification par catégorie
    if hasattr(event.lieu, 'categorie') and event.lieu.categorie:
        WebSocketManager.send_category_notification(
            event.lieu.categorie,
            'category_event_notification',
            {'event_data': event_data}
        )


def notify_event_updated(event):
    """Notifier la modification d'un événement"""
    event_data = EvenementListSerializer(event).data
    
    WebSocketManager.broadcast_to_all(
        'event_updated_notification',
        {'event_data': event_data}
    )


def notify_event_cancelled(event):
    """Notifier l'annulation d'un événement"""
    event_data = EvenementListSerializer(event).data
    
    WebSocketManager.broadcast_to_all(
        'event_cancelled_notification',
        {'event_data': event_data}
    )


# Configuration des tâches périodiques avec Celery (optionnel)
try:
    from celery import shared_task
    
    @shared_task
    def send_periodic_reminders():
        """Tâche Celery pour les rappels périodiques"""
        EventReminderService.send_upcoming_reminders()
        return "Rappels envoyés"
    
    @shared_task
    def websocket_health_check():
        """Tâche Celery pour vérifier l'état des WebSockets"""
        result = WebSocketHealthCheck.test_connection()
        stats = WebSocketHealthCheck.get_connection_stats()
        
        if not result:
            logger.warning("WebSocket health check failed")
        
        return {
            'connection_test': result,
            'stats': stats
        }
    
    @shared_task
    def cleanup_old_connections():
        """Nettoyer les anciennes connexions WebSocket"""
        # Ici vous pouvez implémenter le nettoyage des connexions inactives
        # via Redis ou votre système de cache
        return "Cleanup completed"
        
except ImportError:
    # Celery non installé, fonctions normales
    def send_periodic_reminders():
        EventReminderService.send_upcoming_reminders()
    
    def websocket_health_check():
        return WebSocketHealthCheck.test_connection()


# Middleware pour capturer les informations de session WebSocket
class WebSocketSessionMiddleware:
    """
    Middleware pour gérer les sessions WebSocket
    À utiliser dans le routing WebSocket
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Ajouter des informations de session ou d'authentification
        if scope["type"] == "websocket":
            # Log des connexions
            logger.info(f"Nouvelle connexion WebSocket: {scope.get('path', 'unknown')}")
            
            # Vous pouvez ajouter ici de la logique d'authentification
            # ou de gestion de session
        
        return await self.app(scope, receive, send)


# Classe pour gérer les groupes dynamiques
class DynamicGroupManager:
    """Gestionnaire pour les groupes WebSocket dynamiques"""
    
    @staticmethod
    def create_location_group(latitude, longitude, precision=2):
        """Créer un nom de groupe basé sur la localisation"""
        lat_zone = round(float(latitude) * (10 ** precision))
        lng_zone = round(float(longitude) * (10 ** precision))
        return f'location_{lat_zone}_{lng_zone}'
    
    @staticmethod
    def create_category_group(category):
        """Créer un nom de groupe basé sur la catégorie"""
        return f"category_{category.lower().replace(' ', '_').replace('-', '_')}"
    
    @staticmethod
    def create_user_group(user_id):
        """Créer un nom de groupe pour un utilisateur"""
        return f'user_{user_id}'
    
    @staticmethod
    def create_event_group(event_id):
        """Créer un nom de groupe pour un événement spécifique"""
        return f'event_{event_id}'


# Système de rate limiting pour les WebSockets
class WebSocketRateLimiter:
    """Rate limiting pour les connexions WebSocket"""
    
    def __init__(self, max_connections_per_ip=10, max_messages_per_minute=60):
        self.max_connections_per_ip = max_connections_per_ip
        self.max_messages_per_minute = max_messages_per_minute
        self.connections = {}  # IP -> count
        self.messages = {}     # IP -> [(timestamp, count), ...]
    
    def can_connect(self, ip_address):
        """Vérifier si une IP peut se connecter"""
        current_connections = self.connections.get(ip_address, 0)
        return current_connections < self.max_connections_per_ip
    
    def add_connection(self, ip_address):
        """Ajouter une connexion"""
        self.connections[ip_address] = self.connections.get(ip_address, 0) + 1
    
    def remove_connection(self, ip_address):
        """Supprimer une connexion"""
        if ip_address in self.connections:
            self.connections[ip_address] -= 1
            if self.connections[ip_address] <= 0:
                del self.connections[ip_address]
    
    def can_send_message(self, ip_address):
        """Vérifier si une IP peut envoyer un message"""
        now = timezone.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Nettoyer les anciens messages
        if ip_address in self.messages:
            self.messages[ip_address] = [
                (timestamp, count) for timestamp, count in self.messages[ip_address]
                if timestamp > minute_ago
            ]
        
        # Compter les messages dans la dernière minute
        current_count = sum(
            count for timestamp, count in self.messages.get(ip_address, [])
        )
        
        return current_count < self.max_messages_per_minute
    
    def add_message(self, ip_address):
        """Enregistrer un message envoyé"""
        now = timezone.now()
        if ip_address not in self.messages:
            self.messages[ip_address] = []
        self.messages[ip_address].append((now, 1))


# Instance globale du rate limiter
rate_limiter = WebSocketRateLimiter()


# Système d'analytics pour les WebSockets
class WebSocketAnalytics:
    """Analytics pour les connexions WebSocket"""
    
    @staticmethod
    def log_connection(channel_name, user_agent=None, ip_address=None):
        """Logger une connexion"""
        logger.info(f"WebSocket connection: {channel_name}, IP: {ip_address}")
    
    @staticmethod
    def log_message(channel_name, message_type, data_size=0):
        """Logger un message"""
        logger.debug(f"WebSocket message: {channel_name}, type: {message_type}, size: {data_size}")
    
    @staticmethod
    def log_disconnection(channel_name, reason=None):
        """Logger une déconnexion"""
        logger.info(f"WebSocket disconnection: {channel_name}, reason: {reason}")


# Configuration pour la production
class ProductionWebSocketConfig:
    """Configuration WebSocket pour la production"""
    
    # Limite de connexions par serveur
    MAX_CONNECTIONS = 10000
    
    # Timeout pour les connexions inactives
    CONNECTION_TIMEOUT = timedelta(minutes=30)
    
    # Taille max des messages
    MAX_MESSAGE_SIZE = 64 * 1024  # 64KB
    
    # Configuration Redis pour la scalabilité
    REDIS_CONFIG = {
        'hosts': [('redis-server', 6379)],
        'capacity': 10000,
        'expiry': 3600,
    }


# Tests unitaires pour les WebSockets
class WebSocketTestUtils:
    """Utilitaires pour tester les WebSockets"""
    
    @staticmethod
    def create_test_consumer():
        """Créer un consumer de test"""
        from channels.testing import WebsocketCommunicator
        from .consumers import EventNotificationConsumer
        
        communicator = WebsocketCommunicator(EventNotificationConsumer.as_asgi(), "/ws/events/")
        return communicator
    
    @staticmethod
    async def test_notification_delivery():
        """Tester la livraison des notifications"""
        communicator = WebSocketTestUtils.create_test_consumer()
        connected, subprotocol = await communicator.connect()
        
        assert connected
        
        # Envoyer un message de test
        await communicator.send_json_to({
            'type': 'ping'
        })
        
        # Recevoir la réponse
        response = await communicator.receive_json_from()
        assert response['type'] == 'pong'
        
        await communicator.disconnect()
        return True


# Documentation des endpoints WebSocket
WEBSOCKET_ENDPOINTS_DOC = """
📡 ENDPOINTS WEBSOCKET DISPONIBLES:

1. NOTIFICATIONS GÉNÉRALES:
   ws://localhost:8000/ws/events/
   - Reçoit toutes les notifications d'événements
   - Messages: new_event, event_updated, event_cancelled

2. NOTIFICATIONS PERSONNELLES:
   ws://localhost:8000/ws/personal/
   - Notifications pour l'utilisateur connecté
   - Messages: personal_notification, event_reminder

3. NOTIFICATIONS GÉOGRAPHIQUES:
   ws://localhost:8000/ws/location/{lat}/{lng}/
   ws://localhost:8000/ws/location/{lat}/{lng}/{radius}/
   - Notifications dans une zone géographique
   - Messages: proximity_event, location_event

📤 MESSAGES CLIENTS → SERVEUR:
{
  "type": "ping"                    // Test de connexion
}

{
  "type": "subscribe_location",     // Abonnement géographique
  "latitude": 6.1319,
  "longitude": 1.2228,
  "radius": 10
}

{
  "type": "subscribe_category",     // Abonnement par catégorie
  "categories": ["culture", "sport"]
}

📥 MESSAGES SERVEUR → CLIENT:
{
  "type": "new_event",              // Nouvel événement
  "event": {...},
  "message": "...",
  "timestamp": "..."
}

{
  "type": "proximity_event",        // Événement à proximité
  "event": {...},
  "distance": 2.5,
  "message": "...",
  "timestamp": "..."
}
"""

# print(WEBSOCKET_ENDPOINTS_DOC) if __name__ == "__main__"