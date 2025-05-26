from django.contrib import admin
from .models import DormitoryApplication, Room, SupportMessage, Building

@admin.register(DormitoryApplication)
class DormitoryApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', )
    search_fields = ('student__email', 'student__first_name', 'student__last_name')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['student']
    

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'room_type', 'capacity', 'current_occupancy', 'display_occupants')
    list_filter = ('room_type',)
    search_fields = ('number',)
    filter_horizontal = ('occupants',)
    

    def current_occupancy(self, obj):
        return obj.occupants.count()
    current_occupancy.short_description = 'Occupied'

    def display_occupants(self, obj):
        return ", ".join([u.email for u in obj.occupants.all()])
    display_occupants.short_description = "Occupants"
    
@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'student', 'created_at', 'is_answered']
    list_filter = ['is_answered', 'created_at']
    search_fields = ['subject', 'student__email', 'message']
    readonly_fields = ['created_at', 'answered_at']

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'floors']
    search_fields = ['name', 'address']