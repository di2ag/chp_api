# Generated by Django 4.2 on 2023-04-18 19:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dispatcher', '0004_app_alter_transaction_chp_app'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZenodoFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zenodo_id', models.CharField(max_length=128)),
                ('file_key', models.CharField(max_length=128)),
            ],
        ),
        migrations.RemoveField(
            model_name='app',
            name='curies_file',
        ),
        migrations.RemoveField(
            model_name='app',
            name='meta_knowledge_graph_file',
        ),
        migrations.AddField(
            model_name='app',
            name='curies_zenodo_file',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='curies_zenodo_file', to='dispatcher.zenodofile'),
        ),
        migrations.AddField(
            model_name='app',
            name='meta_knowledge_graph_zenodo_file',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='meta_knowledge_graph_zenodo_file', to='dispatcher.zenodofile'),
        ),
    ]
