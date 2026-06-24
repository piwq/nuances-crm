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
