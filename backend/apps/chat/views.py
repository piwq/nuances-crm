from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import ChatMessage
from .serializers import ChatMessageSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lawyers_list_view(request):
    """
    Все активные сотрудники (юристы И администраторы), кроме себя,
    с количеством непрочитанных сообщений от каждого.
    """
    from apps.accounts.models import CustomUser
    from apps.accounts.serializers import UserPublicSerializer
    from django.db.models import Count, Q

    lawyers = CustomUser.objects.filter(is_active=True).exclude(id=request.user.id).order_by('last_name', 'first_name')

    # Annotate with unread counts
    # messages where recipient is current user, sender is the lawyer, and is_read is False
    unread_counts = ChatMessage.objects.filter(
        recipient=request.user,
        is_read=False
    ).values('user_id').annotate(count=Count('id'))

    unread_map = {item['user_id']: item['count'] for item in unread_counts}

    data = []
    for lawyer in lawyers:
        serializer = UserPublicSerializer(lawyer, context={'request': request})
        lawyer_data = serializer.data
        lawyer_data['unread_count'] = unread_map.get(lawyer.id, 0)
        data.append(lawyer_data)
        
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read_view(request):
    """
    Marks all messages from a specific sender as read.
    """
    sender_id = request.data.get('sender_id')
    if not sender_id:
        return Response({'detail': 'sender_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
    ChatMessage.objects.filter(
        user_id=sender_id,
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
    
    return Response({'status': 'success'})


class ChatHistoryView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['text']

    def get_queryset(self):
        recipient_id = self.request.query_params.get('recipient_id')
        if not recipient_id:
            # Optionally return global messages if recipient_id is absent, 
            # but user specifically wants private chat between lawyers.
            return ChatMessage.objects.none()
        
        user = self.request.user
        # новые сообщения первыми: страница 1 — свежая переписка,
        # следующие страницы — всё более ранняя (фронт разворачивает)
        return ChatMessage.objects.filter(
            (Q(user=user) & Q(recipient_id=recipient_id)) |
            (Q(user_id=recipient_id) & Q(recipient=user))
        ).select_related('user', 'recipient').order_by('-created_at')
