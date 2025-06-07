from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view

from .permissions import IsAitusaOrAdminReadOnly

from .models import *
from .serializers import *
from .serializers import MyTokenObtainPairSerializer

from django.contrib.auth import authenticate

from django.core.mail import send_mail
from django.conf import settings


class UserRegistrationAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False
            user.save()

            token_obj = EmailVerificationToken.objects.create(user=user)

            verify_url = f"http://localhost:3000/verify-email?token={token_obj.token}"

            send_mail(
                subject="Подтверждение почты",
                message=f"Перейдите по ссылке для подтверждения: {verify_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )

            return Response({"message": "Ссылка для подтверждения отправлена на почту"}, status=201)
        return Response(serializer.errors, status=400)

    
@api_view(['POST'])
def verify_email_code(request):
    email = request.data.get('email')
    code = request.data.get('code')

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "Пользователь не найден"}, status=404)

    code_obj = EmailVerificationCode.objects.filter(user=user, code=code, is_used=False).order_by('-created_at').first()

    if not code_obj or code_obj.is_expired():
        return Response({"error": "Код недействителен или истёк"}, status=400)

    user.is_active = True
    user.save()
    code_obj.is_used = True
    code_obj.save()

    return Response({"message": "Email успешно подтверждён"})


class UserViewSet(viewsets.ModelViewSet):
  queryset = User.objects.all()
  serializer_class = UserSerializer
  authentication_classes = [JWTAuthentication, SessionAuthentication]
  permission_classes = [IsAuthenticated]
  permission_classes = [IsAitusaOrAdminReadOnly]

  def get_queryset(self):
      user = self.request.user

      if user.role == 'aitusa':
          return User.objects.filter(role='user').order_by('id') 
      elif user.role == 'admin':
          return User.objects.all().order_by('id')  

      return User.objects.none()  


class UserAPIView(APIView):
  queryset = User.objects.all()
  serializer_class = UserSerializer
  authentication_classes = [JWTAuthentication, SessionAuthentication]
  permission_classes = [IsAuthenticated]

  def get(self, request):
    user_id = request.user.id

    try:
      user = User.objects.get(id=user_id)
    except User.DoesNotExist:
      return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UserSerializer(user)

    return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileAPIView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ChangePasswordAPIView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['current_password']):
                return Response({"current_password": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

def get_client_ip(request):
    return request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))

@api_view(['POST'])
def request_2fa_code(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(email=email, password=password)

    if not user:
        return Response({"error": "Invalid email or password"}, status=401)

    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")

    trusted = TrustedDevice.objects.filter(user=user)
    if any(device.matches(ip, ua) for device in trusted):
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })

    code = TwoFactorCode.generate_code()
    TwoFactorCode.objects.create(user=user, code=code)

    send_mail(
        subject="Your confirmation code",
        message=f"Confirmation code: {code}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )

    return Response({"message": "Code sent to email"})


@api_view(['POST'])
def verify_2fa_code(request):
    email = request.data.get('email')
    code = request.data.get('code')

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "User not found"}, status=404)

    code_obj = TwoFactorCode.objects.filter(user=user, code=code, is_used=False).order_by('-created_at').first()

    if not code_obj or code_obj.is_expired():
        return Response({"error": "Invalid or expired code"}, status=400)

    code_obj.is_used = True
    code_obj.save()

    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")
    TrustedDevice.objects.get_or_create(user=user, ip_address=ip, user_agent=ua)

    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    })


class VerifyEmailTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  

    def get(self, request):
        token = request.query_params.get("token")

        token_obj = EmailVerificationToken.objects.filter(token=token, is_used=False).first()
        if not token_obj or token_obj.is_expired():
            return Response({"error": "Ссылка недействительна или истекла"}, status=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        user.is_active = True
        user.save()

        token_obj.is_used = True
        token_obj.save()

        return Response({"message": "Почта успешно подтверждена!"}, status=status.HTTP_200_OK)
