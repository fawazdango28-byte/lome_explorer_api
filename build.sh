#!/usr/bin/env bash
# build.sh - Script de build pour Render

set -o errexit

echo "🚀 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📦 Collection des fichiers statiques..."
python manage.py collectstatic --no-input

echo "🔄 Application des migrations..."
python manage.py migrate

echo "👤 Création du superutilisateur..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@lome.com', 'Admin123!@#')
    print('✅ Superutilisateur créé')
else:
    print('ℹ️ Superutilisateur existe déjà')
END

echo "✅ Build terminé !"