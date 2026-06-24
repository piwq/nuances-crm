from django.urls import path
from . import views

urlpatterns = [
    path('cases/<uuid:uuid>/history/', views.CaseActivityLogView.as_view(), name='case-history'),
]
