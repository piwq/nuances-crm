from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.utils import log_activity
import django_filters

from common.utils import serve_file_response
from common.permissions import IsAdmin
from .models import Document
from .serializers import DocumentSerializer


class DocumentFilter(django_filters.FilterSet):
    class Meta:
        model = Document
        fields = ['case', 'document_type', 'uploaded_by']


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    filterset_class = DocumentFilter
    ordering_fields = ['uploaded_at', 'title']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        qs = Document.objects.select_related('uploaded_by', 'case')
        if self.request.user.is_lawyer:
            from django.db.models import Q
            qs = qs.filter(
                Q(case__assigned_lawyers=self.request.user) | Q(case__lead_lawyer=self.request.user)
            ).distinct()
        return qs


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    lookup_field = 'uuid'

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(
            user=self.request.user,
            action="UPDATE",
            resource_type="Document",
            resource_uuid=instance.uuid,
            description=f"Обновлен документ: {instance.title}"
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        uuid = instance.uuid
        title = instance.title
        instance.file.delete(save=False)
        instance.delete()
        log_activity(
            user=request.user,
            action="DELETE",
            resource_type="Document",
            resource_uuid=uuid,
            description=f"Удален документ: {title}"
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_download_view(request, uuid):
    try:
        doc = Document.objects.get(uuid=uuid)
    except Document.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.user.is_lawyer:
        case = doc.case
        if not (case.assigned_lawyers.filter(pk=request.user.pk).exists() or
                case.lead_lawyer_id == request.user.pk):
            return Response(status=status.HTTP_403_FORBIDDEN)

    log_activity(
        user=request.user,
        action="DOWNLOAD",
        resource_type="Document",
        resource_uuid=doc.uuid,
        description=f"Скачан документ: {doc.title}"
    )
    return serve_file_response(doc.file)
