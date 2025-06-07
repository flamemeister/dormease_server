from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

from .storage_backends import MinioProfileImageStorage

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLES = (
        ('admin', 'ADMIN'),
        ('user', 'USER'),
        ('aitusa', 'Aitusa Support'),
    )

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Others'),
    )

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.CharField(max_length=10, choices=ROLES, default='user')
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=False, blank=False, default='female')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']  

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',
        related_query_name='customuser',
        blank=True,
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',
        related_query_name='customuser',
        blank=True,
        verbose_name='user permissions',
    )

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.PositiveIntegerField(null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(
        storage=MinioProfileImageStorage(),
        upload_to='',
        null=True,
        blank=True
    )
    course = models.PositiveSmallIntegerField(null=True, blank=True)
    group = models.CharField(max_length=20, blank=True, null=True)
    roommate_preferences = models.TextField(blank=True, null=True)
    is_profile_completed = models.BooleanField(default=False)  

    def __str__(self):
        return f'Профиль: {self.user.first_name} {self.user.last_name}'

from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class TwoFactorCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=5)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))


class TrustedDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    def matches(self, ip, ua):
        return self.ip_address == ip and self.user_agent == ua


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))

import uuid

class EmailVerificationToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(days=1)