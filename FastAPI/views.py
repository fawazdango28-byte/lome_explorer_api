from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.contrib.auth import login
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Avg
from .models import Utilisateur, Lieu, Evenement, AvisLieu, AvisEvenement
from .serializers import (
    UtilisateurSerializer, UtilisateurCreateSerializer, LoginSerializer,
    LieuSerializer, LieuDetailSerializer, LieuListSerializer,
    EvenementSerializer, EvenementDetailSerializer, EvenementListSerializer,
    AvisLieuSerializer, AvisEvenementSerializer
)
import logging

logger = logging.getLogger(__name__)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permission personnalisée pour autoriser seulement les propriétaires à modifier"""
    def has_object_permission(self, request, view, obj):
        # Permissions de lecture pour tous
        if request.method in permissions.SAFE_METHODS:
            return True
        # Permissions d'écriture seulement pour le propriétaire
        if hasattr(obj, 'proprietaire'):
            return obj.proprietaire == request.user
        elif hasattr(obj, 'organisateur'):
            return obj.organisateur == request.user
        elif hasattr(obj, 'utilisateur'):
            return obj.utilisateur == request.user
        return False

# Vues de test
@api_view(['GET'])
@permission_classes([])
def test_connection(request):
    """Vue de test pour vérifier que l'API fonctionne"""
    return Response({
        'message': 'API fonctionne correctement',
        'timestamp': timezone.now().isoformat(),
        'status': 'success'
    })

# Vues d'authentification
@api_view(['POST'])
@permission_classes([])
def register(request):
    """Inscription d'un nouvel utilisateur"""
    serializer = UtilisateurCreateSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UtilisateurSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([])
def login_view(request):
    """Connexion utilisateur"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UtilisateurSerializer(user).data,
            'token': token.key
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Déconnexion utilisateur"""
    try:
        request.user.auth_token.delete()
    except:
        pass
    return Response({'message': 'Déconnexion réussie'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Profil utilisateur connecté"""
    serializer = UtilisateurSerializer(request.user)
    return Response(serializer.data)


# ViewSets principaux
class LieuViewSet(viewsets.ModelViewSet):
    """ViewSet pour les lieux"""
    queryset = Lieu.objects.filter().order_by('-date_creation')
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LieuListSerializer
        elif self.action == 'retrieve':
            return LieuDetailSerializer
        return LieuSerializer
    
    def get_queryset(self):
        queryset = Lieu.objects.all().order_by('-date_creation')
        
        # Filtres
        categorie = self.request.query_params.get('categorie')
        proprietaire = self.request.query_params.get('proprietaire')
        search = self.request.query_params.get('search')
        
        if categorie:
            queryset = queryset.filter(categorie__icontains=categorie)
        
        if proprietaire:
            queryset = queryset.filter(proprietaire__username__icontains=proprietaire)
        
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | 
                Q(description__icontains=search) |
                Q(categorie__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def evenements(self, request, pk=None):
        """Récupérer tous les événements d'un lieu"""
        lieu = self.get_object()
        evenements = lieu.evenements.all().order_by('-date_debut')
        serializer = EvenementListSerializer(evenements, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def avis(self, request, pk=None):
        """Récupérer tous les avis d'un lieu"""
        lieu = self.get_object()
        avis = lieu.avis.all().order_by('-date')
        serializer = AvisLieuSerializer(avis, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def recherche_proximite(self, request):
        """Recherche de lieux par proximité géographique"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        rayon = request.query_params.get('rayon', 10)  # km par défaut
        
        if not lat or not lng:
            return Response(
                {'error': 'Latitude et longitude requises'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calcul approximatif de proximité
        lat_float = float(lat)
        lng_float = float(lng)
        rayon_float = float(rayon)
        
        # Approximation simple
        delta = rayon_float / 111.0  # 1 degré ≈ 111 km
        
        queryset = self.get_queryset().filter(
            latitude__gte=lat_float - delta,
            latitude__lte=lat_float + delta,
            longitude__gte=lng_float - delta,
            longitude__lte=lng_float + delta
        )
        
        serializer = LieuListSerializer(queryset, many=True)
        return Response(serializer.data)


class EvenementViewSet(viewsets.ModelViewSet):
    """ViewSet pour les événements - CORRIGÉ"""
    queryset = Evenement.objects.all().order_by('-date_debut')
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EvenementListSerializer
        elif self.action == 'retrieve':
            # ✅ CORRECTION: Utiliser EvenementSerializer au lieu de EvenementDetailSerializer
            return EvenementSerializer
        return EvenementSerializer
    
    def get_queryset(self):
        queryset = Evenement.objects.select_related(
            'lieu', 'organisateur'
        ).prefetch_related('avis').order_by('-date_debut')
        
        # Filtres
        lieu = self.request.query_params.get('lieu')
        organisateur = self.request.query_params.get('organisateur')
        date_debut = self.request.query_params.get('date_debut')
        date_fin = self.request.query_params.get('date_fin')
        search = self.request.query_params.get('search')
        a_venir = self.request.query_params.get('a_venir')
        passes = self.request.query_params.get('passes')
        
        if lieu:
            queryset = queryset.filter(lieu__nom__icontains=lieu)
        
        if organisateur:
            queryset = queryset.filter(organisateur__username__icontains=organisateur)
        
        if date_debut:
            queryset = queryset.filter(date_debut__gte=date_debut)
        
        if date_fin:
            queryset = queryset.filter(date_fin__lte=date_fin)
        
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | 
                Q(description__icontains=search)
            )
        
        if a_venir and a_venir.lower() == 'true':
            queryset = queryset.filter(date_debut__gt=timezone.now())
        
        if passes and passes.lower() == 'true':
            queryset = queryset.filter(date_fin__lt=timezone.now())
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """
        ✅ CORRECTION: Surcharge de retrieve() pour une meilleure gestion des erreurs
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Evenement.DoesNotExist:
            logger.error(f"Événement non trouvé: {kwargs.get('pk')}")
            return Response(
                {'error': 'Événement non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Erreur retrieve événement: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Erreur lors de la récupération de l\'événement'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def avis(self, request, pk=None):
        """Récupérer tous les avis d'un événement"""
        try:
            evenement = self.get_object()
            avis = evenement.avis.all().order_by('-date')
            serializer = AvisEvenementSerializer(avis, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Erreur récupération avis: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la récupération des avis'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def aujourd_hui(self, request):
        """Événements d'aujourd'hui"""
        aujourd_hui = timezone.now().date()
        queryset = self.get_queryset().filter(
            date_debut__date=aujourd_hui
        )
        serializer = EvenementListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def cette_semaine(self, request):
        """Événements de cette semaine"""
        today = timezone.now().date()
        fin_semaine = today + timezone.timedelta(days=7)
        
        queryset = self.get_queryset().filter(
            date_debut__date__range=[today, fin_semaine]
        )
        serializer = EvenementListSerializer(queryset, many=True)
        return Response(serializer.data)


class AvisLieuViewSet(viewsets.ModelViewSet):
    """ViewSet pour les avis de lieux"""
    queryset = AvisLieu.objects.all().order_by('-date')
    serializer_class = AvisLieuSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        queryset = AvisLieu.objects.all().order_by('-date')
        lieu_id = self.request.query_params.get('lieu')
        if lieu_id:
            queryset = queryset.filter(lieu__id=lieu_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Création d'un avis avec logs détaillés"""
        print("=" * 80)
        print("🔍 AvisLieuViewSet.create() appelée")
        print(f"   User: {request.user}")
        print(f"   User authenticated: {request.user.is_authenticated}")
        print(f"   Request data: {request.data}")
        print(f"   Request headers: {dict(request.headers)}")
        print("=" * 80)
        
        try:
            serializer = self.get_serializer(data=request.data)
            print(f"🔍 Serializer créé: {serializer}")
            
            print(f"🔍 Validation en cours...")
            is_valid = serializer.is_valid(raise_exception=False)
            print(f"   is_valid: {is_valid}")
            
            if not is_valid:
                print(f"   ❌ Erreurs de validation: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"   ✅ Validation OK")
            print(f"   validated_data: {serializer.validated_data}")
            
            print(f"🔍 Sauvegarde en cours...")
            self.perform_create(serializer)
            
            print(f"   ✅ Avis créé avec succès")
            headers = self.get_success_headers(serializer.data)
            print("=" * 80)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            print(f"❌ Exception dans create(): {e}")
            print(f"❌ Type: {type(e)}")
            import traceback
            traceback.print_exc()
            print("=" * 80)
            raise
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mon_avis(self, request):
        """✅ NOUVEAU: Endpoint pour vérifier si l'utilisateur a déjà donné un avis"""
        lieu_id = request.query_params.get('lieu_id')
        
        if not lieu_id:
            return Response({
                'error': 'lieu_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            avis = AvisLieu.objects.get(
                utilisateur=request.user,
                lieu__id=lieu_id
            )
            return Response({
                'has_avis': True,
                'avis': AvisLieuSerializer(avis).data
            })
        except AvisLieu.DoesNotExist:
            return Response({
                'has_avis': False,
                'avis': None
            })


class AvisEvenementViewSet(viewsets.ModelViewSet):
    """ViewSet pour les avis d'événements"""
    queryset = AvisEvenement.objects.all().order_by('-date')
    serializer_class = AvisEvenementSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        queryset = AvisEvenement.objects.all().order_by('-date')
        evenement_id = self.request.query_params.get('evenement')
        if evenement_id:
            queryset = queryset.filter(evenement__id=evenement_id)
        return queryset


# Vues pour les statistiques et données publiques
@api_view(['GET'])
@permission_classes([])
def statistiques(request):
    """Statistiques générales de l'application"""
    return Response({
        'nombre_lieux': Lieu.objects.count(),
        'nombre_evenements': Evenement.objects.count(),
        'nombre_utilisateurs': Utilisateur.objects.filter(is_active=True).count(),
        'nombre_avis_lieux': AvisLieu.objects.count(),
        'nombre_avis_evenements': AvisEvenement.objects.count(),
        'evenements_a_venir': Evenement.objects.filter(
            date_debut__gt=timezone.now()
        ).count()
    })


@api_view(['GET'])
@permission_classes([])
def lieux_populaires(request):
    """Top 10 des lieux les plus populaires (par nombre d'événements)"""
    from django.db.models import Count
    
    lieux = Lieu.objects.annotate(
        nb_evenements=Count('evenements')
    ).order_by('-nb_evenements')[:10]
    
    serializer = LieuListSerializer(lieux, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([])
def evenements_tendances(request):
    """Événements tendances (à venir avec le plus d'avis positifs)"""
    from django.db.models import Count, Avg
    
    evenements = Evenement.objects.filter(
        date_debut__gt=timezone.now()
    ).annotate(
        nb_avis=Count('avis'),
        moyenne_note=Avg('avis__note')
    ).filter(nb_avis__gt=0).order_by('-moyenne_note', '-nb_avis')[:10]
    
    serializer = EvenementListSerializer(evenements, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([])
def donnees_lome(request):
    """Données spécifiques à Lomé"""
    # Coordonnées approximatives de Lomé
    lome_lat_min, lome_lat_max = 6.0, 6.3
    lome_lng_min, lome_lng_max = 1.0, 1.4
    
    lieux_lome = Lieu.objects.filter(
        latitude__range=[lome_lat_min, lome_lat_max],
        longitude__range=[lome_lng_min, lome_lng_max]
    )
    
    evenements_lome = Evenement.objects.filter(
        lieu__in=lieux_lome,
        date_debut__gt=timezone.now()
    )
    
    return Response({
        'nombre_lieux_lome': lieux_lome.count(),
        'nombre_evenements_a_venir': evenements_lome.count(),
        'categories_lieux': list(
            lieux_lome.values_list('categorie', flat=True).distinct()
        ),
        'prochains_evenements': EvenementListSerializer(
            evenements_lome[:5], many=True
        ).data
    })