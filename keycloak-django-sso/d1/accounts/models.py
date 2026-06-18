from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    sub = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    roles = models.JSONField(default=list)
    groups = models.JSONField(default=list)
    last_synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sub
