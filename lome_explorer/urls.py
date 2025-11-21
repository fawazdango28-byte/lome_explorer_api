"""
URL configuration for lome_explorer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from lome_explorer import settings
from rest_framework import routers
from CitationAPI.urls import router as citation_router
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

router = routers.DefaultRouter()
router.registry.extend(citation_router.registry)



urlpatterns = [
    path('admin/', admin.site.urls),

    # API de l'application CitationAPI
    path('api/cita/', include(router.urls)),
    
    # API de l'application FastAPI
    path('fastapi/', include('FastAPI.urls'), name='fastapi'),
    
        # Documentation de l'API
        
    # Documentation de l'API avec drf-spectacular
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # UI pour la documentation (Swagger-UI)
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # UI pour la documentation (Redoc)
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Configuration du titre de l'admin
admin.site.site_header = "Administration - Événements Lomé"
admin.site.site_title = "Événements Lomé"
admin.site.index_title = "Gestion de l'API"