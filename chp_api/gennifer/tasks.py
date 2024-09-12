import os
import time
import pandas as pd
import requests 

from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q
from celery import shared_task
from celery.utils.log import get_task_logger
from copy import deepcopy
from nltk.stem import WordNetLemmatizer
from pattern.en import conjugate

from .models import Dataset, Gene, Study, Task, Result, Algorithm, AlgorithmInstance, Annotated, Annotation, Publication
from dispatcher.models import DispatcherSetting

logger = get_task_logger(__name__)
User = get_user_model()
wnl = WordNetLemmatizer()

def normalize_nodes(curies):
    dispatcher_settings = DispatcherSetting.load()
    base_url = dispatcher_settings.sri_node_normalizer_baseurl
    res = requests.post(f'{base_url}/get_normalized_nodes', json={"curies": curies})
    return res.json()

def extract_variant_info(gene_id):
    split = gene_id.split('(')
    gene_id = split[0]
    if len(split) > 1:
        variant_info = split[1][:-1]
    else:
        variant_info = None
    return gene_id, variant_info

def get_chp_preferred_curie(info):
    for _id in info['equivalent_identifiers']:
        if 'ENSEMBL' in _id['identifier']:
            return _id['identifier']
    return None

def save_inference_task(task, status, failed=False):
    task.status = status["task_status"]
    if failed:
        task.message = status["task_result"]
    else:
        # Construct Dataframe from result
        df = pd.DataFrame.from_records(status["task_result"])
        
        # Add task edge weight features
        stats = df["EdgeWeight"].astype(float).describe()
        task.max_task_edge_weight = stats["max"]
        task.min_task_edge_weight = stats["min"]
        task.avg_task_edge_weight = stats["mean"]
        task.std_task_edge_weight = stats["std"]

        # Collect all genes
        genes = set()
        for _, row in df.iterrows():
            gene1, _ = extract_variant_info(row["Gene1"])
            gene2, _ = extract_variant_info(row["Gene2"])
            genes.add(gene1)
            genes.add(gene2)

        # Normalize
        res = normalize_nodes(list(genes))
        
        # Now Extract results
        for _, row in df.iterrows():
            # Construct Gene Objects
            gene1, variant_info1 = extract_variant_info(row["Gene1"])
            gene2, variant_info2 = extract_variant_info(row["Gene2"])
            try:
                gene1_name = res[gene1]["id"]["label"]
                gene1_chp_preferred_curie = get_chp_preferred_curie(res[gene1])
            except TypeError:
                gene1_name = 'Not found in SRI Node Normalizer.'
                gene1_chp_preferred_curie = None
            except KeyError:
                _, gene1_name = res[gene1]["id"]["identifier"].split(':')
                gene1_chp_preferred_curie = get_chp_preferred_curie(res[gene1])
            try:
                gene2_name = res[gene2]["id"]["label"]
                gene2_chp_preferred_curie = get_chp_preferred_curie(res[gene2])
            except TypeError:
                gene2_name = 'Not found in SRI Node Normalizer.'
                gene2_chp_preferred_curie = None
            except KeyError:
                _, gene2_name = res[gene2]["id"]["identifier"].split(':')
                gene2_chp_preferred_curie = get_chp_preferred_curie(res[gene2])
            gene1_obj, created = Gene.objects.get_or_create(
                    name=gene1_name,
                    curie=gene1,
                    variant=variant_info1,
                    chp_preferred_curie=gene1_chp_preferred_curie,
                    )
            if created:
                gene1_obj.save()
            gene2_obj, created = Gene.objects.get_or_create(
                    name=gene2_name,
                    curie=gene2,
                    variant=variant_info2,
                    chp_preferred_curie=gene2_chp_preferred_curie,
                    )
            if created:
                gene2_obj.save()
            # Construct and save Result
            result, created = Result.objects.get_or_create(
                    tf=gene1_obj,
                    target=gene2_obj,
                    edge_weight=row["EdgeWeight"],
                    task=task,
                    user=task.user,
                    )
            if created:
                result.save()
    task.save()
    # Collect all result PKs for this task
    result_pks = [res.pk for res in task.results.all()]
    # Send to annotation worker
    create_annotations_task(result_pks, task.algorithm_instance.algorithm.directed)
    return True

def get_status(algo, task_id, url=None):
    if url:
        return requests.get(f'{url}/status/{task_id}', headers={'Cache-Control': 'no-cache'}).json()
    return requests.get(f'{algo.url}/status/{task_id}', headers={'Cache-Control': 'no-cache'}).json()

def return_saved_task(tasks, user):
    task = tasks[0]
    # Copy task results
    results = deepcopy(task.results)
    # Create a new task that is a duplicate but assign to this user.
    task.pk = None
    task.results = None
    task.save()

    # Now go through and assign all results to this task and user.
    for result in results:
        result.pk = None
        result.task = task
        result.user = user
        result.save()
    return True

def construct_annotation_request(results, directed):
    data = []
    for result in results:
        data.append({
            "source": {
                "id": result.tf.curie,
                "name": result.tf.name,
            },
            "target": {
                "id": result.target.curie,
                "name": result.target.name,
            },
            "result_pk": result.pk,
            })
    return {"data": data, "directed": directed}

def make_tr_formatted_relation(
        predicate,
        qualified_predicate,
        object_modifier,
        object_aspect,
        ):
    formatted_str = predicate.replace('biolink:', '').replace('_', ' ')
    if qualified_predicate:
        qp = wnl.lemmatize(qualified_predicate.replace('biolink:', ''), 'v')
        try:
            qp = conjugate(qp, 'part')
        except RuntimeError:
            # This function fails the first time its run so just run again, see: https://github.com/clips/pattern/issues/295
            qp = conjugate(qp, 'part')
            pass
        formatted_str += f' By {qp}'
    if object_modifier:
        om = object_modifier.replace('_', ' ')
        formatted_str += f' {om}'
    if object_aspect:
        oa = object_aspect.replace('_', ' ')
        formatted_str += f' {oa}'
    return formatted_str.title()

def save_annotation_task(status, failed=False):
    if failed:
        print('Annotation Failed')
        return
    annotations = status["task_result"]
    for annotation in annotations:
        result = Result.objects.get(pk=annotation["result_pk"])
        if annotation["justification"]:
            # Make OpenAI Annotation
            oai_justification = Annotation.objects.create(
                    type='openai',
                    oai_justification=annotation["justification"]
                    )
            oai_annotated = Annotated.objects.create(
                    result=result,
                    annotation=oai_justification,
                    )
            oai_justification.save()
            oai_annotated.save()
        # Make translator annotations
        for tr_result in annotation["results"]:
            tr_annotation = Annotation.objects.create(
                    type='translator',
                    tr_formatted_relation_string=make_tr_formatted_relation(
                        tr_result["predicate"],
                        tr_result["qualified_predicate"],
                        tr_result["object_modifier"],
                        tr_result["object_aspect"],
                    ),
                    tr_predicate= tr_result["predicate"],
                    tr_qualified_predicate=tr_result["qualified_predicate"],
                    tr_object_modifier=tr_result["object_modifier"],
                    tr_object_aspect=tr_result["object_aspect"],
                    tr_resource_id=tr_result["resource_id"],
                    tr_primary_source=tr_result["primary_source"],
                    )
            tr_annotation.save()
            tr_annotated = Annotated.objects.create(
                result=result,
                annotation=tr_annotation,
            )
            tr_annotated.save()
    print('Saved annotations.')
    return

@shared_task(name="create_annotations_task")
def create_annotations_task(result_pks, directed):
    results = Result.objects.filter(pk__in = result_pks)
    results_to_be_annotated = []
    # First go through results and ensure we haven't already made an annotation request
    for result in results:
        matched_annotations = [a.annotation for a in Annotated.objects.filter(
            result__tf__curie=result.tf.curie,
            result__target__curie=result.target.curie,
            result__task__algorithm_instance__algorithm__directed=result.task.algorithm_instance.algorithm.directed
            )]
        if len(matched_annotations) == 0:
            results_to_be_annotated.append(result)
            continue
        for ma in matched_annotations:
            annotated = Annotated.objects.create(
                    annotation = ma,
                    result=result,
                    )
            annotated.save()
    # Construct annotation service request
    r = construct_annotation_request(results_to_be_annotated, directed)
    # Send to annotation service and wait
    annotate_id = requests.post('http://annotator:5000/run', json=r).json()["task_id"]
    # Get initial status
    status = get_status(None, annotate_id, url='http://annotator:5000')

    # Enter a loop to keep checking back in and populate the task once it has completed.
    #TODO: Not sure if this is best practice
    while True:
        # Check in every 10 seconds
        time.sleep(10)
        status = get_status(None, annotate_id, url='http://annotator:5000')
        if status["task_status"] == 'SUCCESS':
            return save_annotation_task(status)
        if status["task_status"] == "FAILURE":
            return save_annotation_task(status, failed=True)

@shared_task(name="create_gennifer_task")
def create_task(task_pk):
    # Get task
    task = Task.objects.get(pk=task_pk)
    algo = task.algorithm_instance.algorithm
    user = task.user
    ## Get algorithm obj
    #algo = Algorithm.objects.get(name=algorithm_name)

    ## Get or create a new algorithm instance based on the hyperparameters
    #if not hyperparameters:
    #    algo_instance, algo_instance_created = AlgorithmInstance.objects.get_or_create(
    #            algorithm=algo,
    #            hyperparameters__isnull=True,
    #            )
    #else:
    #    algo_instance, algo_instance_created = AlgorithmInstance.objects.get_or_create(
    #            algorithm=algo,
    #            hyperparameters=hyperparameters,
    #            )

    # Get User obj
    #user = User.objects.get(pk=user_pk)
    
    # Get Study obj
    #study = Study.objects.get(pk=study_pk)

    # Initialize dataset instance
    #dataset, dataset_created = Dataset.objects.get_or_create(
    #        zenodo_id=zenodo_id,
    #        user=user,
    #        )

    #if dataset_created:
    #    dataset.save()

    #if not algo_instance_created and not dataset_created:
    #    # This means we've already run the task. So let's just return that and not bother our workers.
    #    tasks = Task.objects.filter(
    #            algorithm_instance=algo_instance,
    #            dataset=dataset,
    #            status='SUCCESS',
    #            )
    #    #TODO: Probably should add some timestamp handling here 
    #    if len(studies) > 0:
    #        return_saved_task(tasks, user)
    
    # Create Hyperparameter serialization
    hyperparameters = {}
    for h in task.algorithm_instance.hyperparameters.all():
        hyperparameters[h.hyperparameter.name] = h.get_value()

    # Send to gennifer app
    gennifer_request = {
            "zenodo_id": task.dataset.zenodo_id,
            "hyperparameters": hyperparameters,
            }
    task_id = requests.post(f'{algo.url}/run', json=gennifer_request).json()["task_id"]

    logger.info(f'TASK_ID: {task_id}')

    # Get initial status
    status = get_status(algo, task_id)
    
    
    #task = Task.objects.create(
    #        algorithm_instance=algo_instance,
    #        user=user,
    #        dataset=dataset,
    #        status=status["task_status"],
    #        study=study,
    #        )
    # Save initial task
    #task.save()

    # Enter a loop to keep checking back in and populate the task once it has completed.
    #TODO: Not sure if this is best practice
    while True:
        # Check in every 2 seconds
        time.sleep(5)
        status = get_status(algo, task_id)
        print(status)
        if status["task_status"] == 'SUCCESS':
            return save_inference_task(task, status)
        if status["task_status"] == "FAILURE":
            return save_inference_task(task, status, failed=True)
        if status["task_status"] != task.status:
            task.status = status["task_status"]
            task.save()
