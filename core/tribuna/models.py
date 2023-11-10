from django.db import models


class Accounts(models.Model):
    tgid = models.CharField(verbose_name='ID пользователя', max_length=48, null=True, unique=True, blank=True)
    tglogin = models.CharField(verbose_name='TG Username', blank=True, max_length=100, null=True)
    tgname = models.CharField(verbose_name='Имя', blank=True, max_length=100)
    regdate = models.DateTimeField(verbose_name='Дата регистрации', null=True, auto_now_add=True)
    lastdate = models.DateTimeField(verbose_name='Последнее использование', null=True, blank=True)
    clublogin = models.CharField(verbose_name='Vas3k username', max_length=100, blank=True, null=True)
    clubname = models.CharField(verbose_name='Vas3k name', max_length=200, blank=True, null=True)
    post_limit = models.PositiveIntegerField(verbose_name='Ограничения на постинг', blank=True, null=True, default=3)
    is_admin = models.BooleanField(verbose_name='Bot admin', default=False)
    has_access = models.BooleanField(verbose_name='Has access', default=False)

    def __str__(self):
        return str(self.tgid)

    def publish(self):
        self.save()

    class Meta:
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'


class UserMessage(models.Model):
    user = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    message_id = models.CharField(max_length=30, blank=True, null=True)
    type = models.CharField(max_length=30, blank=True, null=True)
    data = models.TextField(max_length=4000, blank=True, null=True)
    anonym = models.BooleanField(default=False)
    sent = models.BooleanField(default=False)
    accept = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.type}"
