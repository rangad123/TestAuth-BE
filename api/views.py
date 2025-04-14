import os
import json
import time
import shlex
import subprocess
from urllib.parse import urlparse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets
from rest_framework import status, permissions
from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from django.core.mail import send_mail
from .models import Project, TestCase, TestSuite, Requirement, TestData, TestStep
from .models import TestCaseType, TestCasePriority, RequirementType, EXEDownload
from .serializers import TestCaseTypeSerializer, TestCasePrioritySerializer, RequirementTypeSerializer, ProjectInvitationSerializer, ProjectMemberSerializer
from .serializers import ProjectSerializer, TestCaseSerializer, TestSuiteSerializer, RequirementSerializer, RoleSerializer, TestDataSerializer, BulkTestStepSerializer
from django.contrib.sites.shortcuts import get_current_site
import uuid
import secrets
from .models import User, Role, ProjectInvitation, ProjectMember
from .serializers import UserSerializer, EXEDownloadSerializer


class RoleView(APIView):
    def get(self, request):
        """
        Retrieve all roles.
        """
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new role.
        Restrict creation to the predefined roles.
        """
        predefined_roles = {1: "Admin", 2: "Organization", 3: "Project Member"}
        role_id = request.data.get("id")
        role_name = request.data.get("name")

        # Check if the role ID is within the predefined range
        if role_id not in predefined_roles:
            return Response({"error": "Invalid role ID. Allowed IDs are 1, 2, and 3."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the role name matches the predefined role for the given ID
        if predefined_roles[role_id] != role_name:
            return Response({"error": f"Role name must be '{predefined_roles[role_id]}' for ID {role_id}."}, status=status.HTTP_400_BAD_REQUEST)

        # Create or get the role
        role, created = Role.objects.get_or_create(id=role_id, defaults={"name": role_name})
        if not created:
            return Response({"message": "Role already exists."}, status=status.HTTP_200_OK)

        serializer = RoleSerializer(role)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

#Register Api
class RegisterView(APIView):
    def post(self, request):
        data = request.data

        
        if User.objects.filter(email=data['email']).exists():
            return Response(
                {"success": False, "message": "Email is already registered."},
                status=status.HTTP_400_BAD_REQUEST
            )

       
        hashed_password = make_password(data['password'])

        
        user = User.objects.create(
            name=data['name'],
            email=data['email'],
            password=hashed_password,
            phone=data['phone'],
            country=data['country'],
            role_id=data['roleid']
        )

        serializer = UserSerializer(user)
        return Response(
            {"success": True, "message": "User registered successfully!", "user": serializer.data},
            status=status.HTTP_201_CREATED
        )



#Login View Api
class LoginView(APIView):
    def post(self, request):
        data = request.data
        try:
            user = User.objects.get(email=data['email'])
            if check_password(data['password'], user.password):
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "success": True,
                        "message": "Login successful!",
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "user": {
                            "id":user.id,
                            "roleId":user.role_id,
                            "name": user.name,
                            "email": user.email,
                            "user_id":user.created_by,
                            "created_at": user.created_at,
                            "updated_at": user.updated_at
                        }
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"success": False, "message": "Invalid credentials."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid credentials."},
                status=status.HTTP_400_BAD_REQUEST
            )


# forgotPassword Api
class ForgotPasswordView(APIView):
    def post(self, request):
        data = request.data
        try:
            user = User.objects.get(email=data['email'])
            
            
            token = str(uuid.uuid4())
            user.reset_token = token  
            user.save()

            current_site = get_current_site(request)
            reset_link = f"https://testerally.ai/resetPassword/{token}"

            send_mail(
                'Password Reset Request',
                f'Click here to reset your password: {reset_link}',  # Reset link
                'suriya.prakash@crowd4test.com',  # From email address
                [data['email']],  # User's email
                fail_silently=False,
            )

            return Response(
                {
                    "success": True,
                    "message": "Password reset link has been sent to your email.",
                    "reset_link": reset_link  # For testing purposes
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "Email not found."},
                status=status.HTTP_400_BAD_REQUEST
            )


#ResetPassword Api
class ResetPasswordView(APIView):
    def post(self, request):
        data = request.data
        try:
            
            user = User.objects.get(reset_token=data['uuid'])
            
            
            user.password = make_password(data['password'])
            
            
            user.reset_token = None
            user.save()

            return Response(
                {"success": True, "message": "Password reset successful."}, 
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "Invalid or expired token."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

#Admin View api for Frontend

class UserListView(APIView):

    def get(self, request):
        # Fetch all users from the database
        users = User.objects.all()
        
        # Serialize the data
        serializer = UserSerializer(users, many=True)
        
        # Return the serialized data as a response
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProjectListView(APIView):
    def get(self,request):
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

class TestCaseListView(APIView):
    def get (self,request):
        testcases = TestCase.objects.all()
        serializer = TestCaseSerializer(testcases,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

class TestSuiteListView(APIView):
    def get(self,request):
        test_suites = TestSuite.objects.all()
        serializer = TestSuiteSerializer(test_suites,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

class RequirementListView(APIView):
    def get(self,request):
        requirements = Requirement.objects.all()
        serializer = RequirementSerializer(requirements,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

#Admin Dashboard view for frontend
class OrganizationView(APIView):
    def get(self, request):
        # Fetch users with `role_id = 2` (Organizations)
        organizations = User.objects.filter(role_id=2)
        serializer = UserSerializer(organizations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrganizationProjectDetailsView(APIView):
    def get(self, request, organization_id):
        try:
            # Get the organization user
            organization = User.objects.get(id=organization_id, role_id=2)
            
            # Get projects created by this organization
            projects = Project.objects.filter(user=organization)

            # Serialize project details along with related data
            project_data = []
            for project in projects:
                project_info = ProjectSerializer(project).data
                
                # Fetch related data
                project_info['test_cases'] = TestCaseSerializer(
                    TestCase.objects.filter(project=project), many=True
                ).data
                project_info['test_suites'] = TestSuiteSerializer(
                    TestSuite.objects.filter(project=project), many=True
                ).data
                project_info['requirements'] = RequirementSerializer(
                    Requirement.objects.filter(project=project), many=True
                ).data
                project_info['project_members'] = ProjectMemberSerializer(
                    ProjectMember.objects.filter(project=project), many=True
                ).data
                
                project_data.append(project_info)

            return Response({'organization': UserSerializer(organization).data, 'projects': project_data}, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

class OrganizationProjectsView(APIView):
    def get(self, request, organization_id):
        # Fetch projects for the given organization (organization_id matches User.id)
        try:
            projects = Project.objects.filter(user_id=organization_id)
            serializer = ProjectSerializer(projects, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)


class ProjectMembersView(APIView):
    def get(self, request, project_id):
        try:
            # Fetch project members for the given project ID
            project_members = ProjectMember.objects.filter(project_id=project_id).select_related('user')
            project_invitations = ProjectInvitation.objects.filter(project_id=project_id)  # Fetch all invitations for the project
            members_data = []

            for member in project_members:
                user = member.user

                # Filter invitation records related to this specific member
                # Assuming there is a way to match members with invitations (e.g., by email, name, etc.)
                invitation_status = "No Invitation Found"
                for invitation in project_invitations:
                    if invitation.recipient_email == user.email:  # Example match by email (adjust logic if needed)
                        invitation_status = invitation.status
                        break  # Stop looking once a match is found

                # Append member data with invitation status
                members_data.append({
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "phone": user.phone,
                    "country": user.country,
                    "added_at": member.added_at,
                    "invitation_status": invitation_status,  # Add specific status for this user
                })

            return Response(members_data, status=status.HTTP_200_OK)

        except Project.DoesNotExist:
            return Response({"error": "Project not found."}, status=status.HTTP_404_NOT_FOUND)


#User Main api for Frontend

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        # Filter projects by the logged-in user's ID
        user_id = self.request.query_params.get('user_id')  # Use query_params for GET requests

        if not user_id:
            raise ValidationError("User Id is required in query parameters.")
            
        return Project.objects.filter(user_id=user_id)

    def perform_create(self, serializer):
        user_id = self.request.data.get("user_id")  # Get the user ID from the authenticated user
        # Ensure name, description, and project_type are passed
        name = self.request.data.get('name')
        description = self.request.data.get('description')
        project_type = self.request.data.get('project_type')

        if not name or not description or not project_type:
            raise ValidationError("Name, description, and project type are required.")
        
        # Save the project with the correct user_id
        serializer.save(user_id=user_id)

    def _get_project_for_user(self, project_id, user_id):
        """Helper method to validate and fetch the project linked to the user."""
        try:
            project = Project.objects.get(id=project_id, user_id=user_id)
            return project
        except Project.DoesNotExist:
            raise ValidationError("Project does not exist or is not linked to the user.")


class TestDataView(APIView):
    """
    API View to handle GET and POST requests for TestData.
    Each project can have only one URL.
    """

    def get(self, request, project_id):
        """
        Handles GET requests to retrieve the TestData entry for a specific project.
        :param project_id: ID of the project to retrieve TestData for.
        """
        try:
            test_data = TestData.objects.get(project_id=project_id)
            serializer = TestDataSerializer(test_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TestData.DoesNotExist:
            return Response({"error": "No TestData found for the given project ID."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, project_id):
        """
        Handles POST requests to create or update the TestData entry for a specific project.
        :param project_id: ID of the project to create/update TestData for.
        :param url: URL to associate with the project.
        """
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure only one TestData entry per project
        test_data, created = TestData.objects.get_or_create(project=project)

        # Update or set the URL
        serializer = TestDataSerializer(test_data, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, project_id):
        """
        Handles DELETE requests to remove the TestData entry for a specific project.
        :param project_id: ID of the project to delete TestData for.
        """
        try:
            test_data = TestData.objects.get(project_id=project_id)
            test_data.delete()
            return Response({"message": "TestData deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except TestData.DoesNotExist:
            return Response({"error": "No TestData found for the given project ID."}, status=status.HTTP_404_NOT_FOUND)



class TestCaseViewSet(viewsets.ModelViewSet):
    serializer_class = TestCaseSerializer

    def get_queryset(self):
        user_id = self.request.user.id  # Get the user ID from the authenticated user
        project_id = self.request.query_params.get('project_id')  # Use query parameters for GET

        if not project_id:
            raise ValidationError("Project ID is required in query parameters.")

        return TestCase.objects.filter(project__id=project_id).prefetch_related('steps')

    def perform_create(self, serializer):
        user_id = self.request.user.id
        project_id = self.request.data.get('project_id')
        testcase_type = self.request.data.get('testcase_type', 'Functional')  # Default to 'Functional'
        testcase_priority = self.request.data.get('testcase_priority', 'Medium')  # Default to 'Medium'

        if not project_id:
            raise ValidationError("Project ID is required.")
        
        # Use the helper method to ensure the project is valid for the user
        project = self._get_project_for_user(project_id)

        # Save the test case with the correct project and user
        serializer.save(project=project, testcase_type=testcase_type, testcase_priority=testcase_priority)

    def _get_project_for_user(self, project_id):
        try:
            project = Project.objects.get(id=project_id)
            return project
        except Project.DoesNotExist:
            raise ValidationError("Project not found or does not belong to the user.")


class TestStepViewSet(viewsets.ModelViewSet):
    serializer_class = BulkTestStepSerializer
    queryset = TestStep.objects.all()

    def get_queryset(self):
        if self.request.method == 'GET':
            testcase_id = self.request.query_params.get('testcase_id')
            if not testcase_id:
                raise ValidationError("Testcase ID is required in query parameters.")
            return TestStep.objects.filter(testcase_id=testcase_id)
        return TestStep.objects.all()

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request, *args, **kwargs):
        """
        Create multiple test steps in one request, including test results if provided.
        """
        steps_data = request.data.get('steps', [])
        if not steps_data:
            return Response({"error": "Steps data is required."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BulkTestStepSerializer(data=steps_data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Update a test step, including the test result.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except TestStep.DoesNotExist:
            return Response({"error": "TestStep not found."}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a test step.
        """
        try:
            instance = self.get_object()
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TestStep.DoesNotExist:
            return Response({"error": "TestStep not found."}, status=status.HTTP_404_NOT_FOUND)


class TestSuiteViewSet(viewsets.ModelViewSet):
    serializer_class = TestSuiteSerializer

    def get_queryset(self):
        user_id = self.request.user.id  # Get the user ID from the authenticated user
        project_id = self.request.query_params.get('project_id')  # Use query parameters for GET

        if not project_id:
            raise ValidationError("Project ID is required in query parameters.")

        return TestSuite.objects.filter(project__id=project_id)

    def perform_create(self, serializer):
        user_id = self.request.user.id
        project_id = self.request.data.get('project_id')

        if not project_id:
            raise ValidationError("Project ID is required.")
        
        # Use the helper method to ensure the project is valid for the user
        project = self._get_project_for_user(project_id)

        # Save the test suite with the correct project and user
        serializer.save(project=project)

    def _get_project_for_user(self, project_id):
        try:
            project = Project.objects.get(id=project_id)
            return project
        except Project.DoesNotExist:
            raise ValidationError("Project not found or does not belong to the user.")


class RequirementViewSet(viewsets.ModelViewSet):
    serializer_class = RequirementSerializer

    def get_queryset(self):
        # Filter requirements by the logged-in user's projects
        user_id = self.request.user.id
        project_id = self.request.query_params.get('project_id')  # Use query parameters for GET

        if not project_id:
            raise ValidationError("Project ID is required in query parameters.")

        return Requirement.objects.filter(project__id=project_id)

    def perform_create(self, serializer):
        user_id = self.request.user.id
        project_id = self.request.data.get('project_id')

        if not project_id:
            raise ValidationError("Project ID is required.")
        
        # Use the helper method to ensure the project is valid for the user
        project = self._get_project_for_user(project_id)

        start_date = self.request.data.get('start_date')
        completion_date = self.request.data.get('completion_date')

        # Validate that completion date is after start date
        if start_date and completion_date and start_date > completion_date:
            raise ValidationError("Completion date must be after start date.")

        # Save the requirement with the correct project
        serializer.save(project=project)

    def _get_project_for_user(self, project_id):
        """Helper method to validate and fetch the project linked to the user."""
        try:
            project = Project.objects.get(id=project_id)
            return project
        except Project.DoesNotExist:
            raise ValidationError("Project not found or does not belong to the user.")


# Project Member,invitation api views
class SendInvitationView(APIView):
    def post(self, request):
        data = request.data
        

        # Validate project
        try:
            project = Project.objects.get(id=data['project_id'])
        except Project.DoesNotExist:
            return Response({"error": "Project not found or you are not the owner."}, status=status.HTTP_404_NOT_FOUND)

        try:
            sender = User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            return Response({"error": "Sender user not found."}, status=status.HTTP_404_NOT_FOUND)
        

        # Check if recipient email is valid
        if not data.get('recipient_email'):
            return Response({"error": "Recipient email is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the email exists in the User table
        if User.objects.filter(email=data['recipient_email']).exists():
            return Response({"error": "User already registered with this email."}, status=status.HTTP_400_BAD_REQUEST)

         # Generate a short token for invitation
        token = secrets.token_hex(8)  # Generates a 16-character token     

        # Create invitation
        invitation = ProjectInvitation.objects.create(
            project=project,
            invite_by=sender,
            recipient_email=data['recipient_email'],
            token=token
        )

        # Send email with invitation link
        invite_link = f"https://testerally.ai/member-register/{invitation.token}"
        send_mail(
            subject="Project Invitation",
            message=f"You've been invited to join the project '{project.name}'. Click the link to accept: {invite_link}",
            from_email='suriya.prakash@crowd4test.com',
            recipient_list=[data['recipient_email']]
        )

        return Response({"message": "Invitation sent successfully!"}, status=status.HTTP_201_CREATED)


class AcceptInvitationView(APIView):
    def post(self, request, token):
        # Validate token
        try:
            invitation = ProjectInvitation.objects.get(token=token, status="Pending")
        except ProjectInvitation.DoesNotExist:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already exists
        data = request.data
        try:
            # Try to get the user by the recipient's email
            user = User.objects.get(email=invitation.recipient_email)
            # If user exists, return a message
            return Response(
                {"error": "User already exists with this email."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except User.DoesNotExist:
            # If user does not exist, create a new user
            role = data.get('roleid')  # Assuming roleid is passed in the request data
            if not role:
                return Response(
                    {"error": "Role ID is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user = User.objects.create(
                name=data['name'],
                email=invitation.recipient_email,
                password=make_password(data['password']),
                phone=data.get('phone', ''),
                country=data.get('country', ''),
                role_id=data['roleid']  # Create user with the given roleid
            )

        # Add user to project members
        ProjectMember.objects.create(
            project=invitation.project,
            user=user
        )

        # Update invitation status
        invitation.status = "Accepted"
        invitation.save()

        return Response({"message": "Invitation accepted and user registered!"}, status=status.HTTP_201_CREATED)

#Database TestTypes table view
class TestCaseTypeViewSet(viewsets.ModelViewSet):
    queryset = TestCaseType.objects.all()
    serializer_class = TestCaseTypeSerializer

class TestCasePriorityViewSet(viewsets.ModelViewSet):
    queryset = TestCasePriority.objects.all()
    serializer_class = TestCasePrioritySerializer

class RequirementTypeViewSet(viewsets.ModelViewSet):
    queryset = RequirementType.objects.all()
    serializer_class = RequirementTypeSerializer


class UserProjectDataView(APIView):
    def get(self, request, user_id):
        # Get all projects where the user is a member
        project_memberships = ProjectMember.objects.filter(user_id=user_id)
        project_ids = project_memberships.values_list('project_id', flat=True)

        # Fetch all related projects
        projects = Project.objects.filter(id__in=project_ids)
        project_data = ProjectSerializer(projects, many=True).data

        # Fetch all test cases related to these projects
        test_cases = TestCase.objects.filter(project_id__in=project_ids)
        test_case_data = TestCaseSerializer(test_cases, many=True).data

        # Fetch all test suites related to these projects
        test_suites = TestSuite.objects.filter(project_id__in=project_ids)
        test_suite_data = TestSuiteSerializer(test_suites, many=True).data

        # Fetch all requirements related to these projects
        requirements = Requirement.objects.filter(project_id__in=project_ids)
        requirement_data = RequirementSerializer(requirements, many=True).data

        return Response({
            "projects": project_data,
            "test_cases": test_case_data,
            "test_suites": test_suite_data,
            "requirements": requirement_data
        })
        
# Protected View for authenticated users
class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {"success": True, "message": "You have access to this protected view!"},
            status=status.HTTP_200_OK
        )


class TrackDownloadView(APIView):
    permission_classes = []

    def post(self, request):
        user_id = request.data.get('user_id')
        os_name = request.data.get('os_name')
        os_version = request.data.get('os_version')

        if not user_id or not os_name or not os_version:
            return Response({'error': 'user_id, os_name, and os_version are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        ip = request.META.get('REMOTE_ADDR')

        # Check if a record exists for same user + os_name + os_version
        existing = EXEDownload.objects.filter(user=user, os_name=os_name, os_version=os_version).first()

        if existing:
            if existing.download_count >= 3:
                return Response({'message': 'Download limit reached (3).  Please upgrade your plan to continue downloading.'}, status=status.HTTP_403_FORBIDDEN)
            
            existing.download_count += 1
            existing.ip_address = ip
            existing.save()
            serializer = EXEDownloadSerializer(existing)
        else:
            unique_download_uid = str(uuid.uuid4())
            new_download = EXEDownload.objects.create(
                user=user,
                os_name=os_name,
                os_version=os_version,
                ip_address=ip,
                download_count=1,  # Make sure this field defaults to 1 if not auto-set
                download_uid=unique_download_uid
            )
            serializer = EXEDownloadSerializer(new_download)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id query param is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        downloads = EXEDownload.objects.filter(user=user)
        if not downloads.exists():
            return Response({'message': 'No download record found for this user'}, status=status.HTTP_404_NOT_FOUND)

        serializer = EXEDownloadSerializer(downloads, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



