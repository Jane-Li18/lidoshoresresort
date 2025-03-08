from http.client import HTTPResponse
from django.urls import path
from . import views 
from .views import delete_profile_picture, verify_recaptcha, get_logged_in_guest_details, check_admin_email, check_admin_signup_email, admin_add_room, check_frontdesk_email, check_frontdesk_signup_email, admin_rooms, faq_policy

urlpatterns = [
    path('verify_recaptcha/', verify_recaptcha, name='verify_recaptcha'),
    
    # Lido Blogsite
    path('', views.lidohome, name='lidohome'),
    path('lidoroomrates/', views.lidoroomrates, name='lidoroomrates'),
    path('lidogallery/', views.lidogallery, name='lidogallery'),
    path('lidocafe/', views.lidocafe, name='lidocafe'),
    path('lidoaboutus/', views.lidoaboutus, name='lidoaboutus'),
    path('lidorooms/', views.lidorooms, name='lidorooms'),

    # Lido Booking
    path('lidobooking/', views.lidobooking, name='lidobooking'),
    path('lidocompleted/', views.lidocompleted, name='lidocompleted'),

    # Guest Login Authentication
    path('guest_login/', views.guest_login, name='guest_login'),
    path('guest_profile/', views.guest_profile, name='guest_profile'),
    path('update_guest_profile/', views.update_guest_profile, name='update_guest_profile'),
    path("upload_profile_picture/", views.upload_profile_picture, name="upload_profile_picture"),
    path("delete_profile_picture/", delete_profile_picture, name="delete_profile_picture"),

    path('guest_signup/', views.guest_signup, name='guest_signup'),
    path('guest_logout/', views.guest_logout, name='guest_logout'),
    path('get_guest_details/', get_logged_in_guest_details, name='get_guest_details'),
    path('faq_policy/', views.faq_policy, name='faq_policy'),
    
    path('frontdesk_gallery/', views.frontdesk_gallery, name='frontdesk_gallery'),
    path('upload-image-or-banner/', views.upload_image_or_banner, name='upload_image_or_banner'),
    path('delete-image/<int:image_id>/', views.delete_image, name='delete_image'),
    path('delete-gallery/<slug:gallery_slug>/', views.delete_gallery, name='delete_gallery'),
    path('lidobanner/', views.lidobanner, name='lidobanner'),
    
    # Front Desk Authentication
    path('frontdesklogin/', views.frontdesklogin, name='frontdesklogin'),
    path('frontdesksignup/', views.frontdesksignup, name='frontdesksignup'),
    path('frontdesk_signup_success/', views.frontdesk_signup_success, name='frontdesk_signup_success'),
    path('frontdesk_logout/', views.frontdesklogout, name='frontdesklogout'),
    path('frontdesk_dashboard/', views.frontdesk_dashboard, name='frontdesk_dashboard'),
    path('check_frontdesk_email/', check_frontdesk_email, name='check_frontdesk_email'),
    path('check_frontdesk_signup_email/', check_frontdesk_signup_email, name='check_frontdesk_signup_email'),
    
    path('walk_in/', views.walk_in, name='walk_in'),
    path('submit_walk_in/', views.submit_walk_in, name='submit_walk_in'),
    path('walk_in_success/', views.walk_in_success, name='walk_in_success'),
    path('cottage_rates/', views.cottage_rates, name='cottage_rates'),
    path('submit_cottage_rates/', views.submit_cottage_rates, name='submit_cottage_rates'),
    path('delete/<int:rate_id>/', views.delete_cottage_rates, name='delete_cottage_rates'),
    
    path('update_walk_in_status/', views.update_walk_in_status, name='update_walk_in_status'),
    
    
    
    path('transaction_management/', views.transaction_management, name='transaction_management'),
    path('update_transaction_management_status/', views.update_transaction_management_status, name='update_transaction_management_status'),
    path('rebooking_pending/', views.rebooking_pending, name='rebooking_pending'),
    path('handle-rebooking-request/<int:rebooking_request_id>/', views.handle_rebooking_request, name='handle_rebooking_request'),
    path('save-receipt/', views.save_receipt, name='save_receipt'),


    path('booking/roomrates_booking/', views.room_rates_booking, name='room_rates_booking'),

    path('get_available_rooms/', views.get_available_rooms, name='get_available_rooms'),
    path('api/getRoomSpecificAvailability', views.get_room_specific_availability, name='get_room_specific_availability'),
    path('api/getRoomAvailability', views.get_room_availability, name='get_room_availability'),
    
    path('policy_board/', views.policy_board, name='policy_board'),
    path('save_policy/', views.save_policy, name='save_policy'),
    path('get_policies_by_type/', views.get_policies_by_type, name='get_policies_by_type'),
    path('delete_policy/<int:policy_id>/', views.delete_policy, name='delete_policy'),
    path('faq_policy/', views.faq_policy, name='faq_policy'),
    
    path('create-booking/', views.create_booking, name='create_booking'),  # Register the endpoint
    path('success/', views.success, name='success'),
    path('cancel/', lambda request: HTTPResponse("Payment was canceled!"), name='cancel'),
    path('capture-payment/', views.capture_payment, name='capture_payment'),
    path('invoice/generate/<str:reservation_id>/', views.generate_invoice, name='generate_invoice'),
    path('get-guest-details/', views.get_logged_in_guest_details, name='get_guest_details'),

    
    
    # Admin Authentication
    path('admin_login/', views.admin_login, name='admin_login'),
    path('adminsignup/', views.admin_signup, name='adminsignup'),
    path('admin_signup_success/', views.admin_signup_success, name='admin_signup_success'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
    
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('sales_report/', views.sales_report, name='sales_report'),
    path('download_sales_report/', views.download_sales_report, name='download_sales_report'),
    path('add_sale/', views.add_sale, name='add_sale'),
    path('add_empty_placeholder/', views.add_empty_placeholder, name='add_empty_placeholder'),

    
    path('check_admin_email/', check_admin_email, name='check_admin_email'),
    path('check_admin_signup_email/', check_admin_signup_email, name='check_admin_signup_email'),
    
    path('admin_inventory/', views.admin_inventory, name='admin_inventory'),
    path('submit_admin_inventory/', views.submit_admin_inventory, name='submit_admin_inventory'),
    path('delete/<str:status>/<int:addon_id>/', views.delete_addon, name='delete_addon'),
    path('update_selling_quantity/<int:addon_id>/<str:quantity>/', views.update_selling_quantity, name='update_selling_quantity'),
    path('toggle_sell_by_2/<int:addon_id>/', views.toggle_sell_by_2, name='toggle_sell_by_2'), 
    path('get_stock_quantity/<int:addon_id>/', views.get_stock_quantity, name='get_stock_quantity'),

    
    path('get_schedules/', views.get_schedules, name='get_schedules'),
    path('submit_admin_schedule/', views.submit_admin_schedule, name='submit_admin_schedule'),
    path('get_schedule/<int:schedule_id>/', views.get_schedule, name='get_schedule'),
    path('admin_schedule/', views.admin_schedule, name='admin_schedule'),
    path('delete_schedule/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),

    path('admin_add_room/', admin_add_room, name='admin_add_room'),
    path('admin_rooms/', admin_rooms, name='admin_rooms'),
    path('submit_add_room/', views.submit_add_room, name='submit_add_room'),
    path('rooms/view/<int:room_id>/', views.view_room, name='view_room'),
    path('rooms/edit/<int:room_id>/', views.edit_room, name='edit_room'),
    path('rooms/delete/<int:room_id>/', views.delete_room, name='delete_room'),
    path('delete_multiple_rooms/', views.delete_multiple_rooms, name='delete_multiple_rooms'),
    path('update_room_status/<int:room_id>/', views.update_room_status, name='update_room_status'),

    # Signup success page
    path('signup_success/', views.signup_success, name='signup_success'),

    # Check existing guest email for login and signup
    path('check_email/', views.check_guest_email, name='check_email'),
    path('check_signup_email/', views.check_signup_email, name='check_signup_email'),

    path('check-guest-session/', views.check_guest_session, name='check_guest_session'),
    path('submit-reservation/', views.submit_reservation, name='submit_reservation'),
    path('submit-reservation-gcash/', views.submit_reservation_gcash, name='submit_reservation_gcash'),
    path('rebook/<str:reservation_id>/', views.rebook_reservation, name='rebook_reservation'),

    path('guest_transactions/', views.guest_transactions, name='guest_transactions'),
]
