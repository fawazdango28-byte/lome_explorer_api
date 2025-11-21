from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Utilisateur(AbstractUser):
    """Modèle utilisateur unique pour l'application"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    tel = models.CharField(max_length=20, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
    
    def __str__(self):
        return f"{self.username} ({self.email})"


class Lieu(models.Model):
    """Modèle Lieu"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    description = models.TextField()
    categorie = models.CharField(max_length=100)
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    
    # Relation avec l'utilisateur propriétaire
    proprietaire = models.ForeignKey(
        Utilisateur, 
        on_delete=models.CASCADE, 
        related_name='lieux'
    )
    
    class Meta:
        verbose_name = "Lieu"
        verbose_name_plural = "Lieux"
    
    def __str__(self):
        return self.nom


class Evenement(models.Model):
    """Modèle Événement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    
    # Relations
    lieu = models.ForeignKey(
        Lieu, 
        on_delete=models.CASCADE, 
        related_name='evenements'
    )
    organisateur = models.ForeignKey(
        Utilisateur, 
        on_delete=models.CASCADE, 
        related_name='evenements_organises'
    )
    
    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['-date_debut']
    
    def __str__(self):
        return f"{self.nom} - {self.date_debut.strftime('%d/%m/%Y')}"


class AvisLieu(models.Model):
    """Avis spécifiques aux lieux"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note de 1 à 5"
    )
    texte = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    
    # Relations
    utilisateur = models.ForeignKey(
        Utilisateur, 
        on_delete=models.CASCADE, 
        related_name='avis_lieux_donnes'
    )
    lieu = models.ForeignKey(
        Lieu, 
        on_delete=models.CASCADE, 
        related_name='avis'
    )
    
    class Meta:
        verbose_name = "Avis Lieu"
        verbose_name_plural = "Avis Lieux"
        unique_together = ['utilisateur', 'lieu']  # Un utilisateur ne peut donner qu'un avis par lieu
        ordering = ['-date']
    
    def __str__(self):
        return f"Avis de {self.utilisateur.username} sur {self.lieu.nom} - {self.note}★"


class AvisEvenement(models.Model):
    """Avis spécifiques aux événements"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note de 1 à 5"
    )
    texte = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    
    # Relations
    utilisateur = models.ForeignKey(
        Utilisateur, 
        on_delete=models.CASCADE, 
        related_name='avis_evenements_donnes'
    )
    evenement = models.ForeignKey(
        Evenement, 
        on_delete=models.CASCADE, 
        related_name='avis'
    )
    
    class Meta:
        verbose_name = "Avis Événement"
        verbose_name_plural = "Avis Événements"
        unique_together = ['utilisateur', 'evenement']  # Un utilisateur ne peut donner qu'un avis par événement
        ordering = ['-date']
    
    def __str__(self):
        return f"Avis de {self.utilisateur.username} sur {self.evenement.nom} - {self.note}★"