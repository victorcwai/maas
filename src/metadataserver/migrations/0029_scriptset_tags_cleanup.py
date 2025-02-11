# Generated by Django 2.2.12 on 2022-05-24 07:07

from textwrap import dedent

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("metadataserver", "0028_scriptset_requested_scripts_rename"),
    ]

    operations = [
        migrations.RunSQL(
            dedent(
                """\
                UPDATE metadataserver_scriptset
                SET tags = array(
                  SELECT unnest(tags) INTERSECT
                  SELECT DISTINCT unnest(tags)
                    FROM metadataserver_script
                  )
                """
            )
        ),
    ]
