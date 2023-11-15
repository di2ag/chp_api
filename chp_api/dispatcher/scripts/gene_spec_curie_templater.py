import tqdm
import json
import requests
from collections import defaultdict
from gene_specificity.models import CurieTemplate, CurieTemplateMatch, SpecificityMeanGene, SpecificityMeanTissue

CHUNK_SIZE = 500

def _get_ascendants(curies, category):
    mapping = defaultdict(set)
    # map curie with curie
    for curie in curies:
        mapping[curie].add(curie)
    if category == 'biolink:Gene':
        return dict(mapping)
    for i in tqdm.tqdm(range(0, len(curies), CHUNK_SIZE), desc='Getting ancestors in chunks of size {}'.format(CHUNK_SIZE)):
        curie_subset = curies[i:i+CHUNK_SIZE]
        query_graph = {
            "nodes": {
                "n0": {
                    "categories":[category]
                },
                "n1": {
                    "ids": curie_subset
                },
            },
            "edges": {
                "e0": {
                    "subject": "n1",
                    "object": "n0",
                    "predicates": ["biolink:part_of", "biolink:subclass_of"],
                }
            }
        }
        query = {
            "message": {
                "query_graph": query_graph,
            }
        }
        url = 'https://ontology-kp.apps.renci.org/query'
        r = requests.post(url, json=query, timeout=1000)
        answer = json.loads(r.content)
        for edge_id, edge in answer['message']['knowledge_graph']['edges'].items():
            subject = edge['subject']
            object = edge['object']
            mapping[object].add(subject)
    return dict(mapping)


def run():
    objects = SpecificityMeanGene.objects.all()
    gene_curies = set()
    tissue_curies = set()
    for object in objects:
        gene_curies.add(object.gene_curie)
        tissue_curies.add(object.tissue_curie)
    gene_ascendants = _get_ascendants(list(gene_curies), 'biolink:Gene')
    tissue_ascendants = _get_ascendants(list(tissue_curies), 'biolink:GrossAnatomicalStructure')

    CurieTemplate.objects.all().delete()
    CurieTemplateMatch.objects.all().delete()

    for gene_ancestor, handled_gene_descendants in gene_ascendants.items():
        curie_template = CurieTemplate(curie=gene_ancestor)
        curie_template.save()
        for handled_gene_descendant in handled_gene_descendants:
             curie_template_match = CurieTemplateMatch(curie_template=curie_template,
                                                       curie=handled_gene_descendant)
             curie_template_match.save()
    for tissue_ancestor, handled_tissue_descendants in tissue_ascendants.items():
        curie_template = CurieTemplate(curie=tissue_ancestor)
        curie_template.save()
        for handled_tissue_descendant in handled_tissue_descendants:
             curie_template_match = CurieTemplateMatch(curie_template=curie_template,
                                                       curie=handled_tissue_descendant)
             curie_template_match.save()
