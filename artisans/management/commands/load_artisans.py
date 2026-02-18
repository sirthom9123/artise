"""
Seed Organization records from artisans.json (name, address, email, contact_phone, category).
Run: python manage.py load_artisans
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from artisans.models import Organization, ServiceCategory


# Map JSON category name to ServiceCategory slug (from load_services / serviceCategory.json)
CATEGORY_TO_SLUG = {
    'Plumber': 'home-repairs',
    'Electrician': 'home-repairs',
    'Carpenter': 'home-repairs',
    'Painter': 'home-repairs',
    'Tiler': 'home-repairs',
    'Welder': 'construction',
    'Roofer': 'construction',
    'HVAC Technician': 'appliances',
    'Appliance Repair Technician': 'appliances',
    'Appliance Technician': 'appliances',
    'Landscaper': 'outdoor-services',
    'Panel Beater': 'automotive',
    'Panelbeater': 'automotive',
    'Auto Mechanic': 'automotive',
    'Mechanic': 'automotive',
    'Glazier': 'home-repairs',
}


class Command(BaseCommand):
    help = 'Load organizations from artisans.json (name, address, email, contact_phone, category)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='artisans.json',
            help='Path to artisans.json (relative to project root)',
        )
        parser.add_argument(
            '--no-geocode',
            action='store_true',
            help='Skip geocoding addresses to set latitude/longitude',
        )

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        path = base_dir / options['file']

        if not path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {path}'))
            return

        do_geocode = not options['no_geocode']
        if do_geocode and not getattr(settings, 'MAPBOX_KEY', None):
            self.stdout.write(self.style.WARNING(
                'MAPBOX_KEY is not set. Lat/lon will not be generated. '
                'Set MAPBOX_KEY in .env and re-run without --no-geocode to geocode addresses.'
            ))
            do_geocode = False

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            self.stderr.write(self.style.ERROR('Expected a JSON array of objects.'))
            return

        categories_by_slug = {c.slug: c for c in ServiceCategory.objects.all()}

        with transaction.atomic():
            created = 0
            updated = 0
            geocode_failures = []
            for item in data:
                name = (item.get('name') or '').strip()
                if not name:
                    self.stdout.write(self.style.WARNING('Skipping entry with empty name.'))
                    continue

                category_name = (item.get('category') or '').strip()
                service_category = None
                if category_name and category_name in CATEGORY_TO_SLUG:
                    slug = CATEGORY_TO_SLUG[category_name]
                    service_category = categories_by_slug.get(slug)

                defaults = {
                    'address': (item.get('address') or '').strip(),
                    'contact_email': (item.get('email') or item.get('contact_email') or '').strip(),
                    'contact_phone': (item.get('contact_phone') or '').strip()[:20],
                    'service_category': service_category,
                }

                org, was_created = Organization.objects.update_or_create(
                    name=name,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

                if do_geocode and defaults.get('address'):
                    from artisans.services import update_organization_geolocation
                    update_organization_geolocation(org)
                    org.refresh_from_db()
                    if org.latitude is None and org.longitude is None:
                        geocode_failures.append(name)

        if geocode_failures:
            self.stdout.write(self.style.WARNING(
                f'Geocoding failed for {len(geocode_failures)} org(s) (address not found or API error): '
                + ', '.join(geocode_failures[:5])
                + (' ...' if len(geocode_failures) > 5 else '')
            ))
        self.stdout.write(self.style.SUCCESS(
            f'Organizations: {created} created, {updated} updated (from {path.name})'
        ))
