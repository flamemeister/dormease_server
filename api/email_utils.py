from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_support_reply(email, subject, body):
    html_content = render_to_string("emails/reply_email.html", {
        'subject': subject,
        'message': body,
    })

    msg = EmailMultiAlternatives(
        subject=f"Ответ от Aitusa: {subject}",
        body=body,
        from_email="aldiyar.saken123@gmail.com",
        to=[email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
