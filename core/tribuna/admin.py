from django.contrib import admin

from .models import Accounts, UserMessage


@admin.register(Accounts)
class ProfilesAdmin(admin.ModelAdmin):
    list_display = [
        'tgid',
        'clublogin',
        'clubname',
        'lastdate',
        'regdate',
    ]
    readonly_fields = (
        'tgid',
        'clublogin',
        'clubname',
                       )


@admin.register(UserMessage)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'message_id',
        'type',
        'data',

    ]