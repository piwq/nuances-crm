from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from common.permissions import IsAdmin
from .models import CustomUser
from .serializers import (
    UserSerializer, UserPublicSerializer, UserCreateSerializer,
    UserUpdateSerializer, MeUpdateSerializer,
)


class LoginView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


class TokenRefreshViewCustom(TokenRefreshView):
    pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except TokenError:
        return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_view(request):
    if request.method == 'GET':
        return Response(UserSerializer(request.user).data)

    serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(UserSerializer(request.user).data)


class UserListCreateView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all().order_by('last_name', 'first_name')
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Отвечаем в формате списка: фронтенд вставляет созданного пользователя
        # прямо в таблицу, а в UserCreateSerializer нет ни id, ни is_active —
        # строка получалась нерабочей (кнопки уходили на /users/undefined/)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # причина та же, что и в create: UserUpdateSerializer не содержит id,
        # и строка таблицы после сохранения не находила себя по нему
        return Response(UserSerializer(self.get_object()).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    current = request.data.get('current_password', '')
    new_password = request.data.get('new_password', '')
    if not request.user.check_password(current):
        return Response({'detail': 'Неверный текущий пароль.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new_password, user=request.user)
    except DjangoValidationError as e:
        return Response({'detail': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])
    return Response({'detail': 'Пароль изменён.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def telegram_link_view(request):
    """Deep-link для привязки Telegram: t.me/<бот>?start=<одноразовый токен>."""
    from apps.notifications.telegram import get_bot_username
    from .telegram_link import create_link_token
    username = get_bot_username()
    if not username:
        return Response(
            {'detail': 'Telegram-бот не настроен (TELEGRAM_BOT_TOKEN пуст).'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    token = create_link_token(request.user)
    return Response({'link': f'https://t.me/{username}?start={token}'})


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def calendar_link_view(request):
    """GET — текущая ссылка ICS-подписки (404, если нет),
    POST — выдать или перевыпустить, DELETE — отозвать."""
    import uuid as uuid_lib

    if request.method == 'GET':
        if not request.user.calendar_token:
            return Response(status=status.HTTP_404_NOT_FOUND)
        path = f'/api/v1/calendar/{request.user.calendar_token}.ics'
        return Response({'path': path, 'url': request.build_absolute_uri(path)})

    if request.method == 'DELETE':
        request.user.calendar_token = None
        request.user.save(update_fields=['calendar_token'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # перевыпуск по требованию: старая ссылка сразу перестаёт работать
    if request.user.calendar_token is None or request.data.get('regenerate'):
        request.user.calendar_token = uuid_lib.uuid4()
        request.user.save(update_fields=['calendar_token'])

    path = f'/api/v1/calendar/{request.user.calendar_token}.ics'
    return Response({'path': path, 'url': request.build_absolute_uri(path)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lawyers_list_view(request):
    lawyers = CustomUser.objects.filter(role=CustomUser.ROLE_LAWYER, is_active=True).order_by('last_name')
    return Response(UserPublicSerializer(lawyers, many=True, context={'request': request}).data)
