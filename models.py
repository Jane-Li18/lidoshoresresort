# lidoapp/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from .storage import GalleryTypeStorage

def validate_philippine_phone(value):
    if not value.startswith('09') or len(value) != 11 or not value.isdigit():
        raise ValidationError("Enter a valid Philippine phone number (11 digits and starts with 09)")

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    prefix = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    contact = models.CharField(max_length=11, validators=[validate_philippine_phone])
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('P', 'Prefer not to say')], blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(default='default_avatar.png', upload_to='profile_images')

    def __str__(self):
        return f"{self.user.username} - {self.first_name} {self.last_name}"

class RoomType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Amenity(models.Model):
    name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=100, help_text='FontAwesome icon class for the amenity, e.g., fa-wifi')

    def __str__(self):
        return self.name

class Room(models.Model):
    ROOM_STATUS = ( 
        ("1", "Available"), 
        ("2", "Unavailable"),    
    )

    room_name = models.CharField(max_length=255)
    roomnumber = models.IntegerField()
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    maximum_pax = models.IntegerField()
    size = models.IntegerField()
    price = models.IntegerField()
    status = models.CharField(max_length=2, choices=ROOM_STATUS)
    image = models.ImageField(upload_to='room_images/', null=True, blank=True)
    room_amenities = models.ManyToManyField(Amenity, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('roomnumber', 'room_type')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.room_type} - Room {self.roomnumber}"

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    check_in = models.DateField()
    check_out = models.DateField()
    check_in_time = models.TimeField(default='14:00:00')
    tour_type = models.CharField(max_length=20, choices=[('daytour', 'Daytour'), ('nighttour', 'Nighttour')])
    country = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    num_guests = models.IntegerField()
    num_children = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    receipt = models.FileField(upload_to='receipts/')
    transaction_number = models.CharField(max_length=100)
    payment_type = models.CharField(max_length=20, choices=[('reservation', 'Reservation Only'), ('full_paid', 'Full Paid')])
    total_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    guest = models.ForeignKey(User, on_delete=models.CASCADE)
    booking_id = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.guest.username} - {self.room.roomnumber}"


class GalleryType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class GalleryImage(models.Model):
    gallery_types = models.ManyToManyField(GalleryType)
    image = models.ImageField(upload_to='gallery_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image ID: {self.id}"