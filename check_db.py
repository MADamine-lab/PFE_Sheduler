import os
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'pfe_project.settings'
django.setup()

from scheduler.models import Etudiant, Professeur
from django.contrib.auth.models import User

print(f'Total etudiants: {Etudiant.objects.count()}')
print(f'Total professeurs: {Professeur.objects.count()}')
print(f'Total users: {User.objects.count()}')
print(f'Etudiants avec email: {Etudiant.objects.exclude(email="").count()}')
print(f'Professeurs avec email: {Professeur.objects.exclude(email="").count()}')
