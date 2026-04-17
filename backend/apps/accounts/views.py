from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from common.permissions import IsAdmin
from .models import CustomUser
from .serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer, MeUpdateSerializer


class LoginView(TokenObtainPairView):
    pass


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


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lawyers_list_view(request):
    lawyers = CustomUser.objects.filter(role=CustomUser.ROLE_LAWYER, is_active=True).order_by('last_name')
    return Response(UserSerializer(lawyers, many=True).data)
