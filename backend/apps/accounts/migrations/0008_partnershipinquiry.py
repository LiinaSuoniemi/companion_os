# Generated manually 2026-05-10
# Adds the PartnershipInquiry table for B2B partnership inquiries.
# This is for organizations (NGOs, rehab centers, employers, schools,
# healthcare providers) interested in offering Companion OS to the
# people they already serve. Distinct from PilotApplication (individual
# users).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_pilotapplication'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnershipInquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organization_name', models.CharField(max_length=200)),
                ('contact_person', models.CharField(max_length=200)),
                ('role', models.CharField(blank=True, help_text='Job title or role of the contact person (optional).', max_length=200)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, help_text='Optional. Some partners prefer phone for first contact.', max_length=50)),
                ('organization_type', models.CharField(choices=[('ngo', 'Non-governmental organization (NGO)'), ('rehab', 'Rehabilitation or recovery service'), ('healthcare', 'Healthcare provider or clinic'), ('reentry', 'Reentry / corrections program'), ('employer', 'Employer or EAP'), ('school', 'School or university'), ('research', 'Research institution'), ('other', 'Other')], default='other', max_length=20)),
                ('country', models.CharField(choices=[('fi', 'Finland'), ('ee', 'Estonia'), ('other', 'Other')], default='fi', max_length=10)),
                ('target_population', models.TextField(blank=True, help_text='Optional. Who does the organization serve?')),
                ('what_brings_you', models.TextField(help_text='What is the organization looking for? What problem are they trying to solve?')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_conversation', 'In conversation'), ('declined', 'Declined'), ('partnered', 'Partnered')], default='pending', max_length=20)),
                ('notes', models.TextField(blank=True, help_text='Internal notes after a conversation. Not shown to the inquirer.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Partnership inquiry',
                'verbose_name_plural': 'Partnership inquiries',
                'ordering': ['-created_at'],
            },
        ),
    ]
