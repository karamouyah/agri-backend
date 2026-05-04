# Generated migration for PDF file field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_alter_verificationdocument_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='verificationdocument',
            name='pdf_file',
            field=models.FileField(blank=True, help_text='Auto-generated PDF version of the document', null=True, upload_to='verification_documents_pdf/%Y/%m/'),
        ),
    ]
