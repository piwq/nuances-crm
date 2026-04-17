from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', views.TokenRefreshViewCustom.as_view(), name='auth-refresh'),
    path('auth/logout/', views.logout_view, name='auth-logout'),
    path('auth/me/', views.me_view, name='auth-me'),
    path('users/', views.UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/lawyers/', views.lawyers_list_view, name='user-lawyers'),
]
