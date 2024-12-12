# Import necessary Django modules
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.core.files import File

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.utils import timezone
from datetime import date, datetime
from django.db.models import Sum, Q, Count
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.template.loader import render_to_string
from django.conf import settings
import os
import calendar
from django.db.models.functions import ExtractWeek, ExtractMonth, ExtractYear

# Import external libraries for handling PDFs and requests
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Google reCAPTCHA modules for verification
from google.cloud import recaptchaenterprise_v1
from google.cloud.recaptchaenterprise_v1 import Assessment

# For encoding and making requests
import base64
import requests


from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter  # Import for y-axis formatting
from io import BytesIO
import os
import tempfile
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.db.models import Sum
from django.db.models.functions import ExtractWeek, ExtractYear
from lidoapp.models import Reservation
from datetime import timedelta

def generate_weekly_sales_report(request):
    if 'admin_id' in request.session:
        # Fetch weekly revenue data
        earliest_reservation_date = Reservation.objects.earliest('check_in_date').check_in_date
        weekly_revenue_data = (
            Reservation.objects.filter(check_in_date__gte=earliest_reservation_date)
            .annotate(week=ExtractWeek('check_in_date'), year=ExtractYear('check_in_date'))
            .values('week', 'year')
            .annotate(total_sales=Sum('overall_total_amount'))
            .order_by('year', 'week')
        )

        weekly_revenue = []
        for data in weekly_revenue_data:
            start_of_week = earliest_reservation_date + timedelta(weeks=data['week'] - 1)
            end_of_week = start_of_week + timedelta(days=6)
            weekly_revenue.append({
                "week": f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}",
                "revenue": float(data['total_sales'] or 0),
            })

        # Generate the Matplotlib chart
        fig, ax = plt.subplots(figsize=(10, 6))
        weeks = [data["week"] for data in weekly_revenue]
        revenues = [data["revenue"] for data in weekly_revenue]

        # Bar chart
        bars = ax.bar(weeks, revenues, color='lightgreen', edgecolor='green', linewidth=1)

        # Add labels on top of the bars
        for bar, revenue in zip(bars, revenues):
            ax.text(
                bar.get_x() + bar.get_width() / 2,  # X-coordinate (center of the bar)
                bar.get_height() + 5000,  # Y-coordinate (slightly above the bar)
                f"₱{revenue:,.0f}",  # Format revenue as PHP
                ha='center', va='bottom', fontsize=10, color='black'
            )

        # Add title and subtitle
        ax.set_title("WEEKLY REVENUE", fontsize=16, fontweight='bold', color='green', pad=20)
        ax.text(0.5, 1.02, "Track the revenue generated during each week, displayed with start and end dates (Monday to Sunday) for detailed analysis.",
                fontsize=10, color='gray', ha='center', transform=ax.transAxes)

        # Format y-axis
        def format_currency(value, _):
            return f"PHP {value:,.0f}"
        ax.yaxis.set_major_formatter(FuncFormatter(format_currency))

        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')

        # Gridlines and limits
        ax.set_axisbelow(True)
        ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)
        ax.set_ylim(0, max(revenues) * 1.2)  # Add some padding above the tallest bar

        # Labels
        ax.set_ylabel("PHP", fontsize=12)
        ax.set_xlabel("Weeks", fontsize=12)

        # Save the chart to a BytesIO object
        img_io = BytesIO()
        plt.savefig(img_io, format='png', bbox_inches='tight')
        img_io.seek(0)

        # Generate the PDF with the chart
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
            tmpfile.write(img_io.read())
            tmpfile.close()

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="weekly_sales_report.pdf"'

            p = canvas.Canvas(response, pagesize=letter)
            p.setFont("Helvetica", 12)
            p.drawString(100, 750, "Weekly Sales Report")
            p.drawImage(tmpfile.name, 50, 400, width=500, height=300)
            p.save()
            os.remove(tmpfile.name)

        return response

    else:
        return HttpResponse("Unauthorized", status=401)
    
# Define the absolute paths to the font files
FONT_DIR = os.path.join(settings.BASE_DIR, 'lidoapp', 'static', 'assets', 'fonts')
OPEN_SANS_REGULAR = os.path.join(FONT_DIR, 'open-sans-regular.ttf')
OPEN_SANS_BOLD = os.path.join(FONT_DIR, 'open-sans-bold.ttf')
OPEN_SANS_ITALIC = os.path.join(FONT_DIR, 'open-sans-italic.ttf')

# Register the fonts
pdfmetrics.registerFont(TTFont('OpenSans', OPEN_SANS_REGULAR))
pdfmetrics.registerFont(TTFont('OpenSans-Bold', OPEN_SANS_BOLD))
pdfmetrics.registerFont(TTFont('OpenSans-Italic', OPEN_SANS_ITALIC))

def generate_invoice(request, reservation_id):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate

    reservation = get_object_or_404(Reservation, reservation_ID=reservation_id)

    # Define guest-specific folder for invoices
    guest_folder = os.path.join(settings.MEDIA_ROOT, f"invoices/{reservation.guest.id}/")
    os.makedirs(guest_folder, exist_ok=True)

    # Define file path
    invoice_filename = f"Reservation_Invoice_{reservation.reservation_ID}.pdf"
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

    # Register fonts
    pdfmetrics.registerFont(TTFont('OpenSans', OPEN_SANS_REGULAR))
    pdfmetrics.registerFont(TTFont('OpenSans-Bold', OPEN_SANS_BOLD))
    pdfmetrics.registerFont(TTFont('OpenSans-Italic', OPEN_SANS_ITALIC))

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=14, fontName='OpenSans-Bold')
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName='OpenSans', fontSize=9)
    italic_style = ParagraphStyle('Italic', parent=normal_style, fontName='OpenSans-Italic', alignment=1)
    bold_style = ParagraphStyle('Bold', parent=normal_style, fontName='OpenSans-Bold', fontSize=9)
    highlighted_style = ParagraphStyle('Highlighted', parent=bold_style, textColor=colors.red, fontSize=10)

    elements = []

    # Add Lido Logo
    logo_path = os.path.join(settings.BASE_DIR, 'lidoapp/static/assets/images/components/fulllogo.png')
    elements.append(Image(logo_path, width=50 * mm, height=50 * mm, hAlign='CENTER'))
    elements.append(Spacer(1, 5))

    # Resort Address (Centered and Italic)
    address = """
        Sariaya, Quezon Province<br/>
        Brgy. Talaan, Aplaya, Sariaya, Calabarzon, 4322, Philippines<br/>
        lidoshores.sariaya@gmail.com<br/>
        +639173004577 Viber Only
    """
    elements.append(Paragraph(address.replace("<br/>", "<br />"), italic_style))
    elements.append(Spacer(1, 5))

    # Invoice Header
    elements.append(Paragraph(f"Invoice for Reservation", title_style))
    elements.append(Spacer(1, 10))

    # Highlighted Reservation Details
    elements.append(Paragraph(f"Reservation ID: {reservation.reservation_ID}", highlighted_style))
    elements.append(Paragraph(f"Check-in Date: {reservation.check_in_date} (after 3:00 PM)", highlighted_style))
    elements.append(Paragraph(f"Check-out Date: {reservation.check_out_date} (before 12:00 PM)", highlighted_style))
    elements.append(Paragraph(f"Room Chosen: {reservation.room_chosen}", highlighted_style))
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
        ('FONTNAME', (0, 0), (-1, -1), 'OpenSans'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(guest_table)
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
        ('FONTNAME', (0, 0), (-1, -1), 'OpenSans'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(details_table)
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
            ('FONTNAME', (0, 0), (-1, -1), 'OpenSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(add_ons_table)
        elements.append(Spacer(1, 10))

    # Corkage Fee Note
    elements.append(Paragraph("Note: Corkage fee of P250 applies if bringing food or drinks from outside.", italic_style))
    elements.append(Spacer(1, 10))

    # Footer
    elements.append(Paragraph("Thank you for choosing Lido Shores Resort!", ParagraphStyle('Footer', parent=bold_style, alignment=1)))

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
            "return_url": "https://lidoshoresresort.onrender.com/success",
            "cancel_url": "https://lidoshoresresort.onrender.com/cancel",
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
            # Handle reservation creation
            adult_count = int(reservation_details.get('adult_count', 0))
            children_count = int(reservation_details.get('children_count', 0))
            total_guest_count = adult_count + children_count

            reservation = Reservation(
                guest_id=request.session.get('guest_id'),
                check_in_date=reservation_details.get('check_in_date'),
                check_out_date=reservation_details.get('check_out_date'),
                room_chosen=reservation_details.get('room_chosen'),
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
                add_ons=reservation_details.get('add_ons', []),
                status='Booked',
            )
            reservation.save()

            # Deduct add-on quantities from the database
            add_ons = reservation_details.get('add_ons', {})
            for add_on_name, add_on_details in add_ons.items():
                quantity = int(add_on_details.get('quantity', 0))
                if quantity > 0:
                    try:
                        add_on = AddOn.objects.get(name=add_on_name)
                        if add_on.stock_quantity >= quantity:
                            add_on.stock_quantity -= quantity
                            add_on.save()
                        else:
                            print(f"Not enough stock for {add_on_name}. Current stock: {add_on.stock_quantity}")
                    except AddOn.DoesNotExist:
                        print(f"Add-on {add_on_name} does not exist in the database.")

            return redirect(f"/lidocompleted?reservation_ID={reservation.reservation_ID}")

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
    
# Import models from the current app
from .models import (
    GuestAccount, Reservation, AdminAccount, AddOn, WalkInReservation,
    FrontdeskAccount, Room, RoomImage, Amenity
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


# Blogsite Views
def lidohome(request):
    return render(request, 'blogsite/lidohome.html')

def lidoroomrates(request):
    return render(request, 'blogsite/header/lidoroomrates.html')

def room_rates_booking(request):
    # Fetch all rooms
    rooms = Room.objects.prefetch_related('room_amenities').all()

    # Set the first available room as the default (or apply your custom logic)
    default_room = rooms.filter(room_status='available').order_by('room_price').first()

    return render(request, 'booking/roomrates_booking.html', {
        'rooms': rooms,
        'default_room': default_room
    })


from django.template.loader import render_to_string

def get_available_rooms(request):
    # Extract parameters
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

    # Fetch booked room names or IDs for the specified date range
    booked_rooms = Reservation.objects.filter(
        Q(check_in_date__lt=check_out_date) & Q(check_out_date__gt=check_in_date)
    ).values_list('room_chosen', flat=True)

    # Filter available rooms
    available_rooms = Room.objects.filter(
        Q(room_capacity__gte=total_guests),
        Q(room_status='available'),
        Q(room_price__gte=min_price),
        Q(room_price__lte=max_price),
    ).exclude(
        room_name__in=booked_rooms  # Assuming room_name matches room_chosen in the Reservation model
    ).prefetch_related('room_amenities')

    # Filter by bed type if specified
    if bed_type != 'all':
        available_rooms = available_rooms.filter(bed_type=bed_type)

    # Render the template with available rooms
    rendered_template = render_to_string('booking/roomrates_booking.html', {'rooms': available_rooms})
    return JsonResponse({'html': rendered_template})


def lidobooking(request):
    if 'guest_id' not in request.session:
        return redirect('guestlogin')

    # Retrieve the check-in date, check-out date, and guest count from the GET parameters
    check_in_date_str = request.GET.get('check_in_date')
    check_out_date_str = request.GET.get('check_out_date')
    total_guests = int(request.GET.get('total_guests', 1))  # Default to 1 guest if not provided

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

    # Fetch add-ons from the database where stock_quantity is greater than 0
    addons = AddOn.objects.filter(stock_quantity__gt=0)

    context = {
        'rooms': available_rooms,  # Pass filtered rooms
        'addons': addons,
        'check_in_date': check_in_date,
        'check_out_date': check_out_date,
        'total_guests': total_guests,
    }

    return render(request, 'booking/lidobooking.html', context)

def lidogallery(request):
    return render(request, 'blogsite/header/lidogallery.html')

def lidocafe(request):
    return render(request, 'blogsite/header/lidocafe.html')

def lidoaboutus(request):
    return render(request, 'blogsite/header/lidoaboutus.html')

def lidoguesttransaction(request):
    if 'guest_id' not in request.session:
        return redirect('guestlogin')
    
    guest_id = request.session.get('guest_id')
    guest = GuestAccount.objects.get(id=guest_id)
    reservations = Reservation.objects.filter(guest=guest)
    
    return render(request, 'authentication/guest/lidoguesttransaction.html', {'reservations': reservations})



def lidorooms(request):
    rooms = Room.objects.all()
    print(rooms)
    
    for room in rooms:
        print(room.room_image.url)  # Debugging: Check image URLs

    return render(request, 'blogsite/lidorooms.html', {'rooms': rooms})


def lidoaddons(request):
    addons = AddOn.objects.filter(stock_quantity__gt=0)
    print(addons)  # Debugging line to check if addons are fetched
    return render(request, 'booking/lidoaddons.html', {'addons': addons})


def lidocompleted(request):
    reservation_id = request.GET.get('reservation_ID', None)  # Retrieve from query parameters
    context = {
        'clear_local_storage': True,
        'reservation_id': reservation_id,  # Pass the reservation ID to the template
    }
    return render(request, 'booking/lidocompleted.html', context)





def faqlido(request):
    return render(request, 'authentication/guest/faqlido.html')


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
    

# Helper function to generate room ID
def generate_room_id():
    return random.randint(100000, 999999)

def frontdesk_dashboard(request):
    return render(request, 'authentication/frontdesk/frontdesk_dashboard.html')



def frontdesklogout(request):
    request.session.flush()
    return redirect('frontdesk_dashboard') 
 
def frontdesk_roomlist(request):
    rooms = Room.objects.all()
    context = {
        'rooms': rooms,
        'range_4': range(4)  # This is needed to render four slots in the template
    }
    return render(request, 'authentication/frontdesk/frontdesk_roomlist.html', context)


def frontdesk_rooms(request):
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
        html = render_to_string('authentication/frontdesk/room_list.html', {'rooms': rooms})
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
    return render(request, 'authentication/frontdesk/frontdesk_rooms.html', context)



@csrf_exempt
def submit_add_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        room_price = request.POST.get('room_price')
        room_capacity = request.POST.get('room_capacity')
        room_size = request.POST.get('room_size')
        room_image = request.FILES.get('room_image')
        room_amenities = request.POST.getlist('room_amenities[]')
        additional_images = request.FILES.getlist('additional_images[]')
        bed_type = request.POST.get('bed_type')

        # Validity check for bed type
        valid_bed_types = dict(Room.BED_TYPE_CHOICES).keys()
        if bed_type not in valid_bed_types:
            return JsonResponse({'success': False, 'error': 'Invalid bed type selected.'})

        # Check for required fields
        if not all([room_name, room_price, room_capacity, room_size, room_image, bed_type]):
            return JsonResponse({'success': False, 'error': 'Please fill all required fields and upload a main image.'})

        try:
            with transaction.atomic():
                # Create the room instance and save it
                room = Room(
                    room_name=room_name,
                    room_price=room_price,
                    room_capacity=room_capacity,
                    room_size=room_size,
                    room_image=room_image,
                    bed_type=bed_type
                )
                room.save()

                # Add each selected amenity to the room
                for amenity in room_amenities:
                    if amenity:
                        amenity_obj, created = Amenity.objects.get_or_create(amenity_type=amenity)
                        room.room_amenities.add(amenity_obj)

                # Save each additional image and associate it with the room
                for image in additional_images:
                    if image:
                        # Create and save RoomImage instance, associating it with the created room
                        room_image_instance = RoomImage(room=room, image=image)
                        room_image_instance.save()


            messages.success(request, f"Room '{room_name}' has been created successfully!")
            return JsonResponse({'success': True, 'redirect_url': '/frontdesk_roomlist/'})
        except Exception as e:
            logger.error(f"Error saving room: {e}")
            return JsonResponse({'success': False, 'error': 'Could not save room. Please try again later.'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})






def view_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    main_image = room.room_image  # Main image field
    additional_images = room.additional_images.filter(visible=True)  # Only fetch visible images
    
    return render(request, 'authentication/frontdesk/view_room.html', {
        'room': room,
        'main_image': main_image,
        'additional_images': additional_images,
    })

@csrf_exempt
def edit_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    additional_images = list(room.additional_images.all())

    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        room_price = request.POST.get('room_price')
        room_capacity = request.POST.get('room_capacity')
        room_size = request.POST.get('room_size')
        bed_type = request.POST.get('bed_type')
        room_image = request.FILES.get('room_image')
        room_amenities = request.POST.getlist('room_amenities')

        # Validity check for bed type
        valid_bed_types = dict(Room.BED_TYPE_CHOICES).keys()
        if bed_type not in valid_bed_types:
            messages.error(request, 'Invalid bed type selected.')
            return JsonResponse({'success': False})

        # Only check required fields if main image isn't already present or being updated
        if not all([room_name, room_price, room_capacity, room_size, bed_type]) or (not room.room_image and not room_image):
            messages.error(request, 'Please fill all required fields.')
            return JsonResponse({'success': False})

        try:
            with transaction.atomic():
                # Update room details
                room.room_name = room_name
                room.room_price = room_price
                room.room_capacity = room_capacity
                room.room_size = room_size
                room.bed_type = bed_type

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

            messages.success(request, 'Room updated successfully!')
            return JsonResponse({'success': True, 'redirect_url': redirect('view_room', room_id=room.id).url})

        except Exception as e:
            logger.error(f"Error updating room: {e}")
            messages.error(request, 'Could not update room. Please try again later.')
            return JsonResponse({'success': False})

    amenities = Amenity.objects.all()
    selected_amenities = room.room_amenities.values_list('amenity_type', flat=True)

    return render(request, 'authentication/frontdesk/edit_room.html', {
        'room': room,
        'amenities': amenities,
        'selected_amenities': selected_amenities,
        'additional_images': additional_images,
        'range_4': range(4)
    })

def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    room_name = room.room_name  # Capture the room name before deletion
    room.delete()
    messages.success(request, f'Room "{room_name}" deleted successfully!')
    return redirect('frontdesk_rooms')

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


def validate_image(file):
    if not file.content_type.startswith('image'):
        raise ValidationError("Only image files are allowed.")






# Authentication for Admin
def adminlogin(request):
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




def admin_dashboard(request):
    if 'admin_id' in request.session:
        admin = AdminAccount.objects.get(id=request.session['admin_id'])

        # Get today's date
        today = timezone.now().date()

        # Group sales data by date for the current month (Daily sales for each date)
        reservations_by_date = (
            Reservation.objects.filter(check_in_date__gte=today.replace(day=1))
            .values('check_in_date')
            .annotate(total_sales=Sum('overall_total_amount'))
            .order_by('check_in_date')
        )

        # Group walk-in sales data by date
        walk_in_sales_by_date = (
            WalkInReservation.objects.filter(arrival_datetime__gte=today.replace(day=1))  # Ensure this covers your expected range
            .values('arrival_datetime')
            .annotate(total_sales=Sum('overall_total_amount'))  # Summing up the total sales for each day
            .order_by('arrival_datetime')
        )

        # Format reservation details by date for hover interactions
        reservation_details = (
            Reservation.objects.filter(check_in_date__gte=today.replace(day=1))
            .values('check_in_date', 'check_out_date', 'room_chosen', 'overall_total_amount', 'status')
        )

        # Format walk-in reservation details by date
        walk_in_reservation_details = (
            WalkInReservation.objects.filter(arrival_datetime__gte=today.replace(day=1))
            .values('arrival_datetime', 'first_name', 'last_name', 'status_rate', 'overall_total_amount')
        )

        # Count guest and admin accounts for Pie Chart
        guest_count = GuestAccount.objects.count()
        admin_count = AdminAccount.objects.count()
        account_data = [guest_count, admin_count]

        # Serialize the data for JavaScript
        sales_data = json.dumps(list(reservations_by_date), default=str)
        reservation_details_data = json.dumps(list(reservation_details), default=str)
        walk_in_sales_data = json.dumps(list(walk_in_sales_by_date), default=str)
        walk_in_reservation_details_data = json.dumps(list(walk_in_reservation_details), default=str)
        account_data_json = json.dumps(account_data)

        # Add revenue data to the context
        context = {
            'admin': admin,
            'sales_data': sales_data,
            'reservation_details_data': reservation_details_data,
            'walk_in_sales_data': walk_in_sales_data,
            'walk_in_reservation_details_data': walk_in_reservation_details_data,
            'account_data': account_data_json,
        }

        return render(request, 'authentication/admin/lidoadmindashboard.html', context)
    else:
        return redirect('adminlogin')


def revenue_data_view(request):
    if 'admin_id' in request.session:
        # Get the earliest reservation date
        earliest_reservation_date = Reservation.objects.earliest('check_in_date').check_in_date

        # Weekly Revenue Calculation
        weekly_revenue_data = (
            Reservation.objects.filter(check_in_date__gte=earliest_reservation_date)
            .annotate(week=ExtractWeek('check_in_date'), year=ExtractYear('check_in_date'))
            .values('week', 'year')
            .annotate(total_sales=Sum('overall_total_amount'))
            .order_by('year', 'week')
        )

        weekly_revenue = []
        for data in weekly_revenue_data:
            # Calculate start and end dates for the week
            start_of_week = earliest_reservation_date + timedelta(weeks=data['week'] - 1)
            end_of_week = start_of_week + timedelta(days=6)
            weekly_revenue.append({
                "week": f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}",
                "revenue": float(data['total_sales'] or 0),
                "sales_count": Reservation.objects.filter(
                    check_in_date__range=(start_of_week, end_of_week)
                ).count(),
            })

        # Monthly Revenue Calculation
        monthly_revenue_data = (
            Reservation.objects.filter(check_in_date__gte=earliest_reservation_date)
            .annotate(month=ExtractMonth('check_in_date'), year=ExtractYear('check_in_date'))
            .values('month', 'year')
            .annotate(total_sales=Sum('overall_total_amount'))
            .order_by('year', 'month')
        )

        monthly_revenue = [
            {
                "month": f"{calendar.month_name[data['month']]} {data['year']}",
                "revenue": float(data['total_sales'] or 0),
            }
            for data in monthly_revenue_data
        ]

        return JsonResponse({
            "weekly_labels": [data["week"] for data in weekly_revenue],
            "weekly_values": [data["revenue"] for data in weekly_revenue],
            "weekly_sales_counts": [data["sales_count"] for data in weekly_revenue],
            "monthly_labels": [data["month"] for data in monthly_revenue],
            "monthly_values": [data["revenue"] for data in monthly_revenue],
        })
    else:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    
    
def adminlogout(request):
    request.session.flush()
    return redirect('admin_dashboard')


def create_addon(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock_quantity = request.POST.get('stock_quantity')
        image = request.FILES.get('image')
        
        addon = AddOn(name=name, description=description, price=price, stock_quantity=stock_quantity, image=image)
        addon.save()
        return redirect('admininventory')  # Redirect to the inventory page after adding the add-on

    return render(request, 'authentication/admin/create_addon.html')

# List all add-ons (READ)
def admin_inventory(request):
    addons = AddOn.objects.all()
    return render(request, 'authentication/admin/lidoadmininventory.html', {'addons': addons})

# Update an add-on (UPDATE)
def update_addon(request, addon_id):
    addon = get_object_or_404(AddOn, id=addon_id)
    
    if request.method == 'POST':
        addon.name = request.POST.get('name')
        addon.description = request.POST.get('description')
        addon.price = request.POST.get('price')
        addon.stock_quantity = request.POST.get('stock_quantity')
        if 'image' in request.FILES:
            addon.image = request.FILES['image']
        addon.save()
        return redirect('admininventory')
    
    return render(request, 'authentication/admin/update_addon.html', {'addon': addon})

# Delete an add-on (DELETE)
def delete_addon(request, addon_id):
    addon = get_object_or_404(AddOn, id=addon_id)
    addon.delete()
    return redirect('admininventory')

def walkin(request):
    return render(request, 'authentication/frontdesk/walkin.html')



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
    
    
    






from django.urls import reverse

def submit_walk_in(request):
    if request.method == 'POST':
        # Extract form data
        first_name = request.POST.get('firstName')
        middle_name = request.POST.get('middleName')
        last_name = request.POST.get('lastName')
        email = request.POST.get('email')
        contact_number = request.POST.get('contactNumber')
        address = request.POST.get('address')
        arrival_datetime = request.POST.get('arrivalDateTime')
        status_rate = request.POST.get('statusRate')
        cottage_rate = request.POST.get('cottageRate')
        payment_method = request.POST.get('paymentMethod')
        total_guest_count = int(request.POST.get('totalGuestCount', 0))
        total_child_count = int(request.POST.get('totalChildCount', 0))

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
        total_amount = (total_guest_count * adult_price) + (total_child_count * child_price)

        # Create a new reservation record with a generated Walk-in ID
        walk_in = WalkInReservation.objects.create(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            email=email,
            contact_number=contact_number,
            address=address,
            arrival_datetime=arrival_datetime,
            status_rate=status_rate,
            cottage_rate=cottage_rate,
            payment_method=payment_method,
            total_guest_count=total_guest_count,
            total_child_count=total_child_count,
            overall_total_amount=total_amount,
        )

        # Redirect to success page with the walk_in_ID in the URL
        return redirect(f"{reverse('walk_in_success')}?walk_in_ID={walk_in.walk_in_ID}")

    return HttpResponse("Invalid request method", status=405)


def walk_in_success(request):
    return render(request, 'authentication/admin/walkinsuccess.html')



# Authentication Views
def guestlogin(request):
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

    return render(request, 'authentication/guest/lidoguestlogin.html')

def guestsignup(request):
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
    return render(request, 'authentication/guest/lidoguestsignup.html', {'form': form})

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

def guestlogout(request):
    request.session.flush()
    return redirect('lidohome')

def guestprofile(request):
    guest_id = request.session.get('guest_id')
    if not guest_id:
        return redirect('guestlogin')

    guest = get_object_or_404(GuestAccount, id=guest_id)
    return render(request, 'authentication/guest/guest_profile.html', {'guest': guest})

@csrf_exempt
def update_guest_profile(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            guest_id = request.session.get("guest_id")
            guest = GuestAccount.objects.get(id=guest_id)

            # Update fields
            guest.first_name = data.get("first_name", guest.first_name)
            guest.middle_name = data.get("middle_name", guest.middle_name)
            guest.last_name = data.get("last_name", guest.last_name)
            guest.email = data.get("email", guest.email)
            guest.contact_number = data.get("contact_number", guest.contact_number)
            guest.telephone_number = data.get("telephone_number", guest.telephone_number)
            guest.address1 = data.get("address1", guest.address1)
            guest.country = data.get("country", guest.country)
            guest.city = data.get("city", guest.city)
            
            # Update password if provided
            if "password" in data and data["password"]:
                if data["password"] != data.get("confirmPassword"):
                    return JsonResponse({"success": False, "error": "Passwords do not match."}, status=400)
                guest.set_password(data["password"])  # Hash and set the new password

            guest.save()
            return JsonResponse({"success": True}, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)




def get_logged_in_guest_details(request):
    if 'guest_id' in request.session:
        try:
            guest = GuestAccount.objects.get(id=request.session['guest_id'])
            return JsonResponse({
                'success': True,
                'first_name': guest.first_name,
                'last_name': guest.last_name,
                'email': guest.email,
                'contact_number': guest.contact_number or "N/A",
                'telephone_number': guest.telephone_number or "N/A",
                'address1': guest.address1 or "N/A",
                'country': guest.country or "N/A",
                'city': guest.city or "N/A",
                'created_at': guest.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
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
            data = json.loads(request.body)
            guest_id = request.session.get('guest_id')  # Ensure the user is logged in
            if not guest_id:
                return JsonResponse({'success': False, 'error': 'Guest not logged in.'}, status=400)

            # Compute total_guest_count from adult_count and children_count
            adult_count = int(data.get('adult_count', 0))
            children_count = int(data.get('children_count', 0))
            total_guest_count = adult_count + children_count

            # Create the reservation
            reservation = Reservation(
                guest_id=guest_id,
                check_in_date=data['check_in_date'],
                check_out_date=data['check_out_date'],
                room_chosen=data['room_chosen'],
                adult_count=adult_count,  # Save adult count separately
                children_count=children_count,  # Save children count separately
                total_guest_count=total_guest_count,  # Save computed guest count
                overall_total_amount=data['overall_total_amount'],
                status='Booked',  # Automatically set status to Booked after payment
            )
            reservation.save()

            return JsonResponse({
                'success': True,
                'reservation_ID': str(reservation.reservation_ID),
                'redirect_url': reverse('lidocompleted') + f"?reservation_ID={reservation.reservation_ID}",
            })
        except Exception as e:
            print(f"Error saving reservation: {e}")
            return JsonResponse({'success': False, 'error': 'Could not save reservation.'}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)
