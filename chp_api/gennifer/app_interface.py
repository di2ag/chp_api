from asyncio import constants
from .trapi_interface import TrapiInterface
from .apps import GenniferConfig
from reasoner_pydantic import MetaKnowledgeGraph, Message
from typing import TYPE_CHECKING, Union, List

def get_app_config(message: Union[Message, None]) -> GenniferConfig:
    return GenniferConfig


def get_trapi_interface(get_app_config: GenniferConfig = get_app_config(None)):
    return TrapiInterface(trapi_version='1.5')


def get_meta_knowledge_graph() -> MetaKnowledgeGraph:
    interface: TrapiInterface = get_trapi_interface()
    return interface.get_meta_knowledge_graph()


def get_response(consistent_queries: List[Message], logger):
    """ Should return app responses plus app_logs, status, and description information."""
    responses = []
    interface = get_trapi_interface()
    for consistent_query in consistent_queries:
        response = interface.get_response(consistent_query, logger)
        responses.append(response)
    return responses
