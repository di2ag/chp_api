# Generated by Django 4.2.1 on 2023-05-29 23:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dispatcher', '0008_dispatchersettings_sri_node_normalizer_baseurl'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='DispatcherSettings',
            new_name='DispatcherSetting',
        ),
    ]