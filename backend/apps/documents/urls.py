from django.urls import path
from . import views

urlpatterns = [
    path('documents/', views.DocumentListCreateView.as_view(), name='document-list'),
    path('documents/<uuid:uuid>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<uuid:uuid>/download/', views.document_download_view, name='document-download'),
]
