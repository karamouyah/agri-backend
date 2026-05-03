from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_product_is_active_and_master_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image_data_url",
            field=models.TextField(blank=True, db_column="ImageDataUrl"),
        ),
    ]
