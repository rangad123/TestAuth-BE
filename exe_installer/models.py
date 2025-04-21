from django.db import models
from api.models import User
import uuid 

class EXEDownload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    os_name = models.TextField(null=True, blank=True)
    os_version = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=1)
    last_downloaded = models.DateTimeField(auto_now=True)
    download_uid = models.CharField(max_length=100, unique=True, null=True)
    file_version = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.os_name} ({self.download_uid})"

class SystemInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exe_download = models.ForeignKey(EXEDownload, on_delete=models.SET_NULL, null=True, blank=True)
    os_name = models.CharField(max_length=100)
    os_version = models.CharField(max_length=200)
    architecture = models.CharField(max_length=100)
    cpu = models.CharField(max_length=200)
    ram = models.IntegerField()  # in GB
    screen_resolution = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField()
    mac_address = models.CharField(max_length=50)
    system_fingerprint = models.CharField(max_length=1000) 
    created_at = models.DateTimeField(auto_now_add=True)
