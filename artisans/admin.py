from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import (
    Organization,
    UserProfile,
    ServiceCategory,
    ServiceSubcategory,
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
    EmailVerification,
)
from import_export.admin import ImportExportModelAdmin


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ServiceSubcategory)
class ServiceSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category')
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PreDefinedService)
class PreDefinedServiceAdmin(ImportExportModelAdmin):
    list_display = ('name', 'provider_name', 'category', 'subcategory', 'base_price', 'price_type')
    list_filter = ('category',)


@admin.register(ServiceType)
class ServiceTypeAdmin(ImportExportModelAdmin):
    list_display = ('name', 'organization', 'service_subcategory', 'base_price', 'price_type')


@admin.register(Organization)
class OrganizationAdmin(ImportExportModelAdmin):
    list_display = ('name', 'service_category', 'contact_email', 'created_at')


@admin.register(UserProfile)
class UserProfileAdmin(ImportExportModelAdmin):
    list_display = ('user', 'organization', 'role', 'phone')
    list_filter = ('role',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'organization')
    list_filter = ('organization',)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('job_number', 'service_type', 'customer', 'status', 'scheduled_date', 'duration_value', 'assigned_to')
    list_filter = ('status', 'organization')


@admin.register(JobChecklistItem)
class JobChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'job', 'completed')


@admin.register(JobPhoto)
class JobPhotoAdmin(admin.ModelAdmin):
    list_display = ('job', 'photo_type', 'created_at')


@admin.register(JobSignature)
class JobSignatureAdmin(admin.ModelAdmin):
    list_display = ('job', 'signed_at')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('job', 'amount', 'duration_value', 'status', 'created_at')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at')


@admin.register(TechnicianInvite)
class TechnicianInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'organization', 'status', 'expires_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('job', 'rating', 'created_at')
