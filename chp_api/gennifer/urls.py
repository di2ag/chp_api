from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'datasets', views.DatasetViewSet, basename='dataset')
router.register(r'studies', views.StudyViewSet, basename='study')
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'results', views.ResultViewSet, basename='result')
router.register(r'algorithms', views.AlgorithmViewSet, basename='algorithm')
router.register(r'algorithm_instances', views.AlgorithmInstanceViewSet, basename='algorithm_instance')
router.register(r'hyperparameters', views.HyperparameterViewSet, basename='hyperparameter')
router.register(r'hyperparameter_instances', views.HyperparameterInstanceViewSet, basename='hyperparameter_instance')
router.register(r'genes', views.GeneViewSet, basename='genes')
router.register(r'analyses', views.UserAnalysisSessionViewSet, basename='analyses')

urlpatterns = [
    path('', include(router.urls)),
    path('run/', views.run.as_view()),
    path('graph/', views.CytoscapeView.as_view()),
    path('download_study/<int:study_id>', views.StudyDownloadView.as_view())
    ]
