from django.shortcuts import render
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


# Track download view (modified)
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

        # Check if EXEDownload already exists for this user and OS
        existing_download = EXEDownload.objects.filter(user=user, os_name=os_name, os_version=os_version).first()
        if existing_download:
            return Response(EXEDownloadSerializer(existing_download).data)

        # Create new EXEDownload entry
        unique_download_uid = str(uuid.uuid4())
        new_download = EXEDownload.objects.create(
            user=user,
            os_name=os_name,
            os_version=os_version,
            ip_address=ip,
            download_uid=unique_download_uid,
            download_count=1
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


# Helper function to generate system fingerprint
def generate_system_fingerprint(user, request):
    system_info = get_system_info(user, request)
    return f"{system_info['os_name']}_{system_info['os_version']}_{system_info['cpu']}_{system_info['screen_resolution']}_{system_info['mac_address']}_{user.id}"

# Function to collect system info
def get_system_info(user, request):
    try:
        screens = get_monitors()
        if screens:
            screen_resolution = f"{screens[0].width}x{screens[0].height}"
        else:
            screen_resolution = "Unknown"
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
        "ip_address" : request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR') or "Unknown",
        "mac_address": ":".join(
            ["{:02x}".format((uuid.getnode() >> bits) & 0xff) for bits in range(0, 2 * 6, 8)][::-1]
        ),
    }

# EXE login view (modified)
@api_view(['POST'])
def EXE_login(request):
    download_uid = request.data.get('download_uid')

    if not download_uid:
        return Response({"error": "Download_uid is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        agent_details = EXEDownload.objects.get(download_uid=download_uid)
    except EXEDownload.DoesNotExist:
        return Response({"error": "Download_uid does not match any agent"}, status=status.HTTP_400_BAD_REQUEST)

    user = agent_details.user
    system_fingerprint = generate_system_fingerprint(user, request)

    # Check if the system info matches
    try:
        agentsys_details = SystemInfo.objects.get(exe_download_id=agent_details.id)

        # Check system fingerprint
        if agentsys_details.system_fingerprint == system_fingerprint:
            serializer = SystemInfoSerializer(agentsys_details)
            return Response({
                "message": "Login successful on the same system",
                "system_info": serializer.data
            })
        else:
            return Response({"error": "EXE is running on a different system"}, status=status.HTTP_403_FORBIDDEN)

    except SystemInfo.DoesNotExist:
        system_data = get_system_info(user, request)
        system_data["user"] = user.id
        system_data["exe_download"] = agent_details.id
        system_data["system_fingerprint"] = system_fingerprint

        serializer = SystemInfoSerializer(data=system_data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "System info saved successfully",
                "data": serializer.data
            })
        else:
            return Response(serializer.errors, status=400)
