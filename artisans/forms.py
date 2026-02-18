"""
Artisan Field Service App - MVP Phase 1 Forms
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import (
    Organization,
    UserProfile,
    ServiceCategory,
    PreDefinedService,
    ServiceType,
    Customer,
    Job,
    JobChecklistItem,
    JobPhoto,
    JobSignature,
    Invoice,
    TechnicianInvite,
    Review,
)


class SignUpForm(UserCreationForm):
    """Business owner sign up."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['placeholder'] = 'Email address'
        self.fields['first_name'].widget.attrs['placeholder'] = 'First name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Last name'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class ProfileForm(forms.Form):
    """User account + profile (name, phone, address)."""
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)


class BusinessProfileForm(forms.ModelForm):
    """Business/organization profile (includes service category)."""
    class Meta:
        model = Organization
        fields = ('name', 'address', 'contact_email', 'contact_phone', 'vat_registered', 'vat_number', 'service_category')


class OnboardServicesForm(forms.Form):
    """Select which predefined services to add to the organization."""
    services = forms.ModelMultipleChoiceField(
        queryset=PreDefinedService.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, category=None, **kwargs):
        super().__init__(*args, **kwargs)
        if category:
            self.fields['services'].queryset = PreDefinedService.objects.filter(
                category=category
            ).order_by('provider_name', 'name')


class TechnicianInviteForm(forms.Form):
    """Invite a technician - collects email, first name, last name. Creates user with random password."""
    email = forms.EmailField()
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)


class ServiceTypeForm(forms.ModelForm):
    """Add/edit service type (pricing, price_type, etc.)."""
    class Meta:
        model = ServiceType
        fields = ('name', 'service_subcategory', 'description', 'base_price', 'price_type')


class CustomerForm(forms.ModelForm):
    """Create/edit customer."""
    class Meta:
        model = Customer
        fields = ('name', 'email', 'phone', 'address', 'notes')


class JobForm(forms.ModelForm):
    """Create/edit job."""
    class Meta:
        model = Job
        fields = (
            'customer', 'service_type', 'assigned_to', 'address',
            'scheduled_date', 'scheduled_time', 'duration_value', 'notes'
        )
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'duration_value': forms.NumberInput(attrs={'step': '0.5', 'min': '0', 'placeholder': 'e.g. 2'}),
        }
        help_texts = {
            'duration_value': 'Hours (if service is per hour) or days (if per day). Used to calculate invoice amount.',
        }


class JobChecklistItemForm(forms.ModelForm):
    """Add checklist item to job."""
    class Meta:
        model = JobChecklistItem
        fields = ('title', 'order')


class JobPhotoForm(forms.ModelForm):
    """Upload job photo."""
    class Meta:
        model = JobPhoto
        fields = ('image', 'caption', 'photo_type')


class InvoiceForm(forms.ModelForm):
    """Create/edit invoice. Amount is calculated from job service type and job duration."""
    duration_value = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=8,
        decimal_places=2,
        label='Duration (hours or days)',
        help_text='Required for per-hour/per-day services. Used to calculate amount (base price × duration).',
    )

    class Meta:
        model = Invoice
        fields = ('amount', 'currency', 'payment_plan', 'notes')

    def __init__(self, *args, job=None, service_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._job = job
        self._service_type = service_type
        instance = kwargs.get('instance')
        if job and service_type and service_type.price_type != 'entire_job':
            self.fields['duration_value'].required = True
            if not args:
                if instance and getattr(instance, 'duration_value', None) is not None:
                    self.fields['duration_value'].initial = instance.duration_value
                elif job and getattr(job, 'duration_value', None) is not None:
                    self.fields['duration_value'].initial = job.duration_value
        else:
            self.fields['duration_value'].widget = forms.HiddenInput()


class ReviewForm(forms.ModelForm):
    """Customer review form."""
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.Select(choices=[(i, f'{i} stars') for i in range(1, 6)]),
        }


class BookingForm(forms.Form):
    """Public customer booking form."""
    name = forms.CharField(max_length=200)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea)
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.none(),
        required=False
    )
    preferred_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    preferred_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False
    )
    notes = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['service_type'].queryset = ServiceType.objects.filter(
                organization=organization
            )
