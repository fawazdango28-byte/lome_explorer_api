from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import *


class UtilisateurSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR L'UTILISATEUR - LECTURE SEUL(PROFILE)
    nombre_lieux = serializers.SerializerMethodField()
    nombre_evenements = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            'id','username','email','tel','date_creation',
            'nombre_lieux','nombre_evenements',
            'is_active'
        ]
        read_only_fields = ['id','date_creation']

    def get_nombre_lieux(self, obj):
        return obj.lieux.count()
    
    def get_nombre_evenements(self, obj):
        return obj.evenements_organises.count()
    

class UtilisateurCreateSerializer(serializers.ModelSerializer):
    #SERIALIZER POUR LA CREATION D'UTILISATEUR
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Utilisateur
        fields = [
            'username', 'email', 'password', 'password_confirm', 'tel'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Les mots de passe ne correspondent pas.")
        
        # validation du mot de passe django
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        return attrs
    # surcharge de la methode create 
    def create(seld, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = Utilisateur.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
class LoginSerializer(serializers.Serializer):  
    # SERIALIZER POUR LA CONNEXION
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)

            if not user:
                raise serializers.ValidationError('Email ou mot de passe incorrect.')
            if not user.is_active:
                raise serializers.ValidationError('Compte utilisateur desactivé')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Email et mot de passe requis')
        
        return attrs
    

class LieuSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR LES LIEUX

    proprietaire_nom = serializers.CharField(source='proprietaire.username', read_only=True)
    proprietaire_id = serializers.SerializerMethodField(read_only=True)
    nombre_evenements = serializers.SerializerMethodField()
    moyenne_avis = serializers.SerializerMethodField()

    class Meta:
        model = Lieu
        fields = [
            'id', 'nom', 'description', 'categorie', 'latitude',
            'longitude', 'date_creation', 'proprietaire_id', 'proprietaire', 'proprietaire_nom',
            'nombre_evenements', 'moyenne_avis'
        ]
        read_only_fields = ['id', 'date_creation', 'proprietaire']

    def get_nombre_evenements(self, obj):
        return obj.evenements.count()
    
    def get_proprietaire_id(self, obj):
        """Retourne l'UUID du propriétaire en string"""
        return str(obj.proprietaire.id)
    
    def get_moyenne_avis(self, obj):
        avis = obj.avis.all()

        if avis.exists():
            return round(sum(avis.values_list('note', flat=True)) / avis.count(), 1)
        return None
    
    def create(self, validated_data):
        # Le propriétaire est automatiquement l'utilisateur connecté
        validated_data['proprietaire'] = self.context['request'].user
        return super().create(validated_data)
    

class LieuDetailSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR LES DETAILS D'UN LIEU AVEC SES AVIS

    proprietaire_nom = serializers.CharField(source='proprietaire.username', read_only=True)
    avis = serializers.SerializerMethodField()
    proprietaire_id = serializers.SerializerMethodField(read_only=True)
    nombre_evenements = serializers.SerializerMethodField()
    evenements_a_venir = serializers.SerializerMethodField()
    moyenne_avis = serializers.SerializerMethodField()

    class Meta:
        model = Lieu
        fields = [
            'id', 'nom', 'description', 'categorie', 'latitude',
            'longitude', 'date_creation', 'proprietaire', 'proprietaire_nom',
            'nombre_evenements', 'moyenne_avis', 'avis', 'evenements_a_venir'
        ]
        read_only_fields = ['id', 'date_creation', 'proprietaire']
    
    def get_proprietaire_id(self, obj):
        """Retourne l'UUID du propriétaire en string"""
        return str(obj.proprietaire.id)
    
    def get_nombre_evenements(self, obj):
        return obj.evenements.count()
    
    def get_moyenne_avis(self, obj):
        avis = obj.avis.all()
        if avis.exists():
            return round(sum(avis.values_list('note', flat=True)) / avis.count(), 1)
        return None

    def get_avis(self, obj):
        avis = obj.avis.all()[:5]
        return [
            {
                'id': str(avis_item.id),
                'note': avis_item.note,
                'texte': avis_item.texte,
                'date': avis_item.date,
                'utilisateur_nom': avis_item.utilisateur.username
            } 
            for avis_item in avis
        ]
    
    def get_evenements_a_venir(self, obj):
        from django.utils import timezone

        evenements = obj.evenements.filter(date_debut__gte=timezone.now())[:3]
        return [
            {
                'id': str(evt.id),
                'nom': evt.nom,
                'date_debut': evt.date_debut,
                'date_fin': evt.date_fin
            }
            for evt in evenements
        ]
    
class EvenementSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR LES EVENEMENTS
    organisateur_nom = serializers.CharField(source='organisateur.username', read_only=True)
    organisateur_id = serializers.SerializerMethodField(read_only=True)
    lieu_nom = serializers.CharField(source='lieu.nom', read_only=True)
    lieu_latitude = serializers.DecimalField(source='lieu.latitude', max_digits=10, decimal_places=7, read_only=True)
    lieu_longitude = serializers.DecimalField(source='lieu.longitude', max_digits=10, decimal_places=7, read_only=True)
    moyenne_avis = serializers.SerializerMethodField()
    nombre_avis = serializers.SerializerMethodField()

    class Meta:
        model = Evenement
        fields = [
            'id', 'nom', 'description', 'date_debut', 'date_fin', 'lieu',
            'lieu_nom', 'lieu_latitude', 'lieu_longitude', 'organisateur_id', 'organisateur', 'organisateur_nom', 'moyenne_avis',
            'nombre_avis'
        ]
        read_only_fields = ['id', 'organisateur']

    def get_organisateur_id(self, obj):
        """Retourne l'UUID de l'organisateur en string"""
        return str(obj.organisateur.id)

    def get_moyenne_avis(self, obj):
        avis = obj.avis.all()
        if avis.exists():
            return round(sum(avis.values_list('note', flat=True)) / avis.count(), 1)
        return None
    
    def get_nombre_avis(self, obj):
        return obj.avis.count()
    
    def validate(self, attrs):
        if attrs['date_debut'] >= attrs['date_fin']:
            raise serializers.ValidationError("La date de fin doit être postérieure à la date de debut.")
        return attrs
    
    def create(self, validated_data):
        validated_data['organisateur'] = self.context['request'].user
        return super().create(validated_data)
    

class EvenementDetailSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR LES DETAILS D'EVENEMENTS AVEC SES AVIS ET LIEU
    lieu_details = LieuSerializer(source='lieu', read_only=True)
    avis = serializers.SerializerMethodField()
    

    class Meta(EvenementSerializer.Meta):
        fields = EvenementSerializer.Meta.fields + ['lieu_details', 'avis']
        read_only_fields = ['id', 'organisateur']

    def get_organisateur_id(self, obj):
        """Retourne l'UUID de l'organisateur en string"""
        return str(obj.organisateur.id)

    def get_moyenne_avis(self, obj):
        avis = obj.avis.all()
        if avis.exists():
            return round(sum(avis.values_list('note', flat=True)) / avis.count(), 1)
        return None
    
    def get_nombre_avis(self, obj):
        return obj.avis.count()
    
    def get_avis(self, obj):
        avis = obj.avis.all()
        return [
            {
                'id': str(avis_item.id),
                'note': avis_item.note,
                'texte': avis_item.texte,
                'date': avis_item.date,
                'utilisateur_nom': avis_item.utilisateur.username
            }
            for avis_item in avis
        ]
    
class AvisLieuSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR LES AVIS DES LIEUX
    utilisateur_nom = serializers.CharField(source='utilisateur.username', read_only=True)
    lieu_nom = serializers.CharField(source='lieu.nom', read_only=True)
    utilisateur = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AvisLieu
        fields = [
            'id', 'note', 'texte', 'date', 'utilisateur',
            'utilisateur_nom', 'lieu', 'lieu_nom'
        ]
        read_only = ['id', 'date', 'utilisateur']
    
    def validate(self, attrs):
        """Validation globale"""
        print("=" * 80)
        print("🔍 validate() appelée")
        print(f"   attrs: {attrs}")
        print(f"   attrs.keys(): {attrs.keys()}")
        print(f"   Context: {self.context.keys()}")
        
        request = self.context.get('request')
        print(f"   Request: {request}")
        print(f"   User: {request.user if request else 'No request'}")
        print(f"   User authenticated: {request.user.is_authenticated if request else 'No request'}")
        
        lieu = attrs.get('lieu')
        note = attrs.get('note')
        texte = attrs.get('texte')
        
        print(f"   lieu: {lieu}")
        print(f"   note: {note}")
        print(f"   texte length: {len(texte) if texte else 0}")
        print("=" * 80)
        
        return attrs
    
    def validate_lieu(self, value):
        """Validation du lieu"""
        print(f"🔍 validate_lieu appelée: {value} (type: {type(value)})")
        print(f"   Lieu ID: {value.id if value else 'None'}")
        print(f"   Lieu nom: {value.nom if value else 'None'}")
        
        # Vérifier que le lieu existe
        if not value:
            raise serializers.ValidationError("Le lieu est requis")
        
        # Vérifier que le lieu existe en base
        try:
            lieu_exists = Lieu.objects.filter(id=value.id).exists()
            print(f"   Lieu existe: {lieu_exists}")
            if not lieu_exists:
                raise serializers.ValidationError(f"Le lieu {value.id} n'existe pas")
        except Exception as e:
            print(f"   ❌ Erreur vérification lieu: {e}")
            raise serializers.ValidationError(f"Erreur lors de la vérification du lieu: {e}")
        
        return value

    def validate_note(self, value):
        print(f"🔍 validate_note appelée: {value} (type: {type(value)})")
        if not 1 <= value <= 5:
            raise serializers.ValidationError("La note doit être comprise entre 1 et 5.")
        return value
    
    def create(self, validated_data):
        """Création de l'avis"""
        print("=" * 80)
        print("🔍 create() appelée")
        print(f"   validated_data: {validated_data}")
        
        request = self.context.get('request')
        if request and request.user:
            print(f"   User: {request.user}")
            print(f"   User ID: {request.user.id}")
            validated_data['utilisateur'] = request.user
        else:
            print("   ❌ Pas d'utilisateur dans le contexte !")
        
        try:
            avis = super().create(validated_data)
            print(f"   ✅ Avis créé: {avis.id}")
            print("=" * 80)
            return avis
        except Exception as e:
            print(f"   ❌ Erreur création: {e}")
            print(f"   ❌ Type erreur: {type(e)}")
            import traceback
            traceback.print_exc()
            print("=" * 80)
            raise
    
class AvisEvenementSerializer(serializers.ModelSerializer):
    """Serializer pour les avis d'événements"""
    utilisateur_nom = serializers.CharField(source='utilisateur.username', read_only=True)
    evenement_nom = serializers.CharField(source='evenement.nom', read_only=True)
    utilisateur = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AvisEvenement
        fields = [
            'id', 'note', 'texte', 'date', 'utilisateur',
            'utilisateur_nom', 'evenement', 'evenement_nom'
        ]
        # ✅ Retiré 'evenement' de read_only_fields
        read_only_fields = ['id', 'date']

    def validate_note(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("La note doit être comprise entre 1 et 5.")
        return value

    def validate(self, attrs):
        """Empêche de noter un événement non terminé"""
        from django.utils import timezone
        evenement = attrs.get('evenement')

        if evenement:
            # ✅ Correction : appeler timezone.now() (avec parenthèses)
            if evenement.date_fin > timezone.now():
                raise serializers.ValidationError(
                    "Vous ne pouvez donner un avis que sur un événement terminé."
                )
        else:
            raise serializers.ValidationError("L'événement est requis pour créer un avis.")
        
        return attrs 

    def create(self, validated_data):
        """Associe automatiquement l'utilisateur connecté à l'avis"""
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['utilisateur'] = request.user
        else:
            raise serializers.ValidationError("Utilisateur non authentifié.")
        
        return super().create(validated_data)

    
class LieuListSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR LA LIST DES LIEUX SIMPLIFIER
    proprietaire_id = serializers.SerializerMethodField(read_only=True)
    proprietaire_nom = serializers.CharField(source='proprietaire.username', read_only=True)
    nombre_evenements = serializers.SerializerMethodField()
    moyenne_avis = serializers.SerializerMethodField()

    class Meta:
        model = Lieu
        fields = [
            'id', 'nom','description', 'categorie', 'latitude', 'longitude',
            'proprietaire_nom', 'proprietaire_id', 'moyenne_avis', 'nombre_evenements'
        ]
    def get_proprietaire_id(self, obj):
        """Retourne l'UUID du propriétaire en string"""
        return str(obj.proprietaire.id)
    
    def get_nombre_evenements(self, obj):
        return obj.evenements.count()
    
    def get_moyenne_avis(self, obj):
        avis = obj.avis.all()
        if avis.exists():
            return round(sum(avis.values_list('note', flat=True)) / avis.count(), 1)
        return None
    

class EvenementListSerializer(serializers.ModelSerializer):
    # SERIALIZER POUR LA LISTE DES EVENEMENT SIMPLIFIER
    organisateur_id = serializers.SerializerMethodField(read_only=True)
    organisateur_nom = serializers.CharField(source='organisateur.username', read_only=True)
    lieu_nom = serializers.CharField(source='lieu.nom', read_only=True)
    lieu_latitude = serializers.DecimalField(source='lieu.latitude', max_digits=10, decimal_places=7, read_only=True)
    lieu_longitude = serializers.DecimalField(source='lieu.longitude', max_digits=10, decimal_places=7, read_only=True)
    moyenne_avis = serializers.SerializerMethodField()
    nombre_avis = serializers.SerializerMethodField()

    class Meta:
        model = Evenement
        fields = [
            'id', 'nom', 'description', 'date_debut', 'date_fin',
            'lieu', 'lieu_nom', 'lieu_latitude', 'lieu_longitude',
            'organisateur_id', 'organisateur_nom',
            'moyenne_avis', 'nombre_avis'
        ]

    def get_organisateur_id(self, obj):
        """Retourne l'UUID de l'organisateur en string"""
        return str(obj.organisateur.id)

    def get_moyenne_avis(self, obj):
        avis = obj.avis.all()
        if avis.exists():
            return round(sum(avis.values_list('note', flat=True)) / avis.count(), 1)
        return None
    
    def get_nombre_avis(self, obj):
        return obj.avis.count()