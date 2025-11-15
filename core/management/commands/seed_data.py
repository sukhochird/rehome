from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import CreditTransaction, Package


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

        # Create default packages
        packages = [
            {'name': 'Small Package', 'credits': 10, 'price': 5000},
            {'name': 'Medium Package', 'credits': 25, 'price': 10000},
            {'name': 'Large Package', 'credits': 50, 'price': 18000},
            {'name': 'Extra Large Package', 'credits': 100, 'price': 30000},
        ]
        
        for package_data in packages:
            package, created = Package.objects.get_or_create(
                name=package_data['name'],
                defaults={
                    'credits': package_data['credits'],
                    'price': package_data['price'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created package: {package.name}')
                )
            else:
                # Update existing package
                package.credits = package_data['credits']
                package.price = package_data['price']
                package.is_active = True
                package.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated package: {package.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Seed data created successfully!')
        )
        self.stdout.write('Test accounts:')
        self.stdout.write('  Username: demo, Password: demo123')
        self.stdout.write('  Username: testuser, Password: test123')
