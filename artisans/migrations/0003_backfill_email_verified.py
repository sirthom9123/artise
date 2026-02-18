# Generated data migration - mark existing users as email verified
from django.db import migrations


def backfill_email_verified(apps, schema_editor):
    UserProfile = apps.get_model('artisans', 'UserProfile')
    UserProfile.objects.filter(email_verified=False).update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('artisans', '0002_technicianinvite_first_name_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_email_verified, migrations.RunPython.noop),
    ]
