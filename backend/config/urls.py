from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.clients.urls')),
    path('api/v1/', include('apps.cases.urls')),
    path('api/v1/', include('apps.documents.urls')),
    path('api/v1/', include('apps.tasks.urls')),
    path('api/v1/', include('apps.billing.urls')),
    path('api/v1/chat/', include('apps.chat.urls')),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
