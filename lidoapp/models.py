import uuid
import random
import string
from django.db import models
from django.contrib.auth.hashers import make_password, check_password, is_password_usable
import os
from PIL import Image
from django.utils.text import slugify
from django.utils import timezone

from django.db.models.signals import post_save 
from django.db.models import UniqueConstraint
from django.dispatch import receiver
from django.conf import settings
from django.utils.timezone import now
from datetime import datetime, timedelta


from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.db import transaction

from django.db.models import Q

import cohere
from django.conf import settings

client = cohere.Client(settings.COHERE_API_KEY)  

class HotelInfo(models.Model):
    name = models.CharField(max_length=255, default="Lido Shores Resort")
    address = models.TextField()
    location_url = models.URLField(blank=True, null=True)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    facebook = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    viber = models.URLField(blank=True, null=True)  # <--- ADD THIS
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name



class GuestInquiry(models.Model):
    guest = models.ForeignKey('lidoapp.GuestAccount', on_delete=models.CASCADE, null=True, blank=True)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("question", "answer")

    def __str__(self):
        return f"{self.question[:50]} - {self.answer[:50]}"





def guest_profile_picture_path(instance, filename):
    first_name = instance.first_name.replace(" ", "_")  # Replace spaces
    return f"profile_pictures/{first_name}/{filename}"


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

class Policy(models.Model):
    POLICY_TYPES = [
        ('account', 'Account Policy'),
        ('booking', 'Booking Policy'),
        ('walkin', 'Walk-In Policy'),
        ('cancel', 'Cancel Policy'),
        ('guarantee', 'Guarantee Policy'),
        ('about', 'About Policy'),
        ('address', 'Address Policy'),
        ('description', 'Revel Policy'),
    ]

    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES)  # Differentiates the types
    content = models.TextField()  # Field to store the content
    updated_at = models.DateTimeField(auto_now=True)  # Auto-update timestamp
    created_at = models.DateTimeField(default=now, editable=False)

    def __str__(self):
        return f"{self.get_policy_type_display()} (Updated: {self.updated_at})"

def upload_to(instance, filename):
    folder_name = instance.image_name or "default"
    return f'galleries/{folder_name}/{filename}'

class GalleryImage(models.Model):
    image = models.ImageField(upload_to=upload_to)
    image_name = models.CharField(max_length=255, blank=True, default="")
    gallery_type = models.CharField(max_length=100, blank=True, default="Lido Images")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Default image name
        if not self.image_name:
            count = GalleryImage.objects.count() + 1
            self.image_name = f"Image{count}"

        # Default gallery type
        if not self.gallery_type:
            self.gallery_type = "More Images"

        super().save(*args, **kwargs)  # Save the file first to get the file path

        # Check and compress if image is too large
        if self.image:
            image_path = self.image.path
            with Image.open(self.image) as img:
                if self.image.size > 10 * 1024 * 1024:  # Over 10 MB
                    img = img.convert('RGB')
                    compressed_path = os.path.splitext(image_path)[0] + '.webp'
                    img.save(compressed_path, 'webp', quality=85)
                    self.image.name = os.path.basename(compressed_path)
                    os.remove(image_path)
                    super().save(*args, **kwargs)  # Save again with the new file

class Banner(models.Model):
    banner_name = models.CharField(max_length=255)
    banner_type = models.CharField(max_length=100, blank=True, default="Banners")
    file_path = models.ImageField(upload_to='banner/')
    created_at = models.DateTimeField(auto_now_add=True)



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
        ('Rebooked', 'Rebooked'),
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
    original_check_in_date = models.DateField(null=True, blank=True)
    original_check_out_date = models.DateField(null=True, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    rebooking_date = models.DateField(null=True, blank=True)
    has_been_rebooked = models.BooleanField(default=False)
    last_updated_by = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original_instance = Reservation.objects.get(pk=self.pk)
            original_status = original_instance.status

            # Preserve original dates if not already set
            if not self.original_check_in_date:
                self.original_check_in_date = original_instance.check_in_date
            if not self.original_check_out_date:
                self.original_check_out_date = original_instance.check_out_date

            # Handle room availability when status changes
            if original_status != self.status:
                # Update last_updated_by if status has changed
                self.last_updated_by = kwargs.pop('updated_by', 'System')

                if self.status in ['Cancelled', 'Refunded']:
                    try:
                        room = Room.objects.get(room_name=self.room_chosen)
                    except Room.DoesNotExist:
                        raise ValueError(f"Room '{self.room_chosen}' does not exist.")

                    # Increment room unit
                    room.room_unit += 1

                    # Update room status to 'available' if units > 0
                    if room.room_unit > 0:
                        room.room_status = 'available'

                    room.save()

                    # Restore room availability for the canceled/reserved dates
                    RoomAvailability.objects.filter(
                        room=room,
                        date__gte=self.check_in_date,
                        date__lt=self.check_out_date
                    ).update(is_available=True)

        super().save(*args, **kwargs)

        # Mark room availability as unavailable for non-cancelled statuses
        if self.status not in ['Cancelled', 'Refunded']:
            try:
                room = Room.objects.get(room_name=self.room_chosen)
            except Room.DoesNotExist:
                raise ValueError(f"Room '{self.room_chosen}' does not exist.")

            RoomAvailability.objects.filter(
                room=room,
                date__gte=self.check_in_date,
                date__lt=self.check_out_date
            ).update(is_available=False)

    def __str__(self):
        return f"Reservation {self.reservation_ID} for {self.guest} from {self.check_in_date} to {self.check_out_date}"

    @property
    def disable_rebooking(self):
        return (
            (now() - self.created_at).days > 3
            or self.has_been_rebooked
            or self.latest_rebooking_request and self.latest_rebooking_request.status == 'Cancelled'
        )

    
    @property
    def latest_rebooking_request(self):
        return self.rebooking_requests.order_by('-requested_at').first()
    
class Receipt(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='receipts')
    handled_by = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)  # Add this line
    items = models.JSONField(default=list)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    receipt_file = models.FileField(upload_to='receipts/%Y/%m/%d/', blank=True, null=True)

    def __str__(self):
        return f"Receipt for {self.reservation.reservation_ID} handled by {self.handled_by}"

def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    
    for item in self.items:
        add_on = AddOn.objects.get(id=item['id'])
        if add_on.add_on_quantity >= item['quantity']:
            add_on.add_on_quantity -= item['quantity']
            add_on.save()
        else:
            raise ValueError("Not enough stock available for add-on.")




class RebookingRequest(models.Model):
    reservation = models.ForeignKey('Reservation', on_delete=models.CASCADE, related_name='rebooking_requests')
    requested_check_in_date = models.DateField()
    requested_check_out_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Cancelled', 'Cancelled')
        ],
        default='Pending'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    handled_by = models.ForeignKey('AdminAccount', on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def is_available(self):
        conflicts = RoomAvailability.objects.filter(
            Q(date__gte=self.requested_check_in_date) & Q(date__lt=self.requested_check_out_date) & Q(is_available=False)
        )
        return not conflicts.exists()

    @property
    def suggested_dates(self):
        conflicts = RoomAvailability.objects.filter(
            Q(date__gte=self.requested_check_in_date) & Q(date__lt=self.requested_check_out_date) & Q(is_available=False)
        )
        if conflicts.exists():
            # Example: Fetch a range of available dates (logic may vary)
            return [
                (self.requested_check_in_date + timedelta(days=7), self.requested_check_out_date + timedelta(days=7))
            ]
        return []


    def save(self, *args, **kwargs):
        if self.pk:
            original_status = RebookingRequest.objects.get(pk=self.pk).status
        else:
            original_status = None

        super().save(*args, **kwargs)

        reservation = self.reservation

        if self.status == 'Approved' and original_status != 'Approved':
            if not reservation.original_check_in_date:
                reservation.original_check_in_date = reservation.check_in_date
            if not reservation.original_check_out_date:
                reservation.original_check_out_date = reservation.check_out_date

            reservation.check_in_date = self.requested_check_in_date
            reservation.check_out_date = self.requested_check_out_date
            reservation.status = 'Rebooked'
            reservation.rebooking_date = timezone.now().date()
            reservation.has_been_rebooked = True
            reservation.save(update_fields=[
                'check_in_date', 'check_out_date', 'status', 'rebooking_date', 'has_been_rebooked'
            ])
        elif self.status == 'Cancelled' and original_status != 'Cancelled':
            previous_rebooking = self.__class__.objects.filter(
                reservation=reservation,
                status='Approved'
            ).last()

            if previous_rebooking:
                reservation.check_in_date = previous_rebooking.requested_check_in_date
                reservation.check_out_date = previous_rebooking.requested_check_out_date
            else:
                reservation.check_in_date = reservation.original_check_in_date
                reservation.check_out_date = reservation.original_check_out_date

            reservation.status = 'Booked'
            reservation.has_been_rebooked = False
            reservation.save(update_fields=[
                'check_in_date', 'check_out_date', 'status', 'has_been_rebooked'
            ])



def gcash_receipt_upload_path(instance, filename):
    # Use the first name of the guest and create a folder structure
    guest_first_name = instance.reservation.guest.first_name
    sanitized_first_name = ''.join(e for e in guest_first_name if e.isalnum())  # Remove special characters
    return f'gcash_receipts/{sanitized_first_name}/{filename}'


class GCashReceipt(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="gcash_receipt")
    gcash_number = models.CharField(max_length=15)
    gcash_account_name = models.CharField(max_length=255)
    gcash_reference_number = models.CharField(max_length=100)
    uploaded_receipt = models.ImageField(upload_to=gcash_receipt_upload_path)  # Use custom upload path
    payment_type = models.CharField(max_length=50)  # Full Payment or Down Payment
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GCash Receipt for Reservation {self.reservation.reservation_ID}"



def get_upload_path(instance, filename):
    return f"inventory/addons/{filename}"

class AddOn(models.Model):
    STATUS_CHOICES = [
        ('Add On', 'Add On'),
        ('Supply', 'Supply'),
    ]

    id = models.AutoField(primary_key=True)
    add_on_name = models.CharField(max_length=255, verbose_name="AddOn Name")
    add_on_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="AddOn Price")
    add_on_quantity = models.PositiveIntegerField(verbose_name="AddOn Quantity")
    add_on_image = models.ImageField(upload_to=get_upload_path, verbose_name="AddOn Image")
    add_on_status = models.CharField(max_length=50, choices=STATUS_CHOICES, verbose_name="AddOn Status")
    add_on_descriptions = models.CharField(max_length=255, choices=STATUS_CHOICES, verbose_name="AddOn Status")
    sell_by_2 = models.BooleanField(default=False, verbose_name="Sell by 2")  # New field for "Sell by 2"


    def __str__(self):
        return f"{self.add_on_name} (ID: {self.id})"

    # Check if the add-on is in stock
    def is_in_stock(self):
        return self.add_on_quantity > 0

    def get_selling_quantity(self):
        # Returns 2 if "Sell by 2" is enabled, otherwise the full stock
        return 2 if self.sell_by_2 else self.add_on_quantity
    

class Dropdown(models.Model):
    id = models.AutoField(primary_key=True)
    add_on_name = models.CharField(max_length=255, verbose_name="AddOn Name")

    
    


class WalkInReservation(models.Model):
    STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('Refunded', 'Refunded'),
    ]

    walk_in_ID = models.CharField(max_length=6, unique=True, editable=False, default='')  # 6-digit unique ID
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    contact_number = models.CharField(max_length=15)
    address = models.TextField()
    arrival_datetime = models.DateTimeField()
    status_rate = models.CharField(max_length=50)
    cottage_rate = models.CharField(max_length=50)
    cottage_count = models.PositiveIntegerField(default=1)  # NEW FIELD
    payment_method = models.CharField(max_length=20)
    total_guest_count = models.PositiveIntegerField(default=0)
    total_child_count = models.PositiveIntegerField(default=0)
    overall_total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    guest_id_proof = models.ImageField(upload_to='guest_id_proofs/', blank=True, null=True)
    walk_in_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Ongoing')  # Renamed field

    def save(self, *args, **kwargs):
        if not self.walk_in_ID:  # Only generate if not already set
            self.walk_in_ID = self.generate_unique_id()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_id():
        while True:
            random_id = f"{random.randint(100000, 999999)}"  # Generate 6-digit number
            if not WalkInReservation.objects.filter(walk_in_ID=random_id).exists():
                return random_id

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.status_rate}"




    
class GuestIdProof(models.Model):
    walk_in_reservation = models.ForeignKey(WalkInReservation, on_delete=models.CASCADE, related_name="guest_id_proofs")
    image = models.ImageField(upload_to='guest_id_proofs/')

    def __str__(self):
        return f"ID Proof for {self.walk_in_reservation.first_name} {self.walk_in_reservation.last_name}"


def get_upload_path(instance, filename):
    # Ensure the folder name is safe by stripping special characters
    folder_name = instance.cottage_rate_name.replace(" ", "_")
    return os.path.join('rates', folder_name, filename)

class CottageRate(models.Model):
    id = models.AutoField(primary_key=True)  # Auto-incrementing primary key
    cottage_rate_name = models.CharField(max_length=255, verbose_name="Cottage Rate Name")
    cottage_rate_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cottage Rate Price")
    cottage_rate_capacity = models.PositiveIntegerField(verbose_name="Cottage Rate Capacity")
    cottage_rate_unit = models.PositiveIntegerField(verbose_name="Available Count")
    cottage_rate_image = models.ImageField(upload_to=get_upload_path, verbose_name="Cottage Image")

    def __str__(self):
        return f"{self.cottage_rate_name} (ID: {self.id})"


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
        ('reserved', 'Reserved'),
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
    room_unit = models.PositiveIntegerField(default=1, help_text="Number of units available for this room")
    room_image = models.ImageField(upload_to=room_main_image_path)
    room_images = models.ManyToManyField('RoomImage', blank=True, related_name='rooms')
    room_amenities = models.ManyToManyField('Amenity', blank=True)
    room_status = models.CharField(max_length=15, choices=ROOM_STATUS_CHOICES, default='available')
    last_available_unit = models.PositiveIntegerField(default=1, editable=False)
    room_description = models.TextField(max_length=100, blank=True, help_text="A detailed description of the room's features and layout.")
    bed_type = models.CharField(max_length=10, choices=BED_TYPE_CHOICES, default='queen')
    discount = models.DecimalField(blank=True, max_digits=5, decimal_places=2, default=0.00)
    bed_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if not self.bed_count:
            raise ValidationError("Bed count is required and must be between 1 and 4.")
        
        max_capacity = self.bed_count * 3
        if not (1 <= self.room_capacity <= max_capacity):
            raise ValidationError(
                f"Room capacity must be between 1 and {max_capacity} for the selected bed count."
            )

    def save(self, *args, **kwargs):
        # Save current units when status changes to maintenance
        if self.room_status == 'maintenance' and self.room_unit > 0:
            self.last_available_unit = self.room_unit
            self.room_unit = 0  # Set units to 0

        # Restore units when status changes to available
        elif self.room_status == 'available' and self.room_unit == 0:
            self.room_unit = self.last_available_unit

        super().save(*args, **kwargs)

    @property
    def is_available(self):
        # Check if room is available
        if self.room_status != 'available':
            return False

        # Check for conflicting reservations
        conflicting_reservations = Reservation.objects.filter(
            room_chosen=self,
            check_in_date__lt=now().date() + timedelta(days=1),
            check_out_date__gt=now().date()
        )
        return not conflicting_reservations.exists() and self.room_unit > 0

    def __str__(self):
        # Include room unit count in the string representation
        return f"{self.room_name} (Units: {self.room_unit})"

    def is_new(self):
        # Check if the room is newly created
        return now() - self.created_at <= timedelta(hours=24)

    
    
    
class RoomAvailability(models.Model):
    room = models.ForeignKey(
        'Room',
        on_delete=models.CASCADE,
        related_name='availabilities'
    )
    date = models.DateField()
    is_available = models.BooleanField(default=True)

class Meta:
    constraints = [
        models.UniqueConstraint(fields=['room', 'date'], name='unique_room_date')
    ]



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





class Schedule(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    id = models.AutoField(primary_key=True)
    staff_name = models.CharField(max_length=100)
    staff_role = models.CharField(max_length=100)
    time_shift = models.TimeField()  # Time for start
    time_ends = models.TimeField()   # Time for end
    days = models.CharField(max_length=255)  # Comma-separated days
    color = models.CharField(max_length=7, default="#007bff")  # Hex color

    def __str__(self):
        return f"{self.staff_name} - {self.staff_role} (ID: {self.id})"
    

class Sale(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    handled_by = models.CharField(max_length=100)
    date_created = models.DateTimeField(default=now)
    
class SalesReport(models.Model):
    file_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=now)