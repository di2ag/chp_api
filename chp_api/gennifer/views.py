import requests

from collections import defaultdict

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
#from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, TokenHasScope

from .models import (
        Dataset,
        Study,
        Task,
        Result, 
        Algorithm, 
        Gene, 
        UserAnalysisSession,
        AlgorithmInstance,
        Hyperparameter,
        HyperparameterInstance,
        )
from .serializers import (
        DatasetSerializer,
        StudySerializer, 
        TaskSerializer, 
        ResultSerializer, 
        AlgorithmSerializer, 
        GeneSerializer,
        UserAnalysisSessionSerializer,
        AlgorithmInstanceSerializer,
        HyperparameterSerializer,
        HyperparameterInstanceSerializer,
        )
from .tasks import create_task
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly


class UserAnalysisSessionViewSet(viewsets.ModelViewSet):
    serializer_class = UserAnalysisSessionSerializer
    #filter_backends = [DjangoFilterBackend]
    #filterset_fields = ['id', 'name', 'is_saved']
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]#, TokenHasReadWriteScope]

    def get_queryset(self):
        user = self.request.user
        print(f'User is {user}')
        return UserAnalysisSession.objects.filter(user=user)
    

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'zenodo_id']
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]#, TokenHasReadWriteScope]

    def perform_create(self, serializers):
        try:
            serializers.save(user=self.request.user)
        except ValueError as e:
            raise ValidationError(str(e))

class StudyViewSet(viewsets.ModelViewSet):
    #queryset = Study.objects.all()
    serializer_class = StudySerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]#, TokenHasReadWriteScope]
    
    def get_queryset(self):
        user = self.request.user
        return Study.objects.filter(user=user)
    
    def perform_create(self, serializers):
        try:
            serializers.save(user=self.request.user, status='RECEIVED')
        except ValueError as e:
            raise ValidationError(str(e))

class TaskViewSet(viewsets.ModelViewSet):
    #queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_public', 'dataset', 'algorithm_instance']
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]#, TokenHasReadWriteScope]

    def get_queryset(self):
        user = self.request.user
        return Task.objects.filter(user=user)
    
    def perform_create(self, serializers):
        try:
            serializers.save(user=self.request.user, status='RECEIVED')
        except ValueError as e:
            raise ValidationError(str(e))


class ResultViewSet(viewsets.ModelViewSet):
    #queryset = Result.objects.all()
    serializer_class = ResultSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_public', 'task', 'tf', 'target']
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]#, TokenHasReadWriteScope]

    def get_queryset(self):
        user = self.request.user
        return Result.objects.filter(user=user)

class AlgorithmViewSet(viewsets.ModelViewSet):
    serializer_class = AlgorithmSerializer
    queryset = Algorithm.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]#, TokenHasReadWriteScope]
    #required_scopes = ['read']

class AlgorithmInstanceViewSet(viewsets.ModelViewSet):
    queryset = AlgorithmInstance.objects.all()
    serializer_class = AlgorithmInstanceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]#, TokenHasReadWriteScope]

class HyperparameterViewSet(viewsets.ModelViewSet):
    serializer_class = HyperparameterSerializer
    queryset = Hyperparameter.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['algorithm']
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]#, TokenHasReadWriteScope]
    #required_scopes = ['read']

class HyperparameterInstanceViewSet(viewsets.ModelViewSet):
    queryset = HyperparameterInstance.objects.all()
    serializer_class = HyperparameterInstanceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]#, TokenHasReadWriteScope]

class GeneViewSet(viewsets.ModelViewSet):
    serializer_class = GeneSerializer
    #queryset = Gene.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]#, TokenHasReadWriteScope]
    
    def get_queryset(self):
        user = self.request.user
        # Get user results
        results = Result.objects.filter(user=user)
        tf_genes = Gene.objects.filter(inference_result_tf__pk__in=results)
        target_genes = Gene.objects.filter(inference_result_target__pk__in=results)
        genes_union = tf_genes.union(target_genes)
        print(len(genes_union))
        return genes_union

class CytoscapeHandler:
    def __init__(self, results):
        self.results = results
    
    def construct_node(self, gene_obj):
        if gene_obj.variant:
            name = f'{gene_obj.name}({gene_obj.variant})'
            curie = f'{gene_obj.curie}({gene_obj.variant})'
            chp_preferred_curie = f'{gene_obj.chp_preferred_curie}({gene_obj.variant})'
        else:
            name = gene_obj.name
            curie = gene_obj.curie
            chp_preferred_curie = gene_obj.chp_preferred_curie

        node = {
                "data": {
                    "id": str(gene_obj.pk),
                    "name": name,
                    "curie": curie,
                    "chp_preferred_curie": chp_preferred_curie
                    }
                }
        return node, str(gene_obj.pk)
    
    def construct_edge_annotations(self, annotations):
        obj = {"openai": {"justification": None}, "translator": []}
        tr_dict = defaultdict(list)
        for a in annotations:
            if a.type == 'openai':
                obj["openai"]["justification"] = a.oai_justification
                continue
            if a.type == 'translator':
                tr_dict[a.tr_formatted_relation_string].append(
                    {
                        "predicate": a.tr_predicate,
                        "qualified_predicate": a.tr_qualified_predicate,
                        "object_modifier": a.tr_object_modifier,
                        "object_aspect": a.tr_object_aspect,
                        "resource_id": a.tr_resource_id,
                        "primary_source": a.tr_primary_source,
                    }
                )
        # Reformat to list
        for relation, tr_results in tr_dict.items():
            obj["translator"].append(
                {
                    "formatted_relation": relation,
                    "results": tr_results
                }
            )
        return obj
    
    def construct_edge(self, res, source_id, target_id):
        # Normalize edge weight based on the study
        normalized_weight = (res.edge_weight - res.task.min_task_edge_weight) / (res.task.max_task_edge_weight - res.task.min_task_edge_weight)
        directed = res.task.algorithm_instance.algorithm.directed
        edge_tuple = tuple(sorted([source_id, target_id]))
        annotations = res.annotations.all()
        edge = {
                "data": {
                    "id": str(res.pk),
                    "source": source_id,
                    "target": target_id,
                    "dataset": str(res.task.dataset),
                    "weight": normalized_weight,
                    "algorithm": str(res.task.algorithm_instance),
                    "directed": directed,
                    "annotations": self.construct_edge_annotations(annotations),
                    }
                }
        return edge, edge_tuple, directed

    def add(self, res, nodes, edges, processed_node_ids, processed_undirected_edges):
        # Construct nodes
        tf_node, tf_id = self.construct_node(res.tf)
        target_node, target_id = self.construct_node(res.target)
        # Add nodes if not already added by another result
        if tf_id not in processed_node_ids:
            nodes.append(tf_node)
            processed_node_ids.add(tf_id)
        if target_id not in processed_node_ids:
            nodes.append(target_node)
            processed_node_ids.add(target_id)
        # Add and construct edge
        edge, edge_tuple, edge_is_directed = self.construct_edge(res, tf_id, target_id)
        if edge_is_directed:
            edges.append(edge)
        elif not edge_is_directed and edge_tuple not in processed_undirected_edges:
            edges.append(edge)
            processed_undirected_edges.add(edge_tuple)
        else:
            pass
        return nodes, edges, processed_node_ids, processed_undirected_edges

    def construct_cytoscape_data(self):
        nodes = []
        edges = []
        processed_node_ids = set()
        processed_undirected_edges = set()
        elements = []
        # Construct graph
        for res in self.results:
            nodes, edges, processed_node_ids, processed_undirected_edges  = self.add(
                    res,
                    nodes,
                    edges,
                    processed_node_ids,
                    processed_undirected_edges,
                    )
        elements.extend(nodes)
        elements.extend(edges)
        return {
                "elements": elements
                }


class CytoscapeView(APIView):


    def get(self, request):
        results = Result.objects.all()
        cyto_handler = CytoscapeHandler(results)
        cyto = cyto_handler.construct_cytoscape_data()
        return JsonResponse(cyto)

    def post(self, request):
        elements = []
        gene_ids = request.data.get("gene_ids", None)
        study_ids = request.data.get("study_ids", None)
        algorithm_ids = request.data.get("algorithm_ids", None)
        dataset_ids = request.data.get("dataset_ids", None)
        cached_inference_result_ids = request.data.get("cached_results", None)

        if not (study_ids and gene_ids) and not (algorithm_ids and dataset_ids and  gene_ids):
            return JsonResponse({"elements": elements, "result_ids": []})
        
        # Create Filter
        filters = []
        if gene_ids:
            filters.extend(
                    [
                        {"field": 'tf__pk', "operator": 'in', "value": gene_ids},
                        {"field": 'target__pk', "operator": 'in', "value": gene_ids},
                        ]
                    )
        if study_ids:
            tasks = Task.objects.filter(study__pk__in=study_ids)
            task_ids = [task.pk for task in tasks]
            filters.append({"field": 'task__pk', "operator": 'in', "value": task_ids})
        if algorithm_ids:
            filters.append({"field": 'task__algorithm_instance__algorithm__pk', "operator": 'in', "value": algorithm_ids})
        if dataset_ids:
            filters.append({"field": 'task__dataset__zenodo_id', "operator": 'in', "value": dataset_ids})

        # Construct Query
        query = Q()
        for filter_item in filters:
            field = filter_item["field"]
            operator = filter_item["operator"]
            value = filter_item["value"]
            query &= Q(**{f'{field}__{operator}': value})

        # Get matching results
        results = Result.objects.filter(query)

        if len(results) == 0:
            return JsonResponse({"elements": elements, "result_ids": []})
        
        # Exclude results that have already been sent to user
        if cached_inference_result_ids:
            results = results.exclude(pk__in=cached_inference_result_ids)

        # Capture result_ids
        result_ids = [res.pk for res in results]

        # Initialize Cytoscape Handler
        cyto_handler = CytoscapeHandler(results)
        elements_dict = cyto_handler.construct_cytoscape_data()

        elements_dict["result_ids"] = result_ids
        return JsonResponse(elements_dict)

class StudyDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, study_id=None):
        if not study_id:
            return JsonResponse({"detail": 'No study ID was passed.'})
        # Set response
        response = {
                "study_id": study_id,
                }
        # Get study
        try:
            study = Study.objects.get(pk=study_id, user=request.user)
        except ObjectDoesNotExist:
            response["error"] = 'The study does not exist for request user.'
            return JsonResponse(response)

        response["description"] = study.description
        response["status"] = study.status
        response["tasks"] = []

        # Get tasks assocaited with study
        tasks = Task.objects.filter(study=study)

        # Collect task information
        for task in tasks:
            task_json = {}
            # Collect task information
            task_json["max_task_edge_weight"] = task.max_task_edge_weight
            task_json["min_task_edge_weight"] = task.min_task_edge_weight
            task_json["avg_task_edge_weight"] = task.avg_task_edge_weight
            task_json["std_task_edge_weight"] = task.std_task_edge_weight
            task_json["status"] = task.status
            # Collect algo hyperparameters
            hyper_instance_objs = task.algorithm_instance.hyperparameters.all()
            hypers = {}
            for hyper in hyper_instance_objs:
                hypers[hyper.hyperparameter.name] = {
                        "value": hyper.value_str,
                        "info": hyper.hyperparameter.info
                        }
            # Collect Algorithm instance information
            task_json["algorithm"] = {
                    "name": task.algorithm_instance.algorithm.name,
                    "description": task.algorithm_instance.algorithm.description,
                    "edge_weight_description": task.algorithm_instance.algorithm.edge_weight_description,
                    "edge_weight_type": task.algorithm_instance.algorithm.edge_weight_type,
                    "directed": task.algorithm_instance.algorithm.directed,
                    "hyperparameters": hypers
                    }
            # Collect Dataset information
            task_json["dataset"] = {
                    "title": task.dataset.title,
                    "zenodo_id": task.dataset.zenodo_id,
                    "description": task.dataset.description,
                    }
            # Build cytoscape graph
            if task.status == 'SUCCESS':
                results = Result.objects.filter(task=task)
                cyto_handler = CytoscapeHandler(results)
                task_json["graph"] = cyto_handler.construct_cytoscape_data()
            else:
                task_json["graph"] = None
            response["tasks"].append(task_json)

        return JsonResponse(response)
                    

class run(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """ Request comes in as a list of algorithms to run.
        """
        study_id = request.data.get("study_id", None)
        if not study_id:
            return JsonResponse({"error": 'Must pass a study_id.'})
        response = {
                "study_id": study_id,
                "task_status": [],
                }
        # Get study
        try:
            study = Study.objects.get(pk=study_id, user=request.user)
        except ObjectDoesNotExist:
            response["error"] = 'The study does not exist for request user.'
            return JsonResponse(response)
        # Set Study Status to Started.
        study.status = 'STARTED'
        study.save()
        # Build gennifer requests
        tasks = Task.objects.filter(study=study)
        for task in tasks:
            # If all pass, now send to gennifer services
            task_id = create_task.delay(task.pk).id
            response["task_status"].append(task_id)
        return JsonResponse(response)
