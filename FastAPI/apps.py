from django.apps import AppConfig

class FastapiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'FastAPI'
    verbose_name = 'Gestion des Événements'
    
    def ready(self):
        """Méthode appelée quand l'app est prête"""
        
        try:
            import FastAPI.signals  
            print("✅ Signaux WebSocket chargés avec succès")
        except ImportError as e:
            print(f"❌ Erreur lors du chargement des signaux: {e}")
        
        # Autres initialisations si nécessaire
        self.setup_periodic_tasks()
    
    def setup_periodic_tasks(self):
        """Configuration des tâches périodiques"""
        try:
            # Ici vous pouvez configurer Celery Beat ou d'autres tâches périodiques
            # Par exemple, pour les rappels d'événements

            pass
        except Exception as e:
            print(f"⚠️  Avertissement tâches périodiques: {e}")