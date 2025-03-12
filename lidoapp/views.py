# Import models from the current app
from .models import (
    GuestAccount, Reservation, RebookingRequest, AdminAccount, AddOn,
    FrontdeskAccount, Room, RoomImage, Amenity, Policy, GCashReceipt, RoomAvailability, GalleryImage, WalkInReservation, CottageRate, GuestIdProof,
    Schedule, Sale, SalesReport, Banner, Receipt, Dropdown
)

# Import forms from the current app
from .forms import GuestAccountForm, AdminAccountForm, RoomForm, FrontdeskAccountForm

# Standard libraries
import json
import logging
import re
import random
from datetime import timedelta



# Set up logger for the module
logger = logging.getLogger(__name__)


# Import necessary Django modules
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from django.urls import reverse

from django.core.files.storage import default_storage

from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localtime, now, localdate, make_aware
from django.utils.text import slugify
import pprint
import pytz
from datetime import date, datetime, time
from django.db.models import Sum, Q, Count, Prefetch, Max, F
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.template.loader import render_to_string
from django.conf import settings
import os
import calendar
from django.db.models.functions import ExtractWeek, ExtractMonth, ExtractYear, TruncDate
from django.template.loader import render_to_string
from calendar import month_name

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# Import external libraries for handling PDFs and requests
import requests
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen.canvas import Canvas

# Google reCAPTCHA modules for verification
from google.cloud import recaptchaenterprise_v1
from google.cloud.recaptchaenterprise_v1 import Assessment
from django.contrib.auth.hashers import make_password

# For encoding and making requests
import base64
import requests


from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Image as ReportLabImage 

from PIL import Image as PILImage
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile
import os
from io import BytesIO
from django.shortcuts import get_object_or_404
from django.core.files import File
from lidoapp.models import Reservation, RoomAvailability
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle

from reportlab.platypus import Image as ReportLabImage, Spacer, Paragraph
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from django.http import FileResponse, HttpResponse
import openpyxl
from openpyxl.styles import Alignment

from django.db.models import F, Sum, Value
from django.db.models.functions import Cast
from openpyxl import Workbook
# Clear Django cache (if using caching)
from django.core.cache import cache
cache.clear()



def custom_page_not_found_view(request, exception):
    return render(request, '404.html', status=404)

handler404 = 'lidoapp.urls.custom_page_not_found_view'


# Ensure font files exist before registration
FONT_DIR = os.path.join(settings.BASE_DIR, 'lidoapp', 'static', 'assets', 'fonts')
MONTSERRAT_REGULAR = os.path.join(FONT_DIR, 'Montserrat-Regular.ttf')
MONTSERRAT_BOLD = os.path.join(FONT_DIR, 'Montserrat-Bold.ttf')
MONTSERRAT_ITALIC = os.path.join(FONT_DIR, 'Montserrat-Italic.ttf')

if not all(os.path.exists(font) for font in [MONTSERRAT_REGULAR, MONTSERRAT_BOLD, MONTSERRAT_ITALIC]):
    raise FileNotFoundError("One or more font files are missing in the specified path.")

# Register fonts
pdfmetrics.registerFont(TTFont('Montserrat', MONTSERRAT_REGULAR))
pdfmetrics.registerFont(TTFont('Montserrat-Bold', MONTSERRAT_BOLD))
pdfmetrics.registerFont(TTFont('Montserrat-Italic', MONTSERRAT_ITALIC))


def generate_invoice(request, reservation_id, is_rebooked=False):
    reservation = get_object_or_404(Reservation, reservation_ID=reservation_id)
    
    reservation_status = reservation.status
    
    # Define Philippine timezone
    philippine_timezone = pytz.timezone("Asia/Manila")
    transaction_time = localtime(reservation.created_at, philippine_timezone)

    # Define guest-specific folder for invoices
    guest_folder = os.path.join(settings.MEDIA_ROOT, f"invoices/{reservation.guest.id}/")
    invoices_folder = os.path.join(guest_folder, "invoices")
    receipts_folder = os.path.join(guest_folder, "receipts")
    os.makedirs(guest_folder, exist_ok=True)
    os.makedirs(invoices_folder, exist_ok=True)
    os.makedirs(receipts_folder, exist_ok=True)


    # Define file path
    invoice_filename = f"Reservation_Invoice_{reservation.reservation_ID}.pdf"
    if is_rebooked:
        invoice_filename = f"Rebooked_Invoice_{reservation.reservation_ID}.pdf"
    invoice_path = os.path.join(invoices_folder, invoice_filename)

    
    # Generate the invoice path
    guest_folder = os.path.join(settings.MEDIA_ROOT, f"invoices/{reservation.guest.id}/")
    os.makedirs(guest_folder, exist_ok=True)
    invoice_path = os.path.join(guest_folder, invoice_filename)

    # Setup document and styles
    doc = SimpleDocTemplate(
        invoice_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=14, fontName='Montserrat-Bold')
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Montserrat', fontSize=9)
    italic_style = ParagraphStyle('Italic', parent=normal_style, fontName='Montserrat-Italic', alignment=1)
    bold_style = ParagraphStyle('Bold', parent=normal_style, fontName='Montserrat-Bold', fontSize=9)
    highlighted_style = ParagraphStyle('Highlighted', parent=bold_style, textColor=colors.black, fontSize=10)
    crossed_out_style = ParagraphStyle('CrossedOut', parent=styles['Normal'], fontName='Montserrat', textColor=colors.red, fontSize=9)
    centered_style = ParagraphStyle('Centered', parent=bold_style, alignment=1)

    elements = []

    # Add Lido Logo
    logo_path = os.path.join(settings.BASE_DIR, 'lidoapp/static/assets/images/components/fulllogo.png')
    if os.path.exists(logo_path):
        logo = ReportLabImage(logo_path, width=50 * mm, height=50 * mm, hAlign='CENTER')
        elements.append(logo)
    else:
        elements.append(Paragraph("Lido Shores Resort (Logo Missing)", title_style))

    elements.append(Spacer(1, 5))

    # Resort Address (Centered and Italic)
    # Define a centered style with Montserrat font
    montserrat_centered_style = ParagraphStyle(
        name="MontserratCentered",
        fontName="Montserrat",
        fontSize=10,
        leading=14,  # Line spacing
        alignment=TA_CENTER  # Center alignment
    )

    # Define the address text
    address = """
    Sariaya, Quezon Province<br/>
    Brgy. Talaan, Aplaya, Sariaya, Calabarzon, 4322, Philippines<br/>
    lidoshores.sariaya@gmail.com<br/>
    +639173004577 Viber Only
    """

    # Add the centered address to elements
    elements.append(Paragraph(address, montserrat_centered_style))
    elements.append(Spacer(1, 5))

    # Invoice Header
    elements.append(Paragraph(f"Invoice for Reservation", title_style))
    elements.append(Spacer(1, 10))
    
    # Transaction Date and Time (in Philippine Time)
    elements.append(Paragraph(f"Transaction Date and Time: {transaction_time.strftime('%b %d, %Y %I:%M %p')}", normal_style))
    elements.append(Spacer(1, 5))


    # Check-in/Check-out Dates
    if is_rebooked and reservation.original_check_in_date:
        elements.append(Paragraph(f"Original Check-in Date: <strike>{reservation.original_check_in_date}</strike>", crossed_out_style))
        elements.append(Paragraph(f"Original Check-out Date: <strike>{reservation.original_check_out_date}</strike>", crossed_out_style))

    # Highlight the new/updated check-in and check-out dates
    elements.append(Paragraph(f"New Check-in Date: {reservation.check_in_date} (after 3:00 PM)", bold_style))
    elements.append(Paragraph(f"New Check-out Date: {reservation.check_out_date} (before 12:00 PM)", bold_style))

    # Add any additional rebooking-specific details
    if is_rebooked:
        elements.append(Paragraph(f"Rebooking Confirmed Date: {reservation.rebooking_date}", bold_style))

    elements.append(Spacer(1, 10))
    # Highlighted Reservation Details
    elements.append(Paragraph(f"Reservation ID: {reservation.reservation_ID}", highlighted_style))
    elements.append(Paragraph(f"Room Chosen: {reservation.room_chosen}"))
    elements.append(Paragraph(f"Reservation Status: {reservation.status}"))

    
    # Mode of Payment
    mode_of_payment = "GCash" if hasattr(reservation, 'gcash_receipt') else "PayPal"
    elements.append(Paragraph(f"Mode of Payment: {mode_of_payment}"))
    elements.append(Spacer(1, 10))

    # Guest Details Table
    guest_data = [
        ['Guest Name', f"{reservation.prefix} {reservation.first_name} {reservation.last_name}"],
        ['Email', reservation.email],
        ['Contact Number', reservation.contact_number],
        ['Address 1', reservation.address1],
    ]
    if reservation.address2:
        guest_data.append(['Address 2', reservation.address2])
    if reservation.city:
        guest_data.append(['City', reservation.city])
    if reservation.postal_code:
        guest_data.append(['Postal Code', reservation.postal_code])
    guest_data.append(['Country', reservation.country])

    guest_table = Table(guest_data, colWidths=[40 * mm, 100 * mm])
    guest_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(guest_table)
    elements.append(Spacer(1, 10))
    
    # Add-ons Section
    if reservation.add_ons:
        elements.append(Paragraph("Add-Ons:", bold_style))
        add_ons_data = [['Name', 'Quantity', 'Price per Unit', 'Total']]
        for addon_name, addon_details in reservation.add_ons.items():
            add_ons_data.append([
                addon_name,
                addon_details['quantity'],
                f"P {float(addon_details['price']):,.2f}",
                f"P {float(addon_details['quantity'] * addon_details['price']):,.2f}",
            ])
        add_ons_table = Table(add_ons_data, colWidths=[40 * mm, 20 * mm, 40 * mm, 40 * mm])
        add_ons_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(add_ons_table)
        elements.append(Spacer(1, 10))

    # Guest and Room Details
    elements.append(Paragraph("Guest and Room Details:", bold_style))
    details_data = [
        ['Total Guests', reservation.total_guest_count],
        ['Adults', reservation.adult_count],
        ['Children (Ages 3+)', reservation.children_count],
        ['Overall Total', f"P {float(reservation.overall_total_amount):,.2f}"],
    ]
    if reservation.special_requests:
        details_data.append(['Special Requests', reservation.special_requests])

    details_table = Table(details_data, colWidths=[60 * mm, 80 * mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 10))


        
    # GCash Details Section
    if hasattr(reservation, 'gcash_receipt'):
        gcash_receipt = reservation.gcash_receipt
        elements.append(Paragraph("GCash Payment Details:", bold_style))
        gcash_data = [
            ['GCash Account Name', gcash_receipt.gcash_account_name or "N/A"],
            ['GCash Number', gcash_receipt.gcash_number or "N/A"],
            ['GCash Reference Number', gcash_receipt.gcash_reference_number or "N/A"],
            ['Payment Type', gcash_receipt.payment_type or "N/A"],
        ]

        gcash_table = Table(gcash_data, colWidths=[60 * mm, 100 * mm])
        gcash_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(gcash_table)
        elements.append(Spacer(1, 10))

        # Include the receipt image if available
        if gcash_receipt.uploaded_receipt:
            receipt_path = gcash_receipt.uploaded_receipt.path
            if os.path.exists(receipt_path):
                elements.append(Paragraph("Uploaded Receipt:", bold_style))
                receipt_image = ReportLabImage(receipt_path, width=100 * mm, height=150 * mm)
                elements.append(receipt_image)
            else:
                elements.append(Paragraph("Uploaded Receipt: Missing", italic_style))


                    

    # Always include the Corkage Fee Note section
    # Define a left-aligned style if not already defined
    left_aligned_style = ParagraphStyle(
        'LeftAligned',
        parent=italic_style,
        alignment=TA_LEFT
    )

    # Add the content with left-aligned text
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "<b>Important Information:</b><br/>"
        "• A corkage fee of P250 applies if you bring food or drinks from outside.<br/>"
        "• Please present this invoice copy to the front desk upon checking in.<br/>"
        "• Adding guests exceeding the room capacity will incur an additional fee of P500 per head.<br/><br/>"
        "<b>Daytour Rates (6:00 AM to 5:59 PM):</b><br/>"
        "  - P330 per person<br/>"
        "  - P165 per child (3ft below)<br/><br/>"
        "<b>Nighttour Rates (7:00 PM to 5:59 AM):</b><br/>"
        "  - P500 per person<br/>"
        "  - P250 per child (3ft below)<br/>",
        left_aligned_style
    ))
    elements.append(Spacer(1, 10))


    # Footer
    elements.append(Paragraph("<b>Thank you for your stay at Lido Shores Resort!</b>", centered_style))

    # Build the PDF and save to file
    doc.build(elements)

    # Save invoice file to database
    with open(invoice_path, 'rb') as f:
        reservation.invoice_file.save(invoice_filename, File(f), save=True)

    # Return HTTP response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice_filename}"'
    with open(invoice_path, 'rb') as f:
        response.write(f.read())

    return response


    


def get_access_token():
    client_id = "AZflrFYu7Hzrb8Y453N6quHZ-_quzkcIZguDad2dxZ1scr4_K4T08DWNwE3z1mDCbnpfu-jugzdGp4U2"
    secret = "EATzOQJqOAo1Ca5kT4-3d7kTp-5M_KgOAxMnPIP7SGLuV9j7syqC8_lRnGR3lwNnFp6JK71cLwzKJ1Ux"
    auth = f"{client_id}:{secret}"
    auth_b64 = base64.b64encode(auth.encode()).decode()

    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials"
    }

    response = requests.post(
        "https://api-m.sandbox.paypal.com/v1/oauth2/token",
        headers=headers,
        data=data
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("Error getting access token:", response.json())
        return None

@csrf_exempt
def create_booking(request):
    # Get PayPal access token
    access_token = get_access_token()
    if not access_token:
        return JsonResponse({"error": "Unable to fetch PayPal access token"}, status=500)

    # Parse the request body
    try:
        data = json.loads(request.body)
        print("Received data:", data)  # Debugging: Log incoming data
        total_price = data.get("totalPrice", "0.00")
        reservation_details = data.get("reservationDetails", {})
        print("Received reservationDetails:", reservation_details)  # Debugging
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request"}, status=400)

    # Validate room_chosen
    if not reservation_details.get('room_chosen'):
        print("Missing room_chosen in reservationDetails")
        return JsonResponse({"error": "Room not chosen. Please select a room before proceeding."}, status=400)

    # Save reservation details in session
    request.session['reservation_details'] = reservation_details

    # Prepare PayPal order creation payload
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "PHP",
                    "value": total_price,
                }
            }
        ],
        "application_context": {
            "return_url": "https://www.lidoshoresresort.online/success",
            "cancel_url": "https://www.lidoshoresresort.online/cancel",
        }
    }

    response = requests.post(
        "https://api-m.sandbox.paypal.com/v2/checkout/orders",
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        return JsonResponse(response.json())
    else:
        print("PayPal API Error:", response.json())
        return JsonResponse({"error": "Failed to create PayPal order"}, status=500)


    
@csrf_exempt
def success(request):
    token = request.GET.get('token')
    payer_id = request.GET.get('PayerID')

    access_token = get_access_token()
    if not access_token:
        return HttpResponse("Unable to fetch PayPal access token.", status=500)

    # Capture payment
    url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{token}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(url, headers=headers)

    if response.status_code == 201:
        reservation_details = request.session.get('reservation_details', {})
        try:
            # Validate and convert dates
            check_in_date = reservation_details.get('check_in_date')
            check_out_date = reservation_details.get('check_out_date')

            if isinstance(check_in_date, str):
                check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
            if isinstance(check_out_date, str):
                check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d').date()

            adult_count = int(reservation_details.get('adult_count', 0))
            children_count = int(reservation_details.get('children_count', 0))
            total_guest_count = adult_count + children_count

            # Fetch the room and update its unit
            room_name = reservation_details.get('room_chosen')
            room = Room.objects.select_for_update().get(room_name=room_name)

            if room.room_unit > 0:
                # Decrease the room unit
                room.room_unit -= 1

                # Update room status if no units remain
                if room.room_unit == 0:
                    room.room_status = 'maintenance'

                room.save()

                # Save the reservation
                reservation = Reservation.objects.create(
                    guest_id=request.session.get('guest_id'),
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    room_chosen=room_name,
                    adult_count=adult_count,
                    children_count=children_count,
                    total_guest_count=total_guest_count,
                    overall_total_amount=reservation_details.get('overall_total_amount', '0.00'),
                    prefix=reservation_details.get('prefix', ''),
                    first_name=reservation_details.get('first_name', ''),
                    last_name=reservation_details.get('last_name', ''),
                    email=reservation_details.get('email', ''),
                    contact_number=reservation_details.get('contact_number', ''),
                    address1=reservation_details.get('address1', ''),
                    address2=reservation_details.get('address2', ''),
                    city=reservation_details.get('city', ''),
                    postal_code=reservation_details.get('postal_code', ''),
                    country=reservation_details.get('country', ''),
                    special_requests=reservation_details.get('special_requests', ''),
                    add_ons=reservation_details.get('add_ons', {}),
                    status='Booked',
                )

                # Update add-on quantities
                if reservation_details.get('add_ons'):
                    for addon_name, addon_data in reservation_details['add_ons'].items():
                        try:
                            # Fetch the add-on by name
                            addon = AddOn.objects.get(add_on_name=addon_name)
                            requested_quantity = addon_data.get('quantity', 0)
                            addon.add_on_quantity = F('add_on_quantity') - requested_quantity
                            addon.save()

                            # Ensure the quantity doesn't go below zero
                            addon.refresh_from_db()
                            if addon.add_on_quantity < 0:
                                addon.add_on_quantity = 0
                                addon.save()
                        except AddOn.DoesNotExist:
                            print(f"Add-on with name '{addon_name}' does not exist.")
                        except Exception as e:
                            print(f"Error updating add-on '{addon_name}': {e}")

                # Update room availability for the reservation dates
                RoomAvailability.objects.filter(
                    room=room,
                    date__gte=check_in_date,
                    date__lt=check_out_date
                ).update(is_available=False)

                return redirect(f"/lidocompleted?reservation_ID={reservation.reservation_ID}")
            else:
                return HttpResponse("No available units for the selected room.", status=400)

        except Room.DoesNotExist:
            return HttpResponse(f"Room '{room_name}' does not exist.", status=400)
        except Exception as e:
            print(f"Error saving reservation: {e}")
            return HttpResponse(f"Failed to save reservation: {e}", status=500)
    else:
        print("PayPal Capture Error:", response.json())
        return HttpResponse("Payment failed or was not captured.", status=500)






@csrf_exempt
def capture_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('orderID')
            reservation_details = data.get('reservationDetails')

            # Fetch PayPal access token
            access_token = get_access_token()
            if not access_token:
                return JsonResponse({"error": "Unable to fetch PayPal access token"}, status=500)

            # Capture the payment
            url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }

            response = requests.post(url, headers=headers)
            if response.status_code == 201:  # HTTP 201 Created
                capture_response = response.json()

                # Save the reservation details in the database
                guest_id = request.session.get('guest_id')
                if not guest_id:
                    return JsonResponse({'error': 'Guest not logged in'}, status=400)

                adult_count = int(reservation_details.get('adult_count', 0))
                children_count = int(reservation_details.get('children_count', 0))
                total_guest_count = adult_count + children_count

                reservation = Reservation(
                    guest_id=guest_id,
                    check_in_date=reservation_details['check_in_date'],
                    check_out_date=reservation_details['check_out_date'],
                    room_chosen=reservation_details['room_chosen'],
                    adult_count=adult_count,  # Save adult count
                    children_count=children_count,  # Save children count
                    total_guest_count=total_guest_count,  # Save total guest count
                    overall_total_amount=reservation_details['overall_total_amount'],
                    status='Booked',  # Mark as Booked after successful payment
                )
                reservation.save()

                return JsonResponse({
                    "success": True,
                    "reservation_ID": str(reservation.reservation_ID),
                    "redirect_url": reverse('lidocompleted') + f"?reservation_ID={reservation.reservation_ID}",
                })
            else:
                print("PayPal Capture Error:", response.json())
                return JsonResponse({"error": "Failed to capture payment"}, status=500)
        except Exception as e:
            print(f"Error capturing payment or saving reservation: {e}")
            return JsonResponse({"error": "Internal server error"}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)





def create_assessment(
    project_id: str, recaptcha_key: str, token: str, recaptcha_action: str
) -> Assessment:
    """Create an assessment to analyze the risk of a UI action.
    Args:
        project_id: Your Google Cloud Project ID.
        recaptcha_key: The reCAPTCHA key associated with the site/app
        token: The generated token obtained from the client.
        recaptcha_action: Action name corresponding to the token.
    """

    client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient()

    # Set the properties of the event to be tracked.
    event = recaptchaenterprise_v1.Event()
    event.site_key = recaptcha_key
    event.token = token

    assessment = recaptchaenterprise_v1.Assessment()
    assessment.event = event

    project_name = f"projects/{project_id}"

    # Build the assessment request.
    request = recaptchaenterprise_v1.CreateAssessmentRequest()
    request.assessment = assessment
    request.parent = project_name

    response = client.create_assessment(request)

    # Check if the token is valid.
    if not response.token_properties.valid:
        print(
            "The CreateAssessment call failed because the token was "
            + "invalid for the following reasons: "
            + str(response.token_properties.invalid_reason)
        )
        return

    # Check if the expected action was executed.
    if response.token_properties.action != recaptcha_action:
        print(
            "The action attribute in your reCAPTCHA tag does"
            + "not match the action you are expecting to score"
        )
        return
    else:
        # Get the risk score and the reason(s).
        # For more information on interpreting the assessment, see:
        # https://cloud.google.com/recaptcha-enterprise/docs/interpret-assessment
        for reason in response.risk_analysis.reasons:
            print(reason)
        print(
            "The reCAPTCHA score for this token is: "
            + str(response.risk_analysis.score)
        )
        # Get the assessment name (id). Use this to annotate the assessment.
        assessment_name = client.parse_assessment_path(response.name).get("assessment")
        print(f"Assessment name: {assessment_name}")
    return response

def verify_recaptcha(request):
    token = request.POST.get('token')  # The token sent from the frontend

    # Google reCAPTCHA verification URL
    url = "https://recaptchaenterprise.googleapis.com/v1/projects/lido-shores-reso-1732877061788/assessments?key=YOUR_SECRET_KEY"
    
    # Your secret key (the secret key you got from the reCAPTCHA admin console)
    secret_key = 'YOUR_SECRET_KEY'

    # Prepare the data for verification
    payload = {
        'secret': secret_key,
        'response': token,
    }

    # Verify the CAPTCHA with Google
    response = requests.post(url, data=payload)
    result = response.json()

    if result.get('success'):
        # CAPTCHA passed
        return JsonResponse({"message": "CAPTCHA verified successfully!"})
    else:
        # CAPTCHA failed
        return JsonResponse({"message": "CAPTCHA verification failed!"}, status=400)
    


    

    

# Blogsite Views
def lidohome(request):
    banners = Banner.objects.all().order_by('-created_at')  # Fetch banners
    gallery_images = GalleryImage.objects.all().order_by('-uploaded_at')  # Fetch all gallery images

    # Fetch the latest Description Policy
    latest_description_policy = Policy.objects.filter(policy_type__iexact='description').order_by('-updated_at').first()
    description_content = (
        latest_description_policy.content 
        if latest_description_policy 
        else "Experience an unparalleled coastal retreat at Lido Shores, a distinguished seaside resort in Sariaya, Quezon. Modern comforts blend with traditional hospitality, offering stunning sea views, impeccably appointed accommodations, and attentive service. Discover a sanctuary crafted for your utmost delight."
    )

    return render(
        request,
        'blogsite/lidohome.html',
        {
            'banners': banners,
            'description_content': description_content,
            'gallery_images': gallery_images,  # Pass gallery images to the template
        }
    )



def lidoroomrates(request):
    return render(request, 'blogsite/header/lidoroomrates.html')

def room_rates_booking(request):
    check_in_date = request.GET.get('check_in_date', datetime.today().date())
    check_out_date = request.GET.get('check_out_date', datetime.today().date() + timedelta(days=1))
    total_guests = int(request.GET.get('total_guests', 1))
    excluded_children_count = int(request.GET.get('excluded_children_count', 0))
    guest_count = total_guests - excluded_children_count

    bed_type = request.GET.get('bed_type', 'all').lower()
    min_price = int(request.GET.get('min_price', 0))
    max_price = int(request.GET.get('max_price', 999999))

    print(f"Filtering Rooms with: min_price={min_price}, max_price={max_price}, guest_count={guest_count}")

    # Fetch available rooms, considering units and ignoring status if units > 0
    rooms = Room.objects.prefetch_related('room_amenities').filter(
        room_capacity__gte=guest_count,
        room_price__gte=min_price,
        room_price__lte=max_price,
        room_unit__gt=0  # Ensure there are remaining units
    ).distinct().order_by('-created_at')

    if bed_type != 'all':
        rooms = rooms.filter(bed_type__iexact=bed_type)

    # Debugging
    print("Available Rooms:", list(rooms.values('room_name', 'room_unit', 'room_status')))

    return render(request, 'booking/roomrates_booking.html', {
        'rooms': rooms,
        'check_in_date': check_in_date,
        'check_out_date': check_out_date,
    })





def clean_up_room_availability(room):
    # Step 1: Find and remove duplicates for the specific room
    duplicates = (
        RoomAvailability.objects.filter(room=room)
        .values('room', 'date')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )

    for dup in duplicates:
        records = RoomAvailability.objects.filter(room=dup['room'], date=dup['date'])
        records.exclude(id=records.first().id).delete()

    # Step 2: Remove orphaned availability records (if any)
    RoomAvailability.objects.filter(room__isnull=True).delete()

    # Step 3: Log cleanup success
    print(f"Cleanup completed for room: {room.room_name}")



def get_room_availability(request):
    date = request.GET.get('date')
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Fetch room availability for the specific date
        room_availability = RoomAvailability.objects.filter(
            date=selected_date,
            room__isnull=False,
            room__room_status='available',  # Exclude rooms with 'maintenance' status
            room__room_unit__gt=0  # Include only rooms with units left
        )

        # Check for orphaned records (rooms that don't exist in Room model)
        valid_rooms = Room.objects.values_list('id', flat=True)
        room_availability = room_availability.filter(room_id__in=valid_rooms)

        total_available = room_availability.filter(is_available=True).count()

        availability = {
            ra.room.room_name: ra.is_available
            for ra in room_availability
        }

        return JsonResponse({
            'roomAvailability': availability,
            'totalAvailable': total_available,
            'isFull': total_available == 0  # Mark as 'Full' only if no rooms are available
        })
    except Exception as e:
        print(f"Error fetching room availability: {e}")
        return JsonResponse({'error': str(e)}, status=500)





@receiver(post_save, sender=Reservation)
def update_room_availability(sender, instance, **kwargs):
    room_name = instance.room_chosen
    try:
        room = Room.objects.get(room_name=room_name)
    except Room.DoesNotExist:
        print(f"Room '{room_name}' does not exist.")
        return

    if instance.status in ['Booked', 'Pending']:
        if room.room_unit > 0:
            # Ensure room availability reflects remaining units
            RoomAvailability.objects.filter(
                room=room,
                date__gte=instance.check_in_date,
                date__lt=instance.check_out_date
            ).update(is_available=True)
        else:
            # Set unavailable if no units remain
            RoomAvailability.objects.filter(
                room=room,
                date__gte=instance.check_in_date,
                date__lt=instance.check_out_date
            ).update(is_available=False)




@receiver(post_delete, sender=Reservation)
def update_room_availability_on_deletion(sender, instance, **kwargs):
    room_name = instance.room_chosen
    try:
        room = Room.objects.get(room_name=room_name)
    except Room.DoesNotExist:
        print(f"Room '{room_name}' does not exist.")
        return

    # Restore availability for the deleted reservation's dates
    RoomAvailability.objects.filter(
        room=room,
        date__gte=instance.check_in_date,
        date__lt=instance.check_out_date
    ).exclude(
        date__in=Reservation.objects.filter(
            room_chosen=room_name,
            status__in=['Booked', 'Pending']
        ).values_list('check_in_date', flat=True)
    ).update(is_available=True)
    print(f"Restored availability for room '{room_name}' after reservation deletion.")



@csrf_exempt
def update_reservation_status(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        reservation_id = data.get('reservation_id')
        new_status = data.get('status')

        try:
            reservation = Reservation.objects.get(id=reservation_id)
            room = Room.objects.get(room_name=reservation.room_chosen)

            if new_status in ['Cancelled', 'Refunded']:
                print(f"Updating room for reservation: {reservation_id}")

                # Restore room unit
                print(f"Before Increment: Room Units for '{room.room_name}': {room.room_unit}")
                room.room_unit += 1
                print(f"After Increment: Room Units for '{room.room_name}': {room.room_unit}")

                # Update room status if units are greater than 0
                if room.room_unit > 0:
                    print(f"Changing room status to 'Available' for '{room.room_name}'")
                    room.room_status = 'available'

                # Save the room after updating
                room.save()

                # Update RoomAvailability for the canceled/reserved dates
                RoomAvailability.objects.filter(
                    room=room,
                    date__gte=reservation.check_in_date,
                    date__lt=reservation.check_out_date
                ).update(is_available=True)

                print(f"Room availability restored for '{room.room_name}' from {reservation.check_in_date} to {reservation.check_out_date}")

            # Update reservation status
            reservation.status = new_status
            reservation.save(updated_by='Admin')  # Optional: Track who updated it

            print(f"Reservation status updated to '{new_status}' for reservation ID: {reservation_id}")

            return JsonResponse({'success': True, 'message': 'Reservation status updated and room availability restored.'})
        except Reservation.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Reservation not found.'})
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'message': f"Room '{reservation.room_chosen}' not found."})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})




def get_room_specific_availability(request):
    room_name = request.GET.get('room_name')
    check_in_date = request.GET.get('check_in_date')
    check_out_date = request.GET.get('check_out_date')

    if not room_name or not check_in_date or not check_out_date:
        return JsonResponse({'error': 'Missing parameters', 'is_available': False})

    try:
        check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d').date()

        # Check for overlapping reservations
        overlapping_reservations = Reservation.objects.filter(
            room_chosen=room_name,
            status__in=['Booked', 'Pending'],
            check_in_date__lt=check_out_date,
            check_out_date__gt=check_in_date
        ).exists()

        return JsonResponse({'room_name': room_name, 'is_available': not overlapping_reservations})
    except Exception as e:
        return JsonResponse({'error': str(e), 'is_available': False})



def update_availability_on_cancel(reservation):
    print(f"Updating availability for room {reservation.room_chosen} from {reservation.check_in_date} to {reservation.check_out_date}")
    try:
        room = Room.objects.get(room_name=reservation.room_chosen)
        # Increment room_unit
        room.room_unit += 1

        # Update room status if previously set to maintenance
        if room.room_unit > 0 and room.room_status == 'maintenance':
            room.room_status = 'available'

        room.save()

        # Update RoomAvailability
        RoomAvailability.objects.filter(
            room=room,
            date__gte=reservation.check_in_date,
            date__lt=reservation.check_out_date
        ).update(is_available=True)

        print(f"Availability restored for room '{reservation.room_chosen}'")
    except Room.DoesNotExist:
        print(f"Room '{reservation.room_chosen}' does not exist.")


@receiver(post_save, sender=Room)
def update_availability_on_status_change(sender, instance, **kwargs):
    if instance.room_status == 'maintenance':
        RoomAvailability.objects.filter(room=instance).update(is_available=False)
    elif instance.room_status == 'available' and instance.room_unit > 0:
        RoomAvailability.objects.filter(room=instance).update(is_available=True)

    
@receiver(post_save, sender=Room)
def create_room_availability(sender, instance, created, **kwargs):
    if created:
        # Populate RoomAvailability for the next 12 months
        start_date = date.today()
        end_date = start_date + timedelta(days=365)

        current_date = start_date
        while current_date <= end_date:
            RoomAvailability.objects.create(
                room=instance,
                date=current_date,
                is_available=instance.room_status == 'available' and instance.room_unit > 0
            )
            current_date += timedelta(days=1)
    else:
        # Update availability when room details change (e.g., room_status or room_unit)
        if instance.room_status == 'maintenance' or instance.room_unit == 0:
            RoomAvailability.objects.filter(room=instance).update(is_available=False)
        elif instance.room_status == 'available' and instance.room_unit > 0:
            RoomAvailability.objects.filter(room=instance).update(is_available=True)


def get_available_rooms(request):
    check_in_date = request.GET.get('check_in_date')
    check_out_date = request.GET.get('check_out_date')
    total_guests = int(request.GET.get('total_guests', 1))
    bed_type = request.GET.get('bed_type', 'all')
    min_price = float(request.GET.get('min_price', 0))
    max_price = float(request.GET.get('max_price', 1000000))

    try:
        check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if check_in_date >= check_out_date:
        return JsonResponse({'error': 'Check-out date must be after check-in date'}, status=400)

    # Fetch all rooms with overlapping reservations
    overlapping_reservations = Reservation.objects.filter(
        Q(check_in_date__lt=check_out_date) & Q(check_out_date__gt=check_in_date),
        status__in=['Booked', 'Pending']
    ).values_list('room_chosen', flat=True)

    # Fetch rooms that are available and have units left
    available_rooms = Room.objects.prefetch_related('room_amenities').filter(
        room_capacity__gte=total_guests,
        room_price__gte=min_price,
        room_price__lte=max_price,
        room_unit__gt=0  # Include rooms with remaining units
    ).exclude(
        room_name__in=overlapping_reservations
    ).distinct()

    if bed_type != 'all':
        available_rooms = available_rooms.filter(bed_type__iexact=bed_type)

    room_data = list(available_rooms.values(
        'room_name', 'room_price', 'room_capacity', 'bed_type', 'room_size', 'room_status', 'room_unit'
    ))

    # Debugging response data
    print("Rooms Sent to Frontend:", room_data)

    return JsonResponse({'rooms': room_data})







def lidobooking(request):
    if 'guest_id' not in request.session:
        return redirect('guest_signup')

    # Retrieve the check-in date, check-out date, and guest count from the GET parameters
    check_in_date_str = request.GET.get('check_in_date')
    check_out_date_str = request.GET.get('check_out_date')
    total_guests = int(request.GET.get('total_guests', 1))  # Default to 1 guest if not provided
    filter_sell_by_2 = request.GET.get('filter_sell_by_2', 'all')  # Retrieve filter parameter

    # Initialize dates
    check_in_date = None
    check_out_date = None

    # Parse the dates if they are present in the GET request
    if check_in_date_str and check_out_date_str:
        try:
            check_in_date = datetime.strptime(check_in_date_str, "%b %d, %Y").date()
            check_out_date = datetime.strptime(check_out_date_str, "%b %d, %Y").date()
        except ValueError:
            check_in_date = check_out_date = None  # Handle invalid date format

    # Fetch rooms based on the guest count and availability
    available_rooms = Room.objects.filter(
        room_capacity__gte=total_guests,  # Filter based on the number of guests
        room_status='available'  # Only show available rooms
    ).exclude(
        room_id__in=Reservation.objects.filter(
            check_in_date__lt=check_out_date if check_out_date else datetime.now().date(),
            check_out_date__gt=check_in_date if check_in_date else datetime.now().date()
        ).values_list('room_chosen', flat=True)
    )

    # Fetch add-ons based on the filter parameter
    if filter_sell_by_2 == 'sell_by_2':
        addons = AddOn.objects.filter(sell_by_2=True, add_on_quantity__gt=0)
    elif filter_sell_by_2 == 'not_sell_by_2':
        addons = AddOn.objects.filter(sell_by_2=False, add_on_quantity__gt=0)
    else:  # Show all add-ons by default
        addons = AddOn.objects.filter(add_on_quantity__gt=0)

    # Update each add-on's selling_quantity dynamically
    for addon in addons:
        addon.selling_quantity = 2 if addon.sell_by_2 else addon.add_on_quantity

    # Fetch the latest Guarantee Policy
    guarantee_policy = Policy.objects.filter(policy_type='guarantee').order_by('-updated_at').first()
    guarantee_content = (
        guarantee_policy.content
        if guarantee_policy
        else "<li>This is a <em>Book-and-Buy arrangement</em>.</li>"
             "<li>Full payment through credit card is required upon booking and is non-refundable but may be rebooked subject to applicable charges such as rate difference. Rebooking should be done at <span style='color: red; font-weight: bold;'>least 3 days</span> prior to arrival date. (Hotel Local Time).</li>"
    )

    # Fetch the latest Cancel Policy
    cancel_policy = Policy.objects.filter(policy_type='cancel').order_by('-updated_at').first()
    cancel_content = (
        cancel_policy.content
        if cancel_policy
        else "<li>This reservation is non-cancellable & non-refundable but may be rebooked subject to applicable rate difference.</li>"
             "<li>Rebooking should be done at <span style='color: red; font-weight: bold;'>least 3 days</span> before arrival. Full payment will be forfeited for no-show. Add-Ons will be cancelled automatically.</li>"
    )

    context = {
        'rooms': available_rooms,  # Pass filtered rooms
        'addons': addons,
        'check_in_date': check_in_date,
        'check_out_date': check_out_date,
        'total_guests': total_guests,
        'guarantee_content': guarantee_content,
        'cancel_content': cancel_content,
    }

    return render(request, 'booking/lidobooking.html', context)



def lidogallery(request):
    images = GalleryImage.objects.all()
    gallery_types = GalleryImage.objects.values_list('gallery_type', flat=True).distinct()
    return render(
        request,
        'blogsite/header/lidogallery.html',
        {
            'images': images,
            'gallery_types': gallery_types,
        }
    )


def lidocafe(request):
    return render(request, 'blogsite/header/lidocafe.html')

def lidoaboutus(request):
    return render(request, 'blogsite/header/lidoaboutus.html')

def guest_transactions(request):
    if 'guest_id' not in request.session:
        return redirect('guest_login')

    guest_id = request.session.get('guest_id')
    guest = GuestAccount.objects.get(id=guest_id)

    # Fetch reservations and prefetch rebooking requests & receipts
    reservations = Reservation.objects.filter(guest=guest).prefetch_related(
        Prefetch(
            'rebooking_requests',
            queryset=RebookingRequest.objects.order_by('-requested_at'),
            to_attr='all_requests'
        ),
        Prefetch(
            'receipts',
            queryset=Receipt.objects.exclude(receipt_file="").order_by('-created_at'),  # Exclude empty files
            to_attr='all_receipts'
        )
    ).order_by('-created_at')

    for reservation in reservations:
        # Determine mode of payment and payment type
        if hasattr(reservation, 'gcash_receipt'):
            reservation.mode_of_payment = "GCash"
            reservation.payment_type = reservation.gcash_receipt.payment_type
        else:
            reservation.mode_of_payment = "PayPal"
            reservation.payment_type = "Full Payment"

    return render(request, 'authentication/guest/guest_transactions.html', {'reservations': reservations})



def lidorooms(request):
    rooms = Room.objects.all()
    print(rooms)
    
    for room in rooms:
        print(room.room_image.url)  # Debugging: Check image URLs

    return render(request, 'blogsite/lidorooms.html', {'rooms': rooms})




def lidocompleted(request):
    reservation_id = request.GET.get('reservation_ID', None)  # Retrieve from query parameters
    context = {
        'clear_local_storage': True,
        'reservation_id': reservation_id,  # Pass the reservation ID to the template
    }
    return render(request, 'booking/lidocompleted.html', context)








# Authentication for Front Desk
def frontdesklogin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Ensure the email and password are only checked against AdminAccount
        if password:
            try:
                # Query only the AdminAccount model to check the email
                frontdesk = FrontdeskAccount.objects.get(email=email)
                
                # Verify the password using the `check_password` method
                if frontdesk.check_password(password):
                    request.session['frontdesk_id'] = frontdesk.id
                    return JsonResponse({'success': True, 'redirect_url': reverse('frontdesk_dashboard')})
                else:
                    return JsonResponse({
                        'success': False,
                        'icon_class': 'fa-solid fa-circle-exclamation',
                        'error': 'Incorrect password'
                    }, status=400)
            except FrontdeskAccount.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'icon_class': 'fa-solid fa-circle-exclamation',
                    'error': 'Couldn\'t find your Front Desk Account.'
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'Please enter a password.'
            }, status=400)

    return render(request, 'authentication/frontdesk/frontdesk_login.html')


def frontdesksignup(request):
    if request.method == 'POST':
        form = FrontdeskAccountForm(request.POST)
        if form.is_valid():
            # Log form data to ensure data processing
            print("Form Data:", form.cleaned_data)
            form.save()  # Save the admin account using the form
            return JsonResponse({'status': 'success', 'message': 'Front Desk account created successfully!'})
        else:
            # Log form errors
            print("Form Errors:", form.errors)
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = FrontdeskAccountForm()
    return render(request, 'authentication/frontdesk/frontdesk_signup.html', {'form': form})


def frontdesk_signup_success(request):
    return render(request, 'authentication/frontdesk/frontdesk_signup_success.html')


@csrf_exempt
def check_frontdesk_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if FrontdeskAccount.objects.filter(email=email).exists():
            return JsonResponse({'exists': True}, status=200)
        else:
            return JsonResponse({
                'exists': False,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'Couldn\'t find your Frontdesk Account.'
            }, status=200)
    return JsonResponse({
        'error': 'Invalid request',
        'icon_class': 'fa-solid fa-circle-exclamation'
    }, status=400)
    
    
@csrf_exempt
def check_frontdesk_signup_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Ensure only AdminAccount is checked
        if FrontdeskAccount.objects.filter(email=email).exists():
            return JsonResponse({
                'exists': True,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'This email is already registered as an frontdesk.'
            }, status=200)
        else:
            return JsonResponse({'exists': False}, status=200)

    return JsonResponse({
        'error': 'Invalid request',
        'icon_class': 'fa-solid fa-circle-exclamation'
    }, status=400)


def policy_board(request):
    latest_policies = (
        Policy.objects.values('policy_type')
        .annotate(latest_updated_at=Max('updated_at'))
    )
    policies = Policy.objects.filter(
        updated_at__in=[entry['latest_updated_at'] for entry in latest_policies]
    ).order_by('policy_type')

    # Localize timestamps to the desired timezone
    for policy in policies:
        policy.updated_at = localtime(policy.updated_at)
        logger.info(f"Policy Type: {policy.policy_type}, Updated At: {policy.updated_at}")
    
    return render(request, 'authentication/frontdesk/policy/policy_board.html', {
        'policies': policies,
    })


@csrf_exempt
def save_policy(request):
    """
    Saves a policy based on the provided policy_type and content.
    """
    if request.method == 'POST':
        policy_type = request.POST.get('policy_type')
        content = request.POST.get('content')

        if not policy_type or not content:
            return JsonResponse({'status': 'error', 'message': 'Policy type and content are required.'})

        # Save or update policy
        policy, created = Policy.objects.update_or_create(
            policy_type=policy_type,
            defaults={'content': content}
        )

        action = "created" if created else "updated"
        return JsonResponse({'status': 'success', 'message': f'Policy {action} successfully!'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

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


@csrf_exempt
def get_policies_by_type(request):
    """
    Retrieves policies based on policy_type.
    """
    policy_type = request.GET.get('policy_type')

    if not policy_type:
        return JsonResponse({'status': 'error', 'message': 'Policy type is required.'})

    policies = Policy.objects.filter(policy_type=policy_type).order_by('-updated_at')
    return JsonResponse(
        [
            {
                'id': policy.id,
                'content': policy.content,
                'updated_at': policy.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for policy in policies
        ],
        safe=False
    )

@csrf_exempt
def delete_policy(request, policy_id):
    """
    Deletes a specific policy by ID.
    """
    try:
        policy = Policy.objects.get(id=policy_id)
        policy.delete()
        return JsonResponse({'status': 'success', 'message': 'Policy deleted successfully!'})
    except Policy.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Policy not found.'})

def faq_policy(request):
    """
    Renders the FAQ policy page (specific case for rendering).
    """
    return render(request, 'authentication/frontdesk/policy/faq_policy.html')


# Helper function to generate room ID
def generate_room_id():
    return random.randint(100000, 999999)


def faq_policy(request):
    """
    Renders the FAQ policy page (specific case for rendering).
    """
    return render(request, 'authentication/frontdesk/policy/faq_policy.html')









def transaction_management(request):
    reservations = Reservation.objects.prefetch_related(
        Prefetch(
            'rebooking_requests',
            queryset=RebookingRequest.objects.order_by('-requested_at'),
            to_attr='all_requests'
        ),
        Prefetch(
            'receipts',
            queryset=Receipt.objects.order_by('-created_at'),
            to_attr='all_receipts'
        )
    ).select_related('guest').order_by('-created_at')

    for reservation in reservations:
        if hasattr(reservation, 'gcash_receipt'):
            reservation.mode_of_payment = "GCash"
            reservation.payment_type = reservation.gcash_receipt.payment_type
        else:
            reservation.mode_of_payment = "PayPal"
            reservation.payment_type = "Full Payment"

        reservation._latest_rebooking_request = (
            reservation.rebooking_requests.order_by('-requested_at').first()
        )

    rebooking_requests = RebookingRequest.objects.filter(status='Pending').select_related('reservation', 'reservation__guest')

    # Get add-ons with stock
    add_ons = AddOn.objects.filter(add_on_quantity__gt=0)

    # Get all dropdown items
    dropdown_items = Dropdown.objects.values_list('add_on_name', flat=True)

    # Merge both lists, avoiding duplicates
    combined_add_ons = list(add_ons) + [
        Dropdown(add_on_name=name) for name in dropdown_items if name not in add_ons.values_list('add_on_name', flat=True)
    ]

    return render(request, 'authentication/frontdesk/transactions/transaction_management.html', {
        'reservations': reservations,
        'rebooking_requests': rebooking_requests,
        'add_ons': combined_add_ons,  # Use the combined list
    })



    
@csrf_exempt
def save_receipt(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            reservation_id = data.get('reservation_id')
            handled_by = data.get('handledBy')
            description = data.get('description', '')
            items = data.get('items', [])
            total_amount = data.get('total_amount', 0)

            if not reservation_id:
                return JsonResponse({'status': 'error', 'message': 'Missing reservation_id'})

            reservation = get_object_or_404(Reservation, reservation_ID=reservation_id)

            # Create the receipt entry
            receipt = Receipt.objects.create(
                reservation=reservation,
                handled_by=handled_by,
                description=description,
                items=items,
                total_amount=total_amount
            )

            # Process items: Deduct stock only for AddOn model
            for item in items:
                add_on_name = item.get('name')
                quantity = int(item.get('quantity', 0))

                if add_on_name and quantity > 0:
                    # Check if the item exists in AddOn
                    add_on = AddOn.objects.filter(add_on_name=add_on_name).first()
                    if add_on:
                        # Ensure sufficient stock
                        if add_on.add_on_quantity >= quantity:
                            add_on.add_on_quantity -= quantity
                            add_on.save()
                        else:
                            return JsonResponse({'status': 'error', 'message': f'Insufficient stock for {add_on_name}'})
                    else:
                        # If not in AddOn, check if it's in Dropdown (allow saving)
                        if not Dropdown.objects.filter(add_on_name=add_on_name).exists():
                            return JsonResponse({'status': 'error', 'message': f'Invalid item: {add_on_name}'})

            # Generate receipt PDF
            generate_receipt(receipt.id)

            # Reload receipt to get the saved file
            receipt.refresh_from_db()

            return JsonResponse({
                'status': 'success',
                'message': 'Receipt saved successfully!',
                'receipt_url': receipt.receipt_file.url
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})





def generate_receipt(receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    reservation = receipt.reservation

    # Define Philippine timezone
    philippine_timezone = pytz.timezone("Asia/Manila")
    transaction_time = localtime(receipt.created_at, philippine_timezone)

    # Create directories for saving receipt
    guest_folder = os.path.join(settings.MEDIA_ROOT, f"receipts/{reservation.guest.id}/")
    os.makedirs(guest_folder, exist_ok=True)
    
    # Define file path
    receipt_filename = f"Receipt_{reservation.reservation_ID}.pdf"
    receipt_path = os.path.join(guest_folder, receipt_filename)

    # Remove old receipt if exists
    if os.path.exists(receipt_path):
        os.remove(receipt_path)

    # Setup document
    doc = SimpleDocTemplate(receipt_path, pagesize=(80 * mm, 200 * mm),
                            rightMargin=5 * mm, leftMargin=10 * mm,
                            topMargin=5 * mm, bottomMargin=5 * mm)

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=10, fontName='Montserrat-Bold')
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=7, fontName='Montserrat')
    bold_style = ParagraphStyle('Bold', parent=normal_style, fontName='Montserrat-Bold')
    big_bold_style = ParagraphStyle('BigBold', parent=bold_style, fontSize=9)
    centered_style = ParagraphStyle('Centered', parent=bold_style, alignment=1)

    elements = []

    # Add Logo
    logo_path = os.path.join(settings.BASE_DIR, 'lidoapp/static/assets/images/components/fulllogo.png')
    if os.path.exists(logo_path):
        logo = ReportLabImage(logo_path, width=40 * mm, height=40 * mm, hAlign='CENTER')
        elements.append(logo)
    else:
        elements.append(Paragraph("Lido Shores Resort (Logo Missing)", title_style))

    elements.append(Spacer(1, 2))

    # Add Address (Centered)
    address = Paragraph(
        "<b>Lido Shores Resort</b><br/>"
        "Brgy. Talaan, Aplaya, Sariaya, Quezon Province, Philippines<br/>"
        "Email: lidoshores.sariaya@gmail.com | Viber: +639173004577",
        centered_style
    )
    elements.append(address)
    elements.append(Spacer(1, 5))

    # Receipt Header
    elements.append(Paragraph("RECEIPT", title_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"Transaction Date: {transaction_time.strftime('%b %d, %Y %I:%M %p')}", normal_style))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(f"Reservation ID: <b>{reservation.reservation_ID}</b>", bold_style))
    elements.append(Paragraph(f"Handled By: <b>{receipt.handled_by}</b>", bold_style))
    elements.append(Spacer(1, 5))

    # Items Table (Item | Quantity | Amount)
    data = [[Paragraph("<b>Item</b>", bold_style), Paragraph("<b>Qty</b>", bold_style), Paragraph("<b>Amount</b>", bold_style)]]

    # Convert JSON string to list
    receipt_items = json.loads(receipt.items) if isinstance(receipt.items, str) else receipt.items

    for item in receipt_items:
        name = Paragraph(item.get('name', 'Unknown Item'), normal_style)
        quantity = Paragraph(str(item.get('quantity', 0)), normal_style)
        amount = Paragraph(f"P {float(item.get('amount', 0)):,.2f}", normal_style)
        data.append([name, quantity, amount])

    data.append(["", "", ""])
    data.append([Paragraph("<hr width='100%'/>", normal_style), "", ""])
    data.append([
        Paragraph("<b>TOTAL</b>", big_bold_style),
        "",
        Paragraph(f"<b>P {float(receipt.total_amount):,.2f}</b>", big_bold_style)
    ])

    table = Table(data, colWidths=[45 * mm, 10 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 5))

    if receipt.description:
        elements.append(Paragraph(f"<b>Description:</b> {receipt.description}", normal_style))
        elements.append(Spacer(1, 5))

    elements.append(Paragraph("<b>Thank you for your stay at Lido Shores Resort!</b>", centered_style))

    # Build PDF
    doc.build(elements)

    # Save Receipt in the Database
    with open(receipt_path, 'rb') as f:
        receipt.receipt_file.save(receipt_filename, File(f), save=True)

    return receipt


def get_receipts(request, reservation_id):
    reservation = get_object_or_404(Reservation, reservation_ID=reservation_id)
    receipts = Receipt.objects.filter(reservation=reservation)

    receipt_data = [
        {
            "id": receipt.id,
            "handled_by": receipt.handled_by,
            "items": receipt.items,
            "total_amount": receipt.total_amount,
            "created_at": receipt.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for receipt in receipts
    ]

    return JsonResponse({'status': 'success', 'receipts': receipt_data})


def rebooking_pending(request):
    rebooking_requests = RebookingRequest.objects.filter(status='Pending').select_related('reservation', 'reservation__guest')
    return render(request, 'authentication/frontdesk/rebooking_pending.html', {
        'rebooking_requests': rebooking_requests
    })

def update_transaction_management_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reservation_id = data.get('reservation_ID')
            new_status = data.get('status')
            manipulator_email = request.user.email if request.user.is_authenticated else "Unknown User"

            # Validate new status
            if new_status not in dict(Reservation.STATUS_CHOICES):
                return JsonResponse({'success': False, 'message': 'Invalid status'})

            # Fetch the reservation and update its status
            reservation = Reservation.objects.get(reservation_ID=reservation_id)
            reservation.status = new_status
            reservation.save()

            # Determine if the status is "Rebooked"
            is_rebooked = new_status == 'Rebooked'

            # Regenerate the invoice with the updated status
            generate_invoice(request, reservation_id, is_rebooked=is_rebooked)

            # Log the manipulator
            manipulator = FrontdeskAccount.objects.filter(email=manipulator_email).first()
            manipulator_name = manipulator.__str__() if manipulator else manipulator_email

            # Include manipulator's name in the response
            return JsonResponse({
                'success': True,
                'message': f'Status updated to {new_status} by {manipulator_name}. Invoice has been updated.'
            })
        except Reservation.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Reservation not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})






@csrf_exempt
def frontdesk_dashboard(request):
    reservations = Reservation.objects.all()

    # Fetch query parameter for filtering
    filter_date = request.GET.get('date', None)
    if filter_date:
        reservations = reservations.filter(created_at__date=filter_date)

    booked = reservations.filter(status='Booked').count()
    rebooked = reservations.filter(status='Rebooked').count()
    cancelled = reservations.filter(status='Cancelled').count()
    refunded = reservations.filter(status='Refunded').count()
    pending_reservation = reservations.filter(status='Pending').count()
    pending_rebooking = RebookingRequest.objects.filter(status='Pending').count()

    # Fetch ongoing reservations
    ongoing_reservations = reservations.filter(status__in=['Booked', 'Pending', 'Rebooked']).order_by('-created_at')

    context = {
        'booked': booked,
        'rebooked': rebooked,
        'cancelled': cancelled,
        'refunded': refunded,
        'pending_reservation': pending_reservation,
        'pending_rebooking': pending_rebooking,
        'ongoing_reservations': ongoing_reservations,
        'filter_date': filter_date,
    }
    return render(request, 'authentication/frontdesk/frontdesk_dashboard.html', context)







@csrf_exempt
def frontdesk_gallery(request):
    # Fetch gallery images and banners
    gallery_images = GalleryImage.objects.all().order_by('-uploaded_at')
    banners = Banner.objects.all().order_by('-created_at')

    # Merge images and banners into a single list
    images = list(gallery_images) + list(banners)

    # Get gallery types, adding "Banners" as a distinct type
    gallery_types = list(GalleryImage.objects.values_list('gallery_type', flat=True).distinct()) + ['Banners']

    # Render the template
    return render(
        request,
        'authentication/frontdesk/gallery/frontdesk_gallery.html',
        {
            'images': images,
            'gallery_types': gallery_types,
            'messages': get_messages(request),  # Pass the messages to the template
        }
    )


    
# @csrf_exempt
# def upload_image_or_banner(request):
#     if request.method == 'POST':
#         images_saved = []
#         banners_saved = []

#         # Determine if the upload is for a banner or an image
#         is_banner = request.POST.get('is_banner', 'false') == 'true'

#         for index, image_file in enumerate(request.FILES.getlist('files')):
#             image_name = request.POST.getlist('image_name')[index].strip() if index < len(request.POST.getlist('image_name')) else ""
#             gallery_type = request.POST.getlist('gallery_type')[index].strip() if index < len(request.POST.getlist('gallery_type')) else "More Images"

#             if not image_name:
#                 count = (Banner.objects.count() if is_banner else GalleryImage.objects.count()) + 1
#                 image_name = f"Banner{count}" if is_banner else f"Image{count}"

#             # Open and process the image using Pillow
#             image = Image.open(image_file)
#             max_size = (1920, 1080)
#             image.thumbnail(max_size, Image.Resampling.LANCZOS)

#             # Convert image to WebP
#             output_io = BytesIO()
#             image.save(output_io, format='WEBP', quality=85)
#             output_io.seek(0)

#             converted_image = InMemoryUploadedFile(
#                 output_io, 'ImageField', f"{image_name}.webp", 'image/webp', output_io.getbuffer().nbytes, None
#             )

#             if is_banner:
#                 banner = Banner.objects.create(
#                     file_path=converted_image,
#                     banner_name=image_name,
#                 )
#                 banner.save()
#                 banners_saved.append(image_name)
#             else:
#                 gallery_image = GalleryImage.objects.create(
#                     image=converted_image,
#                     image_name=image_name,
#                     gallery_type=gallery_type,
#                 )
#                 gallery_image.save()
#                 images_saved.append(image_name)

#             if banners_saved or images_saved:
#                 return JsonResponse({"status": "success"})

#         return JsonResponse({"status": "error", "message": "No files were uploaded."})

#     return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)

@csrf_exempt
def upload_image_or_banner(request):
    if request.method == 'POST':
        images_saved = []
        banners_saved = []

        # Determine if the upload is for a banner or an image
        is_banner = request.POST.get('is_banner', 'false') == 'true'

        for index, image_file in enumerate(request.FILES.getlist('files')):
            image_name = (
                request.POST.getlist('image_name')[index].strip()
                if index < len(request.POST.getlist('image_name'))
                else ""
            )
            gallery_type = (
                request.POST.getlist('gallery_type')[index].strip()
                if index < len(request.POST.getlist('gallery_type'))
                else "More Images"
            )

            if not image_name:
                count = (Banner.objects.count() if is_banner else GalleryImage.objects.count()) + 1
                image_name = f"Banner{count}" if is_banner else f"Image{count}"

            # Save the file directly without format conversion
            image = Image.open(image_file)

            # Preserve the original size and orientation
            if image.format not in ["JPEG", "PNG", "GIF"]:  # Ensure compatibility with ImageField
                return JsonResponse({
                    "status": "error",
                    "message": f"Unsupported image format: {image.format}. Only JPEG, PNG, and GIF are allowed."
                })

            # Save the original file as it is
            if is_banner:
                banner = Banner.objects.create(
                    file_path=image_file,  # Save the original file
                    banner_name=image_name,
                )
                banner.save()
                banners_saved.append(image_name)
            else:
                gallery_image = GalleryImage.objects.create(
                    image=image_file,  # Save the original file
                    image_name=image_name,
                    gallery_type=gallery_type,
                )
                gallery_image.save()
                images_saved.append(image_name)

        if banners_saved or images_saved:
            return JsonResponse({
                "status": "success",
                "banners_saved": banners_saved,
                "images_saved": images_saved
            })

        return JsonResponse({"status": "error", "message": "No files were uploaded."})

    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)



@csrf_exempt
def delete_image(request, image_id):
    if request.method == 'DELETE':
        try:
            image = GalleryImage.objects.get(id=image_id)
            image_name = image.image_name
            image.delete()
            messages.success(request, f'Image "{image_name}" deleted successfully.')
        except GalleryImage.DoesNotExist:
            banner = get_object_or_404(Banner, id=image_id)
            banner_name = banner.banner_name
            banner.delete()
            messages.success(request, f'Banner "{banner_name}" deleted successfully.')

        return JsonResponse({'status': 'success', 'message': 'Image/Banner deleted successfully.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)


@csrf_exempt
def delete_gallery(request, gallery_slug):
    if request.method == 'DELETE':
        # Convert the slug back to the original gallery type format
        gallery_type = gallery_slug.replace('-', ' ').title()

        if gallery_type == "Banners":
            # Delete all banners
            banners = Banner.objects.all()
            if banners.exists():
                banners.delete()
                messages.success(request, f'All banners have been deleted successfully.')
                return JsonResponse({'status': 'success', 'message': f'All banners deleted successfully.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'No banners found to delete.'}, status=404)
        else:
            # Find and delete images with the corresponding gallery type
            matching_images = GalleryImage.objects.filter(gallery_type__iexact=gallery_type)
            if matching_images.exists():
                matching_images.delete()
                messages.success(request, f'Gallery "{gallery_type}" and its images deleted successfully.')
                return JsonResponse({'status': 'success', 'message': f'Gallery "{gallery_type}" deleted successfully.'})
            else:
                return JsonResponse({'status': 'error', 'message': f'No images found for gallery "{gallery_type}".'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)


@csrf_exempt
def lidobanner(request):
    # Fetch banners
    banners = Banner.objects.all().order_by('-created_at')

    # Render the template
    return render(
        request,
        'blogsite/lidobanner.html',
        {
            'banners': banners,  # Pass banners to the template
        }
    )






















@csrf_exempt
def frontdesklogout(request):
    request.session.flush()
    return redirect('frontdesk_dashboard') 
 
@csrf_exempt
def admin_add_room(request):
    rooms = Room.objects.all()
    context = {
        'rooms': rooms,
        'range_4': range(4)  # This is needed to render four slots in the template
    }
    return render(request, 'authentication/admin/room_management/admin_add_room.html', context)

@csrf_exempt
def admin_rooms(request):
    # Get sorting and filtering parameters from the request
    sort_by = request.GET.get('sort_by', '-id')
    query = request.GET.get('q', '')
    min_price = request.GET.get('min_price', 100)
    max_price = request.GET.get('max_price', 20000)
    capacity = request.GET.get('capacity', None)
    bed_type = request.GET.get('bed_type', '')

    # Attempt to convert price values to integers
    try:
        min_price = int(min_price)
        max_price = int(max_price)
    except ValueError:
        min_price, max_price = 100, 10000  # Set defaults if conversion fails

    # Get the total count of all rooms in the database
    total_room_count = Room.objects.count()

    # Get all rooms first and apply initial sorting
    rooms = Room.objects.all().order_by(sort_by)

    # Apply price filtering
    rooms = rooms.filter(room_price__gte=min_price, room_price__lte=max_price)

    # Apply additional filters based on user query
    if query:
        rooms = rooms.filter(room_name__icontains=query)

    if capacity:
        try:
            capacity = int(capacity)
            rooms = rooms.filter(room_capacity__gte=capacity)
        except ValueError:
            pass  # Ignore if conversion fails

    if bed_type:
        rooms = rooms.filter(bed_type=bed_type)

    # Get the final count of rooms after all filters
    filtered_room_count = rooms.count()

    # Handle AJAX requests for room listing
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('authentication/admin/room_management/room_list.html', {'rooms': rooms})
        return JsonResponse({'html': html})

    # Prepare context for rendering the room list page
    context = {
        'rooms': rooms,
        'sort_by': sort_by,
        'query': query,
        'bed_type_choices': Room.BED_TYPE_CHOICES,
        'filtered_room_count': filtered_room_count,  # Count of rooms after filters
        'total_room_count': total_room_count         # Total rooms in database
    }
    return render(request, 'authentication/admin/room_management/admin_rooms.html', context)

@csrf_exempt
def update_room_status(request, room_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status = data.get('status')

            print(f"Received status: {status}")  # Debug log

            valid_statuses = [choice[0] for choice in Room.ROOM_STATUS_CHOICES]
            if status not in valid_statuses:
                print(f"Invalid status received: {status}")  # Log invalid status
                return JsonResponse({'success': False, 'error': 'Invalid status value'})

            room = Room.objects.get(id=room_id)
            room.room_status = status
            room.save()

            return JsonResponse({'success': True, 'status': room.get_room_status_display()})
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Room not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})




def validate_image(file, max_size_mb):
    # Check if the file is an image
    if not file.content_type.startswith('image'):
        raise ValidationError("Only image files are allowed.")

    # Check file size
    if file.size > max_size_mb * 1024 * 1024:
        # Reduce quality if file exceeds size limit
        image = Image.open(file)
        image = image.convert('RGB')  # Ensure compatibility for all formats
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85)  # Compress the image
        buffer.seek(0)

        # Replace the file with a compressed version
        file = InMemoryUploadedFile(
            buffer, 'ImageField', file.name, 'image/jpeg',
            buffer.getbuffer().nbytes, None
        )
    return file
    
@csrf_exempt
def submit_add_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        room_price = request.POST.get('room_price')
        room_capacity = request.POST.get('room_capacity')
        room_size = request.POST.get('room_size')
        room_unit = request.POST.get('room_unit')  # New field
        room_status = request.POST.get('room_status', 'available')  # New field
        room_image = request.FILES.get('room_image')
        room_amenities = request.POST.getlist('room_amenities[]')
        additional_images = request.FILES.getlist('additional_images[]')
        bed_type = request.POST.get('bed_type')
        bed_count = request.POST.get('bed_count')
        specific_date = request.POST.get('date')  # Optional date input

        # Validate and compress the main image
        if room_image:
            try:
                room_image = validate_image(room_image, max_size_mb=10)
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # Validate and compress additional images
        compressed_additional_images = []
        for image in additional_images:
            try:
                compressed_image = validate_image(image, max_size_mb=5)
                compressed_additional_images.append(compressed_image)
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # Validate bed_count
        if not bed_count or not bed_count.isdigit() or not (1 <= int(bed_count) <= 4):
            return JsonResponse({'success': False, 'error': 'Invalid Bed Count. Must be between 1 and 4.'})

        bed_count = int(bed_count)

        # Validity check for bed type
        valid_bed_types = dict(Room.BED_TYPE_CHOICES).keys()
        if bed_type not in valid_bed_types:
            return JsonResponse({'success': False, 'error': 'Invalid bed type selected.'})

        # Check for required fields
        if not all([room_name, room_price, room_capacity, room_size, room_image, bed_type]):
            return JsonResponse({'success': False, 'error': 'Please fill all required fields and upload a main image.'})

        # Validate room capacity
        max_capacity = bed_count * 3
        if not (1 <= int(room_capacity) <= max_capacity):
            return JsonResponse({'success': False, 'error': f'Room Capacity must be between 1 and {max_capacity} for the selected Bed Count.'})

        # Validate room_unit
        try:
            room_unit = int(room_unit)
            if room_unit < 1:
                raise ValueError("Room unit must be at least 1.")
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid Room Unit.'})

        try:
            with transaction.atomic():
                # Ensure unique room name
                original_name = room_name
                counter = 1
                while Room.objects.filter(room_name=room_name).exists():
                    room_name = f"{original_name} ({counter})"
                    counter += 1

                # Create the room instance and save it
                room = Room(
                    room_name=room_name,
                    room_price=room_price,
                    room_capacity=room_capacity,
                    room_size=room_size,
                    room_unit=room_unit,  # Set room unit
                    room_status=room_status,  # Set room status
                    bed_type=bed_type,
                    bed_count=bed_count,
                    room_image=room_image
                )
                room.save()

                # Add each selected amenity to the room
                for amenity in room_amenities:
                    if amenity:
                        amenity_obj, created = Amenity.objects.get_or_create(amenity_type=amenity)
                        room.room_amenities.add(amenity_obj)

                # Save each additional image and associate it with the room
                for image in compressed_additional_images:
                    if image:
                        RoomImage.objects.create(room=room, image=image)

                # Handle RoomAvailability (if applicable)
                if specific_date:
                    try:
                        # Delete existing duplicates
                        RoomAvailability.objects.filter(room=room, date=specific_date).delete()

                        # Create new RoomAvailability
                        RoomAvailability.objects.create(
                            room=room,
                            date=specific_date,
                            is_available=True
                        )
                    except IntegrityError as e:
                        logger.error(f"Error creating RoomAvailability: {e}")
                        return JsonResponse({'success': False, 'error': 'Could not save RoomAvailability due to a conflict.'})

                # Trigger cleanup to ensure no duplicates or orphaned records
                clean_up_room_availability(room)

            messages.success(request, f"Room '{room_name}' has been created successfully!")
            return JsonResponse({'success': True, 'redirect_url': '/admin_add_room/'})
        except Exception as e:
            logger.error(f"Error saving room: {e}")
            return JsonResponse({'success': False, 'error': 'Could not save room. Please try again later.'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})



from lidoapp.models import RoomAvailability

@csrf_exempt
def edit_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    additional_images = list(room.additional_images.all())

    if request.method == 'POST':
        # Retrieve form data
        room_name = request.POST.get('room_name')
        room_price = request.POST.get('room_price')
        room_capacity = request.POST.get('room_capacity')
        room_size = request.POST.get('room_size')
        bed_type = request.POST.get('bed_type')
        bed_count = request.POST.get('bed_count')
        room_image = request.FILES.get('room_image')
        room_amenities = request.POST.getlist('room_amenities')
        room_unit = request.POST.get('room_unit')
        room_status = request.POST.get('room_status')

        # Validate required fields
        if not all([room_name, room_price, room_capacity, room_size, bed_type, bed_count, room_unit, room_status]):
            messages.error(request, 'Please fill all required fields.')
            return JsonResponse({'success': False})

        # Validate bed_count
        try:
            bed_count = int(bed_count)
            if not (1 <= bed_count <= 4):
                raise ValueError
        except ValueError:
            messages.error(request, 'Bed Count must be between 1 and 4.')
            return JsonResponse({'success': False})

        # Validate room_capacity based on bed_count
        try:
            room_capacity = int(room_capacity)
            max_capacity = bed_count * 3
            if not (1 <= room_capacity <= max_capacity):
                raise ValueError
        except ValueError:
            messages.error(request, f'Room Capacity must be between 1 and {max_capacity} for the selected Bed Count.')
            return JsonResponse({'success': False})

        # Validate room_unit
        try:
            room_unit = int(room_unit)
            if room_unit < 1:
                raise ValueError("Room Unit must be at least 1.")
        except ValueError:
            messages.error(request, 'Invalid Room Unit.')
            return JsonResponse({'success': False})

        # Validity check for bed type
        valid_bed_types = dict(Room.BED_TYPE_CHOICES).keys()
        if bed_type not in valid_bed_types:
            messages.error(request, 'Invalid bed type selected.')
            return JsonResponse({'success': False})

        # Validate room_status
        valid_statuses = dict(Room.ROOM_STATUS_CHOICES).keys()
        if room_status not in valid_statuses:
            messages.error(request, 'Invalid room status selected.')
            return JsonResponse({'success': False})

        try:
            with transaction.atomic():
                # Ensure unique room name
                original_name = room_name
                counter = 1
                while Room.objects.filter(room_name=room_name).exclude(id=room_id).exists():
                    room_name = f"{original_name} ({counter})"
                    counter += 1

                # Update room details
                room.room_name = room_name
                room.room_price = room_price
                room.room_capacity = room_capacity
                room.room_size = room_size
                room.bed_type = bed_type
                room.bed_count = bed_count
                room.room_unit = room_unit
                room.room_status = room_status

                # Update main room image only if a new image is provided
                if room_image:
                    room.room_image = room_image

                # Update room amenities
                room.room_amenities.clear()
                for amenity_type in room_amenities:
                    amenity, created = Amenity.objects.get_or_create(amenity_type=amenity_type)
                    room.room_amenities.add(amenity)

                # Update or add additional images for specific slots
                for i in range(4):
                    additional_image_file = request.FILES.get(f'additional_images_{i}')
                    if additional_image_file:
                        if i < len(additional_images):
                            # Replace existing image at the specified slot
                            additional_images[i].image = additional_image_file
                            additional_images[i].save()
                        else:
                            # Add a new image if there are more files than existing images
                            RoomImage.objects.create(room=room, image=additional_image_file)

                # Update visibility states for additional images
                for image in additional_images:
                    visibility_key = f'image_visibility_{image.id}'
                    if visibility_key in request.POST:
                        image.visible = (request.POST[visibility_key] == 'visible')
                        image.save()

                room.save()  # Save the updated room instance

                # Trigger cleanup to ensure no duplicates or orphaned records
                clean_up_room_availability(room)

            messages.success(request, 'Room updated successfully!')
            return JsonResponse({'success': True, 'redirect_url': redirect('view_room', room_id=room.id).url})

        except Exception as e:
            logger.error(f"Error updating room: {e}")
            messages.error(request, 'Could not update room. Please try again later.')
            return JsonResponse({'success': False})

    # Prepare data for rendering the form
    amenities = Amenity.objects.all()
    selected_amenities = room.room_amenities.values_list('amenity_type', flat=True)

    return render(request, 'authentication/admin/room_management/edit_room.html', {
        'room': room,
        'amenities': amenities,
        'selected_amenities': selected_amenities,
        'additional_images': additional_images,
        'range_4': range(4)
    })







def view_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    main_image = room.room_image  # Main image field
    additional_images = room.additional_images.filter(visible=True)  # Only fetch visible images
    
    return render(request, 'authentication/admin/room_management/view_room.html', {
        'room': room,
        'main_image': main_image,
        'additional_images': additional_images,
    })



def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    room_name = room.room_name  # Capture the room name before deletion
    room.delete()
    messages.success(request, f'Room "{room_name}" deleted successfully!')
    return redirect('admin_rooms')

def delete_multiple_rooms(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        room_ids = data.get('room_ids', [])
        
        if room_ids:
            Room.objects.filter(id__in=room_ids).delete()
            messages.success(request, 'Selected rooms were successfully deleted.')
            return JsonResponse({'success': True})

        return JsonResponse({'success': False, 'error': 'No rooms selected for deletion'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)








# Authentication for Admin
def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Ensure the email and password are only checked against AdminAccount
        if password:
            try:
                # Query only the AdminAccount model to check the email
                admin = AdminAccount.objects.get(email=email)
                
                # Verify the password using the `check_password` method
                if admin.check_password(password):
                    request.session['admin_id'] = admin.id
                    return JsonResponse({'success': True, 'redirect_url': reverse('admin_dashboard')})  # Redirect to admin dashboard or home
                else:
                    return JsonResponse({
                        'success': False,
                        'icon_class': 'fa-solid fa-circle-exclamation',
                        'error': 'Incorrect password'
                    }, status=400)
            except AdminAccount.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'icon_class': 'fa-solid fa-circle-exclamation',
                    'error': 'Couldn\'t find your Admin Account.'
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'Please enter a password.'
            }, status=400)

    return render(request, 'authentication/admin/lidoadminlogin.html')


def admin_signup(request):
    if request.method == 'POST':
        form = AdminAccountForm(request.POST)
        if form.is_valid():
            # Log form data to ensure data processing
            print("Form Data:", form.cleaned_data)
            form.save()  # Save the admin account using the form
            return JsonResponse({'status': 'success', 'message': 'Admin account created successfully!'})
        else:
            # Log form errors
            print("Form Errors:", form.errors)
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = AdminAccountForm()
    return render(request, 'authentication/admin/lidoadminsignup.html', {'form': form})

def admin_signup_success(request):
    return render(request, 'authentication/admin/admin_signup_success.html')




from django.core.serializers.json import DjangoJSONEncoder
import json

def admin_dashboard(request):
    reservations = Reservation.objects.all()
    receipts = Receipt.objects.all()  # Fetch all receipts

    # Annotate data by month and year
    monthly_data = reservations.annotate(
        month=ExtractMonth('created_at'),
        year=ExtractYear('created_at')
    ).values('month', 'year', 'status').annotate(count=Count('id'))

    statuses = ['Booked', 'Pending', 'Cancelled', 'Refunded', 'Rebooked']
    chart_data = {status: [] for status in statuses}

    months_with_data = set()
    for entry in monthly_data:
        months_with_data.add(entry['month'])
        if entry['status'] in statuses:
            chart_data[entry['status']].append((entry['month'], entry['count']))

    months_with_data = sorted(months_with_data)
    formatted_chart_data = {
        status: [dict(chart_data[status]).get(month, 0) for month in months_with_data]
        for status in statuses
    }

    # Attach payment method dynamically and format dates
    reservations_list = []
    for reservation in reservations:
        payment_method = "GCash" if hasattr(reservation, 'gcash_receipt') else "PayPal"
        reservations_list.append({
            'room_chosen': reservation.room_chosen,
            'payment_method': payment_method,
            'status': reservation.status,
            'overall_total_amount': f"₱ {int(reservation.overall_total_amount):,.2f}",
            'check_in_date': reservation.check_in_date.strftime('%b. %d, %Y') if reservation.check_in_date else None,
            'check_out_date': reservation.check_out_date.strftime('%b. %d, %Y') if reservation.check_out_date else None,
        })

    # Calculate total gain from reservations
    total_gain = reservations.filter(status__in=['Booked', 'Pending', 'Rebooked']).aggregate(Sum('overall_total_amount'))['overall_total_amount__sum'] or 0

    # Calculate total gain from receipts
    total_receipt_amount = receipts.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # Add receipt totals to total gain
    total_gain += total_receipt_amount

    # Calculate total loss from cancellations/refunds
    total_loss = reservations.filter(status__in=['Cancelled', 'Refunded']).aggregate(Sum('overall_total_amount'))['overall_total_amount__sum'] or 0

    overall_total = total_gain - total_loss
    sales = Sale.objects.all()
    last_month = month_name[months_with_data[-1]] if months_with_data else "Unknown"

    context = {
        'reservations_json': json.dumps(reservations_list),
        'chart_data': formatted_chart_data,
        'months': [month_name[m] for m in months_with_data],
        'total_gain': f"₱ {total_gain:,.2f}",
        'total_loss': f"₱ {total_loss:,.2f}",
        'overall_total': f"₱ {overall_total:,.2f}",
        'last_month': last_month,
        'sales': sales,
        'total_receipt_amount': f"₱ {total_receipt_amount:,.2f}"  # Include separately if needed
    }

    return render(request, 'authentication/admin/admin_dashboard.html', context)



def add_sale(request):
    if request.method == 'POST':
        sale_amount = request.POST.get('saleAmount')
        sale_description = request.POST.get('saleDescription')
        handled_by = request.POST.get('handledBy')

        # Save the sale
        Sale.objects.create(
            amount=sale_amount,
            description=sale_description,
            handled_by=handled_by,
            date_created=now()
        )

        return redirect('admin_dashboard')


def add_empty_placeholder(data, column_count):
    """Add a centered placeholder row if data is empty."""
    data.append([f"No record/sales in this month." for _ in range(column_count)])
    return data

def download_sales_report(request):
    report_type = request.POST.get('report_type', 'pdf')
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)  # Portrait orientation
    elements = []

    # Fetch data
    reservations = Reservation.objects.all()
    walk_ins = WalkInReservation.objects.all()
    add_ons = AddOn.objects.all()
    receipts = Receipt.objects.all()  # Fetch all receipts
    added_sales = Sale.objects.aggregate(total_sales=Sum('amount'))['total_sales'] or 0

    # Data filters
    booked_pending_rebooked = reservations.filter(status__in=['Booked', 'Pending', 'Rebooked'])
    refunded_cancelled = reservations.filter(status__in=['Refunded', 'Cancelled'])
    rooms_sales = reservations.values('room_chosen').annotate(total_sales=Sum('overall_total_amount'))
    add_ons_sales = add_ons.values('add_on_name', 'add_on_price', 'add_on_quantity', 'add_on_descriptions')

    # Compute financials
    total_gain = booked_pending_rebooked.aggregate(total=Sum('overall_total_amount'))['total'] or 0
    total_loss = refunded_cancelled.aggregate(total=Sum('overall_total_amount'))['total'] or 0
    total_walk_in_sales = walk_ins.aggregate(total=Sum('overall_total_amount'))['total'] or 0
    total_receipt_amount = receipts.aggregate(total=Sum('total_amount'))['total'] or 0  # Sum of all receipts

    # Get unique reservation IDs that have receipts
    reservation_ids_with_receipts = receipts.values_list('reservation__reservation_ID', flat=True).distinct()

    overall_total = total_gain + total_walk_in_sales + added_sales + total_receipt_amount - total_loss
    
    # Define the folder path for saving
    current_month = now().strftime("%B_%Y")
    report_folder = os.path.join(settings.MEDIA_ROOT, "sales_report", current_month)
    os.makedirs(report_folder, exist_ok=True)  # Ensure the folder exists


    if report_type == 'excel':
        # Generate Excel file
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sales Report"

        # Add summary section
        sheet.append(["Category", "Amount"])
        sheet.append(["Reservation Sales", f"P{int(total_gain):,}"])
        sheet.append(["Walk-In Sales", f"P{int(total_walk_in_sales):,}"])
        sheet.append(["Additional Sales", f"P{int(added_sales):,}"])
        sheet.append(["Receipt Total", f"P{int(total_receipt_amount):,}"])  # **NEW: Total Receipts**
        sheet.append(["Refunded/Cancelled Loss", f"-P{int(total_loss):,}"])
        sheet.append(["Overall Total Sales", f"P{int(overall_total):,}"])
        sheet.append([])

        # Add detailed sections
        # Walk-In Sales
        sheet.append(["Walk-In Sales"])
        sheet.append(["Cottage Rate", "Payment Method", "Status", "Total Amount", "Arrival Date"])
        for walk_in in walk_ins:
            sheet.append([
                walk_in.cottage_rate,
                walk_in.payment_method,
                walk_in.walk_in_status,
                f"P{int(walk_in.overall_total_amount):,}",
                walk_in.arrival_datetime.strftime('%b. %d, %Y') if walk_in.arrival_datetime else "N/A",
            ])

        # Refunded and Cancelled Sales
        sheet.append([])
        sheet.append(["Refunded and Cancelled Sales"])
        sheet.append(["Room", "Status", "Total Amount"])
        for entry in refunded_cancelled:
            sheet.append([
                entry.room_chosen,
                entry.status,
                f"P{int(entry.overall_total_amount):,}",
            ])

        # Rooms Sales
        sheet.append([])
        sheet.append(["Rooms Sales"])
        sheet.append(["Room", "Total Sales"])
        for room in rooms_sales:
            sheet.append([room['room_chosen'], f"P{int(room['total_sales']):,}"])

        # Add-On Sales
        sheet.append([])
        sheet.append(["Add-On Sales"])
        sheet.append(["Name", "Price", "Quantity", "Description"])
        for add_on in add_ons_sales:
            sheet.append([
                add_on['add_on_name'],
                f"P{int(add_on['add_on_price']):,}",
                add_on['add_on_quantity'],
                add_on['add_on_descriptions'],
            ])

        # Add reservation IDs that have receipts
        sheet.append(["Reservation IDs with Receipts"])
        if reservation_ids_with_receipts:
            for reservation_id in reservation_ids_with_receipts:
                sheet.append([reservation_id])
        else:
            sheet.append(["No receipts recorded"])
            
        # Save file locally and database entry
        file_path = os.path.join(report_folder, f"Sales_Report_{current_month}.xlsx")
        workbook.save(file_path)

        SalesReport.objects.create(file_path=file_path, created_at=now())

        # Return Excel response
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=Sales_Report_{current_month}.xlsx'
        workbook.save(response)
        return response

    elif report_type == 'pdf':
        # Generate PDF file (existing logic preserved)
        buffer = BytesIO()
        pdf = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

    # Add Lido Logo and Centered Address
    logo_path = os.path.join(settings.BASE_DIR, 'lidoapp/static/assets/images/components/fulllogo.png')
    if os.path.exists(logo_path):
        logo = ReportLabImage(logo_path, width=50 * mm, height=50 * mm)
        elements.append(logo)

    # Define a centered style with Montserrat font
    montserrat_centered_style = ParagraphStyle(
        name="MontserratCentered",
        fontName="Montserrat",
        fontSize=10,
        leading=14,  # Line spacing
        alignment=TA_CENTER  # Center alignment
    )

    # Define the address text
    address = """
    Sariaya, Quezon Province<br/>
    Brgy. Talaan, Aplaya, Sariaya, Calabarzon, 4322, Philippines<br/>
    lidoshores.sariaya@gmail.com<br/>
    +639173004577 Viber Only
    """

    # Add the centered address to elements
    elements.append(Paragraph(address, montserrat_centered_style))
    elements.append(Spacer(1, 20))

    # Corporate Sales Summary
    corporate_table_data = [
            ['Category', 'Amount'],
            ['Reservation Sales', f"P{int(total_gain):,}"],
            ['Walk-In Sales', f"P{int(total_walk_in_sales):,}"],
            ['Additional Sales', f"P{int(added_sales):,}"],
            ['Receipt Total', f"P{int(total_receipt_amount):,}"],  # **NEW: Total Receipts**
            ['Refunded/Cancelled Loss', f"-P{int(total_loss):,}"],
            ['Overall Total Sales', f"P{int(overall_total):,}"],
        ]
    corporate_table = Table(corporate_table_data)
    corporate_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))


    # Define custom styles
    montserrat_style = ParagraphStyle(
        name="Montserrat",
        fontName="Montserrat-Bold",
        fontSize=14,
        textColor=colors.black,
        spaceAfter=10,
        alignment=TA_CENTER
    )
    
    montserrat_italic = ParagraphStyle(
        name="Montserrat",
        fontName="Montserrat-Italic",
        fontSize=12,
        textColor=colors.black,
        spaceAfter=10,
        alignment=TA_CENTER
    )

    # Get the current month name or specify it manually
    current_month = datetime.now().strftime("%B")  # Example: "January"

    # Add the corporate sales summary and month to the elements
    elements.append(Paragraph("Corporate Sales Summary", montserrat_style))
    elements.append(Paragraph(f"Month of {current_month}", montserrat_italic))
    elements.append(corporate_table)
    elements.append(Spacer(1, 15))


    # Helper function to create bordered table
    def create_table(data, title):
        table = Table(data)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(Paragraph(title, getSampleStyleSheet()['Heading3']))
        elements.append(table)
        elements.append(Spacer(1, 15))

    # Reservation Sales Table
    reservation_table_data = [['Room', 'Payment Method', 'Status', 'Total Amount', 'Check-in', 'Check-out']]
    if not booked_pending_rebooked.exists():
        reservation_table_data.append(["No record/sales in this month."])
    else:
        for reservation in booked_pending_rebooked:
            reservation_table_data.append([
                reservation.room_chosen,
                "GCash" if hasattr(reservation, 'gcash_receipt') else "PayPal",
                reservation.status,
                f"P{int(reservation.overall_total_amount):,}",
                reservation.check_in_date.strftime('%b. %d, %Y') if reservation.check_in_date else "N/A",
                reservation.check_out_date.strftime('%b. %d, %Y') if reservation.check_out_date else "N/A",
            ])
    create_table(reservation_table_data, "Reservation Sales")

    # Walk-In Sales Table
    walk_in_table_data = [['Cottage Rate', 'Payment Method', 'Status', 'Total Amount', 'Arrival Date']]
    if not walk_ins.exists():
        walk_in_table_data.append(["No record/sales in this month."])
    else:
        for walk_in in walk_ins:
            walk_in_table_data.append([
                walk_in.cottage_rate,
                walk_in.payment_method,
                walk_in.walk_in_status,
                f"P{int(walk_in.overall_total_amount):,}",
                walk_in.arrival_datetime.strftime('%b. %d, %Y') if walk_in.arrival_datetime else "N/A",
            ])
    create_table(walk_in_table_data, "Walk-In Sales")
    
    elements.append(Spacer(1, 15))
    
    # Refunded and Cancelled Sales Table
    refunded_cancelled_table_data = [['Room', 'Status', 'Total Amount']]
    if not refunded_cancelled.exists():
        refunded_cancelled_table_data.append(["No record/sales in this month."])
    else:
        for entry in refunded_cancelled:
            refunded_cancelled_table_data.append([
                entry.room_chosen,
                entry.status,
                f"P{int(entry.overall_total_amount):,}",
            ])
    create_table(refunded_cancelled_table_data, "Refunded and Cancelled Sales")


    # Fetch all receipts grouped by reservation
    receipts_by_reservation = (
        Receipt.objects
        .values('reservation__reservation_ID')
        .annotate(total_receipt=Sum('total_amount'))
        .order_by('reservation__reservation_ID')
    )

    # Add reservation IDs that have receipts with total amount
    elements.append(Paragraph("Reservations with Receipts and Their Total Amount", getSampleStyleSheet()['Heading3']))

    # Define table headers
    receipt_table_data = [["Reservation ID", "Total Receipt Amount (PHP)"]]

    # Populate table with data
    if receipts_by_reservation:
        for receipt in receipts_by_reservation:
            receipt_table_data.append([
                receipt['reservation__reservation_ID'],
                f"P {float(receipt['total_receipt']):,.2f}"
            ])
    else:
        receipt_table_data.append(["No receipts recorded", ""])

    # Create table
    receipt_table = Table(receipt_table_data, colWidths=[200, 150])
    receipt_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))

    elements.append(receipt_table)
    elements.append(Spacer(1, 15))

        
        
    # Rooms Sales Table
    rooms_sales_table_data = [['Room', 'Total Sales']]
    if not rooms_sales:
        rooms_sales_table_data.append(["No record/sales in this month."])
    else:
        for room in rooms_sales:
            rooms_sales_table_data.append([room['room_chosen'], f"P{int(room['total_sales']):,}"])
    create_table(rooms_sales_table_data, "Rooms Sales")

    # Add-Ons Sales Table
    add_ons_table_data = [['Name', 'Price', 'Quantity', 'Description']]
    if not add_ons_sales:
        add_ons_table_data.append(["No record/sales in this month."])
    else:
        for add_on in add_ons_sales:
            add_ons_table_data.append([
                add_on['add_on_name'],
                f"P{int(add_on['add_on_price']):,}",
                add_on['add_on_quantity'],
                add_on['add_on_descriptions'],
            ])
    create_table(add_ons_table_data, "Add-On Sales")

    # Generate and Save PDF
    pdf.build(elements)
    
    # Save PDF file locally
    file_path = os.path.join(report_folder, f"Sales_Report_{current_month}.pdf")
    with open(file_path, "wb") as f:
        f.write(buffer.getvalue())

    SalesReport.objects.create(file_path=file_path, created_at=now())
        
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"Sales_Report_{current_month}.pdf")














    
    
def admin_logout(request):
    request.session.flush()
    return redirect('admin_dashboard')

# List all add-ons (READ)






from django.shortcuts import render
from django.db.models import Sum

def sales_report(request):
    if request.is_ajax():
        # Process sales data as before
        total_sales = (
            Reservation.objects.filter(status__in=['Booked', 'Pending'])
            .values('gcash_receipt', 'status')
            .annotate(total=Sum('overall_total_amount'))
        )
        sales_by_method = {
            "Gcash": sum(res['total'] for res in total_sales if res['gcash_receipt']),
            "Paypal": sum(res['total'] for res in total_sales if not res['gcash_receipt']),
        }

        refunded_loss = Reservation.objects.filter(status='Refunded').aggregate(total=Sum('overall_total_amount'))['total'] or 0
        canceled_loss = Reservation.objects.filter(status='Cancelled').aggregate(total=Sum('overall_total_amount'))['total'] or 0
        total_loss = refunded_loss + canceled_loss

        monthly_sales = (
            Reservation.objects.filter(status__in=['Booked', 'Pending'])
            .annotate(month=F('created_at__month'))
            .values('gcash_receipt', 'month')
            .annotate(total=Sum('overall_total_amount'))
        )
        sales_by_month = {
            "Gcash": sum(res['total'] for res in monthly_sales if res['gcash_receipt']),
            "Paypal": sum(res['total'] for res in monthly_sales if not res['gcash_receipt']),
        }

        best_room = (
            Reservation.objects.filter(status__in=['Booked', 'Pending'])
            .values('room_chosen')
            .annotate(total_sales=Sum('overall_total_amount'))
            .order_by('-total_sales')
            .first()
        )
        best_room_name = best_room['room_chosen'] if best_room else "No Data"

        return JsonResponse({
            'total_sales': sales_by_method,
            'refunded_loss': refunded_loss,
            'canceled_loss': canceled_loss,
            'total_loss': total_loss,
            'monthly_sales': sales_by_month,
            'best_room': best_room_name,
        })

    # Default behavior for regular HTTP requests
    return render(request, 'authentication/admin/sales/sales_report.html', {})




















@csrf_exempt
def admin_schedule(request):
    return render(request, 'authentication/admin/schedule/admin_schedule.html', {})

@csrf_exempt
def submit_admin_schedule(request):
    if request.method == 'POST':
        staff_name = request.POST.get('staff_name')
        staff_role = request.POST.get('staff_role')
        time_shift = request.POST.get('time_shift')  # E.g., "9:00 AM"
        time_ends = request.POST.get('time_ends')    # E.g., "5:00 PM"
        selected_days = request.POST.getlist('room_amenities[]')
        color = request.POST.get('color', '#007bff')  # Default color
        schedule_id = request.POST.get('schedule_id')  # For editing

        print(f"Received color: {color}")  # Debugging

        if not staff_name or not staff_role or not time_shift or not time_ends or not selected_days:
            return redirect('admin_schedule')

        try:
            time_shift_parsed = datetime.strptime(time_shift, "%I:%M %p").time()
            time_ends_parsed = datetime.strptime(time_ends, "%I:%M %p").time()
        except ValueError:
            return redirect('admin_schedule')

        if schedule_id:
            # Update an existing schedule
            schedule = Schedule.objects.filter(id=schedule_id).first()
            if schedule:
                schedule.staff_name = staff_name
                schedule.staff_role = staff_role
                schedule.time_shift = time_shift_parsed
                schedule.time_ends = time_ends_parsed
                schedule.days = ",".join(selected_days)
                schedule.color = color  # Save color
                schedule.save()
        else:
            # Create a new schedule
            Schedule.objects.create(
                staff_name=staff_name,
                staff_role=staff_role,
                time_shift=time_shift_parsed,
                time_ends=time_ends_parsed,
                days=",".join(selected_days),
                color=color,  # Save color
            )

        return redirect('admin_schedule')

    return redirect('admin_schedule')





@csrf_exempt
def get_schedules(request):
    schedules = Schedule.objects.all()
    events = []

    for schedule in schedules:
        for day in schedule.days.split(","):
            day_index = get_day_index(day)
            if day_index:
                current_week_start = datetime(2025, 1, 12)
                event_date = current_week_start + timedelta(days=day_index - 1)

                events.append({
                    'id': schedule.id,
                    'title': "",  # Handled by eventContent
                    'start': f"{event_date.strftime('%Y-%m-%d')}T{schedule.time_shift.strftime('%H:%M')}",
                    'end': f"{event_date.strftime('%Y-%m-%d')}T{schedule.time_ends.strftime('%H:%M')}",
                    'backgroundColor': schedule.color,  # Color from the model
                    'borderColor': schedule.color,      # Color from the model
                    'extendedProps': {
                        'staff_name': schedule.staff_name,
                        'staff_role': schedule.staff_role,
                        'time_shift': schedule.time_shift.strftime('%I:%M %p'),
                        'time_ends': schedule.time_ends.strftime('%I:%M %p'),
                    },
                })

    return JsonResponse(events, safe=False)






@csrf_exempt
def get_schedule(request, schedule_id):
    try:
        schedule = Schedule.objects.get(id=schedule_id)
        data = {
            'staff_name': schedule.staff_name,
            'staff_role': schedule.staff_role,
            'time_shift': schedule.time_shift.strftime('%I:%M %p'),  # Format as AM/PM
            'time_ends': schedule.time_ends.strftime('%I:%M %p'),    # Format as AM/PM
            'days': schedule.days.split(','),
        }
        return JsonResponse({'success': True, 'schedule': data})
    except Schedule.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Schedule not found.'})

def get_day_index(day):
    day_map = {
        'monday': 1,
        'tuesday': 2,
        'wednesday': 3,
        'thursday': 4,
        'friday': 5,
        'saturday': 6,
        'sunday': 7,
    }
    return day_map.get(day.lower())  # Default is None if day is invalid


@csrf_exempt
def delete_schedule(request, schedule_id):
    if request.method == 'DELETE':
        try:
            schedule = Schedule.objects.get(id=schedule_id)
            schedule.delete()
            return JsonResponse({'success': True})
        except Schedule.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Schedule not found.'})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})





















def admin_inventory(request):
    addons = AddOn.objects.filter(add_on_status="Add On")
    supplies = AddOn.objects.filter(add_on_status="Supply")
    return render(request, 'authentication/admin/inventory/admin_inventory.html', {
        'addons': addons,
        'supplies': supplies,
    })


@csrf_exempt
def submit_admin_inventory(request):
    if request.method == 'POST':
        add_on_name = request.POST.get('add_on_name')
        add_on_price = request.POST.get('add_on_price')
        add_on_quantity = request.POST.get('add_on_quantity')
        add_on_status = request.POST.get('add_on_status')  # Add this line
        add_on_image = request.FILES.get('add_on_image')

        if not all([add_on_name, add_on_price, add_on_quantity, add_on_status, add_on_image]):
            messages.error(request, "All fields are required.")
            return JsonResponse({'success': False, 'error': 'All fields are required.'})

        try:
            AddOn.objects.create(
                add_on_name=add_on_name,
                add_on_price=add_on_price,
                add_on_quantity=add_on_quantity,
                add_on_status=add_on_status,  # Include the status here
                add_on_image=add_on_image
            )
        except Exception as e:
            messages.error(request, f"Failed to save the product: {e}")
            return JsonResponse({'success': False, 'error': f"Failed to save: {e}"})

        messages.success(request, f'Product "{add_on_name}" saved successfully!')
        return JsonResponse({'success': True, 'reload': True})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
def update_selling_quantity(request, addon_id, quantity):
    try:
        addon = AddOn.objects.get(id=addon_id)
        if quantity == "reset":
            addon.selling_quantity = addon.add_on_quantity
        else:
            addon.selling_quantity = min(int(quantity), addon.add_on_quantity)
        addon.save()
        return JsonResponse({"success": True, "selling_quantity": addon.selling_quantity})
    except AddOn.DoesNotExist:
        return JsonResponse({"success": False, "error": "Add-on not found."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt
def toggle_sell_by_2(request, addon_id):
    if request.method == 'POST':
        try:
            addon = AddOn.objects.get(id=addon_id)
            data = json.loads(request.body)
            addon.sell_by_2 = data.get('enable', False)
            addon.save()
            logger.info(f"AddOn {addon_id} sell_by_2 updated to {addon.sell_by_2}")
            return JsonResponse({"success": True, "message": f"Sell by 2 {'enabled' if addon.sell_by_2 else 'disabled'} for {addon.add_on_name}."})
        except AddOn.DoesNotExist:
            return JsonResponse({"success": False, "error": "Add-on not found."})
        except Exception as e:
            logger.error(f"Error updating sell_by_2 for AddOn {addon_id}: {e}")
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request method."})

def get_stock_quantity(request, addon_id):
    try:
        addon = AddOn.objects.get(id=addon_id)
        return JsonResponse({"success": True, "stock_quantity": addon.add_on_quantity})
    except AddOn.DoesNotExist:
        return JsonResponse({"success": False, "error": "Add-on not found."})


@csrf_exempt
def delete_addon(request, status, addon_id):
    if request.method == 'POST':
        try:
            # Filter by both ID and status
            addon = AddOn.objects.get(id=addon_id, add_on_status=status)
            addon.delete()
            return JsonResponse({'success': True, 'message': 'Add-on deleted successfully.'})
        except AddOn.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Add-on not found.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})



def walk_in(request):
    # Fetch the latest Walk-In Policy
    walk_in_policy = Policy.objects.filter(policy_type='walkin').order_by('-updated_at').first()

    # Fallback to default content if no Walk-In Policy exists
    walk_in_content = (
        walk_in_policy.content
        if walk_in_policy
        else (
            "<ul style='margin: 10px 0; padding-left: 20px; padding-right: 20px; list-style-type: none;'>"
            "<li>The <strong>NOW</strong> button automates the <u>Arrival Date & Time</u> and the <u>Status Rate</u> of the guest.</li><br>"
            "<li>The <strong>Arrival Date & Time</strong> and <strong>Status Rate</strong> cannot be manually edited to prevent manipulation of the status rate fee.</li>"
            "<li>Only the <strong>Number of Guests</strong> and <strong>Number of Children</strong> fields are editable.</li><br>"
            "<li><strong>Discounts:</strong> Guests availing discounts are required to upload a valid guest ID.</li>"
            "</ul>"
        )
    )

    # Fetch all cottage rates and calculate the available count
    cottage_rates = CottageRate.objects.all()
    for rate in cottage_rates:
        reserved_count = WalkInReservation.objects.filter(
            cottage_rate=rate.cottage_rate_name,
            walk_in_status__in=['Ongoing']
        ).aggregate(total_reserved=Sum('cottage_count'))['total_reserved'] or 0
        rate.available_count = max(0, rate.cottage_rate_unit - reserved_count)

    return render(request, 'authentication/frontdesk/walk_in/walk_in.html', {
        'walk_in_content': walk_in_content,
        'cottage_rates': cottage_rates,
    })

def submit_walk_in(request):
    if request.method == 'POST':
        try:
            # Extract form data
            first_name = request.POST.get('firstName')
            middle_name = request.POST.get('middleName', '')
            last_name = request.POST.get('lastName')
            email = request.POST.get('email', '')
            contact_number = request.POST.get('contactNumber')
            address = request.POST.get('address')
            arrival_datetime = request.POST.get('arrivalDateTime')
            status_rate = request.POST.get('statusRate')
            cottage_rate_name = request.POST.get('cottageRate')
            payment_method = request.POST.get('paymentMethod')
            total_guest_count = int(request.POST.get('totalGuestCount', 0))
            total_child_count = int(request.POST.get('totalChildCount', 0))
            cottage_count = int(request.POST.get('cottageCount', 1))

            # Handle guest ID proof
            guest_id_proofs = request.FILES.getlist('guestIdProof[]')

            # Fetch the selected cottage rate
            cottage_rate = CottageRate.objects.filter(cottage_rate_name=cottage_rate_name).first()
            if not cottage_rate:
                return JsonResponse({'success': False, 'error': 'Invalid cottage rate selected.'}, status=400)

            # Calculate reserved count
            reserved_count = WalkInReservation.objects.filter(
                cottage_rate=cottage_rate_name,
                walk_in_status__in=['Ongoing']
            ).aggregate(total_reserved=Sum('cottage_count'))['total_reserved'] or 0

            # Calculate available count
            available_count = max(0, cottage_rate.cottage_rate_unit - reserved_count)

            # Check if enough cottages are available
            if cottage_count > available_count:
                return JsonResponse({'success': False, 'error': 'Not enough cottages available.'}, status=400)

            # Pricing logic
            if status_rate == 'Daytour':
                adult_price = 330
                child_price = 165
            elif status_rate == 'Nighttour':
                adult_price = 500
                child_price = 250
            else:
                return JsonResponse({'success': False, 'error': 'Invalid status rate.'}, status=400)

            # Calculate total amount
            total_amount = (total_guest_count * adult_price) + (total_child_count * child_price) + (
                cottage_count * cottage_rate.cottage_rate_price)

            # Save the walk-in reservation atomically
            with transaction.atomic():
                # Create the walk-in reservation
                walk_in_reservation = WalkInReservation.objects.create(
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name,
                    email=email,
                    contact_number=contact_number,
                    address=address,
                    arrival_datetime=arrival_datetime,
                    status_rate=status_rate,
                    cottage_rate=cottage_rate_name,
                    payment_method=payment_method,
                    total_guest_count=total_guest_count,
                    total_child_count=total_child_count,
                    cottage_count=cottage_count,
                    overall_total_amount=total_amount,
                )

                # Save each guest ID proof image
                for guest_id_proof in guest_id_proofs:
                    GuestIdProof.objects.create(
                        walk_in_reservation=walk_in_reservation,
                        image=guest_id_proof
                    )

            # Redirect to success page with the walk_in_ID in the URL
            return redirect(f"{reverse('walk_in_success')}?walk_in_ID={walk_in_reservation.walk_in_ID}")

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return HttpResponse("Invalid request method", status=405)

def walk_in_success(request):
    return render(request, 'authentication/frontdesk/walk_in/walk_in_success.html')


@csrf_exempt
def update_walk_in_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            walk_in_ID = data.get('walk_in_ID')
            new_status = data.get('new_status')

            walk_in = WalkInReservation.objects.get(walk_in_ID=walk_in_ID)

            # Update the status
            walk_in.walk_in_status = new_status
            walk_in.save()

            return JsonResponse({'success': True, 'message': f'Walk-in reservation marked as {new_status}.'})

        except WalkInReservation.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Walk-in reservation not found.'}, status=404)

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


@receiver(post_save, sender=WalkInReservation)
def update_cottage_availability(sender, instance, **kwargs):
    pass  # No availability logic here

def cottage_rates(request):
    cottage_rates = CottageRate.objects.all()

    for rate in cottage_rates:
        # Calculate reserved count for "Ongoing" reservations
        reserved_count = WalkInReservation.objects.filter(
            cottage_rate=rate.cottage_rate_name,
            walk_in_status__in=['Ongoing']  # Only consider active reservations
        ).aggregate(total_reserved=Sum('cottage_count'))['total_reserved'] or 0

        # Calculate available count (total units - reserved units)
        rate.available_count = max(0, rate.cottage_rate_unit - reserved_count)

        # Fetch avails (details of people availing the cottages)
        rate.avails = WalkInReservation.objects.filter(
            cottage_rate=rate.cottage_rate_name,
            walk_in_status__in=['Ongoing']  # Only ongoing reservations
        ).values(
            'walk_in_ID', 'first_name', 'last_name', 'status_rate', 'walk_in_status', 'total_guest_count', 'total_child_count', 'cottage_count'
        )

    return render(request, 'authentication/frontdesk/walk_in/cottage_rates.html', {
        'cottage_rates': cottage_rates,
    })

@csrf_exempt
def submit_cottage_rates(request):
    if request.method == 'POST':
        # Get form data
        cottage_rate_name = request.POST.get('cottage_rate_name')
        cottage_rate_price = request.POST.get('cottage_rate_price')
        cottage_rate_capacity = request.POST.get('cottage_rate_capacity')
        cottage_rate_unit = request.POST.get('cottage_rate_unit')
        cottage_rate_image = request.FILES.get('rate_image')

        # Validate and save
        if not all([cottage_rate_name, cottage_rate_price, cottage_rate_capacity, cottage_rate_unit, cottage_rate_image]):
            messages.error(request, "All fields are required, including the main image.")
            return JsonResponse({'success': False, 'error': 'All fields are required.'})

        try:
            CottageRate.objects.create(
                cottage_rate_name=cottage_rate_name,
                cottage_rate_price=cottage_rate_price,
                cottage_rate_capacity=cottage_rate_capacity,
                cottage_rate_unit=cottage_rate_unit,
                cottage_rate_image=cottage_rate_image
            )
        except Exception as e:
            messages.error(request, f"Failed to save the cottage rate: {e}")
            return JsonResponse({'success': False, 'error': f"Failed to save: {e}"})

        messages.success(request, f'Cottage rate "{cottage_rate_name}" saved successfully!')
        return JsonResponse({'success': True, 'reload': True})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


def delete_cottage_rates(request, rate_id):
    cottage_rate = get_object_or_404(CottageRate, id=rate_id)
    cottage_rate_name = cottage_rate.cottage_rate_name

    if request.method == 'POST':
        # Delete the associated image
        if cottage_rate.cottage_rate_image:
            image_path = cottage_rate.cottage_rate_image.path
            if os.path.exists(image_path):
                os.remove(image_path)

        # Delete the cottage rate record
        cottage_rate.delete()
        messages.success(request, f'Cottage rate "{cottage_rate_name}" deleted successfully!')
        return redirect('cottage_rates')







@csrf_exempt
def check_admin_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if AdminAccount.objects.filter(email=email).exists():
            return JsonResponse({'exists': True}, status=200)
        else:
            return JsonResponse({
                'exists': False,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'Couldn\'t find your Admin Account.'
            }, status=200)
    return JsonResponse({
        'error': 'Invalid request',
        'icon_class': 'fa-solid fa-circle-exclamation'
    }, status=400)
    
    
@csrf_exempt
def check_admin_signup_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Ensure only AdminAccount is checked
        if AdminAccount.objects.filter(email=email).exists():
            return JsonResponse({
                'exists': True,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'This email is already registered as an admin.'
            }, status=200)
        else:
            return JsonResponse({'exists': False}, status=200)

    return JsonResponse({
        'error': 'Invalid request',
        'icon_class': 'fa-solid fa-circle-exclamation'
    }, status=400)
    
    
    











# Authentication Views
@csrf_exempt
def guest_login(request):
    # Redirect if the user is already logged in
    if request.session.get('guest_id'):
        return redirect('lidohome')  # Redirect to lidohome if already logged in

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if password:
            try:
                guest = GuestAccount.objects.get(email=email)
                if guest.check_password(password):
                    request.session['guest_id'] = guest.id
                    # Redirect to lidohome after successful login
                    return JsonResponse({'success': True, 'redirect_url': reverse('lidohome')})
                else:
                    return JsonResponse({
                        'success': False,
                        'icon_class': 'fa-solid fa-circle-exclamation',
                        'error': 'Incorrect password'
                    }, status=400)
            except GuestAccount.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'icon_class': 'fa-solid fa-circle-exclamation',
                    'error': 'Couldn\'t find your Lido Shores Account.'
                }, status=400)
        else:
            if GuestAccount.objects.filter(email=email).exists():
                return JsonResponse({'success': True})
            else:
                return JsonResponse({
                    'success': False,
                    'icon_class': 'fa-solid fa-circle-exclamation',
                    'error': 'Couldn\'t find your Lido Shores Account.'
                }, status=400)

    return render(request, 'authentication/guest/guest_login.html')


@csrf_exempt
def guest_signup(request):
    if request.method == 'POST':
        form = GuestAccountForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
        else:
            logger.error(form.errors)
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = GuestAccountForm()
    
    # Fetch the latest Account Policy content
    latest_account_policy = Policy.objects.filter(policy_type='account').order_by('-updated_at').first()
    terms_content = latest_account_policy.content if latest_account_policy else "We collect your name, contact info, and preferences when you create a Lido Shores Resort account. During your stay, we use this info to customize your experience, from room setup to personalized recommendations. Data like dining and room service requests may be combined for seamless service. You can manage your preferences anytime or contact us for support. Please follow resort policies for a pleasant stay. Review our Guest Terms and Privacy Policy for details."

    return render(request, 'authentication/guest/guest_signup.html', {
        'form': form,
        'terms_content': terms_content,  # Pass the latest Account Policy content to the template
    })



def signup_success(request):
    return render(request, 'authentication/guest/signup_success.html')

@csrf_exempt
def check_guest_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if GuestAccount.objects.filter(email=email).exists():
            return JsonResponse({'exists': True}, status=200)
        else:
            return JsonResponse({
                'exists': False,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'Couldn\'t find your Lido Shores Account.'
            }, status=200)
    return JsonResponse({
        'error': 'Invalid request',
        'icon_class': 'fa-solid fa-circle-exclamation'
    }, status=400)

@csrf_exempt
def check_signup_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            return JsonResponse({
                'exists': False,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'Please enter a valid email address.'
            }, status=400)

        if GuestAccount.objects.filter(email=email).exists():
            return JsonResponse({
                'exists': True,
                'icon_class': 'fa-solid fa-circle-exclamation',
                'error': 'This email is already taken.'
            }, status=409)
        else:
            return JsonResponse({'exists': False}, status=200)

    return JsonResponse({
        'error': 'Invalid request',
        'icon_class': 'fa-solid fa-circle-exclamation'
    }, status=400)

def check_guest_session(request):
    if 'guest_id' in request.session:
        return JsonResponse({'is_logged_in': True})
    else:
        return JsonResponse({'is_logged_in': False})

def guest_logout(request):
    request.session.flush()
    return redirect('lidohome')

def guest_profile(request):
    guest_id = request.session.get('guest_id')
    if not guest_id:
        return redirect('guest_login')

    guest = get_object_or_404(GuestAccount, id=guest_id)
    return render(request, 'authentication/guest/guest_profile.html', {'guest': guest})

@csrf_exempt
def update_guest_profile(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        guest_id = request.session.get("guest_id")

        if not guest_id:
            return JsonResponse({"success": False, "error": "User not logged in."}, status=401)
        
        try:
            guest = GuestAccount.objects.get(id=guest_id)

            # Update fields
            guest.first_name = data.get("firstName", guest.first_name)
            guest.middle_name = data.get("middleName", guest.middle_name)
            guest.last_name = data.get("lastName", guest.last_name)
            guest.email = data.get("email", guest.email)
            guest.contact_number = data.get("contactNumber", guest.contact_number)
            guest.telephone_number = data.get("telephoneNumber", guest.telephone_number)
            guest.address1 = data.get("address1", guest.address1)
            guest.city = data.get("city", guest.city)
            guest.country = data.get("country", guest.country)

            # Update password only if provided
            password = data.get("password")
            if password:
                guest.set_password(password)

            # Save changes
            guest.save()
            return JsonResponse({"success": True, "message": "Profile updated successfully."})

        except GuestAccount.DoesNotExist:
            return JsonResponse({"success": False, "error": "Guest not found."}, status=404)
    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)

def get_logged_in_guest_details(request):
    if 'guest_id' in request.session:
        try:
            guest = GuestAccount.objects.get(id=request.session['guest_id'])
            missing_fields = []
            
            def get_field_value(field_name):
                value = getattr(guest, field_name, "")
                if not value:
                    missing_fields.append(field_name)
                return value
            
            response_data = {
                'success': True,
                'first_name': get_field_value('first_name'),
                'last_name': get_field_value('last_name'),
                'email': get_field_value('email'),
                'contact_number': get_field_value('contact_number'),
                'telephone_number': get_field_value('telephone_number'),
                'address1': get_field_value('address1'),
                'country': get_field_value('country'),
                'city': get_field_value('city'),
                'created_at': guest.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                'missing_fields': missing_fields,
            }

            return JsonResponse(response_data)
        except GuestAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Guest not found.'}, status=404)
    return JsonResponse({'success': False, 'error': 'User not logged in.'}, status=401)



@csrf_exempt
def upload_profile_picture(request):
    if request.method == "POST" and request.FILES.get("profile_picture"):
        guest_id = request.POST.get("guest_id")
        guest = get_object_or_404(GuestAccount, id=guest_id)
        guest.profile_picture = request.FILES["profile_picture"]
        guest.save()
        return JsonResponse({"success": True, "profile_picture_url": guest.profile_picture.url})
    return JsonResponse({"success": False, "error": "Invalid request"})



@csrf_exempt
def delete_profile_picture(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        guest_id = data.get("guest_id")

        try:
            guest = GuestAccount.objects.get(id=guest_id)
            if guest.profile_picture:
                guest.profile_picture.delete(save=True)
                guest.profile_picture = None
                guest.save()
            return JsonResponse({"success": True}, status=200)
        except GuestAccount.DoesNotExist:
            return JsonResponse({"error": "Guest not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=405)




@csrf_exempt
def submit_reservation(request):
    if request.method == 'POST':
        try:
            # Parse JSON data from the request body
            data = json.loads(request.body)
            
            # Ensure the guest is logged in
            guest_id = request.session.get('guest_id')
            if not guest_id:
                return JsonResponse({'success': False, 'error': 'Guest not logged in.'}, status=400)

            # Parse and compute guest counts
            adult_count = int(data.get('adult_count', 0))
            children_count = int(data.get('children_count', 0))
            total_guest_count = adult_count + children_count

            # Parse and validate check-in and check-out dates
            check_in_date = datetime.strptime(data['check_in_date'], "%Y-%m-%d").date()
            check_out_date = datetime.strptime(data['check_out_date'], "%Y-%m-%d").date()
            if check_in_date >= check_out_date:
                return JsonResponse({'success': False, 'error': 'Check-out date must be after check-in date.'}, status=400)

            # Retrieve the Room object based on room_chosen
            room_name = data.get('room_chosen')
            try:
                room = Room.objects.select_for_update().get(room_name=room_name)
            except Room.DoesNotExist:
                return JsonResponse({'success': False, 'error': f"Room '{room_name}' does not exist."}, status=400)

            # Ensure the room has available units
            if room.room_unit <= 0:
                return JsonResponse({'success': False, 'error': 'No available units for the selected room.'}, status=400)

            # Decrement the room unit
            room.room_unit -= 1

            # Update room status if no units remain
            if room.room_unit == 0:
                room.room_status = 'maintenance'

            room.save()

            # Create the reservation
            reservation = Reservation.objects.create(
                guest_id=guest_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                room_chosen=room_name,  # Store the room name
                adult_count=adult_count,
                children_count=children_count,
                total_guest_count=total_guest_count,
                overall_total_amount=data['overall_total_amount'],
                status='Booked',  # Automatically set status to Booked after payment
                add_ons=data.get('add_ons', {}),  # Store selected add-ons
            )

            # Update room availability for the reservation dates
            RoomAvailability.objects.filter(
                room=room,  # Use the Room object
                date__gte=check_in_date,
                date__lt=check_out_date
            ).update(is_available=False)

            # Update add-on quantities
            add_ons = data.get('add_ons', {})
            for addon_name, addon_data in add_ons.items():
                try:
                    # Fetch the add-on by name
                    addon = AddOn.objects.get(add_on_name=addon_name)
                    requested_quantity = addon_data.get('quantity', 0)

                    # Decrement the add-on quantity
                    addon.add_on_quantity = F('add_on_quantity') - requested_quantity
                    addon.save()

                    # Ensure the quantity doesn't drop below zero
                    addon.refresh_from_db()
                    if addon.add_on_quantity < 0:
                        addon.add_on_quantity = 0
                        addon.save()
                except AddOn.DoesNotExist:
                    print(f"Add-on with name '{addon_name}' does not exist.")
                except Exception as e:
                    print(f"Error updating add-on '{addon_name}': {e}")


            return JsonResponse({
                'success': True,
                'reservation_ID': str(reservation.reservation_ID),
                'redirect_url': reverse('lidocompleted') + f"?reservation_ID={reservation.reservation_ID}",
            })
        except Exception as e:
            # Log the error and return a failure response
            print(f"Error saving reservation: {e}")
            return JsonResponse({'success': False, 'error': 'Could not save reservation.'}, status=500)

    # Return an error response for invalid HTTP methods
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)






@csrf_exempt
def submit_reservation_gcash(request):
    if request.method == 'POST':
        try:
            # Parse form data
            data = request.POST
            guest_id = request.session.get('guest_id')
            if not guest_id:
                return JsonResponse({'success': False, 'error': 'Guest not logged in.'}, status=400)

            # Parse numeric fields
            adult_count = int(data.get('adult_count', 0))
            children_count = int(data.get('children_count', 0))
            total_guest_count = adult_count + children_count

            # Parse add-ons safely
            try:
                add_ons = json.loads(data.get('add_ons', '{}'))
            except json.JSONDecodeError:
                add_ons = {}

            # Convert check-in and check-out dates from string to datetime.date
            check_in_date = datetime.strptime(data.get('check_in_date'), "%Y-%m-%d").date()
            check_out_date = datetime.strptime(data.get('check_out_date'), "%Y-%m-%d").date()
            if check_in_date >= check_out_date:
                return JsonResponse({'success': False, 'error': 'Check-out date must be after check-in date.'}, status=400)

            # Retrieve the Room object based on room_chosen
            room_name = data.get('room_chosen')
            try:
                room = Room.objects.select_for_update().get(room_name=room_name)  # Lock the room for this transaction
            except Room.DoesNotExist:
                return JsonResponse({'success': False, 'error': f"Room '{room_name}' does not exist."}, status=400)

            # Check room availability
            if room.room_unit <= 0:
                return JsonResponse({'success': False, 'error': 'No units available for this room.'}, status=400)

            # Create the reservation
            reservation = Reservation.objects.create(
                guest_id=guest_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                room_chosen=room_name,  # Store the room name
                adult_count=adult_count,
                children_count=children_count,
                total_guest_count=total_guest_count,
                overall_total_amount=data['overall_total_amount'],
                prefix=data.get('prefix', ''),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                email=data.get('email', ''),
                contact_number=data.get('contact_number', ''),
                address1=data.get('address1', ''),
                address2=data.get('address2', ''),
                city=data.get('city', ''),
                postal_code=data.get('postal_code', ''),
                country=data.get('country', ''),
                special_requests=data.get('special_requests', ''),
                add_ons=add_ons,
                status='Pending',
            )

            # Save GCash receipt details
            GCashReceipt.objects.create(
                reservation=reservation,
                gcash_number=data.get('gcashNumber', ''),
                gcash_account_name=data.get('gcashAccountName', ''),
                gcash_reference_number=data.get('gcashReference', ''),
                uploaded_receipt=request.FILES.get('paymentReceipt'),
                payment_type=data.get('paymentTypeInput', ''),
            )

            # Update room availability for the reservation dates
            RoomAvailability.objects.filter(
                room=room,  # Use the Room object
                date__gte=check_in_date,
                date__lt=check_out_date
            ).update(is_available=False)

            # Decrement the room units and update status if no units remain
            room.room_unit -= 1
            if room.room_unit == 0:
                room.room_status = 'maintenance'  # Set to "Under Maintenance"
            room.save()

            return JsonResponse({
                'success': True,
                'reservation_ID': str(reservation.reservation_ID),
                'redirect_url': reverse('lidocompleted') + f"?reservation_ID={reservation.reservation_ID}",
            })
        except Exception as e:
            # Log the error and return a failure response
            print(f"Error processing GCash reservation: {e}")
            return JsonResponse({'success': False, 'error': 'Could not process reservation.'}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)




@csrf_exempt
def rebook_reservation(request, reservation_id):
    if request.method == 'POST':
        try:
            reservation = Reservation.objects.get(reservation_ID=reservation_id)
            data = json.loads(request.body)
            check_in_date = data.get('check_in_date')
            check_out_date = data.get('check_out_date')

            if not check_in_date or not check_out_date:
                return JsonResponse({'success': False, 'message': 'Check-in and Check-out dates are required.'})

            if check_out_date <= check_in_date:
                return JsonResponse({'success': False, 'message': 'Check-out date must be after Check-in date.'})

            if reservation.status != 'Booked' and reservation.status != 'Pending Rebooked':
                return JsonResponse({'success': False, 'message': 'Rebooking is only allowed for "Booked" reservations.'})

            # cancel previous pending requests
            reservation.rebooking_requests.filter(status='Pending').update(status='Cancelled')

            # Create a new rebooking request
            rebooking_request = RebookingRequest.objects.create(
                reservation=reservation,
                requested_check_in_date=check_in_date,
                requested_check_out_date=check_out_date,
                status='Pending'
            )

            reservation.status = "Pending Rebooked"
            reservation.save()

            return JsonResponse({'success': True, 'message': 'Rebooking request submitted successfully.'})

        except Reservation.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Reservation not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Error: {str(e)}"})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})





@csrf_exempt
def get_rebooking_availability(request):
    if request.method == 'GET':
        date = request.GET.get('date')
        try:
            selected_date = datetime.strptime(date, '%Y-%m-%d').date()

            # Fetch room availability for the specific date
            room_availability = RoomAvailability.objects.filter(date=selected_date)

            # Calculate total available rooms
            total_available = room_availability.filter(is_available=True).count()

            # Return room-level availability
            availability = {
                ra.room.room_name: ra.is_available
                for ra in room_availability
            }

            return JsonResponse({
                'totalAvailable': total_available,
                'roomAvailability': availability,
            })
        except Exception as e:
            print(f"Error fetching availability: {e}")
            return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def handle_rebooking_request(request, rebooking_request_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')  # 'approve' or 'cancel'

            rebooking_request = RebookingRequest.objects.get(id=rebooking_request_id)
            reservation = rebooking_request.reservation

            if action == 'approve':
                # Update RoomAvailability for original booking dates to mark them available
                RoomAvailability.objects.filter(
                    room__room_name=reservation.room_chosen,
                    date__gte=reservation.check_in_date,
                    date__lt=reservation.check_out_date
                ).update(is_available=True)

                # Update the reservation dates with the approved rebooking request dates
                reservation.original_check_in_date = reservation.check_in_date
                reservation.original_check_out_date = reservation.check_out_date
                reservation.check_in_date = rebooking_request.requested_check_in_date
                reservation.check_out_date = rebooking_request.requested_check_out_date
                reservation.status = 'Rebooked'  # Update status to Rebooked
                reservation.save()

                # Mark RoomAvailability for the new dates as unavailable
                RoomAvailability.objects.filter(
                    room__room_name=reservation.room_chosen,
                    date__gte=reservation.check_in_date,
                    date__lt=reservation.check_out_date
                ).update(is_available=False)

                # Mark the rebooking request as approved
                rebooking_request.status = 'Approved'
                rebooking_request.save()

                # Regenerate the invoice with the rebooking flag set
                generate_invoice(request, reservation.reservation_ID, is_rebooked=True)

                return JsonResponse({'success': True, 'message': "Rebooking request approved. Invoice updated."})

            elif action == 'cancel':
                # Mark the rebooking request as Cancelled
                rebooking_request.status = 'Cancelled'
                rebooking_request.save()

                return JsonResponse({'success': True, 'message': "Rebooking request has been cancelled."})

            else:
                return JsonResponse({'success': False, 'message': "Invalid action."})

        except RebookingRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': "Rebooking request not found."})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"An error occurred: {str(e)}"})

    return JsonResponse({'success': False, 'message': "Invalid request method."})



