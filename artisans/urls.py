"""
Artisan Field Service App - URL Configuration
"""
from django.urls import path
from . import views

app_name = 'artisans'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('onboard-services/', views.onboard_services_view, name='onboard_services'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verify-email-pending/', views.verify_email_pending_view, name='verify_email_pending'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('profile/change-password/', views.profile_change_password_view, name='profile_change_password'),
    # Dashboard & Profile
    path('', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('organization/', views.organization_edit_view, name='organization_edit'),
    # Jobs
    path('jobs/', views.job_list_view, name='job_list'),
    path('jobs/new/', views.job_create_view, name='job_create'),
    path('jobs/<int:job_id>/', views.job_detail_view, name='job_detail'),
    path('jobs/<int:job_id>/accept/', views.job_accept_view, name='job_accept'),
    path('jobs/<int:job_id>/reject/', views.job_reject_view, name='job_reject'),
    path('jobs/<int:job_id>/start/', views.job_start_view, name='job_start'),
    path('jobs/<int:job_id>/complete/', views.job_complete_view, name='job_complete'),
    path('jobs/<int:job_id>/checklist/', views.job_add_checklist_view, name='job_add_checklist'),
    path('jobs/<int:job_id>/photo/', views.job_add_photo_view, name='job_add_photo'),
    path('jobs/<int:job_id>/checklist/<int:item_id>/toggle/', views.checklist_toggle_view, name='checklist_toggle'),
    # Technicians
    path('technicians/', views.technician_list_view, name='technician_list'),
    path('technicians/invite/', views.technician_invite_view, name='technician_invite'),
    path('invite/<str:token>/', views.technician_accept_invite_view, name='accept_invite'),
    path('customers/', views.customer_list_view, name='customer_list'),
    path('customers/new/', views.customer_create_view, name='customer_create'),
    # Service Types
    path('services/', views.service_type_list_view, name='service_type_list'),
    path('services/add/', views.service_add_view, name='service_add'),
    path('services/new/manual/', views.service_type_create_view, name='service_type_create'),
    path('services/<int:service_type_id>/edit/', views.service_type_edit_view, name='service_type_edit'),
    # Invoices
    path('invoices/', views.invoice_list_view, name='invoice_list'),
    path('invoices/job/<int:job_id>/new/', views.invoice_create_view, name='invoice_create'),
    path('invoices/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
    path('invoices/<int:invoice_id>/edit/', views.invoice_edit_view, name='invoice_edit'),
    path('invoices/<int:invoice_id>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('invoices/<int:invoice_id>/email/', views.invoice_email_view, name='invoice_email'),
    path('invoices/<int:invoice_id>/pay/', views.invoice_mark_paid_view, name='invoice_mark_paid'),
    # Customers
    path('customers/<int:customer_id>/', views.customer_detail_view, name='customer_detail'),
    # Public Booking
    path('book/', views.booking_view, name='booking'),
    path('book/org/<int:org_id>/', views.booking_view, name='booking_org'),
    path('book/status/<int:job_id>/', views.booking_status_view, name='booking_status'),
    path('book/<int:job_id>/review/', views.booking_review_view, name='booking_review'),
]
