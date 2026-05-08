from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_impactsurvey_country'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='voice_preference',
        ),
    ]
