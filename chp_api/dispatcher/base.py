import uuid
import time
import logging
from .logger import Logger
import itertools
from copy import deepcopy
from re import A
#from reasoner_validator import TRAPISchemaValidator
from django.http import JsonResponse
from django.apps import apps
from django.conf import settings
from importlib import import_module
from collections import defaultdict

from .models import Transaction, App, DispatcherSetting, Template, TemplateMatch
from reasoner_pydantic import MetaKnowledgeGraph, Message, MetaEdge, MetaNode
from reasoner_pydantic.qgraph import QNode, QEdge

# Setup logging
logging.addLevelName(25, "NOTE")
# Add a special logging function
def note(self, message, *args, **kwargs):
    self._log(25, message, args, kwargs)
logging.Logger.note = note
logger = logging.getLogger(__name__)

# Import CHP Apps
APPS = [import_module(app+'.app_interface') for app in settings.INSTALLED_CHP_APPS]

class Dispatcher():
    def __init__(self, request, trapi_version, biolink_version):
        """ Base API Query Processor class used to abstract the processing infrastructure from
            the views. Inherits from the CHP Utilities Trapi Query Processor which handles
            node normalization, curie ontology expansion, and semantic operations.

            :param request: Incoming POST request with a TRAPI message.
            :type request: requests.request
        """
        self.request_data = deepcopy(request.data)
        self.biolink_version = biolink_version
        self.trapi_version = trapi_version
        #self.validator = TRAPISchemaValidator(self.trapi_version)
        self.logger = Logger()

    def merge_meta_kg(self, metakg1, metakg2):
        new_metakg = MetaKnowledgeGraph.parse_obj({"nodes": [], "edges": []})
        # Merge nodes
        new_metakg.nodes = metakg1.nodes
        for n, v in metakg2.nodes.items():
            if n in new_metakg.nodes:
                id_prefixes = list(set.union(*[set(list(metakg1.nodes[n].id_prefixes)), set(list(metakg2.nodes[n].id_prefixes))]))
                new_node = MetaNode.parse_obj({"id_prefixes": id_prefixes})
                new_metakg.nodes[n] = new_node
            else:
                new_metakg.nodes[n] = MetaNode.parse_obj(v)
        # Merge edges
        for e in metakg1.edges:
            new_metakg.edges.append(e)
        for e in metakg2.edges:
            new_metakg.edges.append(e)
        return new_metakg

    def get_meta_knowledge_graph(self):
        # Get current trapi and biolink versions
        dispatcher_settings = DispatcherSetting.load()
        merged_meta_kg = None
        for app, app_name in zip(APPS, settings.INSTALLED_CHP_APPS):
            app_db_obj = App.objects.get(name=app_name)
            # Load location from uploaded Zenodo files
            if app_db_obj.meta_knowledge_graph_zenodo_file:
                meta_kg = app_db_obj.meta_knowledge_graph_zenodo_file.load_file(base_url="https://sandbox.zenodo.org/api/records")
            # Load default location
            else:
                get_app_meta_kg_fn = getattr(app, 'get_meta_knowledge_graph')
                meta_kg = get_app_meta_kg_fn().to_dict()
            meta_kg = MetaKnowledgeGraph.parse_obj(meta_kg)
            if merged_meta_kg is None:
                merged_meta_kg = meta_kg
            else:
                merged_meta_kg = self.merge_meta_kg(merged_meta_kg, meta_kg)
        return merged_meta_kg

    def process_invalid_trapi(self, request):
        invalid_query_json = request.data
        invalid_query_json['status'] = 'Malformed Query'
        return JsonResponse(invalid_query_json, status=400)

    def process_request(self, request, trapi_version):
        """ Helper function that extracts the message from the request data.
        """
        logger.info('Starting query')
        message = Message.parse_obj(request.data['message'])
        #logger.info('Validating query')
        #self.validator.validate(message.to_dict(), 'Message')
        logger.info('Message loaded')
        return message

    def get_app_configs(self, message):
        """ Should get a base app configuration for your app or nothing.
        """
        app_configs = []
        for app in APPS:
            get_app_config_fn = getattr(app, 'get_app_config')
            app_configs.append(get_app_config_fn(message))
        return app_configs
    
    def get_trapi_interfaces(self, app_configs):
        """ Should load a base interface of your app.
        """
        if len(app_configs) != len(APPS):
            raise ValueError('You should be loading base configs (if any) so at this point there should be one config per app (or just the app).')
        base_interfaces = []
        for app, app_config in zip(APPS, app_configs):
            get_trapi_interface_fn = getattr(app, 'get_trapi_interface')
            base_interfaces.append(get_trapi_interface_fn(app_config))
        return base_interfaces

    def extract_message_templates(self, message):
        assert len(message.query_graph.edges) == 1, 'CHP apps do not support multihop queries'
        subject = None
        predicates = []
        for edge_id, q_edge in message.query_graph.edges.items():
            subject = q_edge.subject
            if q_edge.predicates is None:
                q_edge = QEdge(subject = q_edge.subject, predicates=['biolink:related_to'], object = q_edge.object)
            for predicate in q_edge.predicates:
                predicates.append(predicate)
        subject_categories = []
        object_categories = []
        for node_id, q_node in message.query_graph.nodes.items():
            if q_node.categories is None:
                q_node = QNode(categories=['biolink:Entity'])
            for category in q_node.categories:
                if node_id == subject:
                    subject_categories.append(category)
                else:
                    object_categories.append(category)
        templates = []
        for edge in itertools.product(*[subject_categories, predicates, object_categories]):
            meta_edge = MetaEdge(subject=edge[0], predicate=edge[1], object=edge[2])
            templates.append(meta_edge)
        return templates

    def get_app_template_matches(self, app_name, templates):
        template_matches = []
        for template in templates:
            matches = TemplateMatch.objects.filter(template__app_name=app_name,
                                                   template__subject = template.subject,
                                                   template__object = template.object,
                                                   template__predicate = template.predicate)
            template_matches.extend(matches)
        return template_matches

    def apply_templates_to_message(self, message, matching_templates):
        consistent_queries = []
        for template in matching_templates:
            consistent_query = message.copy(deep=True)
            for edge_id, edge in consistent_query.query_graph.edges.items():
                edge.predicates = [template.predicate]
                subject_id = edge.subject
                object_id = edge.object
            consistent_query.query_graph.nodes[subject_id].categories = [template.subject]
            consistent_query.query_graph.nodes[object_id].categories = [template.object]
            consistent_queries.append(consistent_query)
        return consistent_queries

    def get_response(self, message):
        """ Main function of the processor that handles primary logic for obtaining
            a cached or calculated query response.
        """
        self.logger.info('Running message.')
        start_time = time.time()
        self.logger.info('Getting message templates.')
        message_templates = self.extract_message_templates(message)

        for app, app_name in zip(APPS, settings.INSTALLED_CHP_APPS):
            self.logger.info('Checking template matches for {}'.format(app_name))
            matching_templates = self.get_app_template_matches(app_name, message_templates)
            self.logger.info('Detected {} matches for {}'.format(len(matching_templates), app_name))
            if len(matching_templates) > 0:
                self.logger.info('Constructing queries on matching templates')
                consistent_app_queries = self.apply_templates_to_message(message, matching_templates)
                self.logger.info('Sending {} consistent queries'.format(len(consistent_app_queries)))
                get_app_response_fn = getattr(app, 'get_response')
                responses = get_app_response_fn(consistent_app_queries, self.logger)
                self.logger.info('Received responses from {}'.format(app_name))
                for response in responses:
                    response.query_graph = message.query_graph
                    self.add_transaction({'message':response.to_dict()}, str(uuid.uuid4()), 'Success', app_name)
                    message.update(response)

        message = message.to_dict()
        message = {'message':message}
        message['logs'] = self.logger.to_dict()
        message['trapi_version'] = self.trapi_version
        message['biolink_version'] = self.biolink_version
        message['status'] = 'Success'
        message['id'] = str(uuid.uuid4())
        message['workflow'] = [{"id": "lookup"}]
        self.add_transaction(message, message['id'], 'Success', 'dispatcher')

        return JsonResponse(message)

    def add_transaction(self, response, _id, status, app_name):
        app_db_obj = App.objects.get(name=app_name)
        # Save the transaction
        transaction = Transaction(
            id = _id,
            status = status,
            query = response,
            versions = settings.VERSIONS,
            chp_app = app_db_obj,
        )
        transaction.save()
