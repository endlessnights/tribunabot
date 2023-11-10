import os
import re
import time
import requests
from django.core.management import BaseCommand
from django.utils import timezone
from telebot import TeleBot, types
from telebot.types import CallbackQuery

from . import config
from ...models import Accounts, UserMessage

try:
    production = os.environ['PROD_OUTLINE_BOT']
except KeyError:
    print('NO PROD_OUTLINE_BOT')
try:
    tg_token = os.environ['TELEGRAM_BOT_SECRET_OUTLINE_BOT']
except KeyError:
    print('NO TELEGRAM_BOT_SECRET_OUTLINE_BOT')
try:
    club_service_token_os = os.environ['CLUB_SERVICE_TOKEN_OUTLINE_BOT']
except KeyError:
    print('NO CLUB_SERVICE_TOKEN_OUTLINE_BOT')

bot = TeleBot(tg_token, threaded=False)
club_service_token = club_service_token_os
bot_admin = 326070831
test_channel_id = '-1002139696426'
headers = {
    'X-Service-Token': '{}'.format(club_service_token),
    'X-Requested-With': 'XMLHttpRequest'
}

last_user_message = {}


def delete_prev_message(message):
    if message.chat.id in last_user_message:
        bot.delete_message(message.chat.id, last_user_message[message.chat.id])
    bot.delete_message(message.chat.id, message.message_id)


def get_user_password_input(message):
    club_profile = requests.get(url='https://vas3k.club/user/by_telegram_id/326070831.json', headers=headers)
    if club_profile.status_code == 200:
        profile_json = club_profile.json()
        club_get_bio = profile_json['user']['bio']
        find_bot_password = re.search(r'\[\[bot_password:(.*?)\]\]', club_get_bio)
        if find_bot_password:
            bot_password = find_bot_password.group(1).strip()
            read_pass_from_user = message.text
            if bot_password == read_pass_from_user:
                p = Accounts.objects.get(tgid=message.chat.id)
                #   Помечаем пользователя, что у него есть доступ к боту и получению настроек
                p.has_access = True
                #   Если пользователь пришел из клуба, ввел пароль из профиля, ставим тариф paid1
                p.rateclass = 'paid1'
                p.save()
                bot.send_message(message.chat.id, 'has access')
            else:
                print(f'''user input: {read_pass_from_user},
vas3k_profile_pass: {bot_password}''')
                bot.send_message(message.chat.id, config.password_is_wrong)
        else:
            print("bot_password not found in the bio field.")


def get_club_profile(telegram_id):
    club_profile = requests.get(url='https://vas3k.club/user/by_telegram_id/{}.json'.format(telegram_id),
                                headers=headers)
    if club_profile.status_code == 200:
        profile_json = club_profile.json()
        club_profile_slug = profile_json['user']['slug']
        club_full_name = profile_json['user']['full_name']
        return club_profile_slug, club_full_name
    else:
        return None


@bot.message_handler(commands=['start'])
def start_bot(message):
    #   Получаем базовые данные из Телеграм учетки
    try:
        if message.from_user.first_name and message.from_user.last_name:
            name = message.from_user.first_name + message.from_user.last_name
        else:
            name = message.from_user.first_name or message.from_user.last_name
    except AttributeError:
        # Handle the case where message.from_user doesn't have first_name or last_name
        name = None

    try:
        username = message.from_user.username
    except AttributeError:
        # Handle the case where message.from_user doesn't have a username
        username = None

    try:
        p, created = Accounts.objects.update_or_create(
            tgid=message.chat.id,
            defaults={
                'tglogin': username,
                'tgname': name,
                'lastdate': timezone.now(),
            }
        )
    except Exception as e:
        # Handle any exceptions that may occur during UserProfile creation/update
        print(f"An error occurred: {e}")

    p = Accounts.objects.get(tgid=message.chat.id)
    if not p.has_access:
        #   Делаем запрос в vas3k.club, получаем данные учетки из клуба, если бот привязан
        club_profile_info = get_club_profile(message.chat.id)
        if club_profile_info is not None:
            p = Accounts.objects.get(tgid=message.chat.id)
            p.has_access = True
            club_profile_slug, club_full_name = club_profile_info
            bot.send_message(message.chat.id, config.hello_club_new_user)
        #   Если бот не привязан, то запрашиваем пароль (указан в профиле клуба)
        #   Или если сайт vas3k клуба возвращает не 200
        else:
            try:
                p = Accounts.objects.get(tgid=message.chat.id)
                if p.has_access:
                    bot.send_message(message.chat.id, config.hello_club_new_user)
                else:
                    get_user_password = bot.send_message(
                        message.chat.id, f'{config.start_text_new.format(p.tgname)}\n{config.ask_password}',
                        parse_mode='HTML')
                    bot.register_next_step_handler(get_user_password, get_user_password_input)
            except Exception as e:
                print(f'{e}:111')

        if club_profile_info is not None:
            p.clublogin = club_profile_slug
            p.clubname = club_full_name
            p.has_access = True
            p.save()
    else:
        bot.send_message(message.chat.id, config.hello_club_user)


@bot.message_handler(commands=['new'])
def new_post(message):
    try:
        p = Accounts.objects.get(tgid=message.chat.id)
        if p.has_access:
            new_post_tooltip = bot.send_message(message.chat.id, config.new_post_tooltip)
            bot.register_next_step_handler(new_post_tooltip, get_new_post)
    except Exception as e:
        bot.send_message(message.chat.id, 'У вас нет доступа к этому боту. Нажмите /start для начала работы с ботом')
        print(e)


def get_new_post(message):
    p = Accounts.objects.get(tgid=message.chat.id)
    UserMessage(
        user=p,
        data=message.text,
        message_id=message.id
    ).save()
    m = UserMessage.objects.get(message_id=message.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    send_public = types.InlineKeyboardButton(
        text='Отправить пост публично',
        callback_data=f"send_post,{message.chat.id},{m.message_id},anonym=False"
    )
    send_anonym = types.InlineKeyboardButton(
        text='Отправить пост анонимно',
        callback_data=f"send_post,{message.chat.id},{m.message_id},anonym=True"
    )
    markup.add(send_public, send_anonym)
    visibility_buttons = bot.send_message(message.chat.id, 'Выберите формат поста', reply_markup=markup)
    last_user_message[message.chat.id] = visibility_buttons.message_id


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if str(call.data).startswith('send_post'):
        bot.answer_callback_query(call.id)
        callback_data = call.data.split(',')
        post_author = int(callback_data[1])
        message_id = int(callback_data[2])
        anonym = callback_data[3].split('=')[1]
        m = UserMessage.objects.get(message_id=message_id)
        if not m.sent:
            post_text = f'Новый пост в Вастрик.Трибуна!\n{m.data}' if anonym == 'True' else f'Новый пост в Вастрик.Трибуна!\nАвтор: {post_author}\n{m.data}'
            bot.send_message(test_channel_id, post_text)
            user_succ_reply = bot.send_message(call.message.chat.id, 'Сообщение отправлено в Вастрик.Трибуна')
            if anonym == 'True':
                m.anonym = True
            else:
                m.anonym = False
            m.sent = True
            m.save()
        else:
            bot.send_message(call.message.chat.id, 'Сообщение уже было отправлено!')
        bot.delete_message(call.message.chat.id, last_user_message[call.message.chat.id])


class Command(BaseCommand):
    help = 'Implemented to Django application telegram bot setup command'

    # if production:
    #     def handle(self, *args, **kwargs):
    #         while True:
    #             try:
    #                 bot.polling(none_stop=True, timeout=30)
    #             except requests.exceptions.ReadTimeout:
    #                 print('Read timeout exception. Retrying in 10 seconds...')
    #                 time.sleep(10)
    # else:
    def handle(self, *args, **kwargs):
        bot.polling(none_stop=True)
