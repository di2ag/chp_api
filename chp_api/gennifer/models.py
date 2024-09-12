import requests
import uuid

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class UserAnalysisSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_data = models.JSONField()
    is_saved = models.BooleanField(default=False)

    def update_session_data(self, new_data):
        self.session_data.update(new_data)
        self.save()

    def __str__(self):
        return self.name

class Algorithm(models.Model):
    name = models.CharField(max_length=128)
    url = models.CharField(max_length=128)
    edge_weight_description = models.TextField(null=True, blank=True)
    edge_weight_type = models.CharField(max_length=128, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    directed = models.BooleanField()

    def __str__(self):
        return self.name


class AlgorithmInstance(models.Model):
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, related_name='instances')

    def __str__(self):
        if self.hyperparameters:
            hypers = tuple([f'{h}' for h in self.hyperparameters.all()])
        else:
            hypers = '()'
        return f'{self.algorithm.name}{hypers}'


class Hyperparameter(models.Model):
    INT = "int"
    BOOL = "bool"
    STR = "str"
    FLOAT = "float"
    TYPE_CHOICES = (
            (INT, "Integer"),
            (BOOL, "Boolean"),
            (STR, "String"),
            (FLOAT, "Float"),
            )
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=5, choices=TYPE_CHOICES, default=FLOAT)
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, related_name='hyperparameters')
    info = models.TextField(null=True, blank=True)

    def get_type(self):
        known_types = {
                "int": int,
                "bool": bool,
                "str": str,
                "float": float,
                }
        return known_types[self.type]
    
    def __str__(self):
        return self.name


class HyperparameterInstance(models.Model):
    hyperparameter = models.ForeignKey(Hyperparameter, on_delete=models.CASCADE, related_name='instances')
    value_str = models.CharField(max_length=128)
    algorithm_instance = models.ForeignKey(AlgorithmInstance, on_delete=models.CASCADE, related_name='hyperparameters')

    def get_value(self):
        return self.hyperparameter.get_type()(self.value_str)

    def __str__(self):
        return f'{self.hyperparameter.name}={self.value_str}'

class Dataset(models.Model):
    title = models.CharField(max_length=128)
    zenodo_id = models.CharField(max_length=128, primary_key=True)
    doi = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    public = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        import re
        
        CLEANR = re.compile('<.*?>')

        info = self.get_record()
        if 'status' in info and 'message' in info and len(info) == 2:
            # This means that retrieval failed
            raise ValueError(f'Could not retrieve zenodo record {self.zenodo_id}. Failed with message: {info["message"]}')
        self.doi = info["doi"]
        self.description = re.sub(CLEANR, '', info["metadata"]["description"])
        self.title = re.sub(CLEANR, '', info["metadata"]["title"])

        super(Dataset, self).save(*args, **kwargs)

    def get_record(self):
        return requests.get(f"https://zenodo.org/api/records/{self.zenodo_id}").json()

    def __str__(self):
        return f'zenodo:{self.zenodo_id}'

class Gene(models.Model):
    name = models.CharField(max_length=128)
    curie = models.CharField(max_length=128)
    variant = models.TextField(null=True, blank=True)
    chp_preferred_curie = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return self.name

class Study(models.Model):
    class Meta:
        verbose_name_plural = "studies"

    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='studies')

    def __str__(self):
        return self.name


class Task(models.Model):
    algorithm_instance = models.ForeignKey(AlgorithmInstance, on_delete=models.CASCADE, related_name='tasks')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='tasks')
    timestamp = models.DateTimeField(auto_now_add=True)
    # Study characteristics for all edge weights in a given study over a dataset
    max_task_edge_weight = models.FloatField(null=True)
    min_task_edge_weight = models.FloatField(null=True)
    avg_task_edge_weight = models.FloatField(null=True)
    std_task_edge_weight = models.FloatField(null=True)
    is_public = models.BooleanField(default=False)
    status = models.CharField(max_length=10)
    error_message = models.TextField(null=True, blank=True)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='tasks')

    def __str__(self):
        return f'{self.algorithm_instance} on {self.dataset.zenodo_id}'


class Result(models.Model):
    # Stands for transcription factor
    tf = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name='inference_result_tf')
    # Target is the gene that is regulated by the transcription factor
    target = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name='inference_result_target')
    edge_weight = models.FloatField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='results')
    is_public = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='results')
    annotations = models.ManyToManyField('Annotation', through='Annotated')

    def __str__(self):
        return f'{self.tf}:{self.tf.curie} -> regulates -> {self.target}:{self.target.curie}'

class Annotation(models.Model):
    # Type of annotation
    TYPE_CHOICES = (
            ('openai', "OpenAI"),
            ('translator', "Translator"),
            )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, default='translator')
    timestamp = models.DateTimeField(auto_now_add=True)
    results = models.ManyToManyField('Result', through='Annotated')
    # Translator fields
    tr_formatted_relation_string = models.CharField(max_length=256, null=True, blank=True)
    tr_predicate = models.CharField(max_length=128, null=True, blank=True)
    tr_qualified_predicate = models.CharField(max_length=128, null=True, blank=True)
    tr_object_modifier = models.CharField(max_length=128, null=True, blank=True)
    tr_object_aspect = models.CharField(max_length=128, null=True, blank=True)
    tr_resource_id = models.CharField(max_length=128, null=True, blank=True)
    tr_primary_source = models.CharField(max_length=128, null=True, blank=True)
    # OpenAI fields
    oai_justification = models.TextField(null=True, blank=True)


class Publication(models.Model):
    curie = models.CharField(max_length=128)
    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE, related_name='publications')  
    
class Annotated(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE)
    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE)

