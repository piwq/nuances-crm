from datetime import datetime
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import django_filters
from django.utils import timezone

from .models import Task, Event
from .serializers import TaskSerializer, EventSerializer


class TaskFilter(django_filters.FilterSet):
    due_date_before = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')
    due_date_after = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')

    class Meta:
        model = Task
        fields = ['case', 'assigned_to', 'status', 'priority']


class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    filterset_class = TaskFilter
    ordering_fields = ['due_date', 'priority', 'created_at']
    ordering = ['due_date']

    def get_queryset(self):
        qs = Task.objects.select_related('case', 'assigned_to')
        if self.request.user.is_lawyer:
            from django.db.models import Q
            qs = qs.filter(
                Q(assigned_to=self.request.user) |
                Q(case__assigned_lawyers=self.request.user) |
                Q(case__lead_lawyer=self.request.user)
            ).distinct()
        return qs


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        qs = Task.objects.select_related('case', 'assigned_to')
        if self.request.user.is_lawyer:
            from django.db.models import Q
            qs = qs.filter(
                Q(assigned_to=self.request.user) |
                Q(case__assigned_lawyers=self.request.user) |
                Q(case__lead_lawyer=self.request.user)
            ).distinct()
        return qs


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def complete_task_view(request, pk):
    try:
        # Secure the object retrieval with IDOR check
        qs = Task.objects.all()
        if request.user.is_lawyer:
            from django.db.models import Q
            qs = qs.filter(
                Q(assigned_to=request.user) |
                Q(case__assigned_lawyers=request.user) |
                Q(case__lead_lawyer=request.user)
            ).distinct()
        
        task = qs.get(pk=pk)
    except Task.DoesNotExist:
        return Response({'detail': 'Задача не найдена или доступ запрещен.'}, status=status.HTTP_404_NOT_FOUND)

    task.status = Task.STATUS_DONE
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at'])
    return Response(TaskSerializer(task, context={'request': request}).data)


class EventFilter(django_filters.FilterSet):
    start = django_filters.DateTimeFilter(field_name='start_datetime', lookup_expr='gte')
    end = django_filters.DateTimeFilter(field_name='start_datetime', lookup_expr='lte')

    class Meta:
        model = Event
        fields = ['case', 'event_type']


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    filterset_class = EventFilter
    ordering = ['start_datetime']

    def get_queryset(self):
        qs = Event.objects.select_related('case').prefetch_related('attendees')
        if self.request.user.is_lawyer:
            from django.db.models import Q
            qs = qs.filter(
                Q(attendees=self.request.user) |
                Q(case__assigned_lawyers=self.request.user) |
                Q(case__lead_lawyer=self.request.user)
            ).distinct()
        return qs


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        qs = Event.objects.select_related('case').prefetch_related('attendees')
        if self.request.user.is_lawyer:
            from django.db.models import Q
            qs = qs.filter(
                Q(attendees=self.request.user) |
                Q(case__assigned_lawyers=self.request.user) |
                Q(case__lead_lawyer=self.request.user)
            ).distinct()
        return qs
