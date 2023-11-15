"""CHP Core API URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('query/', views.query.as_view()),
    path('query', views.query.as_view()),
    path('meta_knowledge_graph/', views.meta_knowledge_graph.as_view()),
    path('versions/', views.versions.as_view()),
    path('transactions/', views.TransactionList.as_view(), name='transaction-list'),
    path('recent/', views.RecentTransactionList.as_view(), name='recent-transaction-list'),
    path('transactions/<str:pk>/', views.TransactionDetail.as_view(), name='transactions-detail')
]
