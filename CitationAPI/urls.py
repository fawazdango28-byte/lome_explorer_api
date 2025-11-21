from rest_framework import routers

from .views import *

router = routers.DefaultRouter()
router.register(r'citations', CitationViewSet, basename='citations')
router.register(r'list-citation', ListCitationViewSet, basename='list-citation')