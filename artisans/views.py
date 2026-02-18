"""
Artisan Field Service App - MVP Phase 1 Views
"""
import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (
    SignUpForm,
    BusinessProfileForm,
    ProfileForm,
    OnboardServicesForm,
    TechnicianInviteForm,
    ServiceTypeForm,
    CustomerForm,
    JobForm,
    JobChecklistItemForm,
    JobPhotoForm,
    InvoiceForm,
    ReviewForm,
    BookingForm,
)
from .models import (
    Organization,
    UserProfile,
    ServiceType,
    PreDefinedService,
    ServiceCategory,
    ServiceSubcategory,
    Customer,
    Job,
    JobChecklistItem,
    JobPhoto,
    JobSignature,
    Invoice,
    TechnicianInvite,
    Review,
    EmailVerification,
)
from .services import (
    send_verification_email,
    send_verification_reminder_email,
    send_technician_invite_email,
    send_invoice_email,
)


def _get_user_profile(user):
    """Get user profile or None."""
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def _require_admin(view_func):
    """Decorator to require admin role."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('artisans:login')
        profile = _get_user_profile(request.user)
        if not profile or profile.role != 'admin':
            messages.error(request, 'Access denied. Admin role required.')
            return redirect('artisans:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def _require_technician(view_func):
    """Decorator to require technician role."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('artisans:login')
        profile = _get_user_profile(request.user)
        if not profile or profile.role != 'technician':
            messages.error(request, 'Access denied. Technician role required.')
            return redirect('artisans:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def _build_verify_url(request, token):
    """Build absolute URL for email verification."""
    return request.build_absolute_uri(reverse('artisans:verify_email', args=[token]))


def _create_email_verification(user, hours=24):
    """Create EmailVerification for user; return (token, EmailVerification)."""
    EmailVerification.objects.filter(user=user).delete()
    token = secrets.token_urlsafe(32)
    ev = EmailVerification.objects.create(
        user=user,
        token=token,
        expires_at=timezone.now() + timedelta(hours=hours),
    )
    return token, ev


# --- Authentication ---

def login_view(request):
    if request.user.is_authenticated:
        return redirect('artisans:dashboard')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            profile = _get_user_profile(user)
            # Technicians from invite: must change password first
            if profile and profile.must_change_password:
                login(request, user)
                return redirect('artisans:change_password')
            # Regular signup: must verify email first
            if profile and not profile.email_verified:
                login(request, user)
                return redirect('artisans:verify_email_pending')
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url or 'artisans:dashboard')
        messages.error(request, 'Invalid email or password.')
    return render(request, 'artisans/auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('artisans:login')


def verify_email_view(request, token):
    """Verify email from link in verification email."""
    ev = EmailVerification.objects.filter(token=token).first()
    if not ev:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect('artisans:login')
    if timezone.now() > ev.expires_at:
        ev.delete()
        messages.error(request, 'Verification link has expired. Please log in to resend.')
        return redirect('artisans:login')
    user = ev.user
    profile = _get_user_profile(user)
    if profile:
        profile.email_verified = True
        profile.save()
    ev.delete()
    if request.user.is_authenticated and request.user == user:
        messages.success(request, 'Email verified! Complete your business profile.')
        return redirect('artisans:onboarding')
    messages.success(request, 'Email verified! You can now log in.')
    return redirect('artisans:login')


@login_required
def verify_email_pending_view(request):
    """Shown when user tries to access app without verifying email."""
    profile = _get_user_profile(request.user)
    if not profile or profile.email_verified:
        return redirect('artisans:dashboard')
    return render(request, 'artisans/auth/verify_email_pending.html')


@login_required
def resend_verification_view(request):
    """Resend verification email."""
    profile = _get_user_profile(request.user)
    if not profile or profile.email_verified:
        return redirect('artisans:dashboard')
    if request.method == 'POST':
        token, _ = _create_email_verification(request.user, hours=24)
        verify_url = _build_verify_url(request, token)
        try:
            send_verification_reminder_email(request.user, verify_url)
            messages.success(request, 'Verification email sent. Check your inbox.')
        except Exception:
            messages.error(request, 'Could not send email. Try again later.')
    return redirect('artisans:verify_email_pending')


@login_required
def change_password_view(request):
    """Force password change for invited technicians."""
    profile = _get_user_profile(request.user)
    if not profile or not profile.must_change_password:
        return redirect('artisans:dashboard')
    form = SetPasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        profile.must_change_password = False
        profile.save()
        update_session_auth_hash(request, form.user)
        messages.success(request, 'Password updated. Welcome!')
        return redirect('artisans:dashboard')
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'artisans/auth/change_password.html', {'form': form})


@login_required
def profile_change_password_view(request):
    """Optional password change from profile (current password required)."""
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        update_session_auth_hash(request, form.user)
        messages.success(request, 'Your password was updated.')
        return redirect('artisans:profile')
    if request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'artisans/auth/change_password.html', {
        'form': form,
        'profile_change': True,
    })


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('artisans:dashboard')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create profile with email_verified=False
            UserProfile.objects.create(
                user=user,
                role='admin',
                email_verified=False,
            )
            token, _ = _create_email_verification(user, hours=24)
            verify_url = _build_verify_url(request, token)
            try:
                send_verification_email(user, verify_url)
            except Exception:
                pass  # Log in production; for dev, verification link shown
            login(request, user)
            return render(request, 'artisans/auth/verify_email_sent.html', {
                'email': user.email,
                'verify_url': verify_url,
                'debug': django_settings.DEBUG,
            })
        messages.error(request, 'Please correct the errors below.')
    else:
        form = SignUpForm()
    return render(request, 'artisans/auth/signup.html', {'form': form})


@login_required
def onboarding_view(request):
    """Business profile creation after signup."""
    profile = _get_user_profile(request.user)
    if profile and profile.organization:
        return redirect('artisans:dashboard')
    if profile and not profile.email_verified:
        messages.warning(request, 'Please verify your email first.')
        return redirect('artisans:verify_email_pending')

    if request.method == 'POST':
        form = BusinessProfileForm(request.POST)
        if form.is_valid():
            org = form.save()
            from artisans.services import update_organization_geolocation
            update_organization_geolocation(org)
            profile.organization = org
            profile.save()
            messages.success(request, 'Business profile created! Select the services you offer.')
            return redirect('artisans:onboard_services')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = BusinessProfileForm()
    return render(request, 'artisans/auth/onboarding.html', {
        'form': form,
        'categories': ServiceCategory.objects.all().order_by('name'),
    })


@login_required
def onboard_services_view(request):
    """Select predefined services to add to the organization (after profile onboarding)."""
    profile = _get_user_profile(request.user)
    if not profile or not profile.organization:
        return redirect('artisans:onboarding')
    org = profile.organization
    if not org.service_category_id:
        messages.warning(request, 'Please complete your business profile with a service category first.')
        return redirect('artisans:onboarding')
    if request.method == 'POST':
        form = OnboardServicesForm(request.POST, category=org.service_category)
        if form.is_valid():
            selected = form.cleaned_data.get('services') or []
            for predefined in selected:
                ServiceType.objects.get_or_create(
                    organization=org,
                    name=predefined.name,
                    defaults={
                        'description': predefined.description,
                        'base_price': predefined.base_price,
                        'price_type': predefined.price_type,
                        'service_subcategory': predefined.subcategory,
                    },
                )
            messages.success(request, f'Added {len(selected)} services. You can update pricing anytime from Services.')
            return redirect('artisans:dashboard')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = OnboardServicesForm(category=org.service_category)
    by_subcategory = []
    predefined = list(
        PreDefinedService.objects.filter(category=org.service_category)
        .select_related('subcategory')
        .order_by('name')
    )
    subcategories = ServiceSubcategory.objects.filter(
        category=org.service_category
    ).order_by('name')
    for sub in subcategories:
        svcs = [p for p in predefined if p.subcategory_id == sub.id]
        if svcs:
            by_subcategory.append((sub, svcs))
    other = [p for p in predefined if p.subcategory_id is None]
    if other:
        by_subcategory.append((None, other))
    return render(request, 'artisans/auth/onboard_services.html', {
        'form': form,
        'profile': profile,
        'category': org.service_category,
        'by_subcategory': by_subcategory,
    })


# --- Dashboard ---

@login_required
def dashboard_view(request):
    profile = _get_user_profile(request.user)
    if not profile:
        return redirect('artisans:onboarding')
    if not profile.email_verified and not profile.must_change_password:
        return redirect('artisans:verify_email_pending')
    if not profile.organization:
        return redirect('artisans:onboarding')
    org = profile.organization
    if profile.role == 'admin' and org.service_category_id and not org.service_types.exists():
        return redirect('artisans:onboard_services')
    today = timezone.now().date()

    if profile.role == 'admin':
        jobs = Job.objects.filter(organization=org).exclude(
            status='cancelled'
        ).order_by('scheduled_date', 'scheduled_time')[:10]
        today_jobs = Job.objects.filter(
            organization=org,
            scheduled_date=today
        ).exclude(status='cancelled').order_by('scheduled_time')
    elif profile.role == 'technician':
        jobs = Job.objects.filter(
            assigned_to=profile
        ).exclude(status='cancelled').order_by('scheduled_date', 'scheduled_time')[:10]
        today_jobs = Job.objects.filter(
            assigned_to=profile,
            scheduled_date=today
        ).exclude(status='cancelled').order_by('scheduled_time')
    else:
        jobs = []
        today_jobs = []

    context = {
        'profile': profile,
        'jobs': jobs,
        'today_jobs': today_jobs,
        'today': today,
    }
    return render(request, 'artisans/dashboard.html', context)


@login_required
def profile_view(request):
    """View and edit user profile (name, phone, address)."""
    profile = _get_user_profile(request.user)
    if not profile:
        return redirect('artisans:onboarding')
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            profile.phone = form.cleaned_data.get('phone') or ''
            profile.address = form.cleaned_data.get('address') or ''
            profile.save()
            messages.success(request, 'Profile updated.')
            return redirect('artisans:profile')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone': profile.phone,
            'address': profile.address,
        })
    return render(request, 'artisans/profile.html', {
        'profile': profile,
        'form': form,
    })


@login_required
def organization_edit_view(request):
    """Edit organization (name, contact, service category). Admin only."""
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin' or not profile.organization:
        return redirect('artisans:dashboard')
    org = profile.organization
    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            from artisans.services import update_organization_geolocation
            update_organization_geolocation(org)
            messages.success(request, 'Organization updated.')
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('artisans:organization_edit')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = BusinessProfileForm(instance=org)
    return render(request, 'artisans/organization_edit.html', {
        'profile': profile,
        'form': form,
        'organization': org,
    })


# --- Jobs ---

@login_required
def job_list_view(request):
    profile = _get_user_profile(request.user)
    if not profile or not profile.organization:
        return redirect('artisans:onboarding')

    org = profile.organization
    if profile.role == 'admin':
        jobs = Job.objects.filter(organization=org).order_by('-scheduled_date', '-scheduled_time')
    elif profile.role == 'technician':
        jobs = Job.objects.filter(assigned_to=profile).order_by('-scheduled_date', '-scheduled_time')
    else:
        jobs = []

    return render(request, 'artisans/jobs/list.html', {
        'profile': profile,
        'jobs': jobs,
    })


@login_required
def job_create_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    org = profile.organization

    if request.method == 'POST':
        form = JobForm(request.POST)
        form.fields['customer'].queryset = Customer.objects.filter(organization=org)
        form.fields['service_type'].queryset = ServiceType.objects.filter(organization=org)
        form.fields['assigned_to'].queryset = UserProfile.objects.filter(
            organization=org, role='technician'
        )
        if form.is_valid():
            job = form.save(commit=False)
            job.organization = org
            if job.assigned_to:
                job.status = 'assigned'
            job.save()
            messages.success(request, f'Job {job.job_number} created.')
            return redirect('artisans:job_detail', job_id=job.id)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = JobForm()
        form.fields['customer'].queryset = Customer.objects.filter(organization=org)
        form.fields['service_type'].queryset = ServiceType.objects.filter(organization=org)
        form.fields['assigned_to'].queryset = UserProfile.objects.filter(
            organization=org, role='technician'
        )

    return render(request, 'artisans/jobs/form.html', {
        'profile': profile,
        'form': form,
        'title': 'Create Job',
    })


@login_required
def job_detail_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile:
        return redirect('artisans:onboarding')

    # Check access
    if profile.role == 'admin':
        if job.organization != profile.organization:
            messages.error(request, 'Job not found.')
            return redirect('artisans:job_list')
    elif profile.role == 'technician':
        if job.assigned_to != profile:
            messages.error(request, 'Job not found.')
            return redirect('artisans:job_list')
    else:
        return redirect('artisans:dashboard')

    return render(request, 'artisans/jobs/detail.html', {
        'profile': profile,
        'job': job,
    })


@login_required
@require_http_methods(['POST'])
def job_accept_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'technician' or job.assigned_to != profile:
        messages.error(request, 'Invalid request.')
        return redirect('artisans:job_list')
    job.status = 'assigned'
    job.save()
    messages.success(request, f'Job {job.job_number} accepted.')
    return redirect('artisans:job_detail', job_id=job.id)


@login_required
@require_http_methods(['POST'])
def job_reject_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'technician' or job.assigned_to != profile:
        messages.error(request, 'Invalid request.')
        return redirect('artisans:job_list')
    job.assigned_to = None
    job.status = 'scheduled'
    job.save()
    messages.success(request, f'Job {job.job_number} rejected.')
    return redirect('artisans:job_list')


@login_required
@require_http_methods(['POST'])
def job_start_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or job.assigned_to != profile:
        messages.error(request, 'Invalid request.')
        return redirect('artisans:job_list')
    job.status = 'in_progress'
    job.save()
    messages.success(request, f'Job {job.job_number} started.')
    return redirect('artisans:job_detail', job_id=job.id)


@login_required
@require_http_methods(['POST'])
def job_complete_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or job.assigned_to != profile:
        messages.error(request, 'Invalid request.')
        return redirect('artisans:job_list')
    job.status = 'completed'
    job.completed_at = timezone.now()
    job.save()
    messages.success(request, f'Job {job.job_number} completed.')
    return redirect('artisans:job_detail', job_id=job.id)


# --- Checklist & Photos ---

@login_required
def job_add_checklist_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or (job.assigned_to != profile and profile.role != 'admin'):
        messages.error(request, 'Invalid request.')
        return redirect('artisans:job_list')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            order = job.checklist_items.count()
            JobChecklistItem.objects.create(job=job, title=title, order=order)
            messages.success(request, 'Checklist item added.')
    return redirect('artisans:job_detail', job_id=job.id)


@login_required
def job_add_photo_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or job.assigned_to != profile:
        messages.error(request, 'Invalid request.')
        return redirect('artisans:job_list')
    if request.method == 'POST' and request.FILES.get('image'):
        JobPhoto.objects.create(
            job=job,
            image=request.FILES['image'],
            caption=request.POST.get('caption', ''),
            photo_type=request.POST.get('photo_type', 'other'),
        )
        messages.success(request, 'Photo uploaded.')
    return redirect('artisans:job_detail', job_id=job.id)


@login_required
@require_http_methods(['POST'])
def checklist_toggle_view(request, job_id, item_id):
    item = get_object_or_404(JobChecklistItem, id=item_id, job_id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or item.job.assigned_to != profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    item.completed = not item.completed
    item.save()
    return JsonResponse({'completed': item.completed})


# --- Technicians ---

@login_required
def technician_list_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    technicians = UserProfile.objects.filter(
        organization=profile.organization,
        role='technician'
    )
    return render(request, 'artisans/technicians/list.html', {
        'profile': profile,
        'technicians': technicians,
    })


@login_required
def technician_invite_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    org = profile.organization

    if request.method == 'POST':
        form = TechnicianInviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            first_name = form.cleaned_data['first_name'].strip()
            last_name = form.cleaned_data['last_name'].strip()

            # One email per technician: already in this org?
            existing_tech = UserProfile.objects.filter(
                organization=org,
                role='technician',
                user__email__iexact=email,
            ).first()
            if existing_tech:
                messages.error(request, f'{email} is already a technician in your organization.')
                return render(request, 'artisans/technicians/invite.html', {
                    'profile': profile,
                    'form': form,
                })

            # One pending invite per email per org
            pending = TechnicianInvite.objects.filter(
                organization=org,
                email__iexact=email,
                status='pending',
            ).first()
            if pending and timezone.now() <= pending.expires_at:
                messages.error(request, f'An invite has already been sent to {email}.')
                return render(request, 'artisans/technicians/invite.html', {
                    'profile': profile,
                    'form': form,
                })

            # Single user per email (get or create)
            user = User.objects.filter(email__iexact=email).first()
            temporary_password = secrets.token_urlsafe(12)
            if user:
                user.set_password(temporary_password)
                user.first_name = first_name
                user.last_name = last_name
                user.save()
            else:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=temporary_password,
                    first_name=first_name,
                    last_name=last_name,
                )

            tech_profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'organization': org,
                    'role': 'technician',
                    'email_verified': True,
                    'must_change_password': True,
                }
            )
            if not created:
                tech_profile.organization = org
                tech_profile.role = 'technician'
                tech_profile.must_change_password = True
                tech_profile.save()

            token = secrets.token_urlsafe(32)
            invite = TechnicianInvite.objects.create(
                organization=org,
                user=user,
                email=email,
                first_name=first_name,
                last_name=last_name,
                token=token,
                expires_at=timezone.now() + timedelta(days=7),
            )

            invite_url = request.build_absolute_uri(
                reverse('artisans:accept_invite', args=[token])
            )
            try:
                send_technician_invite_email(
                    invite, invite_url, temporary_password, org.name
                )
                messages.success(request, f'Invite sent to {email}. They will receive an email with a link to get started.')
            except Exception:
                messages.warning(request, f'Invite created but email failed. Share this link manually: {invite_url}')
            return redirect('artisans:technician_list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = TechnicianInviteForm()
    return render(request, 'artisans/technicians/invite.html', {
        'profile': profile,
        'form': form,
    })


def technician_accept_invite_view(request, token):
    """One-time login via invite link. Logs technician in and redirects to change password."""
    invite = get_object_or_404(TechnicianInvite, token=token, status='pending')
    if timezone.now() > invite.expires_at:
        invite.status = 'expired'
        invite.save()
        messages.error(request, 'Invite has expired.')
        return redirect('artisans:login')
    if not invite.user:
        messages.error(request, 'Invalid invite.')
        return redirect('artisans:login')
    # Log them in and redirect to change password
    login(request, invite.user)
    invite.status = 'accepted'
    invite.save()
    messages.success(request, f'Welcome to {invite.organization.name}! Please set your password.')
    return redirect('artisans:change_password')


# --- Customers ---

@login_required
def customer_list_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    customers = Customer.objects.filter(organization=profile.organization)
    return render(request, 'artisans/customers/list.html', {
        'profile': profile,
        'customers': customers,
    })


@login_required
def customer_detail_view(request, customer_id):
    """View customer and their invoices (payment status). Admin only."""
    customer = get_object_or_404(Customer, id=customer_id)
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin' or customer.organization != profile.organization:
        return redirect('artisans:dashboard')
    invoices = Invoice.objects.filter(job__customer=customer).select_related('job').order_by('-created_at')
    return render(request, 'artisans/customers/detail.html', {
        'profile': profile,
        'customer': customer,
        'invoices': invoices,
    })


@login_required
def customer_create_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.organization = profile.organization
            customer.save()
            messages.success(request, 'Customer added.')
            return redirect('artisans:customer_list')
    else:
        form = CustomerForm()
    return render(request, 'artisans/customers/form.html', {
        'profile': profile,
        'form': form,
        'title': 'Add Customer',
    })


# --- Service Types ---

@login_required
def service_add_view(request):
    """Add service: choose pre-defined (multi-select) or add manually."""
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    org = profile.organization
    if request.method == 'POST':
        form = OnboardServicesForm(request.POST, category=org.service_category)
        if form.is_valid():
            selected = form.cleaned_data.get('services') or []
            added = 0
            for predefined in selected:
                _, created = ServiceType.objects.get_or_create(
                    organization=org,
                    name=predefined.name,
                    defaults={
                        'description': predefined.description,
                        'base_price': predefined.base_price,
                        'price_type': predefined.price_type,
                        'service_subcategory': predefined.subcategory,
                    },
                )
                if created:
                    added += 1
            if added:
                messages.success(request, f'Added {added} service(s). You can edit pricing from the list.')
            else:
                messages.info(request, 'Selected services were already added.')
            return redirect('artisans:service_type_list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = OnboardServicesForm(category=org.service_category) if org.service_category_id else None
    by_subcategory = []
    if org.service_category_id:
        predefined = list(
            PreDefinedService.objects.filter(category=org.service_category)
            .select_related('subcategory')
            .order_by('name')
        )
        subcategories = ServiceSubcategory.objects.filter(
            category=org.service_category
        ).order_by('name')
        for sub in subcategories:
            svcs = [p for p in predefined if p.subcategory_id == sub.id]
            if svcs:
                by_subcategory.append((sub, svcs))
        other = [p for p in predefined if p.subcategory_id is None]
        if other:
            by_subcategory.append((None, other))
    return render(request, 'artisans/services/add.html', {
        'profile': profile,
        'form': form,
        'category': org.service_category,
        'by_subcategory': by_subcategory,
    })


@login_required
def service_type_list_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    service_types = ServiceType.objects.filter(organization=profile.organization)
    return render(request, 'artisans/services/list.html', {
        'profile': profile,
        'service_types': service_types,
    })


@login_required
def service_type_create_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role != 'admin':
        return redirect('artisans:dashboard')
    org = profile.organization
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST)
        if org.service_category_id:
            form.fields['service_subcategory'].queryset = ServiceSubcategory.objects.filter(category=org.service_category)
        if form.is_valid():
            st = form.save(commit=False)
            st.organization = org
            st.save()
            messages.success(request, 'Service type added.')
            return redirect('artisans:service_type_list')
    else:
        form = ServiceTypeForm()
        if org.service_category_id:
            form.fields['service_subcategory'].queryset = ServiceSubcategory.objects.filter(category=org.service_category)
    return render(request, 'artisans/services/form.html', {
        'profile': profile,
        'form': form,
        'title': 'Add Service Type',
    })


@login_required
def service_type_edit_view(request, service_type_id):
    st = get_object_or_404(ServiceType, id=service_type_id)
    profile = _get_user_profile(request.user)
    if not profile or profile.organization != st.organization:
        return redirect('artisans:dashboard')
    org = profile.organization
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, instance=st)
        if org.service_category_id:
            form.fields['service_subcategory'].queryset = ServiceSubcategory.objects.filter(category=org.service_category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated.')
            return redirect('artisans:service_type_list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ServiceTypeForm(instance=st)
        if org.service_category_id:
            form.fields['service_subcategory'].queryset = ServiceSubcategory.objects.filter(category=org.service_category)
    return render(request, 'artisans/services/form.html', {
        'profile': profile,
        'form': form,
        'title': 'Edit Service',
        'service_type': st,
    })


# --- Invoices ---

@login_required
def invoice_list_view(request):
    profile = _get_user_profile(request.user)
    if not profile or profile.role not in ('admin', 'technician'):
        return redirect('artisans:dashboard')
    org = profile.organization
    invoices = Invoice.objects.filter(job__organization=org).order_by('-created_at')
    return render(request, 'artisans/invoices/list.html', {
        'profile': profile,
        'invoices': invoices,
    })


def _invoice_admin_only(inv, profile):
    """Return True if profile is admin and belongs to invoice's org."""
    return profile and profile.role == 'admin' and inv.job.organization == profile.organization


def _invoice_vat_context(invoice):
    """If org is VAT registered, return dict with subtotal, vat_amount, total_incl. Else return empty dict."""
    org = invoice.job.organization
    if not getattr(org, 'vat_registered', False):
        return {}
    subtotal = invoice.amount
    vat_rate = Decimal('0.15')
    vat_amount = (subtotal * vat_rate).quantize(Decimal('0.01'))
    total_incl = subtotal + vat_amount
    return {
        'vat_registered': True,
        'invoice_subtotal': subtotal,
        'invoice_vat_amount': vat_amount,
        'invoice_total_incl': total_incl,
    }


@login_required
def invoice_detail_view(request, invoice_id):
    """View single invoice. Admin only. Options: PDF, email, mark paid."""
    inv = get_object_or_404(Invoice, id=invoice_id)
    profile = _get_user_profile(request.user)
    if not _invoice_admin_only(inv, profile):
        return redirect('artisans:invoice_list')
    job = inv.job
    context = {
        'profile': profile,
        'invoice': inv,
        'job': job,
        **_invoice_vat_context(inv),
    }
    return render(request, 'artisans/invoices/detail.html', context)


@login_required
def invoice_edit_view(request, invoice_id):
    """Edit invoice. Admin only."""
    inv = get_object_or_404(Invoice, id=invoice_id)
    profile = _get_user_profile(request.user)
    if not _invoice_admin_only(inv, profile):
        return redirect('artisans:invoice_list')
    job = inv.job
    service_type = getattr(job, 'service_type', None) or None
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=inv, job=job, service_type=service_type)
        if form.is_valid():
            inv = form.save(commit=False)
            if service_type:
                duration = form.cleaned_data.get('duration_value')
                if duration is None and service_type.price_type != 'entire_job':
                    duration = job.duration_value
                inv.amount = service_type.calculate_amount(duration)
                inv.duration_value = duration
                if duration is not None and job.duration_value != duration:
                    job.duration_value = duration
                    job.save(update_fields=['duration_value'])
            else:
                inv.amount = form.cleaned_data['amount']
            inv.save()
            messages.success(request, 'Invoice updated.')
            return redirect('artisans:invoice_detail', invoice_id=inv.id)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = InvoiceForm(instance=inv, job=job, service_type=service_type)
    return render(request, 'artisans/invoices/form.html', {
        'profile': profile,
        'form': form,
        'job': job,
        'service_type': service_type,
        'invoice': inv,
        'is_edit': True,
    })


@login_required
def invoice_pdf_view(request, invoice_id):
    """Download invoice as PDF. Admin only."""
    inv = get_object_or_404(Invoice, id=invoice_id)
    profile = _get_user_profile(request.user)
    if not _invoice_admin_only(inv, profile):
        return redirect('artisans:invoice_list')
    html = render_to_string('artisans/invoices/pdf.html', {
        'invoice': inv,
        'job': inv.job,
        **_invoice_vat_context(inv),
    })
    try:
        from io import BytesIO
        from xhtml2pdf import pisa
        result = BytesIO()
        pisa_status = pisa.CreatePDF(html.encode('utf-8'), dest=result, encoding='utf-8')
        if pisa_status.err:
            messages.error(request, 'PDF generation failed.')
            return redirect('artisans:invoice_detail', invoice_id=inv.id)
        result.seek(0)
        response = HttpResponse(result.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice-{inv.job.organization.id}-{inv.id}.pdf"'
        return response
    except ImportError:
        messages.warning(request, 'PDF export requires xhtml2pdf. Install with: pip install xhtml2pdf')
        return redirect('artisans:invoice_detail', invoice_id=inv.id)


@login_required
@require_http_methods(['POST'])
def invoice_email_view(request, invoice_id):
    """Email invoice to customer. Admin only."""
    inv = get_object_or_404(Invoice, id=invoice_id)
    profile = _get_user_profile(request.user)
    if not _invoice_admin_only(inv, profile):
        messages.error(request, 'Invalid request.')
        return redirect('artisans:invoice_list')
    try:
        send_invoice_email(inv)
        messages.success(request, f'Invoice sent to {inv.job.customer.email}.')
    except Exception as e:
        messages.error(request, f'Could not send email: {e}')
    return redirect('artisans:invoice_detail', invoice_id=inv.id)


@login_required
def invoice_create_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    profile = _get_user_profile(request.user)
    if not profile or job.organization != profile.organization:
        return redirect('artisans:dashboard')
    if hasattr(job, 'invoice'):
        messages.info(request, 'Invoice already exists.')
        return redirect('artisans:job_detail', job_id=job.id)
    service_type = getattr(job, 'service_type', None) or None
    if request.method == 'POST':
        form = InvoiceForm(request.POST, job=job, service_type=service_type)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.job = job
            if service_type:
                # Use duration from form for per-hour/per-day, else from job
                duration = form.cleaned_data.get('duration_value')
                if duration is None and service_type.price_type != 'entire_job':
                    duration = job.duration_value
                inv.amount = service_type.calculate_amount(duration)
                inv.duration_value = duration
                if duration is not None and job.duration_value != duration:
                    job.duration_value = duration
                    job.save(update_fields=['duration_value'])
            else:
                inv.amount = form.cleaned_data['amount']
            inv.save()
            messages.success(request, 'Invoice created.')
            return redirect('artisans:invoice_list')
    else:
        if service_type:
            duration = job.duration_value
            amount = service_type.calculate_amount(duration)
            form = InvoiceForm(initial={'amount': amount, 'duration_value': duration}, job=job, service_type=service_type)
        else:
            form = InvoiceForm(initial={'amount': 0}, job=job, service_type=service_type)
    return render(request, 'artisans/invoices/form.html', {
        'profile': profile,
        'form': form,
        'job': job,
        'service_type': service_type,
    })


@login_required
@require_http_methods(['POST'])
def invoice_mark_paid_view(request, invoice_id):
    inv = get_object_or_404(Invoice, id=invoice_id)
    profile = _get_user_profile(request.user)
    if not profile or inv.job.organization != profile.organization:
        messages.error(request, 'Invalid request.')
        return redirect('artisans:invoice_list')
    inv.status = 'paid'
    inv.paid_at = timezone.now()
    inv.save()
    messages.success(request, 'Invoice marked as paid.')
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('artisans:invoice_list')


# --- Customer Booking (Public) ---

def booking_view(request, org_id=None):
    """Public booking form. For MVP, we use org ID or first org."""
    if org_id:
        org = get_object_or_404(Organization, id=org_id)
    else:
        org = Organization.objects.first()
    if not org:
        return render(request, 'artisans/booking/closed.html')

    initial = {}
    if request.GET.get('service'):
        try:
            from artisans.models import ServiceType
            st = ServiceType.objects.get(id=request.GET['service'], organization=org)
            initial['service_type'] = st
        except Exception:
            pass
    if request.method == 'POST':
        form = BookingForm(request.POST, organization=org)
        if form.is_valid():
            # Create customer and job
            customer = Customer.objects.create(
                organization=org,
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data.get('phone', ''),
                address=form.cleaned_data['address'],
                notes=form.cleaned_data.get('notes', ''),
            )
            job = Job.objects.create(
                organization=org,
                customer=customer,
                service_type=form.cleaned_data.get('service_type'),
                address=form.cleaned_data['address'],
                scheduled_date=form.cleaned_data['preferred_date'],
                scheduled_time=form.cleaned_data.get('preferred_time'),
                notes=form.cleaned_data.get('notes', ''),
                status='scheduled',
            )
            try:
                from directory.services import send_booking_notification_to_org
                send_booking_notification_to_org(org, job, request=request)
            except Exception:
                pass
            messages.success(request, 'Booking request submitted! We will contact you shortly.')
            return redirect('artisans:booking_status', job_id=job.id)
    else:
        form = BookingForm(organization=org, initial=initial or None)
    return render(request, 'artisans/booking/form.html', {
        'form': form,
        'organization': org,
    })


def booking_status_view(request, job_id):
    """Customer view of job status (public link)."""
    job = get_object_or_404(Job, id=job_id)
    # For MVP, we allow anyone with the link to view (no auth)
    return render(request, 'artisans/booking/status.html', {'job': job})


def booking_review_view(request, job_id):
    """Leave a review for completed job."""
    job = get_object_or_404(Job, id=job_id)
    if job.status != 'completed':
        messages.error(request, 'Reviews can only be left for completed jobs.')
        return redirect('artisans:booking_status', job_id=job.id)
    if hasattr(job, 'review'):
        messages.info(request, 'You have already reviewed this job.')
        return redirect('artisans:booking_status', job_id=job.id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.create(
                job=job,
                rating=form.cleaned_data['rating'],
                comment=form.cleaned_data.get('comment', ''),
            )
            messages.success(request, 'Thank you for your review!')
            return redirect('artisans:booking_status', job_id=job.id)
    else:
        form = ReviewForm()
    return render(request, 'artisans/booking/review.html', {
        'job': job,
        'form': form,
    })
