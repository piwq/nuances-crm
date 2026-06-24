from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ActivityLog
from .serializers import ActivityLogSerializer


class CaseActivityLogView(generics.ListAPIView):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        uuid = self.kwargs['uuid']
        return ActivityLog.objects.filter(
            resource_type="Case",
            resource_uuid=uuid,
        ).select_related('user')[:100]


class RecentActivityView(generics.ListAPIView):
    """Global activity feed: last 30 events, scoped to the user's cases for lawyers."""
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ActivityLog.objects.select_related('user')
        if self.request.user.is_lawyer:
            from apps.cases.models import Case
            my_uuids = Case.objects.filter(
                Q(assigned_lawyers=self.request.user) | Q(lead_lawyer=self.request.user)
            ).values_list('uuid', flat=True)
            qs = qs.filter(resource_uuid__in=my_uuids)
        return qs[:30]
