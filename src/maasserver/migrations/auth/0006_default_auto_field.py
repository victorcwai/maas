# Generated by Django 3.2.12 on 2022-06-13 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0005_auto_20200626_1049"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="permission",
            options={
                "ordering": [
                    "content_type__app_label",
                    "content_type__model",
                    "codename",
                ],
                "verbose_name": "permission",
                "verbose_name_plural": "permissions",
            },
        ),
        migrations.AlterField(
            model_name="user",
            name="first_name",
            field=models.CharField(
                blank=True, max_length=150, verbose_name="first name"
            ),
        ),
    ]
