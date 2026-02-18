"""
Create dummy users (one per organization), link each user to their org via UserProfile,
and create ServiceType records from PreDefinedService for each org's service category.

Prerequisites: load_artisans and load_services must have been run.
Run: python manage.py seed_org_users_and_services
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from artisans.models import Organization, UserProfile, PreDefinedService, ServiceType

# Default password for seeded users (change in production)
SEED_PASSWORD = 'SeedPass123!'


class Command(BaseCommand):
    help = (
        'Create dummy users (one per org), link via UserProfile, '
        'and create ServiceTypes from PreDefinedService per org category.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default=SEED_PASSWORD,
            help='Password to set for created users',
        )
        parser.add_argument(
            '--skip-services',
            action='store_true',
            help='Only create/link users; do not create ServiceTypes',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        password = options['password']
        skip_services = options['skip_services']

        orgs = Organization.objects.select_related('service_category').all()
        if not orgs.exists():
            self.stdout.write(self.style.WARNING('No organizations found. Run load_artisans first.'))
            return

        users_created = 0
        profiles_created = 0
        profiles_updated = 0
        service_types_created = 0

        with transaction.atomic():
            for org in orgs:
                # Unique username from org name + id (slug, max 150 chars for username)
                base_slug = slugify(org.name).replace('-', '_') or 'org'
                username = f"{base_slug}_{org.id}"[:150]
                email = (org.contact_email or '').strip() or f"{username}@example.com"

                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': org.name[:30],
                        'last_name': '',
                        'is_active': True,
                        'is_staff': False,
                        'is_superuser': False,
                    },
                )
                if user_created:
                    user.set_password(password)
                    user.save(update_fields=['password'])
                    users_created += 1
                    self.stdout.write(f'  Created user: {username}')
                else:
                    # Ensure email is set if user existed
                    if not user.email and email:
                        user.email = email
                        user.save(update_fields=['email'])

                profile, profile_created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'organization': org,
                        'role': 'admin',
                        'phone': (org.contact_phone or '')[:20],
                        'address': (org.address or '').strip(),
                    },
                )
                if profile_created:
                    profiles_created += 1
                else:
                    if profile.organization_id != org.id:
                        profile.organization = org
                        profile.role = 'admin'
                        profile.phone = (org.contact_phone or '')[:20]
                        profile.address = (org.address or '').strip()
                        profile.save()
                        profiles_updated += 1

                if skip_services:
                    continue

                if not org.service_category_id:
                    self.stdout.write(self.style.WARNING(
                        f'  Org "{org.name}" has no service_category; skipping ServiceTypes.'
                    ))
                    continue

                predefined = PreDefinedService.objects.filter(
                    category_id=org.service_category_id
                ).select_related('subcategory')

                for predef in predefined:
                    st, created = ServiceType.objects.get_or_create(
                        organization=org,
                        name=predef.name[:100],
                        service_subcategory=predef.subcategory,
                        defaults={
                            'description': predef.description or '',
                            'base_price': predef.base_price,
                            'price_type': predef.price_type,
                        },
                    )
                    if created:
                        service_types_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Users created: {users_created}, Profiles created: {profiles_created}, '
            f'Profiles updated: {profiles_updated}, ServiceTypes created: {service_types_created}'
        ))
