from rest_framework import serializers
from .models import User, Project, TestCase, TestSuite,Requirement,Role,ProjectInvitation,ProjectMember
from .models import TestCaseType, TestCasePriority, RequirementType, TestData,TestStep

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'password', 'phone', 'country', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {'password': {'write_only': True}}

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']

class TestDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestData
        fields = ['id', 'project', 'url']

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'project_id', 'name', 'description', 'project_type','user_id', 'created_at', 'updated_at']

class ProjectInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInvitation
        fields = ['id', 'project', 'invite_by', 'recipient_email', 'token', 'status', 'created_at']


class ProjectMemberSerializer(serializers.ModelSerializer):
    invitation = ProjectInvitationSerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'project', 'user', 'invitation', 'added_at']

class BulkTestStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStep
        fields = ['id', 'testcase', 'step_number', 'step_description', 'teststep_result', 'step_coordinates']

class TestCaseSerializer(serializers.ModelSerializer):
    steps = BulkTestStepSerializer(many=True, read_only=True)

    class Meta:
        model = TestCase
        fields = ['id', 'name', 'project_id', 'testcase_type', 'testcase_priority','steps']

class TestSuiteSerializer(serializers.ModelSerializer):
    labels = serializers.ListField(
        child=serializers.CharField()  # Ensure the child field is a string (CharField)
    )
    testcase = serializers.ListField(
        child=serializers.CharField(), required=False  # Allow single or multiple test cases
    )
    class Meta:
        model = TestSuite
        fields = ['id', 'title', 'description', 'pre_requisite', 'labels', 'project_id', 'testcase']

class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ['id', 'project_id', 'title', 'description', 'type', 'start_date', 'completion_date', 'labels']


#Database types Serializers

class TestCaseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseType
        fields = '__all__'

class TestCasePrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCasePriority
        fields = '__all__'

class RequirementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequirementType
        fields = '__all__'


#for member details 
# api/serializers.py

from exe_installer.models import EXEDownload
from .models import Project, TestCase, ProjectMember, User
from rest_framework import serializers

class MemberTestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'name', 'testcase_type', 'testcase_priority']

class MemberEXEDownloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = EXEDownload
        fields = ['id', 'os_name', 'os_version', 'ip_address', 'download_count', 'last_downloaded', 'file_version', 'is_update_available']

class MemberProjectSerializer(serializers.ModelSerializer):
    test_cases = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'project_id', 'name', 'project_type', 'description', 'test_cases']

    def get_test_cases(self, project):
        user = self.context.get('user')
        return MemberTestCaseSerializer(project.test_cases.filter(project=project), many=True).data

class ProjectMemberDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    projects = serializers.SerializerMethodField()
    exe_downloads = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'projects', 'exe_downloads']

    def get_projects(self, obj):
        user = obj.user
        projects = Project.objects.filter(members__user=user).distinct()
        return MemberProjectSerializer(projects, many=True, context={'user': user}).data

    def get_exe_downloads(self, obj):
        return MemberEXEDownloadSerializer(EXEDownload.objects.filter(user=obj.user), many=True).data
