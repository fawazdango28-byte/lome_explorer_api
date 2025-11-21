
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import Utilisateur, Lieu, Evenement, AvisLieu, AvisEvenement
from .serializers import UtilisateurCreateSerializer, LoginSerializer
from .geolocation_services import GeolocationService, LomeLocationService


def index(request):
    """Page d'accueil"""
    # Statistiques
    stats = {
        'total_lieux': Lieu.objects.count(),
        'total_evenements': Evenement.objects.count(),
        'evenements_a_venir': Evenement.objects.filter(
            date_debut__gt=timezone.now()
        ).count(),
    }
    
    # Événements à venir
    evenements_a_venir = Evenement.objects.filter(
        date_debut__gt=timezone.now()
    ).order_by('date_debut')[:6]
    
    # Lieux populaires
    lieux_populaires = Lieu.objects.annotate(
        nb_evenements=Count('evenements')
    ).order_by('-nb_evenements')[:6]
    
    context = {
        'stats': stats,
        'evenements_a_venir': evenements_a_venir,
        'lieux_populaires': lieux_populaires,
    }
    return render(request, 'index.html', context)


def liste_lieux(request):
    """Liste des lieux"""
    lieux = Lieu.objects.all().order_by('-date_creation')
    
    # Filtres
    categorie = request.GET.get('categorie')
    search = request.GET.get('search')
    
    if categorie:
        lieux = lieux.filter(categorie__icontains=categorie)
    
    if search:
        lieux = lieux.filter(
            Q(nom__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(lieux, 12)
    page_number = request.GET.get('page')
    lieux_page = paginator.get_page(page_number)
    
    # Catégories disponibles
    categories = Lieu.objects.values_list('categorie', flat=True).distinct()
    
    context = {
        'lieux': lieux_page,
        'categories': categories,
        'categorie_active': categorie,
        'search_query': search,
    }
    return render(request, 'lieux/liste.html', context)


def detail_lieu(request, lieu_id):
    """Détail d'un lieu"""
    lieu = get_object_or_404(Lieu, id=lieu_id)
    
    # Événements du lieu
    evenements = lieu.evenements.filter(
        date_debut__gt=timezone.now()
    ).order_by('date_debut')
    
    # Avis
    avis = lieu.avis.all().order_by('-date')
    
    # Moyenne des avis
    moyenne_avis = avis.aggregate(Avg('note'))['note__avg']
    
    context = {
        'lieu': lieu,
        'evenements': evenements,
        'avis': avis,
        'moyenne_avis': moyenne_avis,
    }
    return render(request, 'lieux/detail.html', context)


@login_required
def create_lieu(request):
    """Créer un lieu"""
    if request.method == 'POST':
        nom = request.POST.get('nom')
        description = request.POST.get('description')
        categorie = request.POST.get('categorie')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        try:
            lieu = Lieu.objects.create(
                nom=nom,
                description=description,
                categorie=categorie,
                latitude=latitude,
                longitude=longitude,
                proprietaire=request.user
            )
            messages.success(request, f'Lieu "{lieu.nom}" créé avec succès!')
            return redirect('detail_lieu', lieu_id=lieu.id)
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return render(request, 'lieux/create.html')

@login_required
def edit_lieu(request, lieu_id):
    """Modifier un lieu"""
    lieu = get_object_or_404(Lieu, id=lieu_id)
    
    # Vérifier que l'utilisateur est le propriétaire
    if lieu.proprietaire != request.user:
        messages.error(request, 'Vous n\'êtes pas autorisé à modifier ce lieu.')
        return redirect('detail_lieu', lieu_id=lieu.id)
    
    if request.method == 'POST':
        lieu.nom = request.POST.get('nom')
        lieu.description = request.POST.get('description')
        lieu.categorie = request.POST.get('categorie')
        lieu.latitude = request.POST.get('latitude')
        lieu.longitude = request.POST.get('longitude')
        
        try:
            lieu.save()
            messages.success(request, f'Lieu "{lieu.nom}" modifié avec succès!')
            return redirect('detail_lieu', lieu_id=lieu.id)
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')
    
    categories = ['Restaurant', 'Bar', 'Culture', 'Sport', 'Parc', 'Musée', 
                  'Théâtre', 'Salle de concert', 'Centre commercial', 'Autre']
    context = {
        'lieu': lieu,
        'categories': categories
    }
    return render(request, 'lieux/edit.html', context)


@login_required
def delete_lieu(request, lieu_id):
    """Supprimer un lieu"""
    lieu = get_object_or_404(Lieu, id=lieu_id)
    
    # Vérifier que l'utilisateur est le propriétaire
    if lieu.proprietaire != request.user:
        messages.error(request, 'Vous n\'êtes pas autorisé à supprimer ce lieu.')
        return redirect('detail_lieu', lieu_id=lieu.id)
    
    if request.method == 'POST':
        nom = lieu.nom
        lieu.delete()
        messages.success(request, f'Lieu "{nom}" supprimé avec succès!')
        return redirect('liste_lieux')
    
    return redirect('detail_lieu', lieu_id=lieu.id)


def liste_evenements(request):
    """Liste des événements"""
    evenements = Evenement.objects.all().order_by('date_debut')
    
    # Filtres
    lieu_id = request.GET.get('lieu')
    search = request.GET.get('search')
    date_debut = request.GET.get('date_debut')
    
    if lieu_id:
        evenements = evenements.filter(lieu_id=lieu_id)
    
    if search:
        evenements = evenements.filter(
            Q(nom__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if date_debut:
        evenements = evenements.filter(date_debut__gte=date_debut)
    else:
        # Par défaut, afficher seulement les événements à venir
        evenements = evenements.filter(date_debut__gt=timezone.now())
    
    # Pagination
    paginator = Paginator(evenements, 12)
    page_number = request.GET.get('page')
    evenements_page = paginator.get_page(page_number)
    
    context = {
        'evenements': evenements_page,
        'search_query': search,
    }
    return render(request, 'evenements/liste.html', context)


def detail_evenement(request, evenement_id):
    """Détail d'un événement"""
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    # Avis
    avis = evenement.avis.all().order_by('-date')
    
    # Moyenne des avis
    moyenne_avis = avis.aggregate(Avg('note'))['note__avg']
    
    context = {
        'evenement': evenement,
        'avis': avis,
        'moyenne_avis': moyenne_avis,
    }
    return render(request, 'evenements/detail.html', context)


@login_required
def create_evenement(request):
    """Créer un événement"""
    if request.method == 'POST':
        nom = request.POST.get('nom')
        description = request.POST.get('description')
        lieu_id = request.POST.get('lieu')
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')
        
        try:
            lieu = Lieu.objects.get(id=lieu_id)
            evenement = Evenement.objects.create(
                nom=nom,
                description=description,
                lieu=lieu,
                date_debut=date_debut,
                date_fin=date_fin,
                organisateur=request.user
            )
            messages.success(request, f'Événement "{evenement.nom}" créé avec succès!')
            return redirect('detail_evenement', evenement_id=evenement.id)
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    lieux = Lieu.objects.all()
    context = {'lieux': lieux}
    return render(request, 'evenements/create.html', context)

@login_required
def edit_evenement(request, evenement_id):
    """Modifier un événement"""
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    # Vérifier que l'utilisateur est l'organisateur
    if evenement.organisateur != request.user:
        messages.error(request, 'Vous n\'êtes pas autorisé à modifier cet événement.')
        return redirect('detail_evenement', evenement_id=evenement.id)
    
    if request.method == 'POST':
        evenement.nom = request.POST.get('nom')
        evenement.description = request.POST.get('description')
        lieu_id = request.POST.get('lieu')
        evenement.lieu = Lieu.objects.get(id=lieu_id)
        evenement.date_debut = request.POST.get('date_debut')
        evenement.date_fin = request.POST.get('date_fin')
        
        try:
            evenement.save()
            messages.success(request, f'Événement "{evenement.nom}" modifié avec succès!')
            return redirect('detail_evenement', evenement_id=evenement.id)
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')
    
    lieux = Lieu.objects.all()
    context = {
        'evenement': evenement,
        'lieux': lieux
    }
    return render(request, 'evenements/edit.html', context)


@login_required
def delete_evenement(request, evenement_id):
    """Supprimer un événement"""
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    # Vérifier que l'utilisateur est l'organisateur
    if evenement.organisateur != request.user:
        messages.error(request, 'Vous n\'êtes pas autorisé à supprimer cet événement.')
        return redirect('detail_evenement', evenement_id=evenement.id)
    
    if request.method == 'POST':
        nom = evenement.nom
        evenement.delete()
        messages.success(request, f'Événement "{nom}" supprimé avec succès!')
        return redirect('liste_evenements')
    
    return redirect('detail_evenement', evenement_id=evenement.id)


def login_view(request):
    """Connexion"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenue {user.username}!')
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    
    return render(request, 'auth/login.html')


def register_view(request):
    """Inscription"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        tel = request.POST.get('tel', '')
        
        if password != password_confirm:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
        else:
            try:
                user = Utilisateur.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    tel=tel
                )
                login(request, user)
                messages.success(request, 'Compte créé avec succès!')
                return redirect('index')
            except Exception as e:
                messages.error(request, f'Erreur: {str(e)}')
    
    return render(request, 'auth/register.html')


@login_required
def logout_view(request):
    """Déconnexion"""
    logout(request)
    messages.success(request, 'Déconnexion réussie.')
    return redirect('index')


@login_required
def profile_view(request):
    """Profil utilisateur"""
    user = request.user
    
    # Lieux de l'utilisateur
    mes_lieux = user.lieux.all()
    
    # Événements organisés
    mes_evenements = user.evenements_organises.all().order_by('-date_debut')
    
    # Avis donnés
    avis_lieux = user.avis_lieux_donnes.all().order_by('-date')
    avis_evenements = user.avis_evenements_donnes.all().order_by('-date')
    
    context = {
        'user': user,
        'mes_lieux': mes_lieux,
        'mes_evenements': mes_evenements,
        'avis_lieux': avis_lieux,
        'avis_evenements': avis_evenements,
    }
    return render(request, 'auth/profile.html', context)


def carte_interactive(request):
    """Carte interactive des événements et lieux"""
    import json
    from django.core.serializers import serialize
    
    lieux = Lieu.objects.all()
    evenements = Evenement.objects.filter(
        date_debut__gt=timezone.now()
    )[:50]
    
    # Préparer les données pour JavaScript
    lieux_json = []
    for lieu in lieux:
        lieux_json.append({
            'id': str(lieu.id),
            'nom': lieu.nom,
            'categorie': lieu.categorie,
            'description': lieu.description[:100],
            'lat': float(lieu.latitude),
            'lng': float(lieu.longitude),
            'url': f'/fastapi/lieux/{lieu.id}/'
        })
    
    evenements_json = []
    for evt in evenements:
        evenements_json.append({
            'id': str(evt.id),
            'nom': evt.nom,
            'lieu': evt.lieu.nom,
            'date': evt.date_debut.strftime('%d/%m/%Y %H:%M'),
            'lat': float(evt.lieu.latitude),
            'lng': float(evt.lieu.longitude),
            'url': f'/fastapi/evenements/{evt.id}/'
        })
    
    context = {
        'lieux': lieux,
        'evenements': evenements,
        'lieux_json': json.dumps(lieux_json),
        'evenements_json': json.dumps(evenements_json),
    }
    return render(request, 'map/carte.html', context)