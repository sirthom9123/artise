"""
Load ServiceCategory from serviceCategory.json and PreDefinedService from mock-services.json.
Run: python manage.py load_services
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from artisans.models import ServiceCategory, ServiceSubcategory, PreDefinedService


# Map mock-services provider name to (category_slug, subcategory_name) for linking
PROVIDER_TO_SUBCATEGORY = {
    'Plumber': ('home-repairs', 'Plumbing'),
    'Electrician': ('home-repairs', 'Electrical'),
    'Carpenter': ('home-repairs', 'Carpentry'),
    'Painter': ('home-repairs', 'Painting'),
    'Tiler': ('home-repairs', 'Tiling'),
    'Welder': ('construction', 'Welding'),
    'Roofer': ('construction', 'Roofing'),
    'HVAC Technician': ('appliances', 'Cooling Systems'),
    'Appliance Repair Technician': ('appliances', 'Kitchen Appliances'),
    'Appliance Technician': ('appliances', 'Kitchen Appliances'),
    'Landscaper': ('outdoor-services', 'Landscaping'),
    'Panel Beater': ('automotive', 'Body Repairs'),
    'Auto Mechanic': ('automotive', 'Mechanical Repairs'),
}
# Fallback: provider -> category slug only (subcategory may be null)
PROVIDER_TO_CATEGORY_SLUG = {
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
    'Auto Mechanic': 'automotive',
}


def price_type_from_json(value):
    if value == 'fixed_rate':
        return 'entire_job'
    if value in ('per_hour', 'daily', 'entire_job'):
        return value
    return 'entire_job'


class Command(BaseCommand):
    help = 'Load service categories and predefined services from JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--categories',
            type=str,
            default='serviceCategory.json',
            help='Path to serviceCategory.json (relative to project root)',
        )
        parser.add_argument(
            '--services',
            type=str,
            default='mock-services.json',
            help='Path to mock-services.json (relative to project root)',
        )

    def handle(self, *args, **options):
        from django.conf import settings
        base_dir = Path(settings.BASE_DIR)
        categories_path = base_dir / options['categories']
        services_path = base_dir / options['services']

        if not categories_path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {categories_path}'))
            return
        if not services_path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {services_path}'))
            return

        with transaction.atomic():
            # Load categories and subcategories
            with open(categories_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            categories_by_slug = {}
            subcategories_by_key = {}  # (category_slug, subcategory_slug) -> ServiceSubcategory
            for cat in data.get('categories', []):
                category, _ = ServiceCategory.objects.update_or_create(
                    slug=cat['slug'],
                    defaults={
                        'name': cat['name'],
                        'description': cat.get('description', ''),
                    },
                )
                categories_by_slug[cat['slug']] = category
                for sub_name in cat.get('subcategories', []):
                    sub_slug = sub_name.lower().replace(' ', '-')
                    sub, _ = ServiceSubcategory.objects.update_or_create(
                        category=category,
                        slug=sub_slug,
                        defaults={'name': sub_name},
                    )
                    subcategories_by_key[(cat['slug'], sub_name)] = sub
            self.stdout.write(self.style.SUCCESS(
                f'Loaded {len(categories_by_slug)} categories, '
                f'{len(subcategories_by_key)} subcategory entries'
            ))

            # Load predefined services
            with open(services_path, 'r', encoding='utf-8') as f:
                services_data = json.load(f)
            count = 0
            for provider_block in services_data:
                provider_name = provider_block.get('name', '')
                slug = PROVIDER_TO_CATEGORY_SLUG.get(provider_name)
                if not slug or slug not in categories_by_slug:
                    self.stdout.write(self.style.WARNING(f'Unknown provider/category: {provider_name}, skipping'))
                    continue
                category = categories_by_slug[slug]
                subcategory = None
                if provider_name in PROVIDER_TO_SUBCATEGORY:
                    cat_slug, sub_name = PROVIDER_TO_SUBCATEGORY[provider_name]
                    subcategory = subcategories_by_key.get((cat_slug, sub_name))
                for s in provider_block.get('services', []):
                    PreDefinedService.objects.update_or_create(
                        category=category,
                        provider_name=provider_name,
                        name=s['name'],
                        defaults={
                            'subcategory': subcategory,
                            'description': s.get('description', ''),
                            'base_price': s.get('base_price', 0),
                            'price_type': price_type_from_json(s.get('price_type', 'fixed_rate')),
                        },
                    )
                    count += 1
            self.stdout.write(self.style.SUCCESS(f'Loaded {count} predefined services'))
