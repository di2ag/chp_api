# Generated by Django 4.2.1 on 2023-06-04 02:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gennifer', '0005_gene_chp_preferred_curie'),
    ]

    operations = [
        migrations.AddField(
            model_name='algorithm',
            name='directed',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
