from rest_framework import serializers
from .models import DormitoryApplication, Room, SupportMessage


STATUS_TRANSLATIONS = {
    'PENDING': 'Ожидает рассмотрения',
    'APPROVED': 'Одобрено',
    'REJECTED': 'Отклонено',
    'CANCELED': 'Отменено',
    'EXPIRED': 'Истек срок',
}

class DormitoryApplicationSerializer(serializers.ModelSerializer):
    priority_verbose = serializers.SerializerMethodField()
    status_verbose = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='student.first_name', read_only=True)
    last_name = serializers.CharField(source='student.last_name', read_only=True)

    class Meta:
        model = DormitoryApplication
        fields = [
            'id', 'first_name', 'last_name', 'iin', 'gender', 'city', 'document',
            'priority', 'priority_verbose', 'status', 'status_verbose', 'created_at', 'move_in_date'
        ]
        read_only_fields = ['status', 'created_at', 'student']

    def get_priority_verbose(self, obj):
        return DormitoryApplication.Priority(obj.priority).label if obj.priority else None

    def get_status_verbose(self, obj):
        return obj.get_status_display()

    def validate_iin(self, value):
        if not value.isdigit() or len(value) != 12:
            raise serializers.ValidationError("ИИН должен состоять из 12 цифр.")
        return value

    def validate_priority(self, value):
        if value is None:
            raise serializers.ValidationError("Необходимо выбрать категорию приоритета.")
        return value


class RoomSerializer(serializers.ModelSerializer):
    is_full = serializers.SerializerMethodField()
    building_name = serializers.SerializerMethodField()
    occupied_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id', 'number', 'room_type', 'capacity', 'is_full', 'occupied_count',
            'floor', 'building', 'building_name', 'gender_restriction', 'image'
        ]

    def get_is_full(self, obj):
        return obj.is_full()

    def get_occupied_count(self, obj):
        return obj.occupied_count()

    def get_building_name(self, obj):
        return obj.building.name if obj.building else None


class SupportMessageSerializer(serializers.ModelSerializer):
    student_full_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = '__all__'
        read_only_fields = ['student', 'is_answered', 'answered_at']

    def get_student_full_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

from .models import Building

class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ['id', 'name', 'address', 'floors', 'image']

