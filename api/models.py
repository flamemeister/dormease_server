from django.db import models
from django.conf import settings

from .storage_backends import MinioDocumentStorage
from .storage_backends import MinioRoomImageStorage  
from .storage_backends import MinioBuildingImageStorage

class DormitoryApplication(models.Model):
    class Priority(models.IntegerChoices):
        ORPHANS_DISABLED = 1, 'Orphans, disabled 1/2 groups.'
        FAMILY_DISABLED = 2, 'Disabled 3 group, parents with disabilities'
        SERPIN = 3, 'Serpin 2050'
        ALTYNBELGI_OLYMPIAD = 4, 'Altyn Belgi, olympiads'
        HIGH_ENT = 5, 'High UNT/CT scores'
        HIGH_GRADES = 6, 'Successful students'
        OTHER = 7, 'Others, including foreigners'

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    iin = models.CharField(max_length=12)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    city = models.CharField(max_length=100)
    document = models.FileField(
        storage=MinioDocumentStorage(),
        upload_to='applications/documents/',
        null=True,
        blank=True
    )
    priority = models.PositiveSmallIntegerField(choices=Priority.choices)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELED', 'Canceled'),
        ('EXPIRED', 'Expired'),
    ], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_comment = models.TextField(blank=True, null=True)
    pdf_contract = models.FileField(
        storage=MinioDocumentStorage(),
        upload_to="contracts/",
        null=True,
        blank=True
    )    
    signed_contract = models.FileField(
        storage=MinioDocumentStorage(),
        upload_to="signed_contracts/",
        null=True,
        blank=True
    )
    signed_contract_info_pdf = models.FileField(
    storage=MinioDocumentStorage(),
    upload_to="contracts/",
    null=True,
    blank=True
    )
    contract_signed = models.BooleanField(default=False)
    move_in_date = models.DateField(null=True, blank=True)
    signer_full_name = models.CharField(max_length=255, null=True, blank=True)
    signer_iin = models.CharField(max_length=20, null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    room = models.ForeignKey(
    'Room',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='applications'
    )
    identification_card = models.FileField(
    storage=MinioDocumentStorage(),
    upload_to='applications/identification_cards/',
    null=True, blank=True
    )

    city_proof_document = models.FileField(
        storage=MinioDocumentStorage(),
        upload_to='applications/city_proof/',
        null=True, blank=True
    )

    benefit_proof_document = models.FileField(
        storage=MinioDocumentStorage(),
        upload_to='applications/benefit_proof/',
        null=True, blank=True
    )
    contract_signed = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.student.email} - {self.get_priority_display()}"


class NotificationLog(models.Model):
    recipient = models.EmailField()
    status = models.CharField(max_length=20)
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.status} to {self.recipient} at {self.sent_at}"

class Building(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    floors = models.PositiveIntegerField()
    image = models.ImageField(
        upload_to="buildings/",
        storage=MinioBuildingImageStorage(),
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.name} ({self.address})"

class Room(models.Model):
    ROOM_TYPES = [
        ('double', 'Double'),
        ('triple', 'Triple'),
    ]

    GENDER_CHOICES = [
        ('male', 'Boys only'),
        ('female', 'Girls only'),
    ]

    number = models.CharField(max_length=10)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES)
    capacity = models.PositiveIntegerField(default=1)
    occupants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='rooms')
    floor = models.IntegerField()
    image = models.ImageField(
        upload_to="rooms/",
        storage=MinioRoomImageStorage(),
        null=True,
        blank=True
    )
    

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="rooms", null=False, blank=False)

    gender_restriction = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES  ,
        default='female'      
    )

    def is_full(self):
        return self.occupants.count() >= self.capacity

    def occupied_count(self):
        return self.occupants.count()
    
    def __str__(self):
        return f"Room {self.number} ({self.room_type})"
    
    class Meta:
        unique_together = ('number', 'building')  
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'


class SupportMessage(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_messages')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_answered = models.BooleanField(default=False)
    answer = models.TextField(blank=True, null=True)
    answered_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.subject} от {self.student.email}"

