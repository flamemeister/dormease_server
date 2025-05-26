# REST
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from .permissions import IsAitusaOrAdminReadOnly

from .models import *
from .serializers import *

class UserRegistrationAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response("Success on Register", status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate

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

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MyTokenObtainPairSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
