"""Middleware for artisans app."""
from django.shortcuts import redirect
from django.urls import reverse


class RequirePasswordChangeMiddleware:
    """Redirect users with must_change_password to change password page."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = getattr(request.user, 'profile', None)
                if profile and getattr(profile, 'must_change_password', False):
                    change_url = reverse('artisans:change_password')
                    logout_url = reverse('artisans:logout')
                    if not request.path.startswith((change_url, logout_url)):
                        return redirect(change_url)
            except Exception:
                pass
        return self.get_response(request)
