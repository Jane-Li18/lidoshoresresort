from django.shortcuts import redirect
from django.urls import reverse

class GuestAccessMiddleware:
    """
    Middleware to restrict guests from accessing admin or frontdesk routes.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        guest_id = request.session.get('guest_id')
        path = request.path

        # Check if the user is a guest and trying to access restricted paths
        if guest_id:
            # Restrict guest access to admin and frontdesk paths
            restricted_paths = [
                reverse('admin_dashboard'),
                reverse('frontdesk_dashboard'),
                reverse('adminlogin'),
                reverse('frontdesklogin'),
            ]
            if any(path.startswith(rp) for rp in restricted_paths):
                return redirect('guestlogin')  # Redirect guest to guestlogin

        # Allow request to proceed if no restrictions are triggered
        response = self.get_response(request)
        return response