from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView

from .views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('user/', UserAPIView.as_view(), name='user'),
    path('register/', UserRegistrationAPIView.as_view(), name='register'),
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change-password'),
    path('password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('verify-email/', VerifyEmailTokenView.as_view(), name='verify-email-token'),
]

urlpatterns += [
    path('2fa/email/request/', request_2fa_code, name='2fa-email-request'),
    path('2fa/email/verify/', verify_2fa_code, name='2fa-email-verify'),
]

