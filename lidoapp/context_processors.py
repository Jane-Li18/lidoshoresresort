from .models import GuestAccount

def guest_context(request):
    guest = None
    if request.session.get('guest_id'):
        try:
            guest = GuestAccount.objects.get(id=request.session.get('guest_id'))
        except GuestAccount.DoesNotExist:
            pass
    return {'guest': guest}
