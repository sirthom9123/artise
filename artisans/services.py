"""
Email sending services for Artisan Field Service App
"""
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


def update_organization_geolocation(organization):
    """
    Geocode the organization's address and save latitude/longitude.
    Uses directory.services.geocode_address (Mapbox). No-op if address is empty.
    """
    if not organization or not getattr(organization, 'address', None) or not str(organization.address).strip():
        return
    try:
        from directory.services import geocode_address
        lat, lng = geocode_address(organization.address)
        if lat is not None and lng is not None:
            organization.latitude = lat
            organization.longitude = lng
            organization.save(update_fields=['latitude', 'longitude', 'updated_at'])
    except Exception:
        pass


def send_verification_email(user, verify_url):
    """Send email verification link to new user."""
    subject = 'Verify your ArtisanApp email'
    message = f'''Hello {user.get_full_name() or user.email},

Please verify your email address by clicking the link below:

{verify_url}

This link will expire in 24 hours.

If you didn't create an account, you can ignore this email.

— ArtisanApp
'''
    print(f'Sending verification email to {user.email} with URL: {verify_url}')
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_technician_invite_email(invite, invite_url, temporary_password, org_name):
    """Send technician invite with one-time login link and temporary password."""
    subject = f'You\'ve been invited to join {org_name} on ArtisanApp'
    message = f'''Hello {invite.user.get_full_name()},

You've been invited to join {org_name} as a technician on ArtisanApp.

Your temporary login credentials:
- Email: {invite.user.email}
- Password: {temporary_password}

Click the link below to get started. You'll be asked to set a new password for security:

{invite_url}

This link will expire in 7 days.

— ArtisanApp
'''
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invite.user.email],
        fail_silently=False,
    )


def send_verification_reminder_email(user, verify_url):
    """Resend verification email."""
    return send_verification_email(user, verify_url)


def send_invoice_email(invoice):
    """Email invoice to the job's customer. Uses HTML body."""
    from decimal import Decimal
    job = invoice.job
    customer = job.customer
    org = job.organization
    service_name = job.service_type.name if job.service_type else 'Service'
    vat_registered = getattr(org, 'vat_registered', False)
    if vat_registered:
        subtotal = invoice.amount
        vat_amount = (subtotal * Decimal('0.15')).quantize(Decimal('0.01'))
        total_incl = subtotal + vat_amount
        amount_line = f'Subtotal (excl. VAT): {invoice.currency} {subtotal}\nVAT (15%): {invoice.currency} {vat_amount}\nTotal (incl. VAT): {invoice.currency} {total_incl}'
        amount_rows = f'''<tr><td style="padding: 4px 12px 4px 0;">Subtotal (excl. VAT)</td><td>{invoice.currency} {subtotal}</td></tr>
<tr><td style="padding: 4px 12px 4px 0;">VAT (15%)</td><td>{invoice.currency} {vat_amount}</td></tr>
<tr><td style="padding: 4px 12px 4px 0;">Total (incl. VAT)</td><td><strong>{invoice.currency} {total_incl}</strong></td></tr>'''
    else:
        amount_line = f'Amount: {invoice.currency} {invoice.amount}'
        amount_rows = f'<tr><td style="padding: 4px 12px 4px 0;">Amount</td><td>{invoice.currency} {invoice.amount}</td></tr>'
    inv_num = f'{org.id}-{invoice.id}'
    subject = f'Invoice {inv_num} – {org.name} – {job.job_number}'
    text = f'''Invoice {inv_num}
{org.name}

Job: {job.job_number}
Customer: {customer.name}
Service: {service_name}
{amount_line}
Payment plan: {invoice.get_payment_plan_display()}
Status: {invoice.get_status_display()}

Thank you.
'''
    html = f'''<!DOCTYPE html><html><body style="font-family: sans-serif; max-width: 600px;">
<h2>Invoice {inv_num}</h2>
<p><strong>{org.name}</strong></p>
<table style="border-collapse: collapse;">
<tr><td style="padding: 4px 12px 4px 0;">Job</td><td>{job.job_number}</td></tr>
<tr><td style="padding: 4px 12px 4px 0;">Customer</td><td>{customer.name}</td></tr>
<tr><td style="padding: 4px 12px 4px 0;">Service</td><td>{service_name}</td></tr>
{amount_rows}
<tr><td style="padding: 4px 12px 4px 0;">Payment plan</td><td>{invoice.get_payment_plan_display()}</td></tr>
<tr><td style="padding: 4px 12px 4px 0;">Status</td><td>{invoice.get_status_display()}</td></tr>
</table>
{f'<p>{invoice.notes}</p>' if invoice.notes else ''}
<p>Thank you.</p>
</body></html>'''
    send_mail(
        subject=subject,
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[customer.email],
        fail_silently=False,
        html_message=html,
    )
