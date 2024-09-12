import itertools
from bmt import Toolkit
from importlib import import_module
from collections import defaultdict
from django.core.management.base import BaseCommand
from reasoner_pydantic import MetaKnowledgeGraph, MetaEdge
from django.conf import settings
from ..models import App, Template, TemplateMatch

APPS = [import_module(app+'.app_interface') for app in settings.INSTALLED_CHP_APPS]
TK = Toolkit()


def _collect_metakgs_by_app():
    # Collect each app's meta kg
    app_to_meta_kg = dict()
    for app, app_name in zip(APPS, settings.INSTALLED_CHP_APPS):
        app_db_obj = App.objects.get(name=app_name)
        if app_db_obj.meta_knowledge_graph_zenodo_file:
            meta_kg = app_db_obj.meta_knowledge_graph_zenodo_file.load_file(base_url="https://sandbox.zenodo.org/api/records")
        # Load default location
        else:
            get_app_meta_kg_fn = getattr(app, 'get_meta_knowledge_graph')
            meta_kg = get_app_meta_kg_fn()
        meta_kg = MetaKnowledgeGraph.parse_obj(meta_kg.to_dict())
        app_to_meta_kg[app_name] = meta_kg
    return app_to_meta_kg

def _build_app_templates(meta_kg):
    matcher = defaultdict(set)
    for meta_edge in meta_kg.edges:
        subject_ancestors = TK.get_ancestors(meta_edge.subject, reflexive=True, mixin=False, formatted=True)
        predicate_ancestors = TK.get_ancestors(meta_edge.predicate, reflexive=True, mixin=False, formatted=True)
        object_ancestors = TK.get_ancestors(meta_edge.object, reflexive=True, mixin=False, formatted=True)
        for edge in itertools.product(*[subject_ancestors, predicate_ancestors, object_ancestors]):
            template_meta_edge = MetaEdge(subject=edge[0], predicate=edge[1], object=edge[2])
            matcher[template_meta_edge].add(meta_edge)
    return dict(matcher)

def run():
    app_to_meta_kg = _collect_metakgs_by_app()
    app_to_templates = dict()
    for app_name, meta_kg in app_to_meta_kg.items():
        app_to_templates[app_name] = _build_app_templates(meta_kg)
    Template.objects.all().delete()
    TemplateMatch.objects.all().delete()

    # Populate Templater
    for app_name, app_templates in app_to_templates.items():
        for app_template, app_template_matches in app_templates.items():
            template = Template(app_name = app_name,
                                subject = app_template.subject,
                                object = app_template.object,
                                predicate = app_template.predicate)
            template.save()
            for app_template_match in app_template_matches:
                template_match = TemplateMatch(template=template,
                                               subject = app_template_match.subject,
                                               object = app_template_match.object,
                                               predicate = app_template_match.predicate)
                template_match.save()






