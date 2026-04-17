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
    Returns a list of all lawyers except the current user,
    including unread message counts for each.
    """
    from apps.accounts.models import CustomUser
    from apps.accounts.serializers import UserSerializer
    from django.db.models import Count, Q
    
    lawyers = CustomUser.objects.filter(role=CustomUser.ROLE_LAWYER).exclude(id=request.user.id)
    
    # Annotate with unread counts
    # messages where recipient is current user, sender is the lawyer, and is_read is False
    unread_counts = ChatMessage.objects.filter(
        recipient=request.user,
        is_read=False
    ).values('user_id').annotate(count=Count('id'))
    
    unread_map = {item['user_id']: item['count'] for item in unread_counts}
    
    data = []
    for lawyer in lawyers:
        serializer = UserSerializer(lawyer, context={'request': request})
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
        return ChatMessage.objects.filter(
            (Q(user=user) & Q(recipient_id=recipient_id)) |
            (Q(user_id=recipient_id) & Q(recipient=user))
        ).order_by('created_at')
