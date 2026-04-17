from django.urls import path
from . import views

urlpatterns = [
    path('cases/', views.CaseListCreateView.as_view(), name='case-list'),
    path('cases/stats/', views.case_stats_view, name='case-stats'),
    path('cases/<uuid:uuid>/', views.CaseDetailView.as_view(), name='case-detail'),
    path('cases/<uuid:uuid>/assign-lawyer/', views.assign_lawyer_view, name='case-assign-lawyer'),
    path('cases/<uuid:uuid>/remove-lawyer/<int:user_id>/', views.remove_lawyer_view, name='case-remove-lawyer'),
    path('cases/<uuid:uuid>/change-status/', views.change_status_view, name='case-change-status'),
]
