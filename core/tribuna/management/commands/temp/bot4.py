import json
import os
import re
import requests
from django.core.management import BaseCommand
from django.utils import timezone
from telebot import TeleBot, types
from requests.exceptions import Timeout
from telebot.types import InputMediaPhoto, InputMediaVideo
import threading
import time

from core.tribuna.management.commands import config
from core.tribuna.models import Accounts, UserMessage, BotSettings

try:
    production = os.environ['PROD_TRIBUNA_BOT']
except KeyError:
    print('NO PROD_TRIBUNA_BOT')
try:
    tg_token = os.environ['TELEGRAM_BOT_SECRET_TRIBUNA']
except KeyError:
    print('NO TELEGRAM_BOT_SECRET_TRIBUNA')
try:
    club_service_token_os = os.environ['CLUB_SERVICE_TOKEN_OUTLINE_BOT']
except KeyError:
    print('NO CLUB_SERVICE_TOKEN_OUTLINE_BOT')
    club_service_token_os = os.environ['CLUB_SERVICE_TOKEN_OUTLINE_BOT']

bot = TeleBot(tg_token, threaded=True, num_threads=32)
# bot = TeleBot(tg_token, threaded=False)
club_service_token = club_service_token_os
bot_admin = 326070831
test_channel_id = '-1002139696426'
headers = {
    'X-Service-Token': '{}'.format(club_service_token),
    'X-Requested-With': 'XMLHttpRequest'
}

last_user_message = {}

bot_admins = Accounts.objects.filter(is_admin=True)
bot_settings = BotSettings.objects.first()


def delete_prev_message(message):
    if message.chat.id in last_user_message:
        bot.delete_message(message.chat.id, last_user_message[message.chat.id])
    bot.delete_message(message.chat.id, message.message_id)


def get_user_password_input(message):
    read_pass_from_user = message.text
    p = Accounts.objects.get(tgid=message.chat.id)
    try:
        club_profile = requests.get(url='https://vas3k.club/user/by_telegram_id/326070831.json', headers=headers,
                                    timeout=3)
        if club_profile.status_code == 200:
            profile_json = club_profile.json()
            club_get_bio = profile_json['user']['bio']
            find_bot_password = re.search(r'\[\[bot_password:(.*?)\]\]', club_get_bio)
            if find_bot_password:
                bot_password = find_bot_password.group(1).strip()
                if bot_password == read_pass_from_user:
                    #   Если пользователь пришел из клуба, ввел пароль из профиля
                    bot.send_message(message.chat.id, 'Пароль подошел! Чтобы написать пост, нажмите /new')
                    p.has_access = True
                    p.save()
                else:
                    print(f'''user input: {read_pass_from_user},
    vas3k_profile_pass: {bot_password}''')
                    bot.send_message(message.chat.id, config.password_is_wrong)
            else:
                print("bot_password not found in the bio field.")
    except Timeout:
        if read_pass_from_user == '124legeminus365':
            bot.send_message(message.chat.id, 'Пароль подошел! Чтобы написать пост, нажмите /new')
            p.has_access = True
            p.save()
    except Exception as e:
        print(f'get_user_password_input: {e}')


def get_club_profile(telegram_id):
    try:
        club_profile = requests.get(url='https://vas3k.club/user/by_telegram_id/{}.json'.format(telegram_id),
                                    headers=headers, timeout=3)
        if club_profile.status_code == 200:
            profile_json = club_profile.json()
            club_profile_slug = profile_json['user']['slug']
            club_full_name = profile_json['user']['full_name']
            return club_profile_slug, club_full_name
    except Timeout:
        print('vas3k json didnt answer in 3 seconds')
        return None
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def show_keyboard_buttons(message):
    if Accounts.objects.filter(tgid=message.chat.id, is_admin=True).exists():
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        moderation = types.KeyboardButton(text=config.moderation_list)
        keyboard.add(moderation)
        return keyboard


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
        print(f"An error occurred in def start_bot: {e}")
    p = Accounts.objects.get(tgid=message.chat.id)
    p.get_content = False
    p.has_access = True
    p.save()
    #   Пытаемся узнать, является ли пользлватель участником Вастрик.Клуба
    try:
        club_profile_info = get_club_profile(message.chat.id)
        club_profile_slug, club_full_name = club_profile_info
        p.clublogin = club_profile_slug
        p.clubname = club_full_name
        p.has_access = True
        p.save()
    except Exception as e:
        print(e)
    try:
        if p.has_access:
            bot.send_message(message.chat.id,
                             config.hello_registered_user,
                             parse_mode='HTML')
    except Exception as e:
        print(e)


@bot.message_handler(commands=['help'])
def help_bot(message):
    if Accounts.objects.filter(tgid=message.chat.id, is_admin=True).exists():
        bot.send_message(message.chat.id, config.bot_help_admin)
    else:
        bot.send_message(message.chat.id, config.bot_help)


@bot.message_handler(commands=['about'])
def about_bot(message):
    bot.send_message(message.chat.id, config.about_bot)


@bot.message_handler(commands=['admin'])
def admin_bot(message):
    try:
        bot_settings = BotSettings.objects.first()
        super_admins = Accounts.objects.filter(superadmin=True)
        if Accounts.objects.filter(tgid=message.chat.id, is_admin=True).exists():
            markup = types.InlineKeyboardMarkup(row_width=1)
            block_user = types.InlineKeyboardButton(
                text='Заблокировать пользователя',
                callback_data=f"admin_actions,action=block_user"
            )
            unlock_user = types.InlineKeyboardButton(
                text='Разблокировать пользователя',
                callback_data=f"admin_actions,action=unlock_user_inline"
            )
            banned_list = types.InlineKeyboardButton(
                text='Просмотреть блок-лист',
                callback_data=f"admin_actions,action=banned_list"
            )
            add_admin = types.InlineKeyboardButton(
                text='Добавить админа',
                callback_data=f"admin_actions,action=add_admin"
            )
            add_super_admin = types.InlineKeyboardButton(
                text='Добавить суперадмина',
                callback_data=f"admin_actions,action=add_super_admin"
            )
            admin_list = types.InlineKeyboardButton(
                text='Список админов',
                callback_data=f"admin_actions,action=admin_list"
            )
            if not bot_settings.pre_moder:
                pre_moder_switch_text = 'Включить пре-модерацию'
            else:
                pre_moder_switch_text = 'Выключить пре-модерацию'
            pre_moder_switch = types.InlineKeyboardButton(
                text=pre_moder_switch_text,
                callback_data=f"admin_actions,action=pre_moder"
            )
            if not bot_settings.anonym_func:
                anonym_switch_text = 'Включить анонимность'
            else:
                anonym_switch_text = 'Выключить анонимность'
            anonym_switch = types.InlineKeyboardButton(
                text=anonym_switch_text,
                callback_data=f"admin_actions,action=anonym_func"
            )
            if str(message.chat.id) in str(super_admins):
                markup.add(block_user, unlock_user, banned_list, add_admin, add_super_admin, admin_list,
                           pre_moder_switch, anonym_switch)
            else:
                markup.add(block_user, unlock_user, banned_list)
            delete_prev_message(message)
            show_admin_menu = bot.send_message(message.chat.id, 'Команды администратора бота', reply_markup=markup)
            last_user_message[message.chat.id] = show_admin_menu.message_id
    except Exception as e:
        print(e)


def send_posts_markup(message, first_msg_id, type):
    if not type == 'poll':
        m = UserMessage.objects.get(message_id=first_msg_id)
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
        return markup
    else:
        m = UserMessage.objects.get(poll_id=message.poll.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        send_public = types.InlineKeyboardButton(
            text='Отправить пост публично',
            callback_data=f"send_post,{message.chat.id},{m.poll_id},anonym=False"
        )
        send_anonym = types.InlineKeyboardButton(
            text='Отправить пост анонимно',
            callback_data=f"send_post,{message.chat.id},{m.poll_id},anonym=True"
        )
        markup.add(send_public, send_anonym)
        return markup


@bot.message_handler(commands=['new'])
def new_post(message):
    try:
        p = Accounts.objects.get(tgid=message.chat.id)
        send_to_moderate = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        send_to_moderate_btn = types.KeyboardButton(text=config.send_to_moderate)
        send_to_moderate.add(send_to_moderate_btn)
        try:
            p = Accounts.objects.get(tgid=message.chat.id)
            if p.has_access:
                delete_prev_message(message)
                new_post_tooltip = bot.send_message(message.chat.id, config.new_post_tooltip,
                                                    reply_markup=send_to_moderate)
                last_user_message[message.chat.id] = new_post_tooltip.message_id
                p.get_content = True
                p.save()
        except Exception as e:
            bot.send_message(message.chat.id,
                             'У вас нет доступа к этому боту. Нажмите /start для начала работы с ботом')
            print(e)
    except Exception as e:
        print(e)


@bot.message_handler(commands=['publish'])
def publish_it_action_btn(message):
    p = Accounts.objects.get(tgid=message.chat.id)
    if message.chat.id in user_photos:
        publish_photo_func(message, p)
    elif message.chat.id in user_videos:
        publish_video_func(message, p)
    elif p.get_content and message.text != '/publish':
        publish_text_func(message, p)


user_media_lock = threading.Lock()
user_media = {}


def process_media(p, chat_id, media_list, caption):
    with user_media_lock:
        if chat_id not in user_media:
            user_media[chat_id] = {'count': 0, 'media': []}

        user_media[chat_id]['count'] += 1
        user_media[chat_id]['media'].extend(media_list)

        # If the user has sent some media, store file_ids in the database
        if user_media[chat_id]['count'] > 0:
            timestamp = user_media[chat_id]['media'][0]['date']
            file_ids = [photo['file_id'] for photo in user_media[chat_id]['media']]
            store_media_in_db(p, file_ids, timestamp)

        # If the user has sent the desired number of media, process and store them
        if user_media[chat_id]['count'] >= 10:
            manage_media_post(p, chat_id, user_media[chat_id]['media'], caption)
            create_media_message_record(p, user_media[chat_id]['media'], caption)
            del user_media[chat_id]
            p.get_content = False
            p.save()


def manage_media_post(p, chat_id, media_list, caption):
    # Process and store the media
    # You can customize this function to store the media in the database or perform other actions.
    # In this example, we print the file IDs and captions.
    print("Media List:")
    for media in media_list:
        print(f"File ID: {media['file_id']}, Caption: {media['caption']}")

    # Reset the user's media count and list
    user_media[chat_id] = {'count': 0, 'media': []}


# Message handler for receiving photos and videos
@bot.message_handler(content_types=['photo', 'video'])
def media_message(message):
    try:
        p = Accounts.objects.get(tgid=message.chat.id)
        if p.has_access and p.get_content:
            caption = message.caption if message.caption else ""

            media_info = {
                'file_id': message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id,
                'caption': caption
            }

            # Process the media with a delay
            threading.Thread(target=process_media, args=(p, message.chat.id, [media_info], caption)).start()

    except Exception as e:
        print(f"Error handling media message: {e}")


def store_media_in_db(p, file_ids, timestamp):
    UserMessage(
        user=p,
        message_id=None,  # You might need to adjust this based on your requirements
        file_ids=','.join(file_ids),
        type='photo',  # Assuming the media type is always photo
        data=None,  # You might want to add some data here
        timestamp=timestamp
    ).save()

# create_user_message_record
def create_media_message_record(p, media_list, caption):
    first_media_info = media_list[0]
    media_type = 'photo' if 'file_id' in first_media_info else 'video'

    UserMessage(
        user=p,
        message_id=first_media_info['message_id'],
        file_ids=','.join(media['file_id'] for media in media_list),
        type=media_type,
        data=(caption if caption else '')
    ).save()


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    bot_settings = BotSettings.objects.first()
    bot_admins = Accounts.objects.filter(is_admin=True)
    super_admins = Accounts.objects.filter(superadmin=True)
    if str(call.data).startswith('send_post'):
        callback_data = call.data.split(',')
        post_author = int(callback_data[1])
        message_id = int(callback_data[2])
        anonym = callback_data[3].split('=')[1]
        try:
            m = UserMessage.objects.get(message_id=message_id)
        except Exception as e:
            m = UserMessage.objects.get(poll_id=message_id)
        if anonym == 'True':
            m.anonym = True
            m.save()
        if anonym == 'False':
            m.anonym = False
            m.save()
        #   Если отключена возможность отправки анонимный постов в настройках, то все посты будут публичные
        if not bot_settings.anonym_func:
            m.anonym = False
            m.save()
        if bot_settings.pre_moder:
            markup = types.InlineKeyboardMarkup(row_width=2)
            accept_post = types.InlineKeyboardButton(
                text='✅',
                callback_data=f"post_accept_action,{m.message_id if m.type != 'poll' else m.poll_id},{anonym},accept=True"
            )
            cancel_post = types.InlineKeyboardButton(
                text='❌',
                callback_data=f"post_accept_action,{m.message_id if m.type != 'poll' else m.poll_id},{anonym},accept=False"
            )
            warn_delete_post = types.InlineKeyboardButton(
                text='Удалить и предупредить',
                callback_data=f"post_accept_action,{m.message_id if m.type != 'poll' else m.poll_id},{anonym},accept=Warn"
            )
            block_user = types.InlineKeyboardButton(
                text='Заблокировать юзера',
                callback_data=f"post_accept_action,{m.message_id if m.type != 'poll' else m.poll_id},{anonym},accept=Block"
            )
            markup.add(accept_post, cancel_post, warn_delete_post, block_user)
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            cancel_post = types.InlineKeyboardButton(
                text='Удалить',
                callback_data=f"post_accept_action,{m.message_id if m.type != 'poll' else m.poll_id},{anonym},accept=False"
            )
            warn_delete_post = types.InlineKeyboardButton(
                text='Удалить и предупредить',
                callback_data=f"post_accept_action,{m.message_id if m.type != 'poll' else m.poll_id},{anonym},accept=Warn"
            )
            block_user = types.InlineKeyboardButton(
                text='Заблокировать юзера',
                callback_data=f"post_accept_action,{m.message_id if m.type != 'poll' else m.poll_id},{anonym},accept=Block"
            )
            markup.add(cancel_post, warn_delete_post, block_user)
        if m.type == 'text':
            if not bot_settings.pre_moder:
                for admin in bot_admins:
                    post_text_admins = f'©️{m.user.tgname} {m.user.tglogin if m.user.tglogin else ""} — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}'
                    bot.send_message(admin.tgid,
                                     post_text_admins,
                                     reply_markup=markup,
                                     parse_mode='HTML')
                if m.anonym:
                    post_text_channel = f'{m.data}'
                else:
                    post_text_channel = f'{m.user.tgname} {"@" + m.user.tglogin if m.user.tglogin else ""}\nТекст: {m.data}'
                post_to_channel = bot.send_message(test_channel_id, post_text_channel, parse_mode='HTML')
                #   Сохраняем Message_id поста в канале
                m.channel_message_id = post_to_channel.message_id
                m.save()
            else:
                for admin in bot_admins:
                    post_text = f'©️{m.user.tgname} {m.user.tglogin if m.user.tglogin else ""} — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}'
                    bot.send_message(admin.tgid,
                                     post_text,
                                     reply_markup=markup,
                                     parse_mode='HTML')
        elif m.type == 'poll':
            if not bot_settings.pre_moder:
                poll_options = json.loads(m.options)
                for admin in bot_admins:
                    bot.send_poll(admin.tgid,
                                  question=m.question,
                                  options=poll_options,
                                  allows_multiple_answers=m.allows_multiple_answers_poll)
                    bot.send_message(admin.tgid,
                                     f'©️{m.user.tgname} {m.user.tglogin if m.user.tglogin else ""} — {m.user.tgid}\nОтправлен опрос\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     reply_markup=markup,
                                     parse_mode='HTML',
                                     disable_web_page_preview=True)
                question_text = f'{m.question}\n{"Автор: " + m.user.tgname if not m.anonym else ""}'
                post_to_channel = bot.send_poll(test_channel_id,
                                                question=question_text,
                                                options=poll_options,
                                                allows_multiple_answers=m.allows_multiple_answers_poll)
                m.channel_message_id = post_to_channel.message_id
                m.save()
            else:
                poll_options = json.loads(m.options)
                for admin in bot_admins:
                    bot.send_poll(admin.tgid,
                                  question=m.question,
                                  options=poll_options,
                                  allows_multiple_answers=m.allows_multiple_answers_poll)
                    bot.send_message(admin.tgid,
                                     f'©️{m.user.tgname} {m.user.tglogin if m.user.tglogin else ""} — {m.user.tgid}\nОтправлен опрос\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     reply_markup=markup,
                                     parse_mode='HTML',
                                     disable_web_page_preview=True)
        elif m.type == 'photo' or 'video':
            media_list = str(m.file_ids)
            media_list = [item.strip() for item in media_list.split(",")]
            caption = f'{m.data}'
            #   Если включена премодерация
            if bot_settings.pre_moder:
                for admin in bot_admins:
                    bot.send_media_group(admin.tgid,
                                         [InputMediaVideo(media=item, caption=caption if index == 0 else None) for
                                          index, item in
                                          enumerate(media_list)] if m.type == 'video' else [
                                             InputMediaPhoto(media=item, caption=caption if index == 0 else None,
                                                             parse_mode='HTML') for index, item in
                                             enumerate(media_list)])

                    bot.send_message(admin.tgid,
                                     f'©️{m.user.tgname} {m.user.tglogin if m.user.tglogin else ""} — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     reply_markup=markup,
                                     parse_mode='HTML',
                                     disable_web_page_preview=True)
            #   Если выключена премодерация
            else:
                for admin in bot_admins:
                    bot.send_media_group(admin.tgid,
                                         [InputMediaVideo(media=item, caption=caption if index == 0 else None) for
                                          index, item in
                                          enumerate(media_list)] if m.type == 'video' else [
                                             InputMediaPhoto(media=item, caption=caption if index == 0 else None,
                                                             parse_mode='HTML') for index, item in
                                             enumerate(media_list)])
                    bot.send_message(admin.tgid,
                                     f'©️{m.user.tgname} {m.user.tglogin if m.user.tglogin else ""} — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     parse_mode='HTML',
                                     reply_markup=markup,
                                     disable_web_page_preview=True)
                post_to_channel = bot.send_media_group(test_channel_id,
                                                       [InputMediaVideo(media=item,
                                                                        caption=caption if index == 0 else None) for
                                                        index, item in
                                                        enumerate(media_list)] if m.type == 'video' else [
                                                           InputMediaPhoto(media=item,
                                                                           caption=caption if index == 0 else None,
                                                                           parse_mode='HTML') for index, item in
                                                           enumerate(media_list)])
                channel_message_ids = [message.message_id for message in post_to_channel]
                m.channel_message_id = ','.join(map(str, channel_message_ids))
                m.status = 'accept'
                m.sent = True
                m.save()
        bot.send_message(call.message.chat.id, config.post_sent, parse_mode='HTML', disable_web_page_preview=True)
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.answer_callback_query(call.id)
    if str(call.data).startswith('post_accept_action'):
        callback_data = call.data.split(',')
        message_id = int(callback_data[1])
        anonym = str(callback_data[2])
        action = callback_data[3].split('=')[1]
        try:
            m = UserMessage.objects.get(message_id=message_id)
        except Exception as e:
            print(e)
            m = UserMessage.objects.get(poll_id=message_id)
        if action == 'True':
            if m.type == 'text':
                post_text = (
                    config.anonym_text_post.format(m.data) if anonym == 'True' else config.public_text_post.format(
                        m.data, m.user.tglogin, m.user.tgname))
                bot.send_message(test_channel_id, post_text, parse_mode='HTML')
            elif m.type == 'poll':
                question_text = f'{m.question}\n{"Автор: " + m.user.clubname if not m.anonym else ""}'
                poll_options = json.loads(m.options)
                post_to_channel = bot.send_poll(test_channel_id,
                                                question=question_text,
                                                options=poll_options,
                                                allows_multiple_answers=m.allows_multiple_answers_poll)
                m.channel_message_id = post_to_channel.message_id
                m.save()
            elif m.type == 'photo' or 'video':
                media_list = str(m.file_ids)
                media_list = [item.strip() for item in media_list.split(",")]
                caption = (
                    config.anonym_text_post.format(m.data) if anonym == 'True' else config.public_text_post.format(
                        m.data, m.user.tglogin, m.user.tgname))
                post_to_channel = bot.send_media_group(test_channel_id, [
                    InputMediaPhoto(media=item, caption=caption if index == 0 else None, parse_mode='HTML') for
                    index, item in
                    enumerate(media_list)] if m.type == 'photo' else [
                    InputMediaVideo(media=item, caption=caption if index == 0 else None, parse_mode='HTML') for
                    index, item in enumerate(media_list)])
                channel_message_ids = [message.message_id for message in post_to_channel]
                m.channel_message_id = ','.join(map(str, channel_message_ids))
                m.save()
            user_succ_reply = bot.send_message(m.user.tgid, config.post_sent, parse_mode='HTML',
                                               disable_web_page_preview=True)
            m.sent = True
            m.status = 'accept'
            m.save()
        elif action == 'False':
            if bot_settings.pre_moder:
                user_succ_reply = bot.send_message(m.user.tgid, 'Сообщение не прошло модерацию!')
                m.status = 'failed'
                m.sent = False
                m.save()
            else:
                if not m.status == 'failed':
                    channel_message_ids_list = list(map(int, m.channel_message_id.split(',')))
                    for channel_message_id in channel_message_ids_list:
                        bot.delete_message(test_channel_id, channel_message_id)
                    m.status = 'failed'
                    m.sent = False
                    m.save()
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    block_user = types.InlineKeyboardButton(
                        text='Заблокировать юзера',
                        callback_data=f"post_accept_action,{m.message_id},{anonym},accept=Block"
                    )
                    markup.add(block_user)
                    bot.send_message(call.message.chat.id, 'Показываю кнопки', reply_markup=markup)
                else:
                    bot.answer_callback_query(call.id, 'Пост уже был удален другим админом')
        elif action == 'Warn':
            if bot_settings.pre_moder:
                user_succ_reply = bot.send_message(m.user.tgid, config.warn_msg)
                m.status = 'failed'
                m.sent = False
                m.save()
                bot.answer_callback_query(call.id, 'Удалено с предупреждением')
            else:
                if not m.status == 'failed':
                    channel_message_ids_list = list(map(int, m.channel_message_id.split(',')))
                    for channel_message_id in channel_message_ids_list:
                        bot.delete_message(test_channel_id, channel_message_id)
                    m.status = 'failed'
                    m.sent = False
                    m.save()
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    block_user = types.InlineKeyboardButton(
                        text='Заблокировать юзера',
                        callback_data=f"post_accept_action,{m.message_id},{anonym},accept=Block"
                    )
                    markup.add(block_user)
                    bot.send_message(call.message.chat.id, 'Показываю кнопки', reply_markup=markup)
                    user_succ_reply = bot.send_message(m.user.tgid, config.warn_msg)
                else:
                    bot.answer_callback_query(call.id, 'Пост уже был удален другим админом')
        elif action == 'Block':
            if not m.user.banned:
                user_succ_reply = bot.send_message(m.user.tgid, config.block_msg)
                p = Accounts.objects.get(tgid=m.user.tgid)
                p.banned = True
                p.save()
                bot.answer_callback_query(call.id, 'Пользователь заблокирован')
            else:
                bot.answer_callback_query(call.id, 'Юзер уже был забанен другим админом')
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.answer_callback_query(call.id)
    # admin actions:
    #   block_user
    #   unlock_user
    #   banned_list
    #   add_admin
    #   rem_admin
    #   admin_list
    #   pre_moder
    #   anonym_func
    if str(call.data).startswith('admin_actions'):
        callback_data = call.data.split(',')
        action = callback_data[1].split('=')[1]
        if action == 'block_user':
            block_user_msg = bot.send_message(call.message.chat.id,
                                              'Отправьте юзернейм пользователя или его уникальный идентификатор')
            bot.register_next_step_handler(block_user_msg, block_user_func)
        if action == 'banned_list':
            for user_item in Accounts.objects.filter(banned=True):
                user_tgid = user_item.tgid
                callback_data = f'unlock_user,{user_tgid}'
                markup = types.InlineKeyboardMarkup(row_width=1)
                unlock_user = types.InlineKeyboardButton(
                    text=f'Разблокировать {user_tgid} 👆',
                    callback_data=callback_data
                )
                markup.add(unlock_user)
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text=f'{user_item.clubname + " " + user_item.clublogin if user_item.clubname else user_item.tglogin if user_item.tglogin else user_item.tgname, user_item.tgid}',
                    reply_markup=markup
                )
            bot.answer_callback_query(call.id)

            # bot.register_next_step_handler(block_user_msg, block_user_func)
        if action == 'add_admin':
            add_admin_msg = bot.send_message(call.message.chat.id,
                                             'Отправьте юзернейм пользователя или его уникальный идентификатор')
            bot.register_next_step_handler(add_admin_msg, add_admin_func)
        if action == 'admin_list':
            admin_list_prev = bot.send_message(call.message.chat.id, 'Список админов бота:')

            for user_item in Accounts.objects.filter(is_admin=True):
                user_tgid = user_item.tgid
                callback_data = f"admin_rem,{user_tgid}"
                markup = types.InlineKeyboardMarkup(row_width=1)
                rem_admin = types.InlineKeyboardButton(
                    text=f'Удалить админа {user_tgid} 👆',
                    callback_data=callback_data
                )
                markup.add(rem_admin)
                bot.send_message(call.message.chat.id,
                                 f'{user_item.clubname + " " + user_item.clublogin if user_item.clubname else user_item.tglogin if user_item.tglogin else user_item.tgname, user_item.tgid}',
                                 reply_markup=markup)
        if action == 'unlock_user_inline':
            unlock_user_msg = bot.send_message(call.message.chat.id,
                                               'Отправьте юзернейм пользователя или его уникальный идентификатор')
            bot.register_next_step_handler(unlock_user_msg, unlock_user_func)
        if action == 'pre_moder':
            if bot_settings.pre_moder:
                bot_settings.pre_moder = False
                bot.answer_callback_query(call.id, 'Премодерация отключена!')
                bot_settings.save()
            else:
                bot_settings.pre_moder = True
                bot.answer_callback_query(call.id, 'Премодерация включена!')
                bot_settings.save()
        if action == 'anonym_func':
            if bot_settings.anonym_func:
                bot_settings.anonym_func = False
                bot.answer_callback_query(call.id, 'Анонимность отключена!')
                bot_settings.save()
            else:
                bot_settings.anonym_func = True
                bot.answer_callback_query(call.id, 'Анонимность включена!')
                bot_settings.save()
        if action == 'add_super_admin':
            add_super_admin_msg = bot.send_message(
                call.message.chat.id,
                'Отправьте юзернейм пользователя или его уникальный идентификатор')
            bot.register_next_step_handler(add_super_admin_msg, add_super_admin_func)
    if str(call.data).startswith('admin_rem'):
        callback_data = call.data.split(',')
        admin_id = str(callback_data[1])
        p = Accounts.objects.get(tgid=admin_id)
        p.is_admin = False
        p.save()
        bot.answer_callback_query(call.id, f'Пользователь {p.tgid} был удален из списка админов!')
    if str(call.data).startswith('unlock_user'):
        callback_data = call.data.split(',')
        user_id = str(callback_data[1])
        p = Accounts.objects.get(tgid=user_id)
        p.banned = False
        p.save()
        bot.answer_callback_query(call.id, f'Пользователь {p.tgid} был разблокирован!')
        #   Пытаемся отправить пользователю сообщение, что его разблокировали
        try:
            bot.send_message(p.tgid, config.unblock_msg)
        except Exception as e:
            print(f'unlock_user callback: {e}')


def block_user_func(message):
    user_input = message.text
    try:
        all_users = Accounts.objects.all()
        for user in all_users:
            if str(user_input) in [str(user.tgid), str(user.tglogin)]:
                if not user.banned:
                    user.banned = True
                    user.save()
                    delete_prev_message(message)
                    succ_user_block = bot.send_message(message.chat.id,
                                                       f'✅ Пользователь {user.tgname} {"@" + user.tglogin if user.tglogin else ""} — {user.tgid} был заблокирован!')
                    last_user_message[message.chat.id] = succ_user_block.message_id
                else:
                    delete_prev_message(message)
                    already_user_blocked = bot.send_message(
                        message.chat.id,
                        f'❌ Пользователь {user.tgname} {"@" + user.tglogin if user.tglogin else ""} — {user.tgid} уже находится в блок-листе')
                    last_user_message[message.chat.id] = already_user_blocked.message_id
    except Exception as e:
        bot.send_message(message.chat.id, f'{config.admin_wrong_cmd}\nОшибка: {e}')


def unlock_user_func(message):
    user_input = message.text
    try:
        all_users = Accounts.objects.all()
        for user in all_users:
            if str(user_input) in [str(user.tgid), str(user.tglogin)]:
                if user.banned:
                    user.banned = False
                    user.save()
                    delete_prev_message(message)
                    unlock_user_msg = bot.send_message(message.chat.id,
                                                       f'✅ Пользователь {user.tgname} {"@" + user.tglogin if user.tglogin else ""} — {user.tgid} разблокирован!')
                    last_user_message[message.chat.id] = unlock_user_msg.message_id
                else:
                    delete_prev_message(message)
                    already_unblocked = bot.send_message(message.chat.id,
                                                         f'❌ Пользователь {user.tgname} {"@" + user.tglogin if user.tglogin else ""} — {user.tgid} не находится в блок-листе!')
                    last_user_message[message.chat.id] = already_unblocked.message_id
    except Exception as e:
        bot.send_message(message.chat.id, f'{config.admin_wrong_cmd}\nОшибка: {e}')


def add_admin_func(message):
    user_input = message.text
    try:
        all_users = Accounts.objects.all()
        for user in all_users:
            if str(user_input) in [str(user.tgid), str(user.tglogin)]:
                if not user.is_admin:
                    user.is_admin = True
                    user.save()
                    delete_prev_message(message)
                    add_admin_msg = bot.send_message(
                        message.chat.id,
                        f'✅ Пользователь {user.tgname} {"@" + user.tglogin if user.tglogin else ""} — {user.tgid} теперь администратор бота')
                    last_user_message[message.chat.id] = add_admin_msg.message_id
                else:
                    delete_prev_message(message)
                    already_bot_admin = bot.send_message(message.chat.id,
                                                         f'❌ Пользователь {user.tgname} {"@" + user.tglogin if user.tglogin else ""} — {user.tgid} уже является админом бота!')
                    last_user_message[message.chat.id] = already_bot_admin.message_id
    except Exception as e:
        bot.send_message(message.chat.id, f'{config.admin_wrong_cmd}\nОшибка: {e}')


def add_super_admin_func(message):
    user_input = message.text
    try:
        all_users = Accounts.objects.all()
        for user in all_users:
            if str(user_input) in [str(user.tgid), str(user.tglogin)]:
                if not user.superadmin:
                    user.superadmin = True
                    user.save()
                    delete_prev_message(message)
                    add_superadmin_msg = bot.send_message(
                        message.chat.id,
                        f'✅ Пользователь {user.tgname} {"@" + user.tglogin if user.tglogin else ""} — {user.tgid} теперь супер админ бота')
                    last_user_message[message.chat.id] = add_superadmin_msg.message_id
                else:
                    delete_prev_message(message)
                    already_superadmin_msg = bot.send_message(message.chat.id,
                                                              f'Пользователь {user.tgid} уже является супер админом бота!')
                    last_user_message[message.chat.id] = already_superadmin_msg.message_id
    except Exception as e:
        bot.send_message(message.chat.id, f'{config.admin_wrong_cmd}\nОшибка: {e}')


# Define a dictionary to store user photo information
user_photos = {}
user_videos = {}


@bot.message_handler(content_types=['document', 'audio', 'sticker', 'voice', 'video_note', 'contact', 'location'])
def forbidden_content(message):
    bot.send_message(message.chat.id, config.forbidden_types)
    p = Accounts.objects.get(tgid=message.chat.id)
    p.get_content = False
    p.save()


@bot.message_handler(content_types=['poll'])
def poll_message(message):
    bot_settings = BotSettings.objects.first()
    p = Accounts.objects.get(tgid=message.chat.id)
    if p.get_content:
        remove_reply_markup = types.ReplyKeyboardRemove()
        options = [option.text for option in message.poll.options]
        UserMessage(
            user=p,
            type='poll',
            question=message.poll.question,
            options=json.dumps(options),
            allows_multiple_answers_poll=message.poll.allows_multiple_answers,
            poll_id=message.poll.id
        ).save()
        m = UserMessage.objects.get(poll_id=message.poll.id)
        poll_options = json.loads(m.options)
        if bot_settings.anonym_func:
            visibility_buttons = bot.send_message(message.chat.id, 'Выберите формат поста',
                                                  reply_markup=send_posts_markup(message, message.poll.id, type='poll'))
            bot.send_message(message.chat.id, ':)', reply_markup=remove_reply_markup)
            last_user_message[message.chat.id] = visibility_buttons.message_id
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            send_post = types.InlineKeyboardButton(
                text='Запостить',
                callback_data=f"send_post,{message.chat.id},{message.poll.id},anonym=False"
            )
            markup.add(send_post)
            bot.send_poll(message.chat.id,
                          question=m.question,
                          options=poll_options,
                          allows_multiple_answers=m.allows_multiple_answers_poll)
            bot.send_message(message.chat.id, f'Так будет выглядеть ваше сообщение в канале:', reply_markup=markup)


@bot.message_handler(content_types=['text'])
def text_message(message):
    #   Показываем посты на ПреМодерации админам бота
    p = Accounts.objects.get(tgid=message.chat.id)
    bot_admins = Accounts.objects.filter(is_admin=True)
    if str(message.chat.id) in str(bot_admins):
        if message.text == config.moderation_list:
            posts = UserMessage.objects.filter(status='wait')
            for post in posts:
                markup = types.InlineKeyboardMarkup(row_width=2)
                accept_post = types.InlineKeyboardButton(
                    text='✅',
                    callback_data=f"post_accept_action,{post.message_id},{str(post.anonym)},accept=True"
                )
                cancel_post = types.InlineKeyboardButton(
                    text='❌',
                    callback_data=f"post_accept_action,{post.message_id},{str(post.anonym)},accept=False"
                )
                block_user = types.InlineKeyboardButton(
                    text='Block User',
                    callback_data=f"post_accept_action,{post.message_id},{str(post.anonym)},accept=Block"
                )
                markup.add(accept_post, cancel_post, block_user)
                if post.type == 'text':
                    for admin in bot_admins:
                        bot.send_message(admin.tgid,
                                         f'Отправитель: {"@" + post.user.tglogin if post.user.tglogin else post.user.tgname if post.user.tgname else post.user.tgid}\n{post.data}\nАнонимность: {post.anonym}',
                                         reply_markup=markup)
                elif post.type == 'photo' or 'video':
                    media_list = str(post.file_ids)
                    media_list = [item.strip() for item in media_list.split(",")]
                    caption = f'Отправитель: {post.user.tglogin if post.user.tglogin else post.user.tgname if post.user.tgname else post.user.tgid}\nТекст: {post.data}\nАнонимность: {post.anonym}'
                    for admin in bot_admins:
                        bot.send_media_group(admin.tgid,
                                             [InputMediaPhoto(media=item, caption=caption if index == 0 else None) for
                                              index, item in enumerate(media_list)]
                                             if post.type == 'photo' else [
                                                 InputMediaVideo(media=item, caption=caption if index == 0 else None)
                                                 for index, item in enumerate(media_list)])
                        bot.send_message(admin.tgid,
                                         f'©️{post.user.tgname} {post.user.tglogin if post.user.tglogin else ""} — {post.user.tgid}\nТекст: {post.data}\nАнонимно: {"Да" if post.anonym else "Нет"}',
                                         reply_markup=markup,
                                         parse_mode='HTML',
                                         disable_web_page_preview=True)
    if message.text == config.send_to_moderate:
        if message.chat.id in user_photos:
            publish_photo_func(message, p)
        elif message.chat.id in user_videos:
            publish_video_func(message, p)
    if message.text != config.send_to_moderate and p.get_content:
        publish_text_func(message, p)


def publish_photo_func(message, p):
    if p.get_content:
        #   Если отправляется фото, стопка фото
        if message.chat.id in user_photos:
            remove_reply_markup = types.ReplyKeyboardRemove()
            photos = user_photos[message.chat.id]['photos']
            non_empty_caption = find_non_empty_caption(photos)
            #   Если нет текста у фото
            if non_empty_caption is None:
                ask_for_caption = bot.send_message(message.chat.id, config.no_caption, reply_markup=remove_reply_markup)
                bot.register_next_step_handler(ask_for_caption,
                                               get_media_caption,
                                               profile=p,
                                               type='photo',
                                               medias=user_photos[message.chat.id]['photos']),
                p.get_content = False
                p.save()
            else:
                manage_photo_post(message, photos, non_empty_caption, p)


# def manage_photo_post(message, photos, non_empty_caption, p):
#     bot_settings = BotSettings.objects.first()
#     remove_reply_markup = types.ReplyKeyboardRemove()
#     create_photo_message_record(p, user_photos[message.chat.id]['photos'],
#                                 caption=non_empty_caption if non_empty_caption is not None else None)
#     first_message_id = photos[0]
#     first_msg_id = first_message_id['message_id']
#     if bot_settings.anonym_func:
#         bot.send_message(message.chat.id,
#                          config.post_sent,
#                          reply_markup=send_posts_markup(message, first_msg_id, type='photo'),
#                          parse_mode='HTML',
#                          disable_web_page_preview=True)
#         bot.send_message(message.chat.id, ':)', reply_markup=remove_reply_markup)
#     else:
#         m = UserMessage.objects.get(message_id=first_msg_id)
#         media_list = str(m.file_ids)
#         media_list = [item.strip() for item in media_list.split(",")]
#         caption = f'{m.data}'
#         markup = types.InlineKeyboardMarkup(row_width=1)
#         send_post = types.InlineKeyboardButton(
#             text='Запостить',
#             callback_data=f"send_post,{message.chat.id},{m.message_id},anonym=False"
#         )
#         markup.add(send_post)
#         bot.send_media_group(message.chat.id,
#                              [InputMediaPhoto(media=item, caption=caption if index == 0 else None,
#                                               parse_mode='HTML')
#                               for index, item in enumerate(media_list)])
#         bot.send_message(message.chat.id, 'Так будет выглядеть ваше сообщение в канале:', reply_markup=markup)
#     user_photos.pop(message.chat.id)
#     p.get_content = False
#     p.save()


def publish_video_func(message, p):
    if p.get_content:
        remove_reply_markup = types.ReplyKeyboardRemove()
        videos = user_videos[message.chat.id]['videos']
        non_empty_caption = find_non_empty_caption(videos)
        if non_empty_caption is None:
            ask_for_caption = bot.send_message(message.chat.id, config.no_caption, reply_markup=remove_reply_markup)
            bot.register_next_step_handler(ask_for_caption,
                                           get_media_caption,
                                           profile=p,
                                           type='video',
                                           medias=user_videos[message.chat.id]['videos']),
            p.get_content = False
            p.save()
        else:
            manage_video_post(message, videos, non_empty_caption, p)


def manage_video_post(message, videos, non_empty_caption, p):
    bot_settings = BotSettings.objects.first()
    remove_reply_markup = types.ReplyKeyboardRemove()
    create_video_message_record(p, user_videos[message.chat.id]['videos'],
                                caption=non_empty_caption if non_empty_caption is not None else None)
    first_message_id = videos[0]
    first_msg_id = first_message_id['message_id']
    if bot_settings.anonym_func:
        bot.send_message(message.chat.id,
                         config.post_sent,
                         reply_markup=send_posts_markup(message, first_msg_id, type='video'),
                         disable_web_page_preview=True,
                         parse_mode='HTML')
        bot.send_message(message.chat.id, ':)', reply_markup=remove_reply_markup)
    else:
        m = UserMessage.objects.get(message_id=first_msg_id)
        media_list = str(m.file_ids)
        media_list = [item.strip() for item in media_list.split(",")]
        caption = f'{m.data}'
        markup = types.InlineKeyboardMarkup(row_width=1)
        send_post = types.InlineKeyboardButton(
            text='Запостить',
            callback_data=f"send_post,{message.chat.id},{m.message_id},anonym=False"
        )
        remove_reply_markup = types.ReplyKeyboardRemove()
        markup.add(send_post)
        bot.send_media_group(message.chat.id,
                             [InputMediaVideo(media=item, caption=caption if index == 0 else None,
                                              parse_mode='HTML')
                              for index, item in enumerate(media_list)])
        bot.send_message(message.chat.id, 'Так будет выглядеть ваше сообщение в канале:', reply_markup=markup)
    user_videos.pop(message.chat.id)
    p.get_content = False
    p.save()


def get_media_caption(message, **kwargs):
    media_caption = message.text
    medias = kwargs.get('medias', [])
    p = kwargs.get('profile', [])
    media_type = kwargs.get('type', [])
    if media_type == 'video':
        manage_video_post(message, medias, media_caption, p)
    elif media_type == 'photo':
        manage_photo_post(message, medias, media_caption, p)


def publish_text_func(message, p):
    bot_settings = BotSettings.objects.first()
    remove_reply_markup = types.ReplyKeyboardRemove()
    p.get_content = False
    p.save()
    if len(message.text) > 560:
        bot.send_message(message.chat.id, config.forbidden_types)
    else:
        UserMessage(
            user=p,
            data=message.text,
            message_id=message.id,
            type='text',
        ).save()
        m = UserMessage.objects.get(message_id=message.id)
        if bot_settings.anonym_func:
            visibility_buttons = bot.send_message(message.chat.id, 'Выберите формат поста',
                                                  reply_markup=send_posts_markup(message, message.id, type='text'))
            bot.send_message(message.chat.id, ':)', reply_markup=remove_reply_markup)
            last_user_message[message.chat.id] = visibility_buttons.message_id
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            send_post = types.InlineKeyboardButton(
                text='Запостить',
                callback_data=f"send_post,{message.chat.id},{m.message_id},anonym=False"
            )
            markup.add(send_post)
            bot.send_message(message.chat.id, f'Так будет выглядеть ваше сообщение в канале::\n\n{m.data}',
                             reply_markup=markup)


def find_non_empty_caption(photos):
    for photo_info in photos:
        if photo_info['caption']:
            if not len(photo_info['caption']) > 560:
                return photo_info['caption']
            else:
                return None
    return None


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
