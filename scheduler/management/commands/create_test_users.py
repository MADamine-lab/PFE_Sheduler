from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from scheduler.models import UserProfile, Professeur, Etudiant


class Command(BaseCommand):
    help = 'Create test users for development'

    def handle(self, *args, **options):
        # Test users data
        test_users = [
            {
                'username': 'admin',
                'email': 'admin@demo.local',
                'password': 'demo123',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_superuser': True,
                'is_staff': True,
                'role': 'admin'
            },
            {
                'username': 'prof',
                'email': 'prof@demo.local',
                'password': 'demo123',
                'first_name': 'Professeur',
                'last_name': 'Demo',
                'is_superuser': False,
                'is_staff': True,
                'role': 'prof'
            },
            {
                'username': 'etudiant',
                'email': 'etudiant@demo.local',
                'password': 'demo123',
                'first_name': 'Étudiant',
                'last_name': 'Demo',
                'is_superuser': False,
                'is_staff': False,
                'role': 'etudiant'
            }
        ]

        for user_data in test_users:
            # Create or update user
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_superuser': user_data['is_superuser'],
                    'is_staff': user_data['is_staff'],
                }
            )

            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {user.username} ({user.email})')
                )
            else:
                # Update existing user
                user.email = user_data['email']
                user.first_name = user_data['first_name']
                user.last_name = user_data['last_name']
                user.is_superuser = user_data['is_superuser']
                user.is_staff = user_data['is_staff']
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated existing user: {user.username} ({user.email})')
                )

            # Create or update user profile
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': user_data['role']}
            )

            if profile_created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created profile for {user.username} with role: {profile.role}')
                )
            else:
                profile.role = user_data['role']
                profile.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated profile for {user.username} with role: {profile.role}')
                )

        self.stdout.write(
            self.style.SUCCESS('\nTest users created successfully!')
        )
        self.stdout.write('Login credentials:')
        self.stdout.write('  Admin: admin@demo.local / demo123')
        self.stdout.write('  Professor: prof@demo.local / demo123')
        self.stdout.write('  Student: etudiant@demo.local / demo123')