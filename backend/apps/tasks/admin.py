from django.contrib import admin
from .models import Task, Event


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'case', 'assigned_to', 'priority', 'status', 'due_date']
    list_filter = ['status', 'priority']
    search_fields = ['title', 'case__title']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'case', 'start_datetime', 'location']
    list_filter = ['event_type']
