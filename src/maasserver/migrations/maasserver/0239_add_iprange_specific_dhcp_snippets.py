# Generated by Django 2.2.12 on 2021-05-06 19:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("maasserver", "0238_disable_boot_architectures"),
    ]

    operations = [
        migrations.AddField(
            model_name="dhcpsnippet",
            name="iprange",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="maasserver.IPRange",
            ),
        ),
    ]
