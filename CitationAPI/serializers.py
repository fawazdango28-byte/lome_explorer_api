from rest_framework import serializers

from .models import *

class CitationSerializer(serializers.ModelSerializer):

    auteur = serializers.CharField(source='list.auteur', read_only = True)

    class Meta:
        model = Citation
        fields = [
            'id', 'titre', 'note', 'date_creation', 'auteur'
        ]

class ListCitationSerializer(serializers.ModelSerializer):

    class Meta:
        model = ListCitation
        fields = '__all__'

class CreateCitationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Citation
        fields = '__all__'

class UpdateCitationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Citation
        fields = '__all__'

class DeleteCitationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Citation
        fields = ['id']
