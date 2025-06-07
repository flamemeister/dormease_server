from celery import shared_task

from .models import NotificationLog, DormitoryApplication

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

import os

STATUS_MESSAGES = {
    "PENDING": "Your application has been submitted and is awaiting review.",
    "APPROVED": "Your dormitory application has been approved. A PDF contract is attached. Please sign it via EzSigner and upload it back.",
    "REJECTED": "Unfortunately, your application has been rejected.",
    "CANCELED": "You have canceled your application.",
    "EXPIRED": "The application has expired.",
    "ROOM_CONFIRMED": "The administrator has confirmed the room you selected. Welcome!",
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
                if app.pdf_contract and app.pdf_contract.storage.exists(app.pdf_contract.name):
                    with app.pdf_contract.open('rb') as f:
                        email.attach(f"contract_{app.id}.pdf", f.read(), "application/pdf")
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
