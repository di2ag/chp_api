import json
from gene_specificity.models import GeneToTissue, TissueToGene


def run():
    max_count = 20
    p_val_thresh = 0.05

    with open('gene_to_tissue.json', 'r') as f:
        gene_to_tissue = json.load(f)

    for gene_id, tissue_dict in gene_to_tissue.items():
        i = 0
        for tissue_id, data_obj in tissue_dict.items():
            if i == max_count:
                break
            spec_val = data_obj['spec']
            norm_spec_val = data_obj['norm_spec']
            p_val = data_obj['p_val']
            if p_val > p_val_thresh:
                break
            gtt = GeneToTissue(gene_id = gene_id, tissue_id = tissue_id, spec = spec_val, norm_spec = norm_spec_val, p_val = p_val)
            gtt.save()
            i += 1

    with open('tissue_to_gene.json', 'r') as f:
        tissue_to_gene = json.load(f)

    for tissue_id, gene_dict in tissue_to_gene.items():
        i = 0
        for gene_id, data_obj in gene_dict.items():
             if i == max_count:
                break
             spec_val = data_obj['spec']
             norm_spec_val = data_obj['norm_spec']
             p_val = data_obj['p_val']
             if p_val > p_val_thresh:
                 break
             ttg = TissueToGene(tissue_id = tissue_id, gene_id = gene_id, spec = spec_val, norm_spec = norm_spec_val, p_val = p_val)
             ttg.save()
             i += 1
