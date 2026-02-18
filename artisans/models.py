"""
Artisan Field Service App - MVP Phase 1 Models
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class ServiceCategory(models.Model):
    """Service category (e.g. Home Repairs, Automotive)."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ServiceSubcategory(models.Model):
    """Subcategory under a category (e.g. Plumbing, Electrical under Home Repairs)."""
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['category', 'slug']]

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class Organization(models.Model):
    """Business/tenant - each artisan business."""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    vat_registered = models.BooleanField(
        default=False,
        help_text='If set, invoices will show 15%% VAT (subtotal + VAT = total).',
    )
    vat_number = models.CharField(max_length=50, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text='Latitude for map and distance (geocode from address or set manually).',
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text='Longitude for map and distance.',
    )
    service_category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organizations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Extended user profile with role and organization."""
    ROLE_CHOICES = [
        ('admin', 'Admin (Business Owner)'),
        ('technician', 'Technician'),
        ('customer', 'Customer'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='members'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)  # For invited technicians
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} ({self.get_role_display()})"


class PreDefinedService(models.Model):
    """Baseline service template from mock-services.json; used for onboarding."""
    PRICE_TYPE_CHOICES = [
        ('per_hour', 'Per hour'),
        ('daily', 'Per day'),
        ('entire_job', 'Entire job (fixed rate)'),
    ]
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='predefined_services',
    )
    subcategory = models.ForeignKey(
        'ServiceSubcategory',
        on_delete=models.CASCADE,
        related_name='predefined_services',
        null=True,
        blank=True,
    )
    provider_name = models.CharField(max_length=100, help_text='e.g. Plumber, Electrician')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_type = models.CharField(
        max_length=20,
        choices=PRICE_TYPE_CHOICES,
        default='entire_job',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['category', 'provider_name', 'name']]

    def __str__(self):
        return f"{self.name} ({self.provider_name})"


class ServiceType(models.Model):
    """Types of services offered by the organization (can come from PreDefinedService)."""
    PRICE_TYPE_CHOICES = [
        ('per_hour', 'Per hour'),
        ('daily', 'Per day'),
        ('entire_job', 'Entire job (fixed rate)'),
    ]
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='service_types'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_type = models.CharField(
        max_length=20,
        choices=PRICE_TYPE_CHOICES,
        default='entire_job',
    )
    service_subcategory = models.ForeignKey(
        'ServiceSubcategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_types',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_amount(self, duration_value=None):
        """Calculate invoice amount from base_price, price_type and duration (from job)."""
        from decimal import Decimal
        if self.price_type == 'entire_job':
            return self.base_price.quantize(Decimal('0.01'))
        duration = duration_value if duration_value is not None else Decimal('0')
        total = self.base_price * duration
        return total.quantize(Decimal('0.01'))

    @property
    def price_type_label(self):
        """Short label for display (e.g. 'per hour', 'per day', 'fixed')."""
        if self.price_type == 'per_hour':
            return 'per hour'
        if self.price_type == 'daily':
            return 'per day'
        return 'fixed rate'

    def __str__(self):
        return f"{self.name}"


class Customer(models.Model):
    """Customer for bookings - can be linked to org or standalone for booking form."""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='customers'
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    """Work order / job."""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.SET_NULL,
        null=True,
        related_name='jobs'
    )
    assigned_to = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_jobs'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    job_number = models.CharField(max_length=50, unique=True, blank=True)
    address = models.TextField()
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    duration_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Hours (if service is per hour) or days (if per day). Used for invoice calculation.',
    )
    notes = models.TextField(blank=True)
    # For technician ETA
    technician_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    technician_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    technician_eta = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_date', '-scheduled_time']

    def save(self, *args, **kwargs):
        if not self.job_number:
            import random
            self.job_number = f"JOB-{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_number}: {self.service_type.name}"


class JobChecklistItem(models.Model):
    """Checklist items for a job."""
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='checklist_items'
    )
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.job.job_number} - {self.title}"


class JobPhoto(models.Model):
    """Before/after photos for jobs."""
    PHOTO_TYPE_CHOICES = [
        ('before', 'Before'),
        ('after', 'After'),
        ('other', 'Other'),
    ]
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.FileField(upload_to='job_photos/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True)
    photo_type = models.CharField(
        max_length=20,
        choices=PHOTO_TYPE_CHOICES,
        default='other'
    )
    created_at = models.DateTimeField(auto_now_add=True)


class JobSignature(models.Model):
    """Customer signature capture."""
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name='signature'
    )
    signature_data = models.TextField()  # Base64 image data
    signed_at = models.DateTimeField(auto_now_add=True)


class Invoice(models.Model):
    """Invoice for completed jobs."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    PAYMENT_PLAN_CHOICES = [
        ('full', 'Full payment'),
        ('partial', 'Partial payment'),
        ('installments', 'Installments'),
    ]
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='ZAR')
    duration_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Hours (if service is per hour) or days (if per day) for this invoice.',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_plan = models.CharField(
        max_length=20,
        choices=PAYMENT_PLAN_CHOICES,
        default='full',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.job.job_number}"


class EmailVerification(models.Model):
    """Email verification token for new signups."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verifications'
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Verification for {self.user.email}"


class TechnicianInvite(models.Model):
    """Invite for technicians to join organization. Creates user with temp password."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
    ]
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invites'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='technician_invites',
        null=True,
        blank=True,
        help_text='User account created for this invite'
    )
    email = models.EmailField()
    first_name = models.CharField(max_length=100, default='')
    last_name = models.CharField(max_length=100, default='')
    token = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'email'],
                condition=models.Q(status='pending'),
                name='unique_pending_invite_per_email_per_org',
            )
        ]

    def __str__(self):
        return f"Invite for {self.email} to {self.organization.name}"


class Review(models.Model):
    """Customer review for completed jobs."""
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name='review'
    )
    rating = models.PositiveSmallIntegerField()  # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
