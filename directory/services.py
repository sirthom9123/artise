"""
Directory services: distance, geocoding, notifications.
"""
from decimal import Decimal
import urllib.parse

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse


def get_distance_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two points using geopy. Returns None if geopy unavailable or invalid."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        from geopy.distance import geodesic
        p1 = (float(lat1), float(lon1))
        p2 = (float(lat2), float(lon2))
        return round(geodesic(p1, p2).kilometers, 2)
    except Exception:
        return None


def build_address(last_address_state):
    """Turn address state (string, dict with 'address', or object with .address) into a single address string."""
    if last_address_state is None:
        return ''
    if isinstance(last_address_state, str):
        return last_address_state.strip()
    if hasattr(last_address_state, 'address'):
        return (getattr(last_address_state, 'address') or '').strip()
    if isinstance(last_address_state, dict):
        return (last_address_state.get('address') or '').strip()
    return ''


def is_location_changed(current_address, last_address_state):
    """Return True if the current address differs from the address built from last state."""
    last_address = build_address(last_address_state)
    current = (current_address or '').strip()
    return last_address != current


def get_gps_coordinates(address):
    """Return [longitude, latitude] for address using Mapbox Geocoding API v6. Raises on failure."""
    if not address or not str(address).strip():
        raise ValueError("Address is required.")
    key = getattr(settings, 'MAPBOX_KEY', None) or ''
    if not key:
        raise ValueError("MAPBOX_KEY is not configured.")
    url = (
        'https://api.mapbox.com/search/geocode/v6/forward'
        '?q=' + urllib.parse.quote(str(address).strip()) + '&proximity=ip&access_token=' + key
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    features = data.get('features') or []
    if not features:
        raise ValueError("Invalid address provided.")
    coordinates = features[0].get('geometry', {}).get('coordinates')
    if not coordinates or len(coordinates) < 2:
        raise ValueError("Invalid address provided.")
    return coordinates  # [longitude, latitude]


def geocode_address(address):
    """Return (lat, lon) for address using Mapbox Geocoding API. Returns (None, None) on failure."""
    if not address or not str(address).strip():
        return None, None
    try:
        coords = get_gps_coordinates(address)
        # Mapbox returns [longitude, latitude]
        lon, lat = float(coords[0]), float(coords[1])
        return Decimal(str(lat)), Decimal(str(lon))
    except Exception:
        return None, None


def send_booking_notification_to_org(org, job, request=None):
    """Email org about new booking and create in-app notification. Call from booking view."""
    from django.contrib.sites.shortcuts import get_current_site
    from .models import OrgNotification

    job_url = ''
    if request:
        job_url = request.build_absolute_uri(reverse('artisans:job_detail', args=[job.id]))
    else:
        try:
            from django.contrib.sites.models import Site
            domain = Site.objects.get_current().domain
            scheme = 'https'
            job_url = f"{scheme}://{domain}{reverse('artisans:job_detail', args=[job.id])}"
        except Exception:
            job_url = reverse('artisans:job_detail', args=[job.id])

    # In-app notification (for org admin dashboard / future push)
    OrgNotification.objects.create(
        organization=org,
        notification_type='booking',
        title='New booking request',
        message=f'Job {job.job_number} from {job.customer.name}. Preferred: {job.scheduled_date}.',
        link_url=job_url,
    )

    # Email
    to_email = org.contact_email or None
    if not to_email:
        admin_profile = org.members.filter(role='admin').first()
        if admin_profile and admin_profile.user and admin_profile.user.email:
            to_email = admin_profile.user.email
    if to_email:
        subject = f'New booking: {job.job_number} – {job.customer.name}'
        body = f'''A new booking has been submitted.

Job: {job.job_number}
Customer: {job.customer.name}
Email: {job.customer.email}
Address: {job.address}
Preferred date: {job.scheduled_date}
Notes: {job.notes or "—"}

View job: {job_url}
'''
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
