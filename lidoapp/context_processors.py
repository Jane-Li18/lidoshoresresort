from .models import GuestAccount
from .models import Policy

def global_policies(request):
    # Fetch About Policy
    latest_about_content = Policy.objects.filter(policy_type__iexact='about').order_by('-updated_at').first()
    about_content = latest_about_content.content if latest_about_content else "The resort is nestled amidst lush greenery, providing a tranquil setting with direct beachfront access."

    # Fetch Address Policy
    latest_address_content = Policy.objects.filter(policy_type__iexact='address').order_by('-updated_at').first()
    address_content = latest_address_content.content if latest_address_content else "Brgy. Talaan, Aplaya, Sariaya, Calabarzon, 4322, Philippines"

    return {
        'about_content': about_content,
        'address_content': address_content,
    }


def guest_context(request):
    guest = None
    if request.session.get('guest_id'):
        try:
            guest = GuestAccount.objects.get(id=request.session.get('guest_id'))
        except GuestAccount.DoesNotExist:
            pass
    return {'guest': guest}
