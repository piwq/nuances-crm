from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ActivityLog
from .serializers import ActivityLogSerializer


class CaseActivityLogView(generics.ListAPIView):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []  # queryset нарезан — глобальный OrderingFilter уронит его

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
    filter_backends = []  # queryset нарезан — глобальный OrderingFilter уронит его

    def get_queryset(self):
        qs = ActivityLog.objects.select_related('user')
        if self.request.user.is_scoped:
            from apps.cases.models import Case
            from apps.documents.models import Document
            from common.scoping import scope_cases
            my_cases = scope_cases(Case.objects.all(), self.request.user)
            case_uuids = my_cases.values_list('uuid', flat=True)
            # в логах документов/клиентов лежит их собственный uuid, не uuid дела
            doc_uuids = Document.objects.filter(case__in=my_cases).values_list('uuid', flat=True)
            client_uuids = my_cases.values_list('client__uuid', flat=True)
            qs = qs.filter(
                Q(resource_uuid__in=case_uuids) |
                Q(resource_uuid__in=doc_uuids) |
                Q(resource_uuid__in=client_uuids) |
                Q(user=self.request.user)
            )
        return qs[:30]
