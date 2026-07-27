from django.urls import path
from . import views

urlpatterns = [
    path('tasks/', views.TaskListCreateView.as_view(), name='task-list'),
    path('tasks/bulk/', views.tasks_bulk_view, name='task-bulk'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/complete/', views.complete_task_view, name='task-complete'),
    path('checklists/', views.CaseChecklistListCreateView.as_view(), name='checklist-list'),
    path('checklists/<int:pk>/', views.CaseChecklistDetailView.as_view(), name='checklist-detail'),
    path('cases/<uuid:uuid>/apply-checklist/', views.apply_checklist_view, name='case-apply-checklist'),
    path('events/', views.EventListCreateView.as_view(), name='event-list'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event-detail'),
    path('calendar/<uuid:token>.ics', views.calendar_feed_view, name='calendar-feed'),
]
