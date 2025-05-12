from django.db import models


class User():
    ROLES = (
        ('admin', 'ADMIN'),
        ('user', 'USER')
    )

    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLES, default='user')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    profile_image = models.IntegerField(default=random.randint(1, 10))  


    def __str__(self):
        return self.username