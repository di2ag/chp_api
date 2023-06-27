import requests
from django.conf import settings

from ..models import Algorithm


def run():
    Algorithm.objects.all().delete()
    for url in settings.GENNIFER_ALGORITHM_URLS:
        algo_info = requests.get(f'{url}/info').json()
        algo = Algorithm.objects.create(
                name=algo_info["name"],
                url=url,
                edge_weight_description=algo_info["edge_weight_description"],
                edge_weight_type=algo_info["edge_weight_type"],
                description=algo_info["description"],
                directed=algo_info["directed"],
                )
        algo.save()