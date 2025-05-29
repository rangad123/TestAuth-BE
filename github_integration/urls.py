from . import views
from django.urls import path
from .views import *

urlpatterns = [
    path('testcase/', TestCaseView.as_view(), name='testcase_view'),
    path('project/', ProjectView.as_view(), name='Project_View'),
    path('teststep/', TestStepView.as_view(), name='Teststep_View'),
    path('testsuite/', TestSuiteView.as_view(), name='Testsuite_View'),
    path('case_report/', ReportTestCaseView.as_view(), name='ReportCase_View'),
    path('suite_report/', ReportTestSuiteView.as_view(), name='ReportSuite_View'),



    path('run_testsuite/', views.run_testsuite, name='run_testsuite'),
    path('run_testcase/', views.run_testcase, name='run_testcase'),
    path('get_path/', views.get_available_paths, name='get_path'),
    path('clone_repo/', views.clone_repository_to_path, name='clone_repo'),




    
    # GitHub Integration URLs
    path('github/login/', views.github_login, name='github_login'),
    path('github/', views.github_callback, name='github_callback'),
    path('github/repositories/', views.list_repositories, name='list_repositories'),
    path('github/select_repository/', views.select_repository, name='select_repository'),
    path('github/sync/', views.github_sync, name='github_sync'),
]
