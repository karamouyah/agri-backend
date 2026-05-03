from django.db import migrations

from apps.locations.data import match_location_from_text


def backfill_order_locations(apps, schema_editor):
    Order = apps.get_model("orders", "Order")

    for order in Order.objects.select_related("buyer", "farmer"):
        update_fields = []

        if not order.delivery_wilaya_id or not order.delivery_commune_id:
            buyer = order.buyer
            delivery_wilaya_id = buyer.wilaya_id
            delivery_commune_id = buyer.commune_id
            if not delivery_wilaya_id or not delivery_commune_id:
                delivery_wilaya_id, delivery_commune_id = match_location_from_text(order.delivery_address)

            if delivery_wilaya_id and not order.delivery_wilaya_id:
                order.delivery_wilaya_id = delivery_wilaya_id
                update_fields.append("delivery_wilaya")
            if delivery_commune_id and not order.delivery_commune_id:
                order.delivery_commune_id = delivery_commune_id
                update_fields.append("delivery_commune")

        if not order.pickup_wilaya_id or not order.pickup_commune_id:
            farm = order.farmer.farms.order_by("id").first()
            pickup_wilaya_id = getattr(farm, "wilaya_id", None)
            pickup_commune_id = getattr(farm, "commune_id", None)
            if not pickup_wilaya_id or not pickup_commune_id:
                pickup_wilaya_id, pickup_commune_id = match_location_from_text(order.pickup_address)

            if pickup_wilaya_id and not order.pickup_wilaya_id:
                order.pickup_wilaya_id = pickup_wilaya_id
                update_fields.append("pickup_wilaya")
            if pickup_commune_id and not order.pickup_commune_id:
                order.pickup_commune_id = pickup_commune_id
                update_fields.append("pickup_commune")

        if update_fields:
            order.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_order_delivery_commune_order_delivery_wilaya_and_more"),
        ("users", "0003_backfill_structured_locations"),
    ]

    operations = [
        migrations.RunPython(backfill_order_locations, migrations.RunPython.noop),
    ]
