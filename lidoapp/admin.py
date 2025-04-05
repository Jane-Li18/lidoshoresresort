from django.contrib import admin
from django import forms
from .models import HotelInfo, GuestInquiry, GuestAccount, Receipt, Dropdown, Reservation, AdminAccount, AddOn, FrontdeskAccount, Room, SalesReport, RoomImage, Amenity, Schedule, Banner, RebookingRequest, GalleryImage, Policy, WalkInReservation, CottageRate
from django.db.models import F
from django.contrib.auth.hashers import make_password
from django.utils.html import format_html


admin.site.register(HotelInfo)

@admin.register(GuestInquiry)
class GuestInquiryAdmin(admin.ModelAdmin):
    list_display = ("question", "answer", "created_at")
    search_fields = ("question", "answer")
    list_filter = ("created_at",)
    
    
    
# Register FrontdeskAccount
@admin.register(FrontdeskAccount)
class FrontdeskAccountAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'gender')
    search_fields = ('first_name', 'last_name', 'email')
    

@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('image_name', 'gallery_type', 'uploaded_at')
    list_filter = ('gallery_type', 'uploaded_at')
    search_fields = ('image_name',)

@admin.register(Banner)
class Banner(admin.ModelAdmin):
    list_display = ('banner_name', 'banner_type', 'created_at')
    
@admin.register(Dropdown)
class DropdownAdmin(admin.ModelAdmin):
    list_display = ('add_on_name',)  # Add a comma to make it a tuple


# Register Room model with room_id in the list_display
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'room_name', 'room_price', 'room_unit', 'room_status', 'room_capacity', 'room_size', 'get_bed_type_display')

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

class PolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'policy_type', 'content', 'updated_at', 'created_at')  # Columns to display
    list_filter = ('policy_type',)  # Filter by policy type
    search_fields = ('content',)  # Search by content
    ordering = ('-updated_at',)  # Order by most recently updated

admin.site.register(Policy, PolicyAdmin)

@admin.register(AdminAccount)
class AdminAccountAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'gender')
    search_fields = ('first_name', 'last_name', 'email')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_ID', 'guest', 'check_in_date', 'check_out_date', 
                    'room_chosen', 'status', 'mode_of_payment', 'payment_type', 'invoice_link')
    readonly_fields = ('reservation_ID', 'invoice_link', 'mode_of_payment', 'payment_type')
    search_fields = ('guest__email', 'room_chosen', 'reservation_ID', 'status')
    fields = (
        'reservation_ID', 'guest', 'check_in_date', 'check_out_date', 'room_chosen',
        'add_ons', 'adult_count', 'children_count', 'total_guest_count', 'overall_total_amount', 
        'status', 'mode_of_payment', 'payment_type', 'invoice_link'
    )
    actions = ['confirm_rebook']

    def invoice_link(self, obj):
        if obj.invoice_file:
            return format_html(
                '<a href="{}" target="_blank">Download Invoice</a>',
                obj.invoice_file.url
            )
        return "No Invoice Available"
    invoice_link.short_description = "Invoice"

    def mode_of_payment(self, obj):
        # Determine mode of payment
        if hasattr(obj, 'gcash_receipt'):
            return "GCash"
        return "PayPal"
    mode_of_payment.short_description = "Mode of Payment"

    def payment_type(self, obj):
        # Determine payment type
        if hasattr(obj, 'gcash_receipt'):
            return obj.gcash_receipt.payment_type
        return "Full Payment"  # Default for PayPal
    payment_type.short_description = "Payment Type"

    def confirm_rebook(self, request, queryset):
        # Only process reservations in Pending status
        pending_reservations = queryset.filter(status='Pending')
        updated_count = pending_reservations.update(status='Booked')

        self.message_user(
            request,
            f"Successfully confirmed {updated_count} rebook requests as 'Booked'."
        )
    confirm_rebook.short_description = "Confirm Rebook Requests"


@admin.register(RebookingRequest)
class RebookingRequestAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'requested_check_in_date', 'requested_check_out_date', 'status', 'requested_at', 'handled_by')
    search_fields = ('reservation__reservation_ID', 'status', 'handled_by__email')
    list_filter = ('status', 'requested_at')
    readonly_fields = ('requested_at',)

    def get_queryset(self, request):
        # Customize the queryset to prefetch related data for efficiency
        qs = super().get_queryset(request)
        return qs.select_related('reservation', 'handled_by')


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ('add_on_name', 'add_on_price', 'add_on_quantity', 'add_on_status', 'is_in_stock')
    search_fields = ('add_on_name',)

    def is_in_stock(self, obj):
        return obj.add_on_quantity > 0
    is_in_stock.boolean = True  # Display as a boolean icon
    is_in_stock.short_description = 'In Stock'



@admin.register(WalkInReservation)
class WalkInReservationAdmin(admin.ModelAdmin):
    list_display = ('walk_in_ID', 'first_name', 'last_name', 'walk_in_status', 'status_rate', 'arrival_datetime', 'total_guest_count', 'total_child_count', 'overall_total_amount')
    search_fields = ('first_name', 'last_name', 'walk_in_status', 'email', 'arrival_datetime', 'status_rate')
    list_filter = ('walk_in_status', 'status_rate', 'arrival_datetime')
    readonly_fields = ('overall_total_amount',)


@admin.register(CottageRate)
class CottageRateAdmin(admin.ModelAdmin):
    list_display = ('cottage_rate_name', 'cottage_rate_price', 'cottage_rate_capacity', 'cottage_rate_unit')
    search_fields = ('cottage_rate_name',)
    list_filter = ('cottage_rate_capacity', 'cottage_rate_price', 'cottage_rate_unit')
    
    
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('staff_name', 'staff_role', 'time_shift', 'time_ends', 'formatted_days')
    search_fields = ('staff_name', 'staff_role')
    list_filter = ('days',)
    list_editable = ('time_shift', 'time_ends')
    

    def formatted_days(self, obj):
        return ", ".join(obj.days.split(","))
    formatted_days.short_description = 'Days'


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ('file_path', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('file_path',)
    
    
@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'handled_by', 'total_amount', 'created_at')
    search_fields = ('reservation__reservation_ID', 'handled_by')