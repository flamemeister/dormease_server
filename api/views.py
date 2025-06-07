from rest_framework import viewsets, status, filters, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView

from .models import DormitoryApplication, Room, SupportMessage
from .serializers import DormitoryApplicationSerializer, RoomSerializer, SupportMessageSerializer
from .tasks import send_status_email
from user.serializers import UserProfileSerializer

from api.email_utils import send_support_reply

from django_filters.rest_framework import DjangoFilterBackend
from django.utils.timezone import now
from django.db.models import Avg, F, ExpressionWrapper, DurationField, Count

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from datetime import timedelta, date

from .utils import generate_contract_pdf
from django.core.files import File
import os

import base64
from django.views.decorators.csrf import csrf_exempt
from .pdf_generator import generate_contract_pdf

from .verify_signature import verify_cms_signature

from django.core.files.base import ContentFile

from django.shortcuts import render
from asn1crypto import cms

from .models import Building
from .serializers import BuildingSerializer


class DormitoryApplicationViewSet(viewsets.ModelViewSet):
    queryset = DormitoryApplication.objects.all()
    serializer_class = DormitoryApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status']
    search_fields = ['student__email']

    @swagger_auto_schema(
        operation_description="Студент подаёт заявку на проживание в общежитии",
        tags=["Пользователь"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["iin", "gender", "city", "priority"],
            properties={
                "iin": openapi.Schema(type=openapi.TYPE_STRING),
                "gender": openapi.Schema(type=openapi.TYPE_STRING, enum=["male", "female", "other"]),
                "city": openapi.Schema(type=openapi.TYPE_STRING),
                "priority": openapi.Schema(type=openapi.TYPE_INTEGER),
                "identification_card": openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
                "city_proof_document": openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
                "benefit_proof_document": openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
            }
        ),
        responses={201: openapi.Response("Заявка создана")}
    )

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == 'admin':
            return DormitoryApplication.objects.all()
        return DormitoryApplication.objects.filter(student=user)

    def perform_create(self, serializer):
        user = self.request.user
        active_exists = DormitoryApplication.objects.filter(
            student=user,
            status__in=['PENDING', 'APPROVED']
        ).exists()
        if active_exists:
            raise serializers.ValidationError("You already have active application. Please wait for the result")
        
        instance = serializer.save(student=user)

        for field in ['identification_card', 'city_proof_document', 'benefit_proof_document']:
            if field in self.request.FILES:
                setattr(instance, field, self.request.FILES[field])

        instance.save()

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        operation_description="Одобрить заявку (только для администратора)",
        tags=["Администрирование"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["admin_comment"],
            properties={
                'admin_comment': openapi.Schema(type=openapi.TYPE_STRING, description='Комментарий администратора')
            }
        ),
        responses={200: openapi.Response("Заявка одобрена")}
    )
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_application(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'detail': 'Only administrator has access'}, status=403)

        admin_comment = request.data.get("admin_comment", "").strip()
        if not admin_comment:
            return Response({'error': 'Comment is mandatory.'}, status=400)

        application = get_object_or_404(DormitoryApplication, pk=pk)

        application.status = 'APPROVED'
        application.admin_comment = admin_comment
        application.move_in_date = date.today()  

        pdf_path = generate_contract_pdf(application)
        with open(pdf_path, "rb") as f:
            application.pdf_contract.save(f"contract_{application.id}.pdf", File(f), save=True)

        application.save()
        os.remove(pdf_path)

        send_status_email.delay(application.student.email, 'APPROVED', application.id)

        return Response({'status': 'approved'})

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        operation_description="Отклонить заявку (только для администратора)",
        tags=["Администрирование"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["admin_comment"],
            properties={
                'admin_comment': openapi.Schema(type=openapi.TYPE_STRING, description='Причина отклонения')
            }
        ),
        responses={200: openapi.Response("Заявка отклонена")}
    )
    @action(detail=True, methods=['post'], url_path='reject')
    def reject_application(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'detail': 'Only administrator has access.'}, status=403)

        admin_comment = request.data.get("admin_comment", "").strip()
        if not admin_comment:
            return Response({'error': 'Comment is mandatory.'}, status=400)

        application = get_object_or_404(DormitoryApplication, pk=pk)
        application.status = 'REJECTED'
        application.admin_comment = admin_comment
        application.save()
        send_status_email.delay(application.student.email, 'REJECTED')
        return Response({'status': 'rejected'})

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        operation_description="Отменить заявку (студент или админ)",
        tags=["Пользователь", "Администрирование"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["admin_comment"],
            properties={
                'admin_comment': openapi.Schema(type=openapi.TYPE_STRING, description='Причина отмены (обязательно для админа)')
            }
        ),
        responses={200: openapi.Response("Application is canceled")}
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_application(self, request, pk=None):
        application = get_object_or_404(DormitoryApplication, pk=pk)

        if request.user == application.student:
            application.status = 'CANCELED'
            application.save()
            send_status_email.delay(application.student.email, 'CANCELED')
            return Response({'status': 'canceled'})

        elif request.user.role == 'admin':
            admin_comment = request.data.get("admin_comment", "").strip()
            if not admin_comment:
                return Response({'error': 'Comment is mandatory for administrator.'}, status=400)

            application.status = 'CANCELED'
            application.admin_comment = admin_comment
            application.save()
            send_status_email.delay(application.student.email, 'CANCELED')
            return Response({'status': 'canceled'})

        return Response({'detail': 'No access.'}, status=403)

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        method='get',
        operation_description="Посмотреть мои заявки",
        tags=["Моя заявка"]
    )
    @action(detail=False, methods=['get'], url_path='my')
    def my_applications(self, request):
        apps = DormitoryApplication.objects.filter(student=request.user).order_by('-created_at')
        serializer = self.get_serializer(apps, many=True)
        return Response(serializer.data)

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        method='post',
        tags=["Администрирование"],
        operation_description="Обновить статус заявки вручную (только админ)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['status'],
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, enum=['PENDING', 'APPROVED', 'REJECTED', 'CANCELED', 'EXPIRED']),
                'admin_comment': openapi.Schema(type=openapi.TYPE_STRING, description='Комментарий администратора')
            }
        ),
        responses={200: 'Status updated'}
    )
    @action(detail=True, methods=['post'], url_path='force-update')
    def force_update_status(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'detail': 'Only for administrator.'}, status=403)
        application = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(application._meta.get_field('status').choices):
            return Response({'error': 'Inacceptable status'}, status=400)
        application.status = new_status
        application.admin_comment = request.data.get('admin_comment', '')
        application.save()
        send_status_email.delay(application.student.email, new_status)
        return Response({'status': new_status})

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        method='post',
        tags=["Пользователь"],
        operation_description="Студент выбирает комнату после одобрения заявки",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'room_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID комнаты')
            }
        ),
        responses={200: 'Комната выбрана'}
    )
    @action(detail=True, methods=['post'], url_path='select-room')
    def select_room(self, request, pk=None):
        application = self.get_object()

        if application.student != request.user:
            return Response({'detail': 'Access only for application sender.'}, status=403)
        if application.status != 'APPROVED':
            return Response({'detail': 'Room is available oly after approval.'}, status=400)

        if Room.objects.filter(occupants=request.user).exists():
            return Response({'error': 'You are already settled.'}, status=400)

        room_id = request.data.get('room_id')
        if not room_id:
            return Response({'error': 'room_id is mandatory'}, status=400)

        room = get_object_or_404(Room, id=room_id)

        if room.gender_restriction != 'any' and room.gender_restriction != application.gender:
            return Response({'error': 'This room is for another gender.'}, status=400)

        if room.is_full():
            return Response({'error': 'This room is already full'}, status=400)

        application.room = room
        application.save()

        room.occupants.add(request.user)

        return Response({'success': f'You are successfully settled to {room.number}.'})

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        operation_description="Подтвердить выбор комнаты студентом (только админ)",
        tags=["Администрирование"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["room_id"],
            properties={
                'room_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID комнаты')
            }
        ),
        responses={200: 'Комната подтверждена'}
    )
    @action(detail=True, methods=['post'], url_path='approve-room')
    def approve_room_selection(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'detail': 'Only admin can approve the room selection'}, status=403)
        application = self.get_object()
        room = get_object_or_404(Room, id=request.data.get('room_id'))
        if room.is_full():
            return Response({'error': 'room is already full'}, status=400)
        application.room = room
        application.save()

        room.occupants.add(application.student)  

        send_status_email.delay(application.student.email, 'ROOM_CONFIRMED')
        return Response({'success': f'Room {room.number} successfully confirmed.'})

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        method='get',
        operation_description="Получить список всех руммейтов текущего пользователя",
        tags=["Общие"]
    )
    @action(detail=False, methods=['get'], url_path='my-roommate')
    def get_roommate(self, request):
        user = request.user

        room = Room.objects.filter(occupants=user).first()
        if not room:
            return Response({'detail': 'You are not attached to any room.'}, status=404)

        roommates = room.occupants.exclude(id=user.id)
        if not roommates.exists():
            return Response({'detail': 'You do not have a roommate yet.'}, status=404)

        serializer = UserProfileSerializer([r.profile for r in roommates], many=True)
        return Response(serializer.data)
    
# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="contract-base64")
    def get_contract_base64(self, request, pk=None):
        app = get_object_or_404(DormitoryApplication, pk=pk)
        if not app.pdf_contract:
            return Response({"error": "Contract document is not found"}, status=404)

        with app.pdf_contract.open("rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return Response({"base64": encoded})

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="upload-signed")
    def upload_signed_contract(self, request, pk=None):
        app = get_object_or_404(DormitoryApplication, pk=pk)

        signed_bytes = None
        if "signed_content" in request.data:
            signed_content = request.data.get("signed_content")
            if not isinstance(signed_content, str):
                return Response({"error": "signed_content must be a string (base64)."}, status=400)
            try:
                signed_bytes = base64.b64decode(signed_content)
            except Exception:
                return Response({"error": "Error in decoding base64"}, status=400)
        elif "signed_file" in request.FILES:
            file = request.FILES["signed_file"]
            signed_bytes = file.read()
        else:
            return Response({"error": "Передайте либо 'signed_content' (base64), либо 'signed_file' (файл .cms)"}, status=400)

        if not app.pdf_contract:
            return Response({"error": "PDF-contract is not found"}, status=404)

        try:
            with app.pdf_contract.open("rb") as f:
                original_pdf = f.read()
        except Exception as e:
            return Response({"error": f"Error reading the PDF: {str(e)}"}, status=500)

        if not verify_cms_signature(original_pdf, signed_bytes):  
            return Response({"error": "Signature is not actual."}, status=400)

        app.signed_contract.save(f"signed_{app.id}.cms", ContentFile(signed_bytes), save=True)

        try:
            cms_data = cms.ContentInfo.load(signed_bytes)
            signer_cert = cms_data['content']['certificates'][0].chosen
            subject = signer_cert.subject.native

            full_name = subject.get("common_name")
            iin = subject.get("serial_number")
        except Exception as e:
            return Response({"error": f"Ошибка при извлечении данных подписи: {str(e)}"}, status=500)

        app.signer_full_name = full_name
        app.signer_iin = iin
        app.signed_at = now()
        app.contract_signed = True
        app.save()

        return Response({
            "status": " Подпись сохранена",
            "signed_by": full_name,
            "iin": iin,
            "signed_at": app.signed_at.strftime('%d.%m.%Y %H:%M'),
        })

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="signed")
    def list_signed_contracts(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Доступ запрещён"}, status=403)

        signed_apps = DormitoryApplication.objects.filter(contract_signed=True).select_related("student")
        data = [
            {
                "id": app.id,
                "full_name": f"{app.student.first_name} {app.student.last_name}",
                "signed_contract_url": app.signed_contract.url if app.signed_contract else None,
                "signed_contract_info_pdf_url": app.signed_contract_info_pdf.url if app.signed_contract_info_pdf else None,
            }
            for app in signed_apps
        ]
        return Response(data)
    
# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="contracts")
    def list_all_contracts(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Доступ запрещён"}, status=403)

        apps = DormitoryApplication.objects.select_related("student")
        data = []

        for app in apps:
            data.append({
                "id": app.id,
                "full_name": f"{app.student.first_name} {app.student.last_name}",
                "email": app.student.email,
                "status": app.get_status_display(),
                "signed": app.contract_signed,
                "signed_by": app.signer_full_name,
                "signed_at": app.signed_at.strftime("%d.%m.%Y %H:%M") if app.signed_at else None,
                "contract_url": app.pdf_contract.url if app.pdf_contract else None,
                "signed_contract_url": app.signed_contract.url if app.signed_contract else None,
            })

        return Response(data)

# --------------------------------------------------------------------------------------------------------------------------------------------------------

class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['room_type', 'floor', 'building']

    @swagger_auto_schema(
        operation_description="📋 Получить список всех комнат",
        tags=["Комнаты"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


    @swagger_auto_schema(
        operation_description="📋 Получить данные конкретной комнаты",
        tags=["Комнаты"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    

    @swagger_auto_schema(
        method='get',
        operation_description="👤 Получить список студентов в комнате",
        tags=["Общие"]
    )
    @action(detail=True, methods=['get'], url_path='roommates')
    def roommates_info(self, request, pk=None):
        room = self.get_object()
        roommates = room.occupants.all()
        data = []

        for u in roommates:
            profile = getattr(u, 'profile', None)
            data.append({
                'id': u.id,
                'email': u.email,
                'name': f"{u.first_name} {u.last_name}",
                'course': profile.course if profile else None,
                'group': profile.group if profile else None,
                'roommate_preferences': profile.roommate_preferences if profile else None,
            })

        return Response(data)
    
# --------------------------------------------------------------------------------------------------------------------------------------------------------

class SupportMessageViewSet(viewsets.ModelViewSet):
    queryset = SupportMessage.objects.all().order_by('-created_at')
    serializer_class = SupportMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'aitusa':
            return SupportMessage.objects.all()
        return SupportMessage.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

# --------------------------------------------------------------------------------------------------------------------------------------------------------

    @swagger_auto_schema(
        method='post',
        operation_description="Ответить на обращение студента (только для роли Aitusa)",
        tags=["Aitusa Support"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["answer"],
            properties={
                "answer": openapi.Schema(type=openapi.TYPE_STRING, description="Ответ на обращение")
            }
        ),
        responses={
            200: openapi.Response(description="Ответ отправлен"),
            403: openapi.Response(description="Доступ запрещен"),
            400: openapi.Response(description="Ошибка данных")
        }
    )
    @action(detail=True, methods=['post'], url_path='reply')
    def reply_to_message(self, request, pk=None):
        user = request.user
        if user.role != 'aitusa':
            return Response({'detail': 'Доступ разрешён только роли Aitusa.'}, status=403)

        support_msg = self.get_object()
        answer = request.data.get('answer')

        if not answer:
            return Response({'error': 'Поле "answer" обязательно.'}, status=400)

        support_msg.answer = answer
        support_msg.answered_at = now()
        support_msg.is_answered = True
        support_msg.save()

        send_support_reply(email=support_msg.student.email, subject=support_msg.subject, body=answer)

        return Response({'success': f'Ответ отправлен на {support_msg.student.email}.'})

@swagger_auto_schema(
    method='get',
    tags=["📊 Метрики администратора"],
    operation_description="Получить метрики для административной панели. Требуется роль `admin`.",
    responses={
        200: openapi.Response(
            description="Успешный ответ с метриками",
            examples={
                "application/json": {
                    "total_students": 450,
                    "available_rooms": 9,
                    "total_applications": 673,
                    "rejected_applications": 27,
                    "application_statuses": {
                        "pending": 150,
                        "approved": 400,
                        "rejected": 27,
                        "canceled": 56,
                        "expired": 40
                    },
                    "room_stats": {
                        "total_rooms": 120,
                        "occupied_rooms": 100,
                        "full_rooms": 60,
                        "free_spots": 80
                    },
                    "roommate_preferences_chart": {
                        "chose_own": 112,
                        "waiting": 45,
                        "switched": 0,
                        "unassigned": 78,
                        "special_needs": 40
                    }
                }
            }
        ),
        403: openapi.Response(description="Нет доступа — только для админа"),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_metrics(request):
    if request.user.role != 'admin':
        return Response({'detail': 'Access denied'}, status=403)

    total_apps = DormitoryApplication.objects.count()
    pending = DormitoryApplication.objects.filter(status='PENDING').count()
    approved = DormitoryApplication.objects.filter(status='APPROVED').count()
    rejected = DormitoryApplication.objects.filter(status='REJECTED').count()
    canceled = DormitoryApplication.objects.filter(status='CANCELED').count()
    expired = DormitoryApplication.objects.filter(status='EXPIRED').count()
    from django.contrib.auth import get_user_model

    User = get_user_model()

    total_students = User.objects.filter(role="user").count()
    total_rooms = Room.objects.count()
    occupied_rooms = Room.objects.filter(occupants__isnull=False).distinct().count()
    full_rooms = sum([1 for r in Room.objects.all() if r.is_full()])
    free_spots = sum([r.capacity - r.occupants.count() for r in Room.objects.all()])
    available_rooms = sum([1 for r in Room.objects.all() if not r.is_full()])

    priority_distribution = DormitoryApplication.objects.values('priority').annotate(count=Count('id'))
    gender_distribution = DormitoryApplication.objects.values('gender').annotate(count=Count('id'))
    city_distribution = DormitoryApplication.objects.values('city').annotate(count=Count('id')).order_by('-count')[:5]

    return Response({
        "total_students": total_students,
        "available_rooms": available_rooms,
        "total_applications": total_apps,
        "rejected_applications": rejected,

        "application_statuses": {
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "canceled": canceled,
            "expired": expired,
        },

        "room_stats": {
            "total_rooms": total_rooms,
            "occupied_rooms": occupied_rooms,
            "full_rooms": full_rooms,
            "free_spots": free_spots
        },

        "analytics": {
            "priority_distribution": priority_distribution,
            "gender_distribution": gender_distribution,
            "city_distribution": city_distribution,
        }
    })

# --------------------------------------------------------------------------------------------------------------------------------------------------------

@swagger_auto_schema(
    method='get',
    tags=["📨 Метрики Aitusa"],
    operation_description="Получить статистику по обращениям студентов (роль `aitusa`).",
    responses={
        200: openapi.Response(
            description="Успешный ответ с метриками",
            examples={
                "application/json": {
                    "total_messages": 142,
                    "unanswered": 37,
                    "answered": 105,
                    "new_today": 4,
                    "avg_response_minutes": 58
                }
            }
        ),
        403: openapi.Response(description="Нет доступа — только для сотрудников Aitusa")
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def aitusa_dashboard_metrics(request):
    if request.user.role != 'aitusa':
        return Response({'detail': 'Access denied'}, status=403)

    total = SupportMessage.objects.count()
    unanswered = SupportMessage.objects.filter(is_answered=False).count()
    answered = SupportMessage.objects.filter(is_answered=True).count()
    new_today = SupportMessage.objects.filter(created_at__gte=now() - timedelta(days=1)).count()

    avg_response = SupportMessage.objects.filter(
        is_answered=True,
        answered_at__isnull=False
    ).annotate(
        response_time=ExpressionWrapper(F('answered_at') - F('created_at'), output_field=DurationField())
    ).aggregate(avg=Avg('response_time'))['avg']

    avg_response_minutes = int(avg_response.total_seconds() // 60) if avg_response else None

    return Response({
        "total_messages": total,
        "unanswered": unanswered,
        "answered": answered,
        "new_today": new_today,
        "avg_response_minutes": avg_response_minutes
    })

# --------------------------------------------------------------------------------------------------------------------------------------------------------

class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]

    @swagger_auto_schema(
        operation_description="🏢 Получить список всех общежитий/зданий",
        tags=["Здания"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="🏢 Получить данные конкретного здания",
        tags=["Здания"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
        