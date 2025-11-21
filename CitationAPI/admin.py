from django.contrib import admin
from .models import *

# Class pour montrer tout ce que contient todolist pour ce fait on utilise TabularInline
class CitationInline(admin.TabularInline):
    model = Citation
    extra = 1

# Class pour faire l'enregistrement du models todolist dans l'admin django
@admin.register(ListCitation)
class LIstCitationAdmin (admin.ModelAdmin):
    list_display = ('auteur',)

    inlines = (CitationInline, )

@admin.register(Citation)
class CitationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'note', 'date_creation')
    list_filter = ('date_creation',)
    search_fields = ('titre',)