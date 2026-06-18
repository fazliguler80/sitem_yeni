from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from bina import views

urlpatterns = [
    path('admin/site-degistir/<int:site_id>/', views.site_degistir, name='site_degistir'),
    path('', views.home_page, name='home'),
    path('admin/', admin.site.urls),
    path('portal/', include('bina.portal_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)