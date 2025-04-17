from django.shortcuts import render

# Create your views here.
# For .exe installation tracking code

from django.http import JsonResponse  
from api.models import User
from .models import SystemInfo, EXEDownload
from .serializers import SystemInfoSerializer, EXEDownloadSerializer
from screeninfo import get_monitors
from django.db import IntegrityError
from rest_framework import status 
import platform, psutil, socket, uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView


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

        ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        unique_download_uid = str(uuid.uuid4())

        new_download = EXEDownload.objects.create(
            user=user,
            os_name=os_name,
            os_version=os_version,
            ip_address=ip,
            download_uid=unique_download_uid,
            download_count=1  # Optional: just to indicate this is the first for this record
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


# Function to collect system info
def get_system_info(user):
    try:
        screen = get_monitors()[0]
        screen_resolution = f"{screen.width}x{screen.height}"
    except Exception as e:
        screen_resolution = "Unknown"

    return {
        "user": user.id,  # Will still pass user explicitly in .save()
        "os_name": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "cpu": platform.processor(),
        "ram": psutil.virtual_memory().total // (1024 ** 3),
        "screen_resolution": screen_resolution,
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "mac_address": ":".join(
            ["{:02x}".format((uuid.getnode() >> bits) & 0xff) for bits in range(0, 2 * 6, 8)][::-1]
        ),
    }

@api_view(['POST'])  # Changed to POST
def EXE_login(request):
    download_uid = request.data.get('download_uid')  # Get from body, not GET params

    if not download_uid:
        return Response({"error": "Download_uid is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        agent_details = EXEDownload.objects.get(download_uid=download_uid)
    except EXEDownload.DoesNotExist:
        return Response({"error": "Download_uid does not match any agent"}, status=status.HTTP_400_BAD_REQUEST)

    user = agent_details.user

    try:
        agentsys_details = SystemInfo.objects.get(exe_download_id=agent_details.id)

        current_system = get_system_info(user)

        # Check if the system information matches
        match = (
            agentsys_details.os_name == current_system['os_name'] and
            agentsys_details.cpu == current_system['cpu'] and
            agentsys_details.mac_address == current_system['mac_address'] and
            agentsys_details.screen_resolution == current_system['screen_resolution']
        )

        if match:
            serializer = SystemInfoSerializer(agentsys_details)
            return Response({
                "message": "Login successful on the same system",
                "system_info": serializer.data
            })
        else:
            return Response({"error": "EXE is running on a different system"}, status=status.HTTP_403_FORBIDDEN)

    except SystemInfo.DoesNotExist:
        # Get the current system information
        system_data = get_system_info(user)

        # Check if the system info already exists
        existing_info = SystemInfo.objects.filter(
            user=user,
            os_name=system_data["os_name"],
            os_version=system_data["os_version"],
            architecture=system_data["architecture"],
            cpu=system_data["cpu"],
            ram=system_data["ram"],
            screen_resolution=system_data["screen_resolution"],
            ip_address=system_data["ip_address"],
            mac_address=system_data["mac_address"],
        ).first()

        if existing_info:
            # If system info already exists, return a response indicating that
            return Response({
                "message": "System info already exists for this agent. You can't run the agent on this system.",
                "Key_error":"This agent_key created for different system you are entering in different system.",
            }, status=400)

        # Save the new system info
        system_data["user"] = user.id  # Add user to the system data
        system_data["exe_download"] = agent_details.id  # Add exe_download to the system data

        serializer = SystemInfoSerializer(data=system_data)

        if serializer.is_valid():
            serializer.save()  # Save the new system info
            return Response({
                "message": "System info saved successfully",
                "data": serializer.data
            })
        else:
            return Response(serializer.errors, status=400)
