from rest_framework import serializers
from .models import User, Project, TestCase, TestSuite,Requirement,Role,ProjectInvitation,ProjectMember
from .models import TestCaseType, TestCasePriority, RequirementType, TestData,TestStep, EXEDownload

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
    class Meta:
        model = ProjectMember
        fields = ['id', 'project', 'user', 'added_at']

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


class EXEDownloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = EXEDownload
        fields = '__all__'