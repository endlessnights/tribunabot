from django.contrib import admin

from .models import Accounts, UserMessage, BotSettings


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
        'anonym',
        'status',
        'sent',
        'message_id',
        'type',
        'data',

    ]


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'anonym_func',
        'pre_moder',
    ]