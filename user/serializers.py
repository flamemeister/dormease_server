from rest_framework import serializers
from api.models import DormitoryApplication
from .models import *
from api.models import Room  
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class BasicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']


class UserProfileSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer(read_only=True)
    profile_image = serializers.ImageField(required=False)

    class Meta:
        model = UserProfile
        fields = [
            'user',
            'age',
            'bio',
            'course',
            'group',
            'roommate_preferences',
            'profile_image',
        ]


class UserSerializer(serializers.ModelSerializer):
    is_profile_completed = serializers.SerializerMethodField()
    move_in_date = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    room_number = serializers.SerializerMethodField()
    building_name = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    building = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'is_active',
            'is_staff', 'gender', 'last_login', 'move_in_date',
            'group', 'room_number', 'building_name', 'course', 'building',
            'is_superuser', 'groups', 'user_permissions', 'is_profile_completed', 'profile'
        ]
        extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = ['is_profile_completed']

    def get_is_profile_completed(self, obj):
        try:
            return obj.profile.is_profile_completed
        except UserProfile.DoesNotExist:
            return False

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        if instance.age and instance.course and instance.group:
            instance.is_profile_completed = True
            instance.save(update_fields=["is_profile_completed"])

        return instance
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    
    def get_move_in_date(self, obj):
        latest_app = DormitoryApplication.objects.filter(student=obj, status='APPROVED').order_by('-created_at').first()
        return latest_app.move_in_date if latest_app else None

    def get_group(self, obj):
        return getattr(obj.profile, 'group', None)

    def get_room_number(self, obj):
        room = Room.objects.filter(occupants=obj).first()
        return room.number if room else None
    
    def get_building_name(self, obj):
        app = DormitoryApplication.objects.filter(student=obj, status='APPROVED').order_by('-created_at').first()
        return app.room.building.name if app and app.room and app.room.building else None
    
    def get_course(self, obj):  
        return getattr(obj.profile, 'course', None)
    
    def get_building(self, obj):
        room = Room.objects.filter(occupants=obj).select_related('building').first()
        return room.building.name if room and room.building else None
    

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'gender']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_new_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return attrs
    
    
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role

        try:
            token['profile_completed'] = user.profile.is_profile_completed
        except UserProfile.DoesNotExist:
            token['profile_completed'] = False

        return token
