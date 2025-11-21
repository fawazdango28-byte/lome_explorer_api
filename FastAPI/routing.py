from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/events/', consumers.EventNotificationConsumer.as_asgi()),
    path('ws/personal/', consumers.PersonalNotificationConsumer.as_asgi()),
    path('ws/location/<str:latitude>/<str:longitude>/', consumers.LocationBasedConsumer.as_asgi()),
    path('ws/location/<str:latitude>/<str:longitude>/<int:radius>/', consumers.LocationBasedConsumer.as_asgi()),
]