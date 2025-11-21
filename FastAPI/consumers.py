import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from .models import Utilisateur, Evenement, Lieu
from .serializers import EvenementSerializer, LieuSerializer
import logging

logger = logging.getLogger(__name__)


class EventNotificationConsumer(AsyncWebsocketConsumer):
    """Consumer principal pour les notifications d'événements"""
    
    async def connect(self):
        """Connexion WebSocket"""
        logger.info("🔌 NOUVELLE CONNEXION WEBSOCKET")
        # Groupe global pour tous les événements
        self.room_group_name = 'events_notifications'
        
        # Rejoindre le groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        print(f"✅ Ajouté au groupe: {self.room_group_name}")
        print(f"✅ Channel layer: {self.channel_layer}")
        await self.accept()
        
        # Log de connexion
        logger.info(f"Nouvelle connexion WebSocket: {self.channel_name}")
        
        # Envoyer un message de bienvenue
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connexion WebSocket établie avec succès',
            'timestamp': timezone.now().isoformat()
        }))
        print("✅ Message de bienvenue envoyé")
        print("=" * 80)
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket"""
        logger.info(f"🔌 DÉCONNEXION: {self.channel_name}, code: {close_code}")
        # Quitter le groupe
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"Déconnexion WebSocket: {self.channel_name}, code: {close_code}")
    
    async def receive(self, text_data):
        """Recevoir des messages du client"""
        logger.info(f"📩 MESSAGE REÇU: {text_data}")
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Répondre au ping du client
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
                logger.info("📤 PONG ENVOYÉ")
            
            elif message_type == 'subscribe_location':
                # S'abonner aux événements d'une zone géographique
                await self.handle_location_subscription(data)
            
            elif message_type == 'subscribe_category':
                # S'abonner aux événements d'une catégorie
                await self.handle_category_subscription(data)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Format JSON invalide'
            }))
    
    async def handle_location_subscription(self, data):
        """Gérer l'abonnement par localisation"""
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        radius = data.get('radius', 10)  # km par défaut
        
        if latitude and longitude:
            # Stocker les préférences de localisation pour cette connexion
            self.user_location = {
                'latitude': float(latitude),
                'longitude': float(longitude),
                'radius': float(radius)
            }
            
            # Rejoindre un groupe spécifique à la zone
            location_group = f"location_{int(latitude*100)}_{int(longitude*100)}"
            await self.channel_layer.group_add(
                location_group,
                self.channel_name
            )
            
            await self.send(text_data=json.dumps({
                'type': 'subscription_confirmed',
                'subscription_type': 'location',
                'latitude': latitude,
                'longitude': longitude,
                'radius': radius
            }))
    
    async def handle_category_subscription(self, data):
        """Gérer l'abonnement par catégorie"""
        categories = data.get('categories', [])
        
        if categories:
            self.user_categories = categories
            
            # Rejoindre les groupes de catégories
            for category in categories:
                category_group = f"category_{category.lower().replace(' ', '_')}"
                await self.channel_layer.group_add(
                    category_group,
                    self.channel_name
                )
            
            await self.send(text_data=json.dumps({
                'type': 'subscription_confirmed',
                'subscription_type': 'categories',
                'categories': categories
            }))
    
    # Handlers pour les différents types de notifications
    async def new_event_notification(self, event):
        """Notification pour un nouvel événement"""
        print("=" * 80)
        print("🔔 new_event_notification APPELÉE !")
        print(f"   Event data: {event}")
        print("=" * 80)
        
        logger.info("🔔 new_event_notification APPELÉE !")
        logger.info(f"   Event: {event}")
        
        # Préparer le message pour le client
        message = {
            'type': 'new_event',
            'event': event['event_data'],
            'message': f"Nouvel événement: {event['event_data']['nom']}",
            'timestamp': timezone.now().isoformat()
        }
        
        print(f"📤 Envoi au client Flutter: {message}")
        logger.info(f"📤 Envoi au client Flutter")
        
        # Envoyer au client WebSocket
        await self.send(text_data=json.dumps(message))
        
        print("✅ Message envoyé au client !")
        print("=" * 80)
        logger.info("✅ Message envoyé au client Flutter")
    
    async def event_updated_notification(self, event):
        """Notification pour un événement modifié"""
        print("🔔 event_updated_notification APPELÉE")
        logger.info("🔔 event_updated_notification APPELÉE")
        await self.send(text_data=json.dumps({
            'type': 'event_updated',
            'event': event['event_data'],
            'message': f"Événement modifié: {event['event_data']['nom']}",
            'timestamp': timezone.now().isoformat()
        }))
    
    async def event_cancelled_notification(self, event):
        """Notification pour un événement annulé"""
        print("🔔 event_cancelled_notification APPELÉE")
        logger.info("🔔 event_cancelled_notification APPELÉE")
        await self.send(text_data=json.dumps({
            'type': 'event_cancelled',
            'event': event['event_data'],
            'message': f"Événement annulé: {event['event_data']['nom']}",
            'timestamp': timezone.now().isoformat()
        }))
    
    async def new_place_notification(self, event):
        """Notification pour un nouveau lieu"""
        print("🔔 new_place_notification APPELÉE")
        logger.info("🔔 new_place_notification APPELÉE")
        await self.send(text_data=json.dumps({
            'type': 'new_place',
            'place': event['place_data'],
            'message': f"Nouveau lieu: {event['place_data']['nom']}",
            'timestamp': timezone.now().isoformat()
        }))
    
    async def proximity_event_notification(self, event):
        """Notification pour un événement à proximité"""
        print("🔔 proximity_event_notification APPELÉE")
        logger.info("🔔 proximity_event_notification APPELÉE")
        await self.send(text_data=json.dumps({
            'type': 'proximity_event',
            'event': event['event_data'],
            'distance': event.get('distance'),
            'message': f"Événement à proximité: {event['event_data']['nom']}",
            'timestamp': timezone.now().isoformat()
        }))


class PersonalNotificationConsumer(AsyncWebsocketConsumer):
    """Consumer pour les notifications personnelles d'un utilisateur"""
    
    async def connect(self):
        """Connexion WebSocket pour utilisateur authentifié"""
        # Vérifier l'authentification
        user = self.scope.get('user')
        if isinstance(user, AnonymousUser):
            await self.close()
            return
        
        self.user = user
        self.room_group_name = f'user_{user.id}'
        
        # Rejoindre le groupe personnel
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les notifications non lues
        await self.send_unread_notifications()
        
        logger.info(f"Connexion personnelle pour utilisateur {user.username}")
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Récupérer les notifications non lues"""
        try:
            utilisateur = Utilisateur.objects.get(id=self.user.id)
            notifications = utilisateur.notifications.filter(lue=False).order_by('-date_creation')
            return [notif.to_dict() for notif in notifications]
        except Utilisateur.DoesNotExist:
            return []
    
    async def send_unread_notifications(self):
        """Envoyer les notifications non lues"""
        notifications = await self.get_unread_notifications()
        
        if notifications:
            await self.send(text_data=json.dumps({
                'type': 'unread_notifications',
                'count': len(notifications),
                'notifications': notifications
            }))
    
    async def personal_notification(self, event):
        """Notification personnelle"""
        await self.send(text_data=json.dumps({
            'type': 'personal_notification',
            'notification': event['notification_data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def event_reminder(self, event):
        """Rappel d'événement"""
        await self.send(text_data=json.dumps({
            'type': 'event_reminder',
            'event': event['event_data'],
            'reminder_time': event['reminder_time'],
            'message': f"Rappel: {event['event_data']['nom']} dans {event['reminder_time']}",
            'timestamp': timezone.now().isoformat()
        }))


class LocationBasedConsumer(AsyncWebsocketConsumer):
    """Consumer spécialisé pour les notifications basées sur la localisation"""
    
    async def connect(self):
        """Connexion avec localisation"""
        # Récupérer les paramètres de localisation depuis l'URL
        self.latitude = self.scope['url_route']['kwargs'].get('latitude')
        self.longitude = self.scope['url_route']['kwargs'].get('longitude')
        self.radius = self.scope['url_route']['kwargs'].get('radius', 10)
        
        if not self.latitude or not self.longitude:
            await self.close()
            return
        
        # Créer le nom du groupe basé sur la zone géographique
        lat_zone = int(float(self.latitude) * 100)
        lng_zone = int(float(self.longitude) * 100)
        self.room_group_name = f'location_{lat_zone}_{lng_zone}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les événements actuels dans la zone
        await self.send_current_events_in_area()
    
    async def disconnect(self, close_code):
        """Déconnexion"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    @database_sync_to_async
    def get_events_in_area(self):
        """Récupérer les événements dans la zone"""
        from .geolocation_services import GeolocationService
        
        geo_service = GeolocationService()
        nearby_places = geo_service.find_nearby_places(
            float(self.latitude), 
            float(self.longitude), 
            float(self.radius)
        )
        
        lieu_ids = [item['lieu'].id for item in nearby_places]
        evenements = Evenement.objects.filter(
            lieu__id__in=lieu_ids,
            date_debut__gt=timezone.now()
        ).select_related('lieu', 'organisateur')[:10]
        
        return list(evenements)
    
    async def send_current_events_in_area(self):
        """Envoyer les événements actuels dans la zone"""
        evenements = await self.get_events_in_area()
        
        events_data = []
        for event in evenements:
            event_data = await self.serialize_event(event)
            events_data.append(event_data)
        
        await self.send(text_data=json.dumps({
            'type': 'current_events',
            'location': {
                'latitude': float(self.latitude),
                'longitude': float(self.longitude),
                'radius': float(self.radius)
            },
            'events': events_data,
            'count': len(events_data)
        }))
    
    @database_sync_to_async
    def serialize_event(self, event):
        """Sérialiser un événement de manière asynchrone"""
        from .serializers import EvenementListSerializer
        return EvenementListSerializer(event).data
    
    async def location_event_notification(self, event):
        """Notification d'événement dans la zone"""
        await self.send(text_data=json.dumps({
            'type': 'location_event',
            'event': event['event_data'],
            'distance': event.get('distance'),
            'timestamp': timezone.now().isoformat()
        }))