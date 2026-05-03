from django.db import migrations

from apps.locations.data import sync_algeria_locations


def seed_locations(apps, schema_editor):
    Wilaya = apps.get_model("locations", "Wilaya")
    Commune = apps.get_model("locations", "Commune")
    sync_algeria_locations(Wilaya, Commune)


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_locations, migrations.RunPython.noop),
    ]
