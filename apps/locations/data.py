"""
File responsibility: Stores static seed data that is imported by migrations, commands, or serializers.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
import json
from functools import lru_cache
from pathlib import Path

from django.db import transaction


SHARED_LOCATIONS_PATH = Path(__file__).resolve().parents[3] / "shared" / "algeria-locations.json"


def normalize_location_text(value):
    """Handles normalize_location_text, using the declared parameters and returning the expected value or API response."""
    if not value:
        return ""
    text = str(value).replace(",", " ").replace("-", " ")
    return " ".join(text.casefold().split())


@lru_cache(maxsize=1)
def load_algeria_locations():
    """Handles load_algeria_locations, using the declared parameters and returning the expected value or API response."""
    with SHARED_LOCATIONS_PATH.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def build_location_index():
    """Handles build_location_index, using the declared parameters and returning the expected value or API response."""
    dataset = load_algeria_locations()
    wilayas = []
    communes_by_wilaya = {}
    commune_candidates = []

    for wilaya in dataset.get("wilayas", []):
        normalized_wilaya = normalize_location_text(wilaya["name"])
        wilaya_payload = {
            "id": int(wilaya["id"]),
            "code": str(wilaya["code"]),
            "name": wilaya["name"],
            "normalized_name": normalized_wilaya,
        }
        wilayas.append(wilaya_payload)

        commune_rows = []
        for commune in wilaya.get("communes", []):
            normalized_commune = normalize_location_text(commune["name"])
            commune_payload = {
                "id": int(commune["id"]),
                "wilaya_id": wilaya_payload["id"],
                "name": commune["name"],
                "normalized_name": normalized_commune,
            }
            commune_rows.append(commune_payload)
            commune_candidates.append(commune_payload)

        communes_by_wilaya[wilaya_payload["id"]] = sorted(
            commune_rows,
            key=lambda item: (-len(item["normalized_name"]), item["name"]),
        )

    wilayas.sort(key=lambda item: (-len(item["normalized_name"]), item["id"]))
    commune_candidates.sort(key=lambda item: (-len(item["normalized_name"]), item["id"]))

    return {
        "wilayas": wilayas,
        "communes_by_wilaya": communes_by_wilaya,
        "commune_candidates": commune_candidates,
    }


def match_location_from_text(value):
    """Handles match_location_from_text, using the declared parameters and returning the expected value or API response."""
    normalized = normalize_location_text(value)
    if not normalized:
        return None, None

    index = build_location_index()
    wilaya_match = None
    commune_match = None

    for wilaya in index["wilayas"]:
        if wilaya["normalized_name"] and wilaya["normalized_name"] in normalized:
            wilaya_match = wilaya
            break

    if wilaya_match:
        for commune in index["communes_by_wilaya"].get(wilaya_match["id"], []):
            if commune["normalized_name"] and commune["normalized_name"] in normalized:
                commune_match = commune
                break
    else:
        for commune in index["commune_candidates"]:
            if commune["normalized_name"] and commune["normalized_name"] in normalized:
                commune_match = commune
                break

        if commune_match:
            wilaya_match = next(
                (wilaya for wilaya in index["wilayas"] if wilaya["id"] == commune_match["wilaya_id"]),
                None,
            )

    if not wilaya_match:
        return None, None

    return wilaya_match["id"], commune_match["id"] if commune_match else None


def sync_algeria_locations(wilaya_model=None, commune_model=None):
    """Handles sync_algeria_locations, using the declared parameters and returning the expected value or API response."""
    if wilaya_model is None or commune_model is None:
        from apps.locations.models import Commune, Wilaya

        wilaya_model = wilaya_model or Wilaya
        commune_model = commune_model or Commune

    dataset = load_algeria_locations()
    created_wilayas = 0
    created_communes = 0

    with transaction.atomic():
        for wilaya in dataset.get("wilayas", []):
            _, created = wilaya_model.objects.update_or_create(
                id=int(wilaya["id"]),
                defaults={
                    "code": str(wilaya["code"]),
                    "name": wilaya["name"],
                },
            )
            if created:
                created_wilayas += 1

            for commune in wilaya.get("communes", []):
                _, created = commune_model.objects.update_or_create(
                    id=int(commune["id"]),
                    defaults={
                        "wilaya_id": int(wilaya["id"]),
                        "name": commune["name"],
                    },
                )
                if created:
                    created_communes += 1

    return {
        "wilayas": len(dataset.get("wilayas", [])),
        "communes": sum(len(wilaya.get("communes", [])) for wilaya in dataset.get("wilayas", [])),
        "created_wilayas": created_wilayas,
        "created_communes": created_communes,
    }

