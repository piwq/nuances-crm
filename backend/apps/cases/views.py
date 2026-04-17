from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q

from common.utils import log_activity

from common.permissions import IsAdmin, IsLawyerAssignedToCase
from .models import Case
from .serializers import CaseSerializer, CaseListSerializer
from .filters import CaseFilter


class CaseListCreateView(generics.ListCreateAPIView):
    filterset_class = CaseFilter
    ordering_fields = ['created_at', 'title', 'opened_at', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CaseListSerializer
        return CaseSerializer

    def get_queryset(self):
        qs = Case.objects.select_related('client', 'lead_lawyer').prefetch_related('assigned_lawyers', 'tasks')
        if self.request.user.is_lawyer:
            qs = qs.filter(
                Q(assigned_lawyers=self.request.user) | Q(lead_lawyer=self.request.user)
            ).distinct()
        return qs


class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'uuid'

    def get_queryset(self):
        qs = Case.objects.select_related('client', 'lead_lawyer').prefetch_related(
            'assigned_lawyers', 'documents', 'tasks', 'time_entries'
        )
        if self.request.user.is_lawyer:
            qs = qs.filter(
                Q(assigned_lawyers=self.request.user) | Q(lead_lawyer=self.request.user)
            ).distinct()
        return qs

    def get_serializer_class(self):
        return CaseSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdmin()]
        return [IsAuthenticated(), IsLawyerAssignedToCase()]

    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(
            user=self.request.user,
            action="UPDATE",
            resource_type="Case",
            resource_uuid=instance.uuid,
            description=f"Обновлено дело: {instance.title}"
        )

    def perform_destroy(self, instance):
        uuid = instance.uuid
        title = instance.title
        instance.delete()
        log_activity(
            user=self.request.user,
            action="DELETE",
            resource_type="Case",
            resource_uuid=uuid,
            description=f"Удалено дело: {title}"
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_lawyer_view(request, uuid):
    try:
        # Secure retrieval: Only admin OR assigned/lead lawyer can view case details to assign others?
        # Actually, assignment is restricted to ADMIN only (line 60), but we should still
        # ensure the case exists.
        case = Case.objects.get(uuid=uuid)
    except Case.DoesNotExist:
        return Response({'detail': 'Дело не найдено.'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_admin:
        return Response({'detail': 'Только администратор может назначать юристов.'}, status=status.HTTP_403_FORBIDDEN)

    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'detail': 'user_id обязателен.'}, status=status.HTTP_400_BAD_REQUEST)

    from apps.accounts.models import CustomUser
    try:
        lawyer = CustomUser.objects.get(pk=user_id, role=CustomUser.ROLE_LAWYER)
    except CustomUser.DoesNotExist:
        return Response({'detail': 'Юрист не найден.'}, status=status.HTTP_404_NOT_FOUND)

    case.assigned_lawyers.add(lawyer)
    log_activity(
        user=request.user,
        action="ASSIGN_LAWYER",
        resource_type="Case",
        resource_uuid=case.uuid,
        description=f"Назначен юрист {lawyer.get_full_name()} на дело {case.title}"
    )
    return Response({'detail': 'Юрист назначен.'})


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def remove_lawyer_view(request, uuid, user_id):
    try:
        case = Case.objects.get(uuid=uuid)
    except Case.DoesNotExist:
        return Response({'detail': 'Дело не найдено.'}, status=status.HTTP_404_NOT_FOUND)

    case.assigned_lawyers.remove(user_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def change_status_view(request, uuid):
    try:
        qs = Case.objects.all()
        if request.user.is_lawyer:
            qs = qs.filter(
                Q(assigned_lawyers=request.user) | Q(lead_lawyer=request.user)
            ).distinct()
        case = qs.get(uuid=uuid)
    except Case.DoesNotExist:
        return Response({'detail': 'Дело не найдено или доступ запрещен.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if new_status not in dict(Case.STATUS_CHOICES):
        return Response({'detail': 'Недопустимый статус.'}, status=status.HTTP_400_BAD_REQUEST)

    case.status = new_status
    if new_status == Case.STATUS_CLOSED and not case.closed_at:
        from datetime import date
        case.closed_at = date.today()
    case.save(update_fields=['status', 'closed_at'])
    return Response(CaseSerializer(case, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_stats_view(request):
    qs = Case.objects.all()
    if request.user.is_lawyer:
        qs = qs.filter(
            Q(assigned_lawyers=request.user) | Q(lead_lawyer=request.user)
        ).distinct()
    
    total = qs.count()
    by_status = {
        row['status']: row['count']
        for row in qs.values('status').annotate(count=Count('id'))
    }
    by_category = {
        row['category']: row['count']
        for row in qs.values('category').annotate(count=Count('id'))
    }
    return Response({
        'total': total,
        'by_status': by_status,
        'by_category': by_category,
    })
