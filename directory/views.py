"""
Directory: find nearby artisans by category/subcategory, view orgs, book.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.db.models import Count, Avg
from django.urls import reverse

from artisans.models import (
    ServiceCategory,
    ServiceSubcategory,
    ServiceType,
    Organization,
    Job,
    Review,
)
from directory.services import get_distance_km


def _get_user_lat_lng(request):
    """Get lat/lng from request (query or session after search)."""
    lat = request.GET.get('lat') or request.session.get('directory_lat')
    lng = request.GET.get('lng') or request.session.get('directory_lng')
    if lat is not None and lng is not None:
        try:
            return float(lat), float(lng)
        except (TypeError, ValueError):
            pass
    return None, None


def search_view(request):
    """Step 1: Search by category, subcategory, and optional location (address or use my location)."""
    categories = ServiceCategory.objects.all().order_by('name')
    # Build category_id -> [subcategories] for JS to populate subcategory dropdown on category change
    subcategories_by_category = {}
    for cat in categories:
        subcategories_by_category[cat.id] = [
            {'id': s.id, 'name': s.name}
            for s in ServiceSubcategory.objects.filter(category=cat).order_by('name')
        ]
    import json
    subcategories_json = json.dumps(subcategories_by_category)

    raw_cat = request.GET.get('category') or request.session.get('directory_category_id')
    category_id = int(raw_cat) if raw_cat and str(raw_cat).isdigit() else None
    subcategories = subcategories_by_category.get(category_id, []) if category_id else []

    if request.method == 'POST':
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory')
        address = (request.POST.get('address') or '').strip()
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        request.session['directory_category_id'] = category_id
        request.session['directory_subcategory_id'] = subcategory_id
        if lat and lng:
            request.session['directory_lat'] = lat
            request.session['directory_lng'] = lng
        elif address:
            from directory.services import geocode_address
            lat_d, lng_d = geocode_address(address)
            if lat_d is not None:
                request.session['directory_lat'] = str(lat_d)
                request.session['directory_lng'] = str(lng_d)
        # Redirect to map of nearby organizations
        url = reverse('directory:org_list')
        return redirect(url)

    return render(request, 'directory/search.html', {
        'categories': categories,
        'subcategories': subcategories,
        'subcategories_json': subcategories_json,
        'category_id': category_id,
        'mapbox_key': getattr(settings, 'MAPBOX_KEY', ''),
    })


def services_view(request):
    """Step 2: Pick a service (from selected category/subcategory)."""
    category_id = request.session.get('directory_category_id')
    subcategory_id = request.session.get('directory_subcategory_id')
    if not category_id:
        return redirect('directory:search')

    category = get_object_or_404(ServiceCategory, id=category_id)
    # Services = ServiceTypes that belong to orgs with this category, optionally filtered by subcategory
    qs = ServiceType.objects.filter(organization__service_category=category).distinct()
    if subcategory_id:
        qs = qs.filter(service_subcategory_id=subcategory_id)
    services = qs.select_related('organization').order_by('name')

    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        if service_id:
            request.session['directory_service_id'] = service_id
            return redirect('directory:org_list')
        return redirect('directory:services')

    return render(request, 'directory/services.html', {
        'category': category,
        'services': services,
        'subcategory_id': subcategory_id,
    })


def org_list_view(request):
    """Step 2: View map of nearby organizations (by category/subcategory). Optional: filter by a selected service."""
    user_lat, user_lng = _get_user_lat_lng(request)
    category_id = request.session.get('directory_category_id')
    subcategory_id = request.session.get('directory_subcategory_id')
    service_id = request.session.get('directory_service_id')

    service_type = None
    if service_id:
        try:
            service_type = ServiceType.objects.select_related('organization').get(id=service_id)
        except ServiceType.DoesNotExist:
            service_id = None

    # Without category we cannot show orgs (e.g. direct link); require search first
    if not category_id:
        return redirect('directory:search')

    category = get_object_or_404(ServiceCategory, id=category_id)

    # Build org list: by category (and optional subcategory). If a service was pre-selected, same logic as before (orgs in that service's subcategory).
    if service_type:
        subcategory = service_type.service_subcategory
        if subcategory:
            org_ids = ServiceType.objects.filter(service_subcategory=subcategory).values_list('organization_id', flat=True).distinct()
        else:
            org_ids = [service_type.organization_id]
        orgs = Organization.objects.filter(id__in=org_ids)
    else:
        # Flow: search -> map. Orgs in this category (and optionally with a service in this subcategory).
        orgs = Organization.objects.filter(service_category_id=category_id)
        if subcategory_id:
            org_ids_with_sub = ServiceType.objects.filter(
                service_subcategory_id=subcategory_id
            ).values_list('organization_id', flat=True).distinct()
            orgs = orgs.filter(id__in=org_ids_with_sub)
    # Reviews are on Job; Job has organization via job.organization. So we need completed jobs with reviews.
    org_list = []
    for org in orgs:
        jobs_count = Job.objects.filter(organization=org).exclude(status='cancelled').count()
        review_agg = Review.objects.filter(job__organization=org).aggregate(avg_rating=Avg('rating'), count=Count('id'))
        avg_rating = review_agg['avg_rating']
        review_count = review_agg['count'] or 0
        dist_km = get_distance_km(user_lat, user_lng, org.latitude, org.longitude) if (user_lat and user_lng) else None
        org_list.append({
            'org': org,
            'distance_km': dist_km,
            'jobs_count': jobs_count,
            'review_count': review_count,
            'avg_rating': round(avg_rating, 1) if avg_rating is not None else None,
        })

    # Sort by distance (None last)
    org_list.sort(key=lambda x: (x['distance_km'] is None, x['distance_km'] or 999999))

    return render(request, 'directory/org_list.html', {
        'category': category,
        'service_type': service_type,
        'org_list': org_list,
        'user_lat': user_lat,
        'user_lng': user_lng,
        'mapbox_key': getattr(settings, 'MAPBOX_KEY', ''),
    })


def org_detail_view(request, org_id):
    """Step 3: View one org (distance, reviews), choose a service, then Book."""
    org = get_object_or_404(Organization, id=org_id)
    org_services = org.service_types.order_by('name')
    user_lat, user_lng = _get_user_lat_lng(request)
    distance_km = get_distance_km(user_lat, user_lng, org.latitude, org.longitude) if (user_lat and user_lng and org.latitude and org.longitude) else None
    jobs_count = Job.objects.filter(organization=org).exclude(status='cancelled').count()
    reviews = Review.objects.filter(job__organization=org).select_related('job').order_by('-created_at')[:10]
    review_agg = Review.objects.filter(job__organization=org).aggregate(avg_rating=Avg('rating'), count=Count('id'))
    avg_rating = review_agg['avg_rating']
    review_count = review_agg['count'] or 0
    book_base_url = reverse('artisans:booking_org', args=[org.id])

    return render(request, 'directory/org_detail.html', {
        'organization': org,
        'org_services': org_services,
        'distance_km': distance_km,
        'jobs_count': jobs_count,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1) if avg_rating is not None else None,
        'review_count': review_count,
        'book_base_url': book_base_url,
        'mapbox_key': getattr(settings, 'MAPBOX_KEY', ''),
    })
