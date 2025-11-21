from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from .geolocation_services import (
    GeolocationService, IPGeolocationService, LomeLocationService,
    get_user_location_from_request, get_client_ip
)
from .models import Lieu, Evenement
from .serializers import LieuListSerializer, EvenementListSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def detect_user_location(request):
    """
    Détecter automatiquement la localisation de l'utilisateur
    """
    try:
        location = get_user_location_from_request(request)
        
        # Enrichir avec des informations sur Lomé si applicable
        if location['latitude'] and location['longitude']:
            is_in_lome = LomeLocationService.is_in_lome(
                location['latitude'], 
                location['longitude']
            )
            
            if is_in_lome:
                quartier = LomeLocationService.get_quartier_from_coordinates(
                    location['latitude'], 
                    location['longitude']
                )
                location['quartier'] = quartier
                location['ville'] = 'Lomé'
            
            # Ajouter l'adresse si pas déjà présente
            if 'address' not in location:
                geo_service = GeolocationService()
                reverse_result = geo_service.reverse_geocode(
                    location['latitude'], 
                    location['longitude']
                )
                if reverse_result:
                    location['address'] = reverse_result['address']
        
        return Response(location)
        
    except Exception as e:
        return Response({
            'error': 'Erreur lors de la détection de localisation',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def geocode_address(request):
    """
    Convertir une adresse en coordonnées GPS
    """
    address = request.data.get('address')
    if not address:
        return Response({
            'error': 'Adresse requise'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    geo_service = GeolocationService()
    result = geo_service.geocode_address(address)
    
    if result:
        # Ajouter informations spécifiques à Lomé
        is_in_lome = LomeLocationService.is_in_lome(
            result['latitude'], 
            result['longitude']
        )
        
        if is_in_lome:
            result['quartier'] = LomeLocationService.get_quartier_from_coordinates(
                result['latitude'], 
                result['longitude']
            )
            result['ville'] = 'Lomé'
        
        return Response(result)
    else:
        return Response({
            'error': 'Adresse non trouvée'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def reverse_geocode(request):
    """
    Convertir des coordonnées GPS en adresse
    """
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not latitude or not longitude:
        return Response({
            'error': 'Latitude et longitude requises'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        geo_service = GeolocationService()
        is_valid, lat, lng = geo_service.validate_coordinates(latitude, longitude)
        
        result = geo_service.reverse_geocode(lat, lng)
        
        if result:
            # Enrichir avec informations Lomé
            if LomeLocationService.is_in_lome(lat, lng):
                result['quartier'] = LomeLocationService.get_quartier_from_coordinates(lat, lng)
                result['ville'] = 'Lomé'
            
            return Response(result)
        else:
            return Response({
                'error': 'Adresse non trouvée pour ces coordonnées'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except ValidationError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def lieux_proximite(request):
    """
    Trouver les lieux à proximité d'un point
    """
    latitude = request.GET.get('lat')
    longitude = request.GET.get('lng')
    radius = request.GET.get('radius', 10)  # km
    
    if not latitude or not longitude:
        # Essayer de détecter automatiquement
        location = get_user_location_from_request(request)
        if location.get('latitude'):
            latitude = location['latitude']
            longitude = location['longitude']
        else:
            return Response({
                'error': 'Coordonnées GPS requises ou position non détectable'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        geo_service = GeolocationService()
        is_valid, lat, lng = geo_service.validate_coordinates(latitude, longitude)
        radius_km = float(radius)
        
        nearby_places = geo_service.find_nearby_places(lat, lng, radius_km)
        
        # Préparer la réponse
        results = []
        for item in nearby_places:
            lieu_data = LieuListSerializer(item['lieu']).data
            lieu_data['distance'] = item['distance']
            results.append(lieu_data)
        
        return Response({
            'center': {'latitude': lat, 'longitude': lng},
            'radius_km': radius_km,
            'count': len(results),
            'lieux': results
        })
        
    except (ValidationError, ValueError) as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def evenements_proximite(request):
    """
    Trouver les événements à proximité d'un point
    """
    latitude = request.GET.get('lat')
    longitude = request.GET.get('lng')
    radius = request.GET.get('radius', 15)  # km
    date_from = request.GET.get('date_from')  # Format: YYYY-MM-DD
    
    if not latitude or not longitude:
        location = get_user_location_from_request(request)
        if location.get('latitude'):
            latitude = location['latitude']
            longitude = location['longitude']
        else:
            return Response({
                'error': 'Coordonnées GPS requises'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.utils import timezone
        geo_service = GeolocationService()
        is_valid, lat, lng = geo_service.validate_coordinates(latitude, longitude)
        radius_km = float(radius)
        
        # Trouver les lieux à proximité
        nearby_places = geo_service.find_nearby_places(lat, lng, radius_km)
        lieu_ids = [item['lieu'].id for item in nearby_places]
        
        # Filtrer les événements
        queryset = Evenement.objects.filter(lieu__id__in=lieu_ids)
        
        if date_from:
            queryset = queryset.filter(date_debut__gte=date_from)
        else:
            # Par défaut, événements à venir seulement
            queryset = queryset.filter(date_debut__gt=timezone.now())
        
        queryset = queryset.order_by('date_debut')
        
        # Calculer les distances
        results = []
        for evenement in queryset:
            distance = geo_service.calculate_distance(
                (lat, lng),
                (float(evenement.lieu.latitude), float(evenement.lieu.longitude))
            )
            
            event_data = EvenementListSerializer(evenement).data
            event_data['distance'] = distance
            event_data['lieu_distance'] = distance
            results.append(event_data)
        
        # Trier par distance
        results.sort(key=lambda x: x['distance'] or float('inf'))
        
        return Response({
            'center': {'latitude': lat, 'longitude': lng},
            'radius_km': radius_km,
            'count': len(results),
            'evenements': results
        })
        
    except (ValidationError, ValueError) as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def suggestions_adresses(request):
    """
    Suggestions d'adresses pour l'autocomplétion
    """
    query = request.GET.get('q', '')
    if len(query) < 2:
        return Response({
            'suggestions': []
        })
    
    # Suggestions spécifiques à Lomé
    lome_suggestions = LomeLocationService.get_lome_suggestions(query)
    
    # Ajouter des suggestions de géocodage si nécessaire
    geo_suggestions = []
    if len(lome_suggestions) < 3:
        geo_service = GeolocationService()
        try:
            # Recherche avec Nominatim pour plus de suggestions
            import geopy
            geolocator = geopy.geocoders.Nominatim(user_agent="evenements_lome_api")
            results = geolocator.geocode(
                f"{query}, Lomé, Togo", 
                exactly_one=False, 
                limit=5
            )
            
            if results:
                for result in results:
                    if result.address not in geo_suggestions:
                        geo_suggestions.append(result.address)
                        
        except Exception:
            pass  # Ignorer les erreurs de géocodage
    
    all_suggestions = lome_suggestions + geo_suggestions
    
    return Response({
        'query': query,
        'suggestions': all_suggestions[:8]  # Limiter à 8 suggestions
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_distance(request):
    """
    Calculer la distance entre deux points
    """
    origin_lat = request.data.get('origin_lat')
    origin_lng = request.data.get('origin_lng')
    dest_lat = request.data.get('dest_lat')
    dest_lng = request.data.get('dest_lng')
    
    if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
        return Response({
            'error': 'Coordonnées origine et destination requises'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        geo_service = GeolocationService()
        
        # Valider les coordonnées
        is_valid_origin, o_lat, o_lng = geo_service.validate_coordinates(origin_lat, origin_lng)
        is_valid_dest, d_lat, d_lng = geo_service.validate_coordinates(dest_lat, dest_lng)
        
        distance = geo_service.calculate_distance(
            (o_lat, o_lng),
            (d_lat, d_lng)
        )
        
        return Response({
            'origin': {'latitude': o_lat, 'longitude': o_lng},
            'destination': {'latitude': d_lat, 'longitude': d_lng},
            'distance_km': distance,
            'distance_m': round(distance * 1000) if distance else None
        })
        
    except ValidationError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def quartiers_lome(request):
    """
    Obtenir la liste des quartiers de Lomé avec leurs coordonnées
    """
    quartiers = []
    for key, data in LomeLocationService.QUARTIERS_LOME.items():
        quartiers.append({
            'key': key,
            'nom': data['nom'],
            'latitude': data['lat'],
            'longitude': data['lng']
        })
    
    return Response({
        'quartiers': quartiers,
        'count': len(quartiers)
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_lome_location(request):
    """
    Valider si une localisation est dans Lomé
    """
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not latitude or not longitude:
        return Response({
            'error': 'Coordonnées requises'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        geo_service = GeolocationService()
        is_valid, lat, lng = geo_service.validate_coordinates(latitude, longitude)
        
        is_in_lome = LomeLocationService.is_in_lome(lat, lng)
        
        response_data = {
            'latitude': lat,
            'longitude': lng,
            'is_in_lome': is_in_lome,
        }
        
        if is_in_lome:
            quartier = LomeLocationService.get_quartier_from_coordinates(lat, lng)
            response_data['quartier'] = quartier
        
        return Response(response_data)
        
    except ValidationError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def ip_location(request):
    """
    Obtenir la localisation à partir de l'IP du client
    """
    ip = get_client_ip(request)
    
    if not ip or ip in ['127.0.0.1', 'localhost']:
        return Response({
            'error': 'IP locale détectée',
            'ip': ip,
            'location': {
                'latitude': 6.1319,
                'longitude': 1.2228,
                'city': 'Lomé',
                'country': 'Togo',
                'source': 'default'
            }
        })
    
    ip_service = IPGeolocationService()
    location = ip_service.get_location_from_ip(ip)
    
    if location:
        return Response({
            'ip': ip,
            'location': location
        })
    else:
        return Response({
            'error': 'Localisation IP non disponible',
            'ip': ip
        }, status=status.HTTP_404_NOT_FOUND)


# Vue pour générer une carte des événements
@api_view(['GET'])
@permission_classes([AllowAny])
def map_data(request):
    """
    Données pour générer une carte des lieux et événements
    """
    from django.utils import timezone
    
    # Paramètres de filtrage
    bounds = request.GET.get('bounds')  # Format: "lat1,lng1,lat2,lng2"
    show_events = request.GET.get('events', 'true').lower() == 'true'
    show_places = request.GET.get('places', 'true').lower() == 'true'
    
    data = {
        'lieux': [],
        'evenements': [],
        'center': {'latitude': 6.1319, 'longitude': 1.2228}  # Centre de Lomé
    }
    
    # Filtrage par zone géographique si spécifiée
    if bounds:
        try:
            lat1, lng1, lat2, lng2 = map(float, bounds.split(','))
            min_lat, max_lat = min(lat1, lat2), max(lat1, lat2)
            min_lng, max_lng = min(lng1, lng2), max(lng1, lng2)
        except (ValueError, TypeError):
            bounds = None
    else:
        # Limites par défaut pour Lomé
        min_lat, max_lat = 6.0, 6.3
        min_lng, max_lng = 1.0, 1.4
    
    # Récupérer les lieux
    if show_places:
        lieux_queryset = Lieu.objects.filter(
            latitude__gte=min_lat,
            latitude__lte=max_lat,
            longitude__gte=min_lng,
            longitude__lte=max_lng
        )
        
        for lieu in lieux_queryset:
            data['lieux'].append({
                'id': str(lieu.id),
                'nom': lieu.nom,
                'categorie': lieu.categorie,
                'latitude': float(lieu.latitude),
                'longitude': float(lieu.longitude),
                'nombre_evenements': lieu.evenements.filter(
                    date_debut__gt=timezone.now()
                ).count()
            })
    
    # Récupérer les événements à venir
    if show_events:
        evenements_queryset = Evenement.objects.filter(
            date_debut__gt=timezone.now(),
            lieu__latitude__gte=min_lat,
            lieu__latitude__lte=max_lat,
            lieu__longitude__gte=min_lng,
            lieu__longitude__lte=max_lng
        ).select_related('lieu')
        
        for evenement in evenements_queryset:
            data['evenements'].append({
                'id': str(evenement.id),
                'nom': evenement.nom,
                'date_debut': evenement.date_debut.isoformat(),
                'lieu_nom': evenement.lieu.nom,
                'latitude': float(evenement.lieu.latitude),
                'longitude': float(evenement.lieu.longitude),
            })
    
    return Response(data)