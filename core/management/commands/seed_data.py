from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import CreditTransaction


class Command(BaseCommand):
    help = 'Seed the database with test users and data'

    def handle(self, *args, **options):
        # Create test users
        test_users = [
            {'username': 'demo', 'email': 'demo@example.com', 'password': 'demo123'},
            {'username': 'testuser', 'email': 'test@example.com', 'password': 'test123'},
        ]

        for user_data in test_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                }
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {user.username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User already exists: {user.username}')
                )

        self.stdout.write(
            self.style.SUCCESS('Seed data created successfully!')
        )
        self.stdout.write('Test accounts:')
        self.stdout.write('  Username: demo, Password: demo123')
        self.stdout.write('  Username: testuser, Password: test123')
