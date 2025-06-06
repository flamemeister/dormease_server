# user/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    context = {
        'reset_url': f"https://localhost:3000/reset-password?token={reset_password_token.key}&email={reset_password_token.user.email}",
        'user': reset_password_token.user,
    }

    subject = 'Сброс пароля'
    to_email = reset_password_token.user.email
    text = f'Ссылка для сброса пароля: {context["reset_url"]}'
    html = render_to_string('emails/password_reset_email.html', context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    email.attach_alternative(html, "text/html")
    email.send()
