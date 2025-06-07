
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from rest_framework import permissions

from .views import DormitoryApplicationViewSet, RoomViewSet, SupportMessageViewSet, BuildingViewSet, admin_dashboard_metrics, aitusa_dashboard_metrics

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = DefaultRouter()
router.register(r'applications', DormitoryApplicationViewSet, basename='applications')
router.register(r'rooms', RoomViewSet, basename='rooms')
router.register(r'support', SupportMessageViewSet, basename='support')
router.register(r'buildings', BuildingViewSet, basename='buildings')

schema_view = get_schema_view(
   openapi.Info(
      title="Dorm API",
      default_version='v1',
      description="Documentation for dormitory management",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', include(router.urls)),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path("metrics/admin/", admin_dashboard_metrics),
    path("metrics/aitusa/", aitusa_dashboard_metrics),

]

