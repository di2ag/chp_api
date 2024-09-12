from django.urls import path, include

from .views import UserDetails

urlpatterns = [
        path('me/', UserDetails.as_view())
        ]
