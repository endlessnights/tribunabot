from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import BotSettings


@receiver(post_migrate)
def create_demo_user(sender, **kwargs):
    if sender.name == 'tribuna':
        user_model = get_user_model()
        # Check if a superuser already exists
        if not user_model.objects.filter(is_superuser=True).exists():
            demo_user = user_model.objects.create_user(
                username='root',
                password='RootPassword',
                email='demo@example.com',
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            demo_user.save()


@receiver(post_migrate)
def create_init_bot_settings(sender, **kwargs):
    if sender.name == 'tribuna':
        if not BotSettings.objects.exists():
            default_settings = BotSettings(
                anonym_func=False,
                pre_moder=False,
            )
            default_settings.save()