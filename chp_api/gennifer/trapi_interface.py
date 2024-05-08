'''trapi interface'''
import os
import uuid
import json
import pkgutil
import logging

from typing import Tuple, Union
from pydantic import parse_obj_as
from django.db.models import QuerySet
from reasoner_pydantic.utils import HashableMapping
from django.core.exceptions import ObjectDoesNotExist
from reasoner_pydantic import MetaKnowledgeGraph, Message, KnowledgeGraph
from reasoner_pydantic.kgraph import RetrievalSource, Attribute
from reasoner_pydantic.results import NodeBinding, EdgeBinding, Result, Results, Analysis

from .models import Result, Gene

# Setup logging
logging.addLevelName(25, "NOTE")
# Add a special logging function
def note(self, message, *args, **kwargs):
    self._log(25, message, args, kwargs)
logging.Logger.note = note
internal_logger = logging.getLogger(__name__)

APP_PATH = os.path.dirname(os.path.abspath(__file__))

class TrapiInterface:
    def __init__(self, trapi_version: str = '1.5'):
        self.trapi_version = trapi_version

    def get_meta_knowledge_graph(self) -> MetaKnowledgeGraph:
        return self._read_meta_knowledge_graph()

    def _read_meta_knowledge_graph(self) -> MetaKnowledgeGraph:
        with open(os.path.join(APP_PATH, 'app_meta_data', 'meta_knowledge_graph.json'), 'r') as mkg_file:
            mkg_json = json.load(mkg_file)
        return MetaKnowledgeGraph.parse_obj(mkg_json)

    def get_name(self) -> str:
        return 'gennifer'

    def _get_sources(self):
        source_1 = RetrievalSource(resource_id = "infores:connections-hypothesis",
                                   resource_role="primary_knowledge_source")
        return [source_1]

    def _get_attributes(self, val, algorithm_instance, dataset):
        att_1 = Attribute(
                attribute_type_id = algorithm_instance.algorithm.edge_weight_type,
                value_type_id='biolink:has_evidence',
                value=val,
                description=algorithm_instance.algorithm.edge_weight_description,
                )
        att_2 = Attribute(
                attribute_type_id='grn_inference_algorithm',
                value_type_id='biolink:supporting_study_method_type',
                value=str(algorithm_instance),
                description=algorithm_instance.algorithm.description,
                )
        att_3 = Attribute(
                attribute_type_id='inferenced_dataset',
                value_type_id='biolink:supporting_data_set',
                value=f'zenodo:{dataset.zenodo_id}',
                description=f'{dataset.title}: {dataset.description}',
                )
        att_4 = Attribute(
                attribute_type_id = 'knowledge_level',
                value='statistical_association'
                )
        return [att_1, att_2, att_3, att_4]

    def _add_results(
            self,
            message,
            qg_subject_id, 
            subject_curies, 
            subject_category,
            predicate, 
            qg_edge_id,
            qg_object_id, 
            object_curies, 
            object_category, 
            vals,
            algorithms,
            datasets,
            ):
        node_binding_group = []
        edge_binding_group = []
        nodes = dict()
        edges = dict()
        val_id = 0
        for subject_curie in subject_curies:
            for object_curie in object_curies:
                nodes[subject_curie] = {"categories": [subject_category], "attributes" : []}
                nodes[object_curie] = {"categories": [object_category], "attributes" : []}
                kg_edge_id = str(uuid.uuid4())
                edges[kg_edge_id] = {"predicate": predicate,
                                     "subject": subject_curie,
                                     "object": object_curie,
                                     "sources": self._get_sources(),
                                     "attributes": self._get_attributes(
                                         vals[val_id],
                                         algorithms[val_id],
                                         datasets[val_id],
                                         )}
                val_id += 1
                node_bindings = {qg_subject_id: set(), qg_object_id: set()}
                edge_bindings = {qg_edge_id : set()}
                node_bindings[qg_subject_id].add(NodeBinding(id = subject_curie, attributes=[]))
                node_bindings[qg_object_id].add(NodeBinding(id = object_curie, attributes=[]))
                edge_bindings[qg_edge_id].add(EdgeBinding(id = kg_edge_id, attributes=[]))
                node_binding_group.append(node_bindings)
                edge_binding_group.append(edge_bindings)
        kgraph = KnowledgeGraph(nodes=nodes, edges=edges)
        if message.knowledge_graph is not None:
            message.knowledge_graph.update(kgraph)
        else:
            message.knowledge_graph = kgraph
        return node_binding_group, edge_binding_group

    def _extract_qnode_info(self, qnode):
        return qnode.ids, qnode.categories[0]

    def get_response(self, message: Message, logger):
        for edge_id, edge in message.query_graph.edges.items():
            predicate = edge.predicates[0]
            qg_edge_id = edge_id
            qg_subject_id = edge.subject
            qg_object_id = edge.object
        subject_curies, subject_category = self._extract_qnode_info(message.query_graph.nodes[qg_subject_id])
        object_curies, object_category = self._extract_qnode_info(message.query_graph.nodes[qg_object_id])
        # annotation
        node_bindings = []
        edge_bindings = []
        #TODO: Should probably offer support to return all results
        if subject_curies is not None and object_curies is not None:
            logger.info('Annotation edges detected')
            logger.info('Annotate edge not currently supported')
            return message
        elif object_curies is not None:
            logger.info('Wildcard detected')
            for curie in object_curies:
                # Get object gene, if we don't have then continue
                obj_genes = Gene.objects.filter(chp_preferred_curie=curie)
                if len(obj_genes) == 0:
                    continue
                if predicate == 'biolink:regulates':
                    results = []
                    for obj_gene in obj_genes:
                        results.extend(Result.objects.filter(target=obj_gene, is_public=True))
                    subject_curies = [r.tf.chp_preferred_curie for r in results]
                elif predicate == 'biolink:regulated_by':
                    results = []
                    for obj_gene in obj_genes:
                        results.extend(Result.objects.filter(tf=obj_gene, is_public=True))
                    subject_curies = [r.target.chp_preferred_curie for r in results]
                else:
                    raise ValueError(f'Unknown predicate: {predicate}.')
                vals = [r.edge_weight for r in results]
                algorithms = [r.study.algorithm_instance for r in results]
                datasets = [r.study.dataset for r in results]
                node_binding_group, edge_binding_group = self._add_results(
                        message,
                        qg_subject_id,
                        subject_curies,
                        subject_category,
                        predicate,
                        qg_edge_id,
                        object_mapping,
                        qg_object_id,
                        [curie],
                        object_category,
                        vals,
                        algorithms,
                        datasets
                        )
                node_bindings.extend(node_binding_group)
                edge_bindings.extend(edge_binding_group)
        elif subject_curies is not None:
            logger.info('Wildcard detected')
            for curie in subject_curies:
                # Get object gene, if we don't have then continue
                sub_genes = Gene.objects.filter(chp_preferred_curie=curie)
                if len(sub_genes) == 0:
                    continue
                if predicate == 'biolink:regulates':
                    results = []
                    for sub_gene in sub_genes:
                        results.extend(Result.objects.filter(tf=sub_gene, is_public=True))
                    object_curies = [r.target.chp_preferred_curie for r in results]
                elif predicate == 'biolink:regulated_by':
                    results = []
                    for sub_gene in sub_genes:
                        results.extend(Result.objects.filter(target=sub_gene, is_public=True))
                    object_curies = [r.tf.chp_preferred_curie for r in results]
                else:
                    raise ValueError(f'Unknown predicate: {predicate}.')
                vals = [r.edge_weight for r in results]
                algorithms = [r.study.algorithm_instance for r in results]
                datasets = [r.study.dataset for r in results]
                node_binding_group, edge_binding_group = self._add_results(
                        message,
                        qg_subject_id,
                        subject_curies,
                        subject_category,
                        predicate,
                        qg_edge_id,
                        qg_object_id, 
                        [curie], 
                        object_category,
                        vals,
                        algorithms,
                        datasets,
                        )
                node_bindings.extend(node_binding_group)
                edge_bindings.extend(edge_binding_group)
        else:
            logger.info('No curies detected. Returning no results')
            return message
        results = Results(__root__ = parse_obj_as(HashableMapping, {}))
        for node_binding_dict, edge_binding_dict in zip(node_bindings, edge_bindings):
            analysis = Analysis(resource_id='infores:connections-hypothesis', edge_bindings = edge_binding_dict, attributes=[])
            result = Result(node_bindings = node_binding_dict, analyses=[analysis])
            results.add(result)
        message.results = results
        return message
