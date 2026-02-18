"""Context processors for artisans app."""
from .models import UserProfile


def profile(request):
    """Add user profile to template context."""
    if request.user.is_authenticated:
        try:
            return {'profile': request.user.profile}
        except UserProfile.DoesNotExist:
            return {'profile': None}
    return {'profile': None}
