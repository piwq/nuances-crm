from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.utils import log_activity
import django_filters

from common.utils import serve_file_response
from common.permissions import IsAdmin
from .models import Document, DocumentTemplate
from .serializers import DocumentSerializer, DocumentTemplateSerializer


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


class DocumentTemplateListCreateView(generics.ListCreateAPIView):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer

    def get_permissions(self):
        # просматривать шаблоны может любой, загружать — только админ
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [IsAuthenticated()]


class DocumentTemplateDetailView(generics.RetrieveDestroyAPIView):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAdmin]


def _build_template_context(case):
    from datetime import date
    client = case.client
    return {
        'case_number': case.case_number,
        'case_title': case.title,
        'case_category': case.get_category_display(),
        'court_name': case.court_name,
        'court_case_number': case.court_case_number,
        'client_name': client.display_name if client else '',
        'client_email': client.email if client else '',
        'client_phone': client.phone if client else '',
        'client_address': (client.address or client.legal_address) if client else '',
        'client_inn': client.tax_id if client else '',
        'lead_lawyer': case.lead_lawyer.get_full_name() if case.lead_lawyer else '',
        'today': date.today().strftime('%d.%m.%Y'),
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_from_template_view(request):
    """Сгенерировать документ из .docx-шаблона и прикрепить к делу."""
    from io import BytesIO
    from django.core.files.base import ContentFile
    from apps.cases.models import Case

    template_id = request.data.get('template')
    case_id = request.data.get('case')
    if not template_id or not case_id:
        return Response({'detail': 'Нужны template и case.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        template = DocumentTemplate.objects.get(pk=template_id)
        case = Case.objects.select_related('client', 'lead_lawyer').get(pk=case_id)
    except (DocumentTemplate.DoesNotExist, Case.DoesNotExist):
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.user.is_lawyer:
        if not (case.assigned_lawyers.filter(pk=request.user.pk).exists() or
                case.lead_lawyer_id == request.user.pk):
            return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        from docxtpl import DocxTemplate
        template.file.open('rb')
        try:
            src = BytesIO(template.file.read())
        finally:
            template.file.close()
        doc = DocxTemplate(src)
        doc.render(_build_template_context(case))
        out = BytesIO()
        doc.save(out)
        out.seek(0)
    except Exception as e:
        return Response({'detail': f'Ошибка генерации документа: {e}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    filename = f'{template.name}_{case.case_number}.docx'
    document = Document.objects.create(
        case=case,
        title=template.name,
        document_type=template.document_type,
        file=ContentFile(out.read(), name=filename),
        uploaded_by=request.user,
        description=f'Сгенерировано из шаблона «{template.name}»',
    )
    log_activity(
        user=request.user,
        action="CREATE",
        resource_type="Document",
        resource_uuid=document.uuid,
        description=f"Сгенерирован документ из шаблона: {document.title}",
    )
    return Response(DocumentSerializer(document, context={'request': request}).data,
                    status=status.HTTP_201_CREATED)


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
