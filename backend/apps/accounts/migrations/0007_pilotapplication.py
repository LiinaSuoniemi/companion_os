# Generated manually 2026-05-10
# Adds the PilotApplication table that was missing from migrations.
# Without this migration, POSTing the pilot application form on the
# landing page raises an OperationalError (table does not exist) and
# returns a 500. After this migration runs, the form works.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_remove_user_voice_preference'),
    ]

    operations = [
        migrations.CreateModel(
            name='PilotApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('what_brings_you', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('waitlisted', 'Waitlisted')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
