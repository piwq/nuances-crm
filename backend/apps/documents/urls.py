from django.urls import path
from . import views

urlpatterns = [
    path('documents/', views.DocumentListCreateView.as_view(), name='document-list'),
    path('document-templates/', views.DocumentTemplateListCreateView.as_view(), name='document-template-list'),
    path('document-templates/<int:pk>/', views.DocumentTemplateDetailView.as_view(), name='document-template-detail'),
    path('documents/generate/', views.generate_from_template_view, name='document-generate'),
    path('documents/<uuid:uuid>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<uuid:uuid>/download/', views.document_download_view, name='document-download'),
]
