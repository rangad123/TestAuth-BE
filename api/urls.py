from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet,TestCaseViewSet,TestSuiteViewSet,RequirementViewSet
from .views import RegisterView, LoginView, ForgotPasswordView, ResetPasswordView
from .views import TestCaseTypeViewSet, TestCasePriorityViewSet, RequirementTypeViewSet, SendInvitationView, AcceptInvitationView, TestStepViewSet
from .views import UserListView, ProjectListView, TestCaseListView, TestSuiteListView, RequirementListView, RoleView, ProjectMemberDetailsView
from .views import OrganizationView, OrganizationProjectsView, ProjectMembersView, TestDataView, UserProjectDataView, OrganizationProjectDetailsView

# Router for viewsets
router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'testcases', TestCaseViewSet, basename='testcase')
router.register(r'testsuites', TestSuiteViewSet, basename='testsuite')
router.register(r'requirements', RequirementViewSet, basename='requirement')
router.register(r'testcase-types', TestCaseTypeViewSet,basename='test-type')
router.register(r'testcase-priorities', TestCasePriorityViewSet,basename='test-priorities')
router.register(r'requirement-types', RequirementTypeViewSet,basename='requirements-type')
router.register(r'teststeps', TestStepViewSet,basename='teststeps')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgotPassword/', ForgotPasswordView.as_view(), name='forgotPassword'),
    path('resetPassword/', ResetPasswordView.as_view(), name='resetPassword'),
    path('admin/users/', UserListView.as_view(), name='user-list'),
    path('admin/projects/', ProjectListView.as_view(), name='project-list'),
    path('admin/testcases/', TestCaseListView.as_view(), name='testcase-list'),
    path('admin/testsuites/', TestSuiteListView.as_view(), name='testsuite-list'),
    path('admin/requirements/', RequirementListView.as_view(), name='requirement-list'),
    path('admin/roles/', RoleView.as_view(), name='role-management'),
    path('send-invite/', SendInvitationView.as_view(), name='send_invite'),  # URL for sending invitation
    path('accept-invite/<str:token>/', AcceptInvitationView.as_view(), name='accept_invite'),  # URL for accepting the invitation
    path('organizations/', OrganizationView.as_view(), name='organization-list'),
    path('organizations/<int:organization_id>/projects/', OrganizationProjectsView.as_view(), name='organization-projects'),
    path('projects/<int:project_id>/members/', ProjectMembersView.as_view(), name='project-members'),
    path('testdata/<int:project_id>/', TestDataView.as_view(), name='testdata'),
    path('user-projects/<int:user_id>/', UserProjectDataView.as_view(), name='user-project-data'),
    path('organization/<int:organization_id>/projects/', OrganizationProjectDetailsView.as_view(), name='organization-projects'),
    path('project-member-details/', ProjectMemberDetailsView.as_view(), name='ProjectMemberDetailsView'),

]

# Include router URLs for viewsets
urlpatterns += router.urls
