from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from channels.layers import get_channel_layer

from asgiref.sync import async_to_sync

from .models import Room
from .serializers import RoomSerializer

@receiver([m2m_changed, post_save], sender=Room)
def notify_room_update(sender, instance, **kwargs):
    serializer = RoomSerializer(instance)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "rooms",
        {
            "type": "room_update",
            "data": {
                "type": "room_updated",
                "room": serializer.data
            }
        }
    )
