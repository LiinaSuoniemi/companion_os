# Written manually 2026-05-07
# Adds mode tracking and token count to UsageEvent.
# These fields support the "which modes were used, how many tokens were processed"
# claim on the privacy notice and consent form.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usage', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usageevent',
            name='mode',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='usageevent',
            name='token_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
