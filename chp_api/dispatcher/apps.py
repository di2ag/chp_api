import requests_cache

from django.apps import AppConfig


class DispatcherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dispatcher'

    # Install a requests cache
    requests_cache.install_cache('dispatcher_cache')

