from http.client import HTTPResponse
from django.urls import path
from . import views 
from .views import delete_profile_picture, verify_recaptcha, get_logged_in_guest_details, check_admin_email, check_admin_signup_email, frontdesk_roomlist, check_frontdesk_email, check_frontdesk_signup_email, frontdesk_rooms, faqlido

urlpatterns = [
    path('verify-recaptcha/', verify_recaptcha, name='verify_recaptcha'),
    
    # Lido Blogsite
    path('', views.lidohome, name='lidohome'),
    path('lidoroomrates/', views.lidoroomrates, name='lidoroomrates'),
    path('lidogallery/', views.lidogallery, name='lidogallery'),
    path('lidocafe/', views.lidocafe, name='lidocafe'),
    path('lidoaboutus/', views.lidoaboutus, name='lidoaboutus'),
    path('lidorooms/', views.lidorooms, name='lidorooms'),

    # Lido Booking
    path('lidobooking/', views.lidobooking, name='lidobooking'),
    path('lidoaddons/', views.lidoaddons, name='lidoaddons'),
    path('lidocompleted/', views.lidocompleted, name='lidocompleted'),

    # Guest Login Authentication
    path('guestlogin/', views.guestlogin, name='guestlogin'),
    path('guestprofile/', views.guestprofile, name='guestprofile'),
    path('update_guest_profile/', views.update_guest_profile, name='update_guest_profile'),
    path("upload_profile_picture/", views.upload_profile_picture, name="upload_profile_picture"),
    path("delete-profile-picture/", delete_profile_picture, name="delete_profile_picture"),

    path('guestsignup/', views.guestsignup, name='guestsignup'),
    path('guestlogout/', views.guestlogout, name='guestlogout'),
    path('get-guest-details/', get_logged_in_guest_details, name='get_guest_details'),
    path('faqlido/', views.faqlido, name='faqlido'),
    
    # Front Desk Authentication
    path('frontdesklogin/', views.frontdesklogin, name='frontdesklogin'),
    path('frontdesksignup/', views.frontdesksignup, name='frontdesksignup'),
    path('frontdesk-signup-success/', views.frontdesk_signup_success, name='frontdesk_signup_success'),
    path('frontdesk-logout/', views.frontdesklogout, name='frontdesklogout'),
    path('frontdesk-dashboard/', views.frontdesk_dashboard, name='frontdesk_dashboard'),
    path('check_frontdesk_email/', check_frontdesk_email, name='check_frontdesk_email'),
    path('check_frontdesk_signup_email/', check_frontdesk_signup_email, name='check_frontdesk_signup_email'),
    path('frontdesk_roomlist/', frontdesk_roomlist, name='frontdesk_roomlist'),
    path('frontdesk_rooms/', frontdesk_rooms, name='frontdesk_rooms'),
    path('submit_add_room/', views.submit_add_room, name='submit_add_room'),
    path('rooms/view/<int:room_id>/', views.view_room, name='view_room'),
    path('rooms/edit/<int:room_id>/', views.edit_room, name='edit_room'),
    path('rooms/delete/<int:room_id>/', views.delete_room, name='delete_room'),
    path('delete_multiple_rooms/', views.delete_multiple_rooms, name='delete_multiple_rooms'),
    

    path('get_available_rooms/', views.get_available_rooms, name='get_available_rooms'),
    
    path('create-booking/', views.create_booking, name='create_booking'),  # Register the endpoint
    path('success/', views.success, name='success'),
    path('cancel/', lambda request: HTTPResponse("Payment was canceled!"), name='cancel'),
    path('capture-payment/', views.capture_payment, name='capture_payment'),
    path('invoice/generate/<str:reservation_id>/', views.generate_invoice, name='generate_invoice'),

    
    
    # Admin Authentication
    path('adminlogin/', views.adminlogin, name='adminlogin'),
    path('adminsignup/', views.admin_signup, name='adminsignup'),
    path('admin-signup-success/', views.admin_signup_success, name='admin_signup_success'),
    path('admin-logout/', views.adminlogout, name='adminlogout'),
    
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('revenue-data/', views.revenue_data_view, name='revenue_data'),
    path('download-weekly-sales-report/', views.generate_weekly_sales_report, name='download_weekly_sales_report'),
    
    path('check_admin_email/', check_admin_email, name='check_admin_email'),
    path('check_admin_signup_email/', check_admin_signup_email, name='check_admin_signup_email'),
    path('admin-inventory/', views.admin_inventory, name='admininventory'),
    path('admin-inventory/create/', views.create_addon, name='create_addon'),
    path('admin-inventory/update/<int:addon_id>/', views.update_addon, name='update_addon'),
    path('admin-inventory/delete/<int:addon_id>/', views.delete_addon, name='delete_addon'),
    path('walkin/', views.walkin, name='walkin'),
    path('submit-walk-in/', views.submit_walk_in, name='submit_walk_in'),
    path('walk_in_success/', views.walk_in_success, name='walk_in_success'),
    



    # Signup success page
    path('signup-success/', views.signup_success, name='signup_success'),

    # Check existing guest email for login and signup
    path('check-email/', views.check_guest_email, name='check_email'),
    path('check-signup-email/', views.check_signup_email, name='check_signup_email'),

    path('check-guest-session/', views.check_guest_session, name='check_guest_session'),
    path('submit-reservation/', views.submit_reservation, name='submit_reservation'),

    path('lidoguesttransaction/', views.lidoguesttransaction, name='lidoguesttransaction'),
]
