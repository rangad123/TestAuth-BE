
from django.db import models
from api.models import User

class SystemInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    os_name = models.CharField(max_length=100)
    os_version = models.CharField(max_length=200)
    architecture = models.CharField(max_length=100)
    cpu = models.CharField(max_length=200)
    ram = models.IntegerField()  # in GB
    screen_resolution = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField()
    mac_address = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'os_name', 'os_version')  # prevent duplicates
