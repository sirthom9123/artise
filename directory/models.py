"""
Directory app: in-app notifications for org (e.g. new booking).
Push can be implemented later via Web Push or FCM; for now we store and email.
"""
from django.conf import settings
from django.db import models


class OrgNotification(models.Model):
    """Notification for an organization (e.g. new booking). Shown in-app; email sent separately."""
    TYPE_CHOICES = [
        ('booking', 'New booking'),
        ('other', 'Other'),
    ]
    organization = models.ForeignKey(
        'artisans.Organization',
        on_delete=models.CASCADE,
        related_name='directory_notifications',
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='booking')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    # Link to related object (e.g. job id)
    link_url = models.CharField(max_length=500, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.organization.name}: {self.title}"
