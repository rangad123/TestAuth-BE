# serializers.py

from rest_framework import serializers
from .models import SystemInfo, EXEDownload

class EXEDownloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = EXEDownload
        fields = '__all__'

class SystemInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemInfo
        fields = '__all__'

