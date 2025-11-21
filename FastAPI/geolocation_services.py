import requests
from geopy.geocoders import Nominatim, GoogleV3
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class GeolocationService:
    """Service principal de géolocalisation"""
    
    def __init__(self):
        self.nominatim = Nominatim(user_agent="evenements_lome_api")
        # Si vous avez une clé Google Maps API
        self.google_geocoder = None
        if hasattr(settings, 'GOOGLE_MAPS_API_KEY'):
            self.google_geocoder = GoogleV3(api_key=settings.GOOGLE_MAPS_API_KEY)
    
    def geocode_address(self, address, prefer_lome=True):
        """
        Convertir une adresse en coordonnées GPS
        """
        cache_key = f"geocode_{address.lower().replace(' ', '_')}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Ajouter "Lomé, Togo" pour améliorer la précision
            if prefer_lome and "lomé" not in address.lower() and "lome" not in address.lower():
                search_address = f"{address}, Lomé, Togo"
            else:
                search_address = address
            
            # Essayer avec Nominatim en premier (gratuit)
            location = self.nominatim.geocode(
                search_address, 
                timeout=10,
                exactly_one=True
            )
            
            if location:
                result = {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'address': location.address,
                    'provider': 'nominatim'
                }
                # Cache pour 24h
                cache.set(cache_key, result, 60 * 60 * 24)
                return result
            
            # Fallback sur Google Maps si disponible
            if self.google_geocoder:
                location = self.google_geocoder.geocode(search_address, timeout=10)
                if location:
                    result = {
                        'latitude': location.latitude,
                        'longitude': location.longitude,
                        'address': location.address,
                        'provider': 'google'
                    }
                    cache.set(cache_key, result, 60 * 60 * 24)
                    return result
            
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Erreur de géocodage pour '{address}': {e}")
            return None
    
    def reverse_geocode(self, latitude, longitude):
        """
        Convertir des coordonnées GPS en adresse
        """
        cache_key = f"reverse_{latitude}_{longitude}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            location = self.nominatim.reverse(
                f"{latitude}, {longitude}",
                timeout=10,
                exactly_one=True
            )
            
            if location:
                result = {
                    'address': location.address,
                    'latitude': latitude,
                    'longitude': longitude,
                    'provider': 'nominatim'
                }
                # Cache pour 24h
                cache.set(cache_key, result, 60 * 60 * 24)
                return result
            
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Erreur de géocodage inverse pour {latitude}, {longitude}: {e}")
            return None
    
    def calculate_distance(self, coord1, coord2):
        """
        Calculer la distance entre deux points GPS
        coord1 et coord2 sont des tuples (latitude, longitude)
        Retourne la distance en kilomètres
        """
        try:
            distance = geodesic(coord1, coord2).kilometers
            return round(distance, 2)
        except Exception as e:
            logger.error(f"Erreur calcul distance: {e}")
            return None
    
    def find_nearby_places(self, latitude, longitude, radius_km=10):
        """
        Trouver les lieux à proximité d'un point
        """
        from .models import Lieu
        
        # Calcul approximatif pour filtrer en base (optimisation)
        # 1 degré ≈ 111 km
        delta = radius_km / 111.0
        
        nearby_lieux = Lieu.objects.filter(
            latitude__gte=latitude - delta,
            latitude__lte=latitude + delta,
            longitude__gte=longitude - delta,
            longitude__lte=longitude + delta
        )
        
        # Calcul précis de la distance
        results = []
        for lieu in nearby_lieux:
            distance = self.calculate_distance(
                (latitude, longitude),
                (float(lieu.latitude), float(lieu.longitude))
            )
            if distance and distance <= radius_km:
                results.append({
                    'lieu': lieu,
                    'distance': distance
                })
        
        # Trier par distance
        results.sort(key=lambda x: x['distance'])
        return results
    
    def validate_coordinates(self, latitude, longitude):
        """
        Valider des coordonnées GPS
        """
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            if not (-90 <= lat <= 90):
                raise ValidationError("Latitude doit être entre -90 et 90")
            
            if not (-180 <= lng <= 180):
                raise ValidationError("Longitude doit être entre -180 et 180")
            
            return True, lat, lng
            
        except (ValueError, TypeError):
            raise ValidationError("Coordonnées GPS invalides")


class IPGeolocationService:
    """Service pour obtenir la position à partir de l'IP"""
    
    @staticmethod
    def get_location_from_ip(ip_address):
        """
        Obtenir la localisation approximative à partir d'une IP
        """
        cache_key = f"ip_location_{ip_address}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Service gratuit ipapi.co
            response = requests.get(
                f"https://ipapi.co/{ip_address}/json/",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('error'):
                    logger.warning(f"Erreur API IP: {data.get('reason')}")
                    return None
                
                result = {
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'city': data.get('city'),
                    'country': data.get('country_name'),
                    'region': data.get('region'),
                    'provider': 'ipapi'
                }
                
                # Cache pour 1h
                cache.set(cache_key, result, 60 * 60)
                return result
            
        except requests.RequestException as e:
            logger.error(f"Erreur requête géolocalisation IP: {e}")
        
        # Fallback: service alternatif
        try:
            response = requests.get(
                f"http://ip-api.com/json/{ip_address}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    result = {
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                        'city': data.get('city'),
                        'country': data.get('country'),
                        'region': data.get('regionName'),
                        'provider': 'ip-api'
                    }
                    
                    cache.set(cache_key, result, 60 * 60)
                    return result
                    
        except requests.RequestException as e:
            logger.error(f"Erreur service fallback géolocalisation IP: {e}")
        
        return None


class LomeLocationService:
    """Service spécialisé pour les données de Lomé"""
    
    # Coordonnées approximatives des quartiers de Lomé
    QUARTIERS_LOME = {
        'centre_ville': {'lat': 6.1319, 'lng': 1.2228, 'nom': 'Centre-ville'},
        'bè': {'lat': 6.1500, 'lng': 1.2000, 'nom': 'Bè'},
        'tokoin': {'lat': 6.1400, 'lng': 1.2400, 'nom': 'Tokoin'},
        'adidogomé': {'lat': 6.1100, 'lng': 1.2100, 'nom': 'Adidogomé'},
        'nyékonakpoé': {'lat': 6.1600, 'lng': 1.2300, 'nom': 'Nyékonakpoé'},
        'aflao_gakli': {'lat': 6.1000, 'lng': 1.1900, 'nom': 'Aflao Gakli'},
        'amoutivé': {'lat': 6.1200, 'lng': 1.2500, 'nom': 'Amoutivé'},
    }
    
    @classmethod
    def get_quartier_from_coordinates(cls, latitude, longitude):
        """
        Déterminer le quartier de Lomé à partir des coordonnées
        """
        geo_service = GeolocationService()
        
        distances = []
        for quartier_key, quartier_data in cls.QUARTIERS_LOME.items():
            distance = geo_service.calculate_distance(
                (latitude, longitude),
                (quartier_data['lat'], quartier_data['lng'])
            )
            if distance:
                distances.append({
                    'quartier': quartier_data['nom'],
                    'key': quartier_key,
                    'distance': distance
                })
        
        if distances:
            # Retourner le quartier le plus proche
            distances.sort(key=lambda x: x['distance'])
            closest = distances[0]
            
            # Si la distance est raisonnable (< 5km), retourner le quartier
            if closest['distance'] < 5:
                return closest['quartier']
        
        return 'Lomé'  # Valeur par défaut
    
    @classmethod
    def is_in_lome(cls, latitude, longitude):
        """
        Vérifier si des coordonnées sont dans Lomé
        """
        # Limites approximatives de Lomé
        lome_bounds = {
            'north': 6.2,
            'south': 6.0,
            'east': 1.4,
            'west': 1.0
        }
        
        return (
            lome_bounds['south'] <= latitude <= lome_bounds['north'] and
            lome_bounds['west'] <= longitude <= lome_bounds['east']
        )
    
    @classmethod
    def get_lome_suggestions(cls, query):
        """
        Suggestions d'adresses pour Lomé
        """
        suggestions = []
        
        # Lieux connus de Lomé
        lieux_connus = [
            'Marché de Tokoin',
            'Port de Lomé',
            'Université de Lomé',
            'Stade de Kégué',
            'Palais des Congrès',
            'Grand Marché de Lomé',
            'Plage de Lomé',
            'Cathédrale du Sacré-Cœur',
        ]
        
        query_lower = query.lower()
        for lieu in lieux_connus:
            if query_lower in lieu.lower():
                suggestions.append(lieu)
        
        # Ajouter les quartiers
        for quartier_data in cls.QUARTIERS_LOME.values():
            if query_lower in quartier_data['nom'].lower():
                suggestions.append(quartier_data['nom'])
        
        return suggestions[:5]  # Limiter à 5 suggestions


# Fonctions utilitaires pour les vues
def get_user_location_from_request(request):
    """
    Obtenir la localisation de l'utilisateur à partir de la requête
    """
    # Essayer d'abord les coordonnées GPS si fournies
    lat = request.GET.get('lat') or request.POST.get('latitude')
    lng = request.GET.get('lng') or request.POST.get('longitude')
    
    if lat and lng:
        geo_service = GeolocationService()
        try:
            is_valid, lat, lng = geo_service.validate_coordinates(lat, lng)
            if is_valid:
                return {'latitude': lat, 'longitude': lng, 'source': 'gps'}
        except ValidationError:
            pass
    
    # Fallback sur l'IP
    ip = get_client_ip(request)
    if ip:
        ip_service = IPGeolocationService()
        location = ip_service.get_location_from_ip(ip)
        if location and location.get('latitude'):
            return {
                'latitude': location['latitude'],
                'longitude': location['longitude'],
                'city': location.get('city'),
                'source': 'ip'
            }
    
    # Position par défaut: centre de Lomé
    return {
        'latitude': 6.1319,
        'longitude': 1.2228,
        'city': 'Lomé',
        'source': 'default'
    }


def get_client_ip(request):
    """Récupérer l'IP réelle du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip