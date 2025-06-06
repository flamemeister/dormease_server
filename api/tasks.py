from celery import shared_task
from .models import NotificationLog, DormitoryApplication
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import os

STATUS_MESSAGES = {
    "PENDING": "Ваша заявка отправлена и ожидает рассмотрения.",
    "APPROVED": "Ваша заявка на общежитие одобрена. Во вложении вы найдёте PDF-договор. Пожалуйста, подпишите его через EzSigner и загрузите обратно.",
    "REJECTED": "К сожалению, ваша заявка была отклонена.",
    "CANCELED": "Вы отменили свою заявку.",
    "EXPIRED": "Срок действия заявки истёк.",
    "ROOM_CONFIRMED": "Администратор подтвердил выбранную вами комнату. Добро пожаловать!",
}

@shared_task(bind=True, max_retries=3)
def send_status_email(self, to_email, status, application_id=None):
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

        if status == "APPROVED" and application_id:
            try:
                app = DormitoryApplication.objects.get(id=application_id)
                if app.pdf_contract and os.path.exists(app.pdf_contract.path):
                    email.attach_file(app.pdf_contract.path)
            except DormitoryApplication.DoesNotExist:
                pass  

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
