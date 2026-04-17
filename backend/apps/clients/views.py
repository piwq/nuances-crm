from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.utils import log_activity

from common.permissions import IsAdmin
from .models import Client, ContactPerson
from .serializers import ClientSerializer, ClientListSerializer, ContactPersonSerializer
from .filters import ClientFilter


class ClientListCreateView(generics.ListCreateAPIView):
    queryset = Client.objects.all()
    filterset_class = ClientFilter
    ordering_fields = ['created_at', 'last_name', 'company_name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ClientListSerializer
        return ClientSerializer


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.prefetch_related('contact_persons')
    serializer_class = ClientSerializer
    lookup_field = 'uuid'

    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(
            user=self.request.user,
            action="UPDATE",
            resource_type="Client",
            resource_uuid=instance.uuid,
            description=f"Обновлен клиент: {instance.display_name}"
        )

    def perform_destroy(self, instance):
        uuid = instance.uuid
        name = instance.display_name
        instance.delete()
        log_activity(
            user=self.request.user,
            action="DELETE",
            resource_type="Client",
            resource_uuid=uuid,
            description=f"Удален клиент: {name}"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_cases_view(request, uuid):
    from apps.cases.models import Case
    from apps.cases.serializers import CaseListSerializer
    try:
        client = Client.objects.get(uuid=uuid)
    except Client.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    cases = Case.objects.filter(client=client).order_by('-created_at')
    return Response(CaseListSerializer(cases, many=True, context={'request': request}).data)


class ContactPersonListCreateView(generics.ListCreateAPIView):
    serializer_class = ContactPersonSerializer

    def get_queryset(self):
        return ContactPerson.objects.filter(client__uuid=self.kwargs['uuid'])

    def perform_create(self, serializer):
        client = Client.objects.get(uuid=self.kwargs['uuid'])
        serializer.save(client=client)


class ContactPersonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ContactPerson.objects.all()
    serializer_class = ContactPersonSerializer
