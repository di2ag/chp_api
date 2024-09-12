# Connections Hypothesis Provider API Documentation

## Introduction
Connections Hypothesis Provider (CHP) is a collaborative service developed by Dartmouth College and Tufts University, in partnership with the National Center for Advancing Translational Sciences (NCATS). CHP's mission is to utilize clinical data and structured biochemical knowledge to create computational representations of pathway structures and molecular components. This effort supports both human and machine-driven analysis, enabling pathway-based biomarker discovery and contributing to the drug development process.

Currently, CHP serves as a platform for Gene Regulatory Network (GRN) discovery, allowing researchers to upload their own RNASeq data, or work with pre-existing datasets. Users can analyze, refine, and explore novel gene-to-gene regulatory relationships through our core discovery tool, GenNIFER, a web-based portal featuring state-of-the-art GRN inferencing algorithms. Additionally, the platform integrates with the Translator ecosystem, allowing users to contextualize their findings using existing knowledge sources.

Through its integration with the [Knowledge Collaboratory](https://github.com/MaastrichtU-IDS/knowledge-collaboratory) team, GenNIFER also enables researchers to publish their findings back into the Translator ecosystem, facilitating further collaboration and discovery.

This Docker repository contains the necessary build instructions to launch our tooling in support of the CHP API. Specifically, CHP API powers the following:
* [GenNIFER](https://github.com/di2ag/gennifer): our tool for GRN discovery.
* [Tissue-Gene Specificity Tool](https://github.com/di2ag/gene-specificity): our tool for assessing a gene’s expression specificity to a tissue.
  
For more specifics about either application, see their respective repository READMEs.

## Interacting with CHP API
The CHP API provides supporting data as a Knowledge Provider (KP) for the Translator consortium and can be interacted with from our build servers. For a list of knowledge that we support, see our meta knowledge graph. Further details about CHP API can be found in its [SmartAPI](http://smart-api.info/registry?q=412af63e15b73e5a30778aac84ce313f) registration. We also provide examples for how to interact with the individual tools in their own relevant repository.
### Build servers
* Production: https://chp-api.transltr.io
* Testing: https://chp-api.test.transltr.io
* Staging: https://chp-api.ci.transltr.io

### Endpoints
* [query](query.md) : `POST /query/`
* [predicates](predicates.md) : `GET /meta_knowledge_graph/`

### Meta Knowledge Graph
<details>
  <summary> Click to view json example</summary>

  ```json
  {
    "nodes": {
      "biolink:Gene": {
        "id_prefixes": [
          "ENSEMBL"
        ],
        "attributes": null
      },
      "biolink:GrossAnatomicalStructure": {
        "id_prefixes": [
          "UBERON",
          "EFO"
        ],
        "attributes": null
      }
    },
    "edges": [
      {
        "subject": "biolink:Gene",
        "predicate": "biolink:expressed_in",
        "object": "biolink:GrossAnatomicalStructure",
        "qualifiers": null,
        "attributes": null,
        "knowledge_types": null,
        "association": null
      },
      {
        "subject": "biolink:GrossAnatomicalStructure",
        "predicate": "biolink:expresses",
        "object": "biolink:Gene",
        "qualifiers": null,
        "attributes": null,
        "knowledge_types": null,
        "association": null
      },
      {
        "subject": "biolink:Gene",
        "predicate": "biolink:regulates",
        "object": "biolink:Gene",
        "qualifiers": null,
        "attributes": null,
        "knowledge_types": null,
        "association": null
      },
      {
        "subject": "biolink:Gene",
        "predicate": "biolink:regulated_by",
        "object": "biolink:Gene",
        "qualifiers": null,
        "attributes": null,
        "knowledge_types": null,
        "association": null
      }
    ]
}
```
</details>

### SmartAPI
CHP is registered with [SmartAPI](http://smart-api.info/registry?q=412af63e15b73e5a30778aac84ce313f).

## Contact for this code
Gregory Hyde (gregory.m.hyde.th@dartmouth.edu)

## TRAPI and Biolink
Trapi = 1.5.0

Biolink = 4.2.0
