from django.urls import path
from . import views

urlpatterns = [
    path('clients/', views.ClientListCreateView.as_view(), name='client-list'),
    path('clients/<uuid:uuid>/', views.ClientDetailView.as_view(), name='client-detail'),
    path('clients/<uuid:uuid>/cases/', views.client_cases_view, name='client-cases'),
    path('clients/<uuid:uuid>/contact-persons/', views.ContactPersonListCreateView.as_view(), name='contact-person-list'),
    path('contact-persons/<int:pk>/', views.ContactPersonDetailView.as_view(), name='contact-person-detail'),
]
