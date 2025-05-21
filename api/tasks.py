from celery import shared_task
from .models import NotificationLog
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

STATUS_MESSAGES = {
    "PENDING": "Ваша заявка отправлена и ожидает рассмотрения.",
    "APPROVED": "Ваша заявка на общежитие одобрена. Вы можете выбрать комнату.",
    "REJECTED": "К сожалению, ваша заявка была отклонена.",
    "CANCELED": "Вы отменили свою заявку.",
    "EXPIRED": "Срок действия заявки истёк.",
    "ROOM_CONFIRMED": "Администратор подтвердил выбранную вами комнату. Добро пожаловать!",
}

@shared_task(bind=True, max_retries=3)
def send_status_email(self, to_email, status):
    try:
        text = STATUS_MESSAGES.get(status, f'Статус вашей заявки: {status}')
        html_content = render_to_string("emails/status_update.html", {"message": text})

        email = EmailMultiAlternatives(
            subject='Изменение статуса вашей заявки на общежитие',
            body=text,  
            from_email='noreply@aitu.kz',
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        NotificationLog.objects.create(
            recipient=to_email,
            status=status,
            success=True
        )
    except Exception as e:
        NotificationLog.objects.create(
            recipient=to_email,
            status=status,
            success=False,
            error_message=str(e)
        )
        raise self.retry(exc=e, countdown=10)
