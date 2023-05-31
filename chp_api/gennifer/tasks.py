import os
import time
import pandas as pd
import requests 

from django.db import transaction
from django.contrib.auth.models import User
from celery import shared_task
from celery.utils.log import get_task_logger
from copy import deepcopy

from .models import Dataset, Gene, InferenceStudy, InferenceResult, Algorithm, AlgorithmInstance
from dispatcher.models import DispatcherSetting

logger = get_task_logger(__name__)

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

def save_inference_study(study, status, failed=False):
    study.status = status["task_status"]
    if failed:
        study.message = status["task_result"]
    else:
        # Construct Dataframe from result
        df = pd.DataFrame.from_records(status["task_result"])
        
        # Add study edge weight features
        stats = df["EdgeWeight"].astype(float).describe()
        study.max_study_edge_weight = stats["max"]
        study.min_study_edge_weight = stats["min"]
        study.avg_study_edge_weight = stats["mean"]
        study.std_study_edge_weight = stats["std"]

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
            try:
                gene2_name = res[gene2]["id"]["label"]
                gene2_chp_preferred_curie = get_chp_preferred_curie(res[gene2])
            except TypeError:
                gene2_name = 'Not found in SRI Node Normalizer.'
                gene2_chp_preferred_curie = None
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
            result = InferenceResult.objects.create(
                    tf=gene1_obj,
                    target=gene2_obj,
                    edge_weight=row["EdgeWeight"],
                    study=study,
                    user=study.user,
                    )
            result.save()
    study.save()
    return True

def get_status(algo, task_id):
    return requests.get(f'{algo.url}/status/{task_id}', headers={'Cache-Control': 'no-cache'}).json()


def return_saved_study(studies, user):
    study = studies[0]
    # Copy study results
    results = deepcopy(study.results)
    # Create a new study that is a duplicate but assign to this user.
    study.pk = None
    study.results = None
    study.save()

    # Now go through and assign all results to this study and user.
    for result in results:
        result.pk = None
        result.study = study
        result.user = user
        result.save()
    return True


@shared_task(name="create_gennifer_task")
def create_task(algorithm_name, zenodo_id, hyperparameters, user_pk):
    # Get algorithm obj
    algo = Algorithm.objects.get(name=algorithm_name)

    # Get or create a new algorithm instance based on the hyperparameters
    if not hyperparameters:
        algo_instance, algo_instance_created = AlgorithmInstance.objects.get_or_create(
                algorithm=algo,
                hyperparameters__isnull=True,
                )
    else:
        algo_instance, algo_instance_created = AlgorithmInstance.objects.get_or_create(
                algorithm=algo,
                hyperparameters=hyperparameters,
                )

    # Get User obj
    user = User.objects.get(pk=user_pk)

    # Initialize dataset instance
    dataset, dataset_created = Dataset.objects.get_or_create(
            zenodo_id=zenodo_id,
            upload_user=user,
            )

    if dataset_created:
        dataset.save()

    if not algo_instance_created and not dataset_created:
        # This means we've already run the study. So let's just return that and not bother our workers.
        studies = InferenceStudy.objects.filter(
                algorithm_instance=algo_instance,
                dataset=dataset,
                status='SUCCESS',
                )
        #TODO: Probably should add some timestamp handling here 
        if len(studies) > 0:
            return_saved_study(studies, user)
            
    # Send to gennifer app
    gennifer_request = {
            "zenodo_id": zenodo_id,
            "hyperparameters": hyperparameters,
            }
    task_id = requests.post(f'{algo.url}/run', json=gennifer_request).json()["task_id"]

    logger.info(f'TASK_ID: {task_id}')

    # Get initial status
    status = get_status(algo, task_id)
    
    # Create Inference Study
    study = InferenceStudy.objects.create(
            algorithm_instance=algo_instance,
            user=user,
            dataset=dataset,
            status=status["task_status"],
            )
    # Save initial study
    study.save()

    # Enter a loop to keep checking back in and populate the study once it has completed.
    #TODO: Not sure if this is best practice
    while True:
        # Check in every 2 seconds
        time.sleep(5)
        status = get_status(algo, task_id)
        if status["task_status"] == 'SUCCESS':
            return save_inference_study(study, status)
        if status["task_status"] == "FAILURE":
            return save_inference_study(study, status, failed=True)
        if status["task_status"] != study.status:
            study.status = status["task_status"]
            study.save()
