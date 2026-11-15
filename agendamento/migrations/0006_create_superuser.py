import os
from django.db import migrations

def create_admin_user(apps, schema_editor):
    User = apps.get_model("auth", "User")

    username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

    if username and password and not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email or "", password=password)

class Migration(migrations.Migration):

    dependencies = [
        ("agendamento", "0005_consulta_booking_constraints"),
    ]

    operations = [
        migrations.RunPython(create_admin_user),
    ]