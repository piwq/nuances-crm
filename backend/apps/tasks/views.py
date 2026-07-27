from datetime import datetime
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
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
    search_fields = ['title', 'description', 'case__title']
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
    task.save(update_fields=['status', 'completed_at', 'updated_at'])
    return Response(TaskSerializer(task, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])  # доступ даёт сам секретный токен в URL
def calendar_feed_view(request, token):
    """ICS-подписка: календарь пользователя для телефона/Google Calendar."""
    from django.http import HttpResponse, Http404
    from apps.accounts.models import CustomUser
    from .icalendar import build_calendar, user_calendar_events

    user = CustomUser.objects.filter(calendar_token=token, is_active=True).first()
    if not user:
        raise Http404

    name = f'CRM «Нюансы» — {user.get_full_name() or user.username}'
    body = build_calendar(name, user_calendar_events(user))
    response = HttpResponse(body, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="nuances.ics"'
    response['Cache-Control'] = 'no-cache'
    return response


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
