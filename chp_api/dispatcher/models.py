import os
import json
import requests
from django.db import models


class ZenodoFile(models.Model):
    zenodo_id = models.CharField(max_length=128)
    file_key = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.zenodo_id}/{self.file_key}'

    def get_record(self):
        return requests.get(f"https://zenodo.org/api/records/{self.zenodo_id}").json()

    def load_file(self, base_url="https://zenodo.org/api/records"):
        r = requests.get(f"{base_url}/{self.zenodo_id}").json()
        files = {f["key"]: f for f in r["files"]}
        f = files[self.file_key]
        download_link = f["links"]["self"]
        file_type = f["type"]
        if file_type == 'json':
            return requests.get(download_link).json()
        raise NotImplementedError(f'File type of: {ext} is not implemented.')

class App(models.Model):
    name = models.CharField(max_length=128)
    curies_zenodo_file = models.OneToOneField(ZenodoFile, on_delete=models.CASCADE, null=True, blank=True, related_name='curies_zenodo_file')
    meta_knowledge_graph_zenodo_file = models.OneToOneField(ZenodoFile, on_delete=models.CASCADE, null=True, blank=True, related_name='meta_knowledge_graph_zenodo_file')

    def __str__(self):
        return self.name

class Template(models.Model):
    app_name = models.CharField(max_length=128)
    subject = models.CharField(max_length=128)
    object = models.CharField(max_length=128)
    predicate = models.CharField(max_length=128)

class TemplateMatch(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    subject = models.CharField(max_length=128)
    object = models.CharField(max_length=128)
    predicate = models.CharField(max_length=128)

class Transaction(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    date_time = models.DateTimeField(auto_now=True)
    query = models.JSONField(default=dict)
    status = models.CharField(max_length=100, default="", null=True)
    versions = models.JSONField(default=dict)
    chp_app = models.ForeignKey(App, on_delete=models.CASCADE, null=True, blank=True)


class Singleton(models.Model):

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(Singleton, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class DispatcherSettings(Singleton):
    trapi_version = models.CharField(max_length=28, default='1.4')

    def __str__(self):
        return 'settings'
