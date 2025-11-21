from django.db import models

# Create your models here.
class Citation(models.Model):
    titre = models.CharField(max_length=255)
    note = models.TextField()
    date_creation = models.DateTimeField(auto_now=True)
    list = models.ForeignKey('ListCitation', null=False, on_delete=models.CASCADE)

class ListCitation(models.Model):
    auteur = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Liste citation'
        verbose_name_plural = 'Listes citations'