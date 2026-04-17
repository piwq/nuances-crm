from django.urls import path
from . import views

urlpatterns = [
    path('history/', views.ChatHistoryView.as_view(), name='chat-history'),
    path('lawyers/', views.lawyers_list_view, name='chat-lawyers'),
    path('mark-read/', views.mark_as_read_view, name='mark-read'),
]
