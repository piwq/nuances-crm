from django.urls import path
from . import views

urlpatterns = [
    path('tasks/', views.TaskListCreateView.as_view(), name='task-list'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/complete/', views.complete_task_view, name='task-complete'),
    path('events/', views.EventListCreateView.as_view(), name='event-list'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event-detail'),
]
