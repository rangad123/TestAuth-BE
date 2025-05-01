from django.urls import path, re_path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('handle_command/', views.handle_command, name='handle_command'),
    path('execute_test_case/', views.Execute_command, name='Execute_command'),
    path('run_testsuite/', views.run_testsuite, name='run_testsuite'),
    path('wait/', views.wait, name='wait'),
    path('insert_screen/', views.insert_screen, name='insert_screen'),
    path('get_browser_tabs/', views.get_browser_tabs, name='get_browser_tabs'),
    path('process_browser_tab/', views.process_browser_tab, name='process_browser_tab'),




    

    #re_path(r'^react_app/.*$', views.react_app, name='react_app'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)