# Connections Hypothesis Provider API Documentation

## Description
Connections Hypothesis Provider (CHP) is a service built by Dartmouth College (PI – Dr. Eugene Santos) and Tufts University (Co-PI – Joseph Gormley) in collaboration with the National Center for Advancing Translational Sciences (NCATS). CHP aims to leverage clinical data along with structured biochemical knowledge to derive a computational representation of pathway structures and molecular components to support human and machine-driven interpretation, enable pathway-based biomarker discovery, and aid in the drug development process.
In its current version, CHP supports queries relating to genetic, therapeutic, and patient clinical features (e.g. tumor staging) contribution toward patient survival, as computed within the context of our test pilot: a robust breast cancer dataset from The Cancer Genome Atlas (TCGA). We are using this as a proving ground for our system’s basic operations as we work to incorporate structured pathway knowledge from Reactome and pathway analysis methods into the tool. 

## Introduction
Our system utilizes the Bayesian Knowledge Base (BKB), which is a directed probabilistic graphical model capable of modeling incomplete, cyclic and heterogenous knowledge. We currently expose a portion of our computational framework as a proving ground to reason over patterns that exist within the TCGA dataset, determine sensitivity of features to the underlying conditional probabilities, and guide hypothesis generation. Querying semantics are of the form P(Target=t | Evidence=e). To this end we’ve explored setting survival time targets specifying mutational profiles and drug treatments as evidence, though this process is generalizable to any TCGA feature type (e.g., tumor staging, gene copy number, age of diagnosis, etc.). 
However, as we incorporate pathway knowledge from domain-standard resources like Reactome and overlay biochemical pathway traversal logic, we will extend these querying semantics to derive inferences relating to biochemical mechanisms. The short-term benefits of tacking on this difficult task are to provide mechanism-of-action level analysis over cellular behavior and clinical outcomes. The long-term benefits of this work is to characterize three categories of information and discovery critical to pathway science, pathway components, pathway topology, and pathway dynamics.
Queries are governed by the Translator Reasoner API (TRAPI) which support the Biolink Model ontology. We’ve constructed a TRAPI compliant schema that represents our probabilistic queries and is digestible by our service. Upon receiving TRAPI compliant queries we return a conditional probability pertaining to the query as well as the auditable features our system captured and their overall sensitivity to the conditional probability. These features can be used to guide future exploration of the dataset and be used to lead to novel conclusions over the data. 

## Terms and Definitions
The greater NCATS consortium uses a series of terms (that we have adopted) to convey meaning quickly. A link to those terms and their definitions are available here: https://docs.google.com/spreadsheets/d/1C8hKXacxtQC5UzXI4opQs1r4pBJ_5hqgXrZH_raYQ4w/edit#gid=1581951609  
We extend this list local to our KP (Look, here is an NCATS term right here!) with the following terms: 
•	Connections Hypothesis Provider – CHP
•	The Cancer Genome Atlas – TCGA
•	Bayesian Knowledge Base – BKB

## Smart API
CHP is registered with Smart API: https://smart-api.info/ui/855adaa128ce5aa58a091d99e520d396

## How To Use
We encourage anyone looking for tooling/instructions, to interface with our API, to the following repository, CHP Client, https://github.com/di2ag/chp_client. CHP Client is a lightweight Python client that interfaces CHP. It is meant to be an easy-to-use wrapper utility to both run and build TRAPI queries that the CHP web service will understand. 

Our API is in active developement and is currently following [Translator Reasoner API standards 1.2.0](https://github.com/NCATSTranslator/ReasonerAPI)

Our API is currently live at: [https://chp-api.transltr.io](https://chp-api.transltr.io)

## Open Endpoints
* [query](query.md) : `POST /query/`
* [predicates](predicates.md) : `GET /predicates/`
* [curies](curies.md) : `GET /curies/`

## Other Notable Links
Our roadmap outlining or KP’s milestones and the progression of those milestones: https://github.com/di2ag/Connections-Hypothesis-Provider-Roadmap

Our NCATS Wiki Page: https://github.com/NCATSTranslator/Translator-All/wiki/Connections-Hypothesis-Provider

A repository for our reasoning code: https://github.com/di2ag/chp


## Contacts
Dr. Eugene Santos (PI): Eugene.Santos.Jr@dartmouth.edu

Joseph Gormley (Co-PI): jgormley@tuftsmedicalcenter.org

