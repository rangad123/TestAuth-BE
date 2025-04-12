from django.urls import path, re_path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('handle_command/', views.handle_command, name='handle_command'),
    path('Execute_command/', views.Execute_command, name='Execute_command'),
    path("user-login-success/", views.user_login_success, name="user-login-success"),

    #re_path(r'^react_app/.*$', views.react_app, name='react_app'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)