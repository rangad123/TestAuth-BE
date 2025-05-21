from . import views
from django.urls import path

urlpatterns = [
    path('create_testcase/', views.create_testcase, name='create_testcase'),
    path('run_testsuite/', views.run_testsuite, name='run_testsuite'),
    path('run_testcase/', views.run_testcase, name='run_testcase'),
    path('get_testcase/<str:testcase_id>/<int:user_id>/', views.get_testcase, name='get_testcase'),
    path('get_path/', views.get_available_paths, name='get_path'),
    path('clone_repo/', views.clone_repository_to_path, name='clone_repo'),




    
    # GitHub Integration URLs
    path('github/login/', views.github_login, name='github_login'),
    path('github/callback/', views.github_callback, name='github_callback'),
    path('github/repositories/', views.list_repositories, name='list_repositories'),
    path('github/select_repository/', views.select_repository, name='select_repository'),
]
