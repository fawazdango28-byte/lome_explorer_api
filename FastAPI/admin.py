from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Utilisateur, Lieu, Evenement, AvisLieu, AvisEvenement


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Administration des utilisateurs"""
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'tel', 'is_active', 'date_joined', 'nombre_lieux', 'nombre_evenements'
    ]
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    # Ajouter les champs personnalisés
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('tel',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('email', 'tel')
        }),
    )
    
    def nombre_lieux(self, obj):
        count = obj.lieux.count()
        if count > 0:
            url = reverse('admin:FastAPI_lieu_changelist') + f'?proprietaire__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    nombre_lieux.short_description = 'Lieux'
    
    def nombre_evenements(self, obj):
        count = obj.evenements_organises.count()
        if count > 0:
            url = reverse('admin:FastAPI_evenement_changelist') + f'?organisateur__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    nombre_evenements.short_description = 'Événements'


@admin.register(Lieu)
class LieuAdmin(admin.ModelAdmin):
    """Administration des lieux"""
    list_display = [
        'nom', 'categorie', 'proprietaire', 'coordonnees', 
        'date_creation', 'nombre_evenements', 'moyenne_avis'
    ]
    list_filter = ['categorie', 'date_creation', 'proprietaire']
    search_fields = ['nom', 'description', 'categorie']
    ordering = ['-date_creation']
    date_hierarchy = 'date_creation'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'description', 'categorie', 'proprietaire')
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'description': 'Coordonnées GPS du lieu'
        }),
    )
    
    readonly_fields = ['date_creation']
    
    def coordonnees(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    coordonnees.short_description = 'Coordonnées GPS'
    
    def nombre_evenements(self, obj):
        count = obj.evenements.count()
        if count > 0:
            url = reverse('admin:FastAPI_evenement_changelist') + f'?lieu__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    nombre_evenements.short_description = 'Événements'
    
    def moyenne_avis(self, obj):
        avis = obj.avis.all()
        if avis.exists():
            moyenne = sum(avis.values_list('note', flat=True)) / avis.count()
            stars = '⭐' * int(moyenne)
            return f"{moyenne:.1f} {stars}"
        return "Aucun avis"
    moyenne_avis.short_description = 'Avis'
    
    actions = ['exporter_coordonnees']
    
    def exporter_coordonnees(self, request, queryset):
        """Action pour exporter les coordonnées des lieux sélectionnés"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="lieux_coordonnees.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Nom', 'Catégorie', 'Latitude', 'Longitude', 'Description'])
        
        for lieu in queryset:
            writer.writerow([
                lieu.nom, lieu.categorie, lieu.latitude, 
                lieu.longitude, lieu.description[:100]
            ])
        
        self.message_user(request, f"{queryset.count()} lieux exportés avec succès.")
        return response
    
    exporter_coordonnees.short_description = "Exporter les coordonnées GPS"


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    """Administration des événements"""
    list_display = [
        'nom', 'organisateur', 'lieu', 'date_debut', 
        'date_fin', 'statut_evenement', 'nombre_avis'
    ]
    list_filter = ['date_debut', 'organisateur', 'lieu__categorie']
    search_fields = ['nom', 'description', 'organisateur__username', 'lieu__nom']
    ordering = ['-date_debut']
    date_hierarchy = 'date_debut'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'description', 'organisateur')
        }),
        ('Lieu et dates', {
            'fields': ('lieu', 'date_debut', 'date_fin')
        }),
    )
    
    def statut_evenement(self, obj):
        from django.utils import timezone
        now = timezone.now()
        
        if obj.date_debut > now:
            return format_html('<span style="color: blue;">À venir</span>')
        elif obj.date_debut <= now <= obj.date_fin:
            return format_html('<span style="color: green;">En cours</span>')
        else:
            return format_html('<span style="color: gray;">Terminé</span>')
    statut_evenement.short_description = 'Statut'
    
    def nombre_avis(self, obj):
        count = obj.avis.count()
        if count > 0:
            url = reverse('admin:FastAPI_avisevenement_changelist') + f'?evenement__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    nombre_avis.short_description = 'Avis'
    
    actions = ['marquer_termines']
    
    def marquer_termines(self, request, queryset):
        """Action personnalisée (exemple)"""
        from django.utils import timezone
        termines = queryset.filter(date_fin__lt=timezone.now())
        count = termines.count()
        self.message_user(request, f"{count} événements terminés identifiés.")
    
    marquer_termines.short_description = "Identifier les événements terminés"


class AvisBaseAdmin(admin.ModelAdmin):
    """Classe de base pour l'administration des avis"""
    list_display = ['utilisateur', 'note_etoiles', 'texte_court', 'date']
    list_filter = ['note', 'date']
    search_fields = ['utilisateur__username', 'texte']
    ordering = ['-date']
    date_hierarchy = 'date'
    
    readonly_fields = ['date']
    
    def note_etoiles(self, obj):
        stars = '⭐' * obj.note + '☆' * (5 - obj.note)
        return f"{obj.note}/5 {stars}"
    note_etoiles.short_description = 'Note'
    
    def texte_court(self, obj):
        if len(obj.texte) > 50:
            return obj.texte[:50] + "..."
        return obj.texte
    texte_court.short_description = 'Commentaire'


@admin.register(AvisLieu)
class AvisLieuAdmin(AvisBaseAdmin):
    """Administration des avis de lieux"""
    list_display = AvisBaseAdmin.list_display + ['lieu']
    list_filter = AvisBaseAdmin.list_filter + ['lieu__categorie']
    search_fields = AvisBaseAdmin.search_fields + ['lieu__nom']


@admin.register(AvisEvenement)
class AvisEvenementAdmin(AvisBaseAdmin):
    """Administration des avis d'événements"""
    list_display = AvisBaseAdmin.list_display + ['evenement']
    list_filter = AvisBaseAdmin.list_filter + ['evenement__date_debut']
    search_fields = AvisBaseAdmin.search_fields + ['evenement__nom']


# Configuration générale de l'admin
admin.site.site_header = "Administration - Événements Lomé"
admin.site.site_title = "Événements Lomé Admin"
admin.site.index_title = "Tableau de bord"

# Personnalisation du tableau de bord
class EventsAdminConfig(AdminConfig):
    default_site = 'FastAPI.admin.EventsAdminSite'

class EventsAdminSite(admin.AdminSite):
    site_header = "Gestion des Événements - Lomé"
    site_title = "Admin Événements"
    index_title = "Tableau de bord principal"
    
    def index(self, request, extra_context=None):
        from django.utils import timezone
        
        # Statistiques pour le tableau de bord
        extra_context = extra_context or {}
        extra_context.update({
            'total_utilisateurs': Utilisateur.objects.filter(is_active=True).count(),
            'total_lieux': Lieu.objects.count(),
            'total_evenements': Evenement.objects.count(),
            'evenements_a_venir': Evenement.objects.filter(
                date_debut__gt=timezone.now()
            ).count(),
            'avis_total': AvisLieu.objects.count() + AvisEvenement.objects.count(),
        })
        
        return super().index(request, extra_context)