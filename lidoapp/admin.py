from django.contrib import admin
from django import forms
from .models import GuestAccount, Reservation, AdminAccount, AddOn, WalkInReservation, FrontdeskAccount, Room, RoomImage, Amenity
from django.db.models import F
from django.contrib.auth.hashers import make_password
from django.utils.html import format_html

# Register FrontdeskAccount
@admin.register(FrontdeskAccount)
class FrontdeskAccountAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'gender')
    search_fields = ('first_name', 'last_name', 'email')

# Register Room model with room_id in the list_display
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'room_name', 'room_price', 'room_capacity', 'room_size', 'get_bed_type_display')

    def get_bed_type_display(self, obj):
        return obj.get_bed_type_display()
    
    get_bed_type_display.short_description = 'Bed Type'


# Register RoomImage model
@admin.register(RoomImage)
class RoomImageAdmin(admin.ModelAdmin):
    list_display = ('id',)
    search_fields = ('id',)

# Register Amenity model
@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('amenity_type',)
    search_fields = ('amenity_type',)

# The rest of your previously registered models
class GuestAccountAdminForm(forms.ModelForm):
    class Meta:
        model = GuestAccount
        fields = ['first_name', 'middle_name', 'last_name', 'last_name', 'email', 'password', 'contact_number', 'telephone_number', 'address1']

    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Leave blank to keep the current password.",
        required=False
    )

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            return make_password(password)  # Hash the password
        return self.instance.password  # Keep the existing password if left blank
    
@admin.register(GuestAccount)
class GuestAccountAdmin(admin.ModelAdmin):
    form = GuestAccountAdminForm
    list_display = ('first_name', 'last_name', 'email', 'address1', 'contact_number', 'birthdate', 'gender')
    search_fields = ('first_name', 'last_name', 'email')

    def save_model(self, request, obj, form, change):
        # Automatically hash the password if changed
        if form.cleaned_data.get("password"):
            obj.password = form.cleaned_data["password"]
        super().save_model(request, obj, form, change)




@admin.register(AdminAccount)
class AdminAccountAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'gender')
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_ID', 'guest', 'check_in_date', 'check_out_date', 'room_chosen', 'status', 'invoice_link')
    readonly_fields = ('reservation_ID', 'invoice_link')  # Make reservation_ID and invoice_link read-only
    search_fields = ('guest__email', 'room_chosen', 'reservation_ID', 'status')  # Search fields
    fields = (
        'reservation_ID', 'guest', 'check_in_date', 'check_out_date', 'room_chosen',
        'add_ons', 'adult_count', 'children_count', 'total_guest_count', 'overall_total_amount', 
        'status', 'invoice_link'
    )

    def invoice_link(self, obj):
        if obj.invoice_file:
            return format_html(
                '<a href="{}" target="_blank">Download Invoice</a>',
                obj.invoice_file.url
            )
        return "No Invoice Available"
    invoice_link.short_description = "Invoice"


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock_quantity')  # Display the fields in the admin
    search_fields = ('name', 'description')


@admin.register(WalkInReservation)
class WalkInReservationAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'status_rate', 'arrival_datetime', 'total_guest_count', 'total_child_count', 'overall_total_amount')
    search_fields = ('first_name', 'last_name', 'status_rate', 'email', 'arrival_datetime')
    list_filter = ('status_rate', 'arrival_datetime')
    readonly_fields = ('overall_total_amount',)  # Make the total amount read-only
    fields = ('first_name', 'middle_name', 'last_name', 'email', 'contact_number', 'address', 'arrival_datetime', 'status_rate', 'cottage_rate', 'payment_method', 'total_guest_count', 'total_child_count', 'overall_total_amount')  # Specify the fields to display
