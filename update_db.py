import json
import os
import sys
import django
from pathlib import Path

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')
django.setup()

from apps.locations.models import Commune, Wilaya

shared_path = Path(__file__).resolve().parent.parent / "shared" / "algeria-locations.json"
print("Reading from:", shared_path)

with open(shared_path, "r", encoding="utf-8-sig") as f:
    dataset = json.load(f)

for w_data in dataset.get("wilayas", []):
    Wilaya.objects.filter(id=int(w_data["id"])).update(name=w_data["name"])
    for c_data in w_data.get("communes", []):
        Commune.objects.filter(id=int(c_data["id"])).update(name=c_data["name"])

print("Wilayas and Communes names updated successfully!")
