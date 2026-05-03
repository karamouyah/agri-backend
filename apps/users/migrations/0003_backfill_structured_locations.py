from django.db import migrations

from apps.locations.data import load_algeria_locations, match_location_from_text, normalize_location_text


def backfill_structured_locations(apps, schema_editor):
    Buyer = apps.get_model("users", "Buyer")
    Farm = apps.get_model("users", "Farm")
    Transporter = apps.get_model("users", "Transporter")
    Wilaya = apps.get_model("locations", "Wilaya")
    through_model = Transporter.delivery_wilayas.through

    dataset = load_algeria_locations()
    wilaya_name_index = [
        (normalize_location_text(item["name"]), int(item["id"]))
        for item in dataset.get("wilayas", [])
    ]
    wilaya_name_index.sort(key=lambda item: -len(item[0]))

    for farm in Farm.objects.all():
        wilaya_id, commune_id = match_location_from_text(farm.location)
        update_fields = []
        if wilaya_id and not farm.wilaya_id:
            farm.wilaya_id = wilaya_id
            update_fields.append("wilaya")
        if commune_id and not farm.commune_id:
            farm.commune_id = commune_id
            update_fields.append("commune")
        if update_fields:
            farm.save(update_fields=update_fields)

    for buyer in Buyer.objects.select_related("person"):
        wilaya_id, commune_id = match_location_from_text(buyer.person.address)
        update_fields = []
        if wilaya_id and not buyer.wilaya_id:
            buyer.wilaya_id = wilaya_id
            update_fields.append("wilaya")
        if commune_id and not buyer.commune_id:
            buyer.commune_id = commune_id
            update_fields.append("commune")
        if update_fields:
            buyer.save(update_fields=update_fields)

    for transporter in Transporter.objects.select_related("person"):
        update_fields = []
        if transporter.capacity and not transporter.max_load_kg:
            transporter.max_load_kg = transporter.capacity
            update_fields.append("max_load_kg")

        coverage_ids = set()
        coverage_text = " ".join(
            [segment for segment in [transporter.service_area, transporter.person.address] if segment]
        )
        normalized_coverage = normalize_location_text(coverage_text)

        for normalized_name, wilaya_id in wilaya_name_index:
            if normalized_name and normalized_name in normalized_coverage:
                coverage_ids.add(wilaya_id)

        matched_wilaya_id, _matched_commune_id = match_location_from_text(coverage_text)
        if matched_wilaya_id:
            coverage_ids.add(matched_wilaya_id)

        if coverage_ids:
            names = list(
                Wilaya.objects.filter(id__in=coverage_ids).order_by("id").values_list("name", flat=True)
            )
            next_service_area = ", ".join(names)
            if next_service_area and transporter.service_area != next_service_area:
                transporter.service_area = next_service_area
                update_fields.append("service_area")

            existing_ids = set(
                through_model.objects.filter(transporter_id=transporter.id).values_list("wilaya_id", flat=True)
            )
            for wilaya_id in coverage_ids - existing_ids:
                through_model.objects.create(transporter_id=transporter.id, wilaya_id=wilaya_id)

        if update_fields:
            transporter.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0002_seed_algeria_locations"),
        ("users", "0002_buyer_commune_buyer_wilaya_farm_commune_farm_wilaya_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_structured_locations, migrations.RunPython.noop),
    ]
