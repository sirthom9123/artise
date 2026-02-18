from django.contrib import admin
from .models import OrgNotification


@admin.register(OrgNotification)
class OrgNotificationAdmin(admin.ModelAdmin):
    list_display = ('organization', 'notification_type', 'title', 'read', 'created_at')
    list_filter = ('notification_type', 'read')
