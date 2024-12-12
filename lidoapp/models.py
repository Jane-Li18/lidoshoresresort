import uuid
import random
import string
from django.db import models
from django.contrib.auth.hashers import make_password, check_password, is_password_usable
import os
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.db.models import Sum

def guest_profile_picture_path(instance, filename):
    return f"profile_pictures/{instance.first_name}/{filename}"


class GuestAccount(models.Model):
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    birthdate = models.DateField()
    gender = models.CharField(max_length=20)
    custom_gender = models.CharField(max_length=50, blank=True, null=True)
    refer_as = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    profile_picture = models.ImageField(upload_to=guest_profile_picture_path, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    telephone_number = models.CharField(max_length=15, blank=True, null=True)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=now, editable=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

    def save(self, *args, **kwargs):
        # Hash the password if it is not hashed or if it's updated in admin
        if not is_password_usable(self.password) or self._state.adding or 'password' in kwargs.get('update_fields', []):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    

class AdminAccount(models.Model):
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    birthdate = models.DateField()
    gender = models.CharField(max_length=20)
    custom_gender = models.CharField(max_length=50, blank=True, null=True)
    refer_as = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    
class FrontdeskAccount(models.Model):
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    birthdate = models.DateField()
    gender = models.CharField(max_length=20)
    custom_gender = models.CharField(max_length=50, blank=True, null=True)
    refer_as = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


def generate_readable_reservation_id():
    # Generate a readable reservation ID (e.g., 1GD82993)
    prefix = random.choice(string.ascii_uppercase)  # First character (uppercase letter)
    middle = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))  # Two more alphanumeric
    suffix = ''.join(random.choices(string.digits, k=5))  # Five digits
    return f"{prefix}{middle}{suffix}"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Booked', 'Booked'),
        ('Cancelled', 'Cancelled'),
        ('Refunded', 'Refunded'),
    ]
    reservation_ID = models.CharField(
        max_length=10,
        default=generate_readable_reservation_id,
        editable=False,
        unique=True,
    )
    guest = models.ForeignKey('GuestAccount', on_delete=models.CASCADE)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    room_chosen = models.CharField(max_length=255)
    add_ons = models.JSONField(default=list, blank=True, null=True)
    adult_count = models.PositiveIntegerField(default=1)
    children_count = models.PositiveIntegerField(default=0)
    total_guest_count = models.PositiveIntegerField(default=0)
    overall_total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    prefix = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    contact_number = models.CharField(max_length=15)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100)
    special_requests = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    invoice_file = models.FileField(upload_to='invoices/%Y/%m/%d/', blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_guest_count = self.adult_count + self.children_count
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation {self.reservation_ID} for {self.guest} from {self.check_in_date} to {self.check_out_date}"







class AddOn(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    image = models.ImageField(upload_to='addons/', blank=True, null=True)

    def __str__(self):
        return self.name

    # Check if the add-on is in stock
    def is_in_stock(self):
        return self.stock_quantity > 0
    
    


class WalkInReservation(models.Model):
    walk_in_ID = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    contact_number = models.CharField(max_length=15)
    address = models.TextField()
    arrival_datetime = models.DateTimeField()
    status_rate = models.CharField(max_length=50)
    cottage_rate = models.CharField(max_length=50)
    payment_method = models.CharField(max_length=20)
    total_guest_count = models.PositiveIntegerField(default=0)  # New field
    total_child_count = models.PositiveIntegerField(default=0)  # New field
    overall_total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # New field

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.status_rate}"




def generate_room_id():
    return random.randint(100000, 999999)

def room_main_image_path(instance, filename):
    """Path for main image of each room."""
    room_name_slug = slugify(instance.room_name)
    return os.path.join('rooms', room_name_slug, 'main_image', filename)

def room_additional_image_path(instance, filename):
    """Path for additional images of each room."""
    if isinstance(instance, RoomImage):
        room_name_slug = slugify(instance.room.room_name)
    else:
        room_name_slug = slugify(instance.room_name)
    return os.path.join('rooms', room_name_slug, 'additional_images', filename)


class Room(models.Model):
    ROOM_AMENITIES = [
        ('wifi', 'In-Room Wifi'),
        ('tv', 'Flat Screen TV'),
        ('ac', 'Air Conditioning'),
        ('heater', 'Heater'),
        ('coffee_maker', 'Coffee Maker'),
        ('microwave', 'Microwave'),
        ('kitchenette', 'Kitchenette'),
        ('toilet', 'Toilet Room'),
        ('extratoilet', 'Extra Toilet Room'),
        ('extrabed', 'Extra Bed Room'),
        ('bathrobe', 'Bathrobe'),
        ('toiletries', 'Complimentary Toiletries'),
        ('desk', 'Work Desk'),
        ('phone', 'Telephone'),
        ('balcony', 'Private Balcony'),
        ('sofa', 'Convertable Sofa'),
        ('dining_area', 'Dining Area'),
        ('barbeque', 'Outside Barbeque Area'),
        ('fireplace', 'Fireplace'),
    ]
    
    ROOM_STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
    ]
    
    BED_TYPE_CHOICES = [
        ('single', 'Single Bed'),
        ('double', 'Double Bed'),
        ('queen', 'Queen Bed'),
        ('king', 'King Bed'),
        ('twin', 'Twin Bed'),
    ]

    room_id = models.PositiveIntegerField(default=generate_room_id, unique=True)
    room_name = models.CharField(max_length=100)
    room_price = models.DecimalField(max_digits=10, decimal_places=2)
    room_capacity = models.PositiveIntegerField()
    room_size = models.PositiveIntegerField(help_text="Enter the size in square feet.")
    room_image = models.ImageField(upload_to=room_main_image_path)
    room_images = models.ManyToManyField('RoomImage', blank=True, related_name='rooms')
    room_amenities = models.ManyToManyField('Amenity', blank=True)
    room_status = models.CharField(max_length=15, choices=ROOM_STATUS_CHOICES, default='available')
    room_description = models.TextField(max_length=100, blank=True, help_text="A detailed description of the room's features and layout.")
    bed_type = models.CharField(max_length=10, choices=BED_TYPE_CHOICES, default='queen')
    discount = models.DecimalField(blank=True, max_digits=5, decimal_places=2, default=0.00)
    
    @property
    def is_available(self):
        # Check if room is available
        if self.room_status != 'available':
            return False

        # Check for conflicting reservations
        conflicting_reservations = Reservation.objects.filter(
            room_chosen=self,
            check_in_date__lt=datetime.now().date() + timedelta(days=1),
            check_out_date__gt=datetime.now().date()
        )
        return not conflicting_reservations.exists()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.room_name
    
    def is_new(self):
        return now() - self.created_at <= timedelta(hours=24)
    
    


class RoomImage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to=room_additional_image_path)
    visible = models.BooleanField(default=True)  # Add this field

    def __str__(self):
        return f"Room Image {self.id}"

    
@receiver(post_save, sender=Room)
def create_room_directories(sender, instance, **kwargs):
    # Ensure directory structure exists for main_image and additional_images
    main_image_path = room_main_image_path(instance, '')
    additional_images_path = room_additional_image_path(instance, '')

    os.makedirs(os.path.join(settings.MEDIA_ROOT, main_image_path), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, additional_images_path), exist_ok=True)



class Amenity(models.Model):
    amenity_type = models.CharField(choices=Room.ROOM_AMENITIES, max_length=20, unique=True)

    def __str__(self):
        # Return the human-readable label from ROOM_AMENITIES choices
        return self.get_amenity_display()

    def get_amenity_display(self):
        # Use a dictionary lookup to return the human-readable name
        return dict(Room.ROOM_AMENITIES).get(self.amenity_type, self.amenity_type)





