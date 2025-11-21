from rest_framework import viewsets
from .serializers import *
from .models import *

class CitationViewSet(viewsets.ModelViewSet):
    queryset = Citation.objects.all()
    serializer_class = CitationSerializer
    filterset_fields = ['date_creation']
    search_field = ['titre',]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateCitationSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateCitationSerializer
        elif self.action == 'destroy':
            return DeleteCitationSerializer
        return CitationSerializer
    
class ListCitationViewSet(viewsets.ModelViewSet):
    queryset = ListCitation.objects.all()
    serializer_class = ListCitationSerializer
