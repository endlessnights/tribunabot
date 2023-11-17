import json
import os
import re
import time
import requests
from django.core.management import BaseCommand
from django.utils import timezone
from telebot import TeleBot, types
from requests.exceptions import Timeout
from telebot.types import CallbackQuery, InputMediaPhoto, InputMediaVideo

from . import config
from ...models import Accounts, UserMessage, BotSettings

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
        print(f"An error occurred: {e}")

    p = Accounts.objects.get(tgid=message.chat.id)
    if not p.has_access:
        #   Делаем запрос в vas3k.club, получаем данные учетки из клуба, если бот привязан
        club_profile_info = get_club_profile(message.chat.id)
        if club_profile_info is not None:
            p = Accounts.objects.get(tgid=message.chat.id)
            p.has_access = True
            club_profile_slug, club_full_name = club_profile_info
            bot.send_message(message.chat.id, config.hello_new_user, parse_mode='HTML')
        #   Если бот не привязан, то запрашиваем пароль (указан в профиле клуба)
        #   Или если сайт vas3k клуба возвращает не 200
        else:
            try:
                p = Accounts.objects.get(tgid=message.chat.id)
                if p.has_access:
                    bot.send_message(message.chat.id, config.hello_new_user, parse_mode='HTML')
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
        bot.send_message(message.chat.id, config.hello_registered_user, reply_markup=show_keyboard_buttons(message),
                         parse_mode='HTML')


def send_posts_markup(message, first_msg_id):
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


@bot.message_handler(commands=['new'])
def new_post(message):
    p = Accounts.objects.get(tgid=message.chat.id)
    send_to_moderate = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    send_to_moderate_btn = types.KeyboardButton(text=config.send_to_moderate)
    send_to_moderate.add(send_to_moderate_btn)
    try:
        p = Accounts.objects.get(tgid=message.chat.id)
        if p.has_access:
            new_post_tooltip = bot.send_message(message.chat.id, config.new_post_tooltip, reply_markup=send_to_moderate)
            p.get_content = True
            p.save()
    except Exception as e:
        bot.send_message(message.chat.id, 'У вас нет доступа к этому боту. Нажмите /start для начала работы с ботом')
        print(e)


@bot.message_handler(content_types=['photo'])
def photo_message(message):
    try:
        p = Accounts.objects.get(tgid=message.chat.id)
        if p.has_access and p.get_content:
            caption = message.caption if message.caption else ""
            # Check if the user_photos dictionary has an entry for the user
            if message.chat.id not in user_photos:
                user_photos[message.chat.id] = {'count': 0, 'photos': []}
            # Increment the count of photos sent by the user
            user_photos[message.chat.id]['count'] += 1
            # Store the message_id and file_id of the photo
            user_photos[message.chat.id]['photos'].append({
                'message_id': message.message_id,
                'file_id': message.photo[-1].file_id,
                'caption': caption
            })
            # If the user has sent 10 photos, disable further photo zsending
            if user_photos[message.chat.id]['count'] > 10:
                p.get_content = False
                p.save()
                bot.send_message(message.chat.id,
                                 config.photo_limit)
                # Create a UserMessage record with the available photos
                create_photo_message_record(p, user_photos[message.chat.id]['photos'], caption)
                user_photos.pop(message.chat.id)
    except Exception as e:
        print(f'photo_message: {e}')


# create_user_message_record
def create_photo_message_record(p, photos, caption):
    first_photo_info = photos[0]
    UserMessage(
        user=p,
        message_id=first_photo_info['message_id'],
        file_ids=','.join(photo['file_id'] for photo in photos),
        type='photo',
        data=(caption if caption else '')
    ).save()


@bot.message_handler(content_types=['video'])
def video_message(message):
    try:
        p = Accounts.objects.get(tgid=message.chat.id)
        if p.has_access and p.get_content:
            caption = message.caption if message.caption else ""
            # Check if the user_photos dictionary has an entry for the user
            if message.chat.id not in user_videos:
                user_videos[message.chat.id] = {'count': 0, 'videos': []}
            # Increment the count of photos sent by the user
            user_videos[message.chat.id]['count'] += 1
            # Store the message_id and file_id of the photo
            user_videos[message.chat.id]['videos'].append({
                'message_id': message.message_id,
                'file_id': message.video.file_id,
                'caption': caption
            })
            # If the user has sent 10 photos, disable further photo sending
            if user_videos[message.chat.id]['count'] > 10:
                p.get_content = False
                p.save()
                bot.send_message(message.chat.id,
                                 config.video_limit)
                # Create a UserMessage record with the available photos
                create_video_message_record(p, user_videos[message.chat.id]['videos'], caption)
                user_videos.pop(message.chat.id)
    except Exception as e:
        print(f'video_message: {e}')


# create_user_message_record
def create_video_message_record(p, videos, caption):
    first_video_info = videos[0]
    UserMessage(
        user=p,
        message_id=first_video_info['message_id'],
        file_ids=','.join(video['file_id'] for video in videos),
        type='video',
        data=(caption if caption else '')
    ).save()


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if str(call.data).startswith('send_post'):
        callback_data = call.data.split(',')
        post_author = int(callback_data[1])
        message_id = int(callback_data[2])
        anonym = callback_data[3].split('=')[1]
        m = UserMessage.objects.get(message_id=message_id)
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
                callback_data=f"post_accept_action,{m.message_id},{anonym},accept=True"
            )
            cancel_post = types.InlineKeyboardButton(
                text='❌',
                callback_data=f"post_accept_action,{m.message_id},{anonym},accept=False"
            )
            warn_delete_post = types.InlineKeyboardButton(
                text='Удалить и предупредить',
                callback_data=f"post_accept_action,{m.message_id},{anonym},accept=Warn"
            )
            block_user = types.InlineKeyboardButton(
                text='Заблокировать юзера',
                callback_data=f"post_accept_action,{m.message_id},{anonym},accept=Block"
            )
            markup.add(accept_post, cancel_post, warn_delete_post, block_user)
        if m.type == 'text':
            for admin in bot_admins:
                if bot_settings.pre_moder:
                    bot.send_message(admin.tgid,
                                     f'©️{m.user.clubname} <a href="https://vas3k.club/user/{m.user.clublogin}">{m.user.clublogin}</a> — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     reply_markup=markup,
                                     parse_mode='HTML')
                else:
                    bot.send_message(admin.tgid,
                                     f'©️{m.user.clubname} <a href="https://vas3k.club/user/{m.user.clublogin}">{m.user.clublogin}</a> — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     parse_mode='HTML')
        elif m.type == 'photo' or 'video':
            media_list = str(m.file_ids)
            media_list = [item.strip() for item in media_list.split(",")]
            caption = f'{m.data}'
            for admin in bot_admins:
                bot.send_media_group(admin.tgid,
                                     [InputMediaVideo(media=item, caption=caption if index == 0 else None) for
                                      index, item in
                                      enumerate(media_list)] if m.type == 'video' else [
                                         InputMediaPhoto(media=item, caption=caption if index == 0 else None,
                                                         parse_mode='HTML') for index, item in enumerate(media_list)])
                if bot_settings.pre_moder:
                    bot.send_message(admin.tgid,
                                     f'©️{m.user.clubname} <a href="https://vas3k.club/user/{m.user.clublogin}">{m.user.clublogin}</a> — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     reply_markup=markup,
                                     parse_mode='HTML',
                                     disable_web_page_preview=True)
                else:
                    bot.send_message(admin.tgid,
                                     f'©️{m.user.clubname} <a href="https://vas3k.club/user/{m.user.clublogin}">{m.user.clublogin}</a> — {m.user.tgid}\nТекст: {m.data}\nАнонимно: {"Да" if m.anonym else "Нет"}',
                                     parse_mode='HTML',
                                     disable_web_page_preview=True)
        bot.send_message(call.message.chat.id, config.post_sent, parse_mode='HTML')
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.answer_callback_query(call.id)
    if str(call.data).startswith('post_accept_action'):
        callback_data = call.data.split(',')
        message_id = int(callback_data[1])
        anonym = str(callback_data[2])
        action = callback_data[3].split('=')[1]
        m = UserMessage.objects.get(message_id=message_id)
        if action == 'True':
            if m.type == 'text':
                post_text = (
                    config.anonym_text_post.format(m.data) if anonym == 'True' else config.public_text_post.format(
                        m.data, m.user.clubname, m.user.clublogin, m.user.clublogin, ))
                bot.send_message(test_channel_id, post_text, parse_mode='HTML')
            elif m.type == 'photo' or 'video':
                media_list = str(m.file_ids)
                media_list = [item.strip() for item in media_list.split(",")]
                caption = (
                    config.anonym_text_post.format(m.data) if anonym == 'True' else config.public_text_post.format(
                        m.data, m.user.clubname, m.user.clublogin, m.user.clublogin))
                bot.send_media_group(test_channel_id, [
                    InputMediaPhoto(media=item, caption=caption if index == 0 else None, parse_mode='HTML') for
                    index, item in
                    enumerate(media_list)] if m.type == 'photo' else [
                    InputMediaVideo(media=item, caption=caption if index == 0 else None, parse_mode='HTML') for
                    index, item in enumerate(media_list)])
            user_succ_reply = bot.send_message(m.user.tgid, config.post_sent, parse_mode='HTML')
            m.sent = True
            m.status = 'accept'
            m.save()
        elif action == 'False':
            user_succ_reply = bot.send_message(m.user.tgid, 'Сообщение не прошло модерацию!')
            m.status = 'failed'
            m.sent = False
            m.save()
        elif action == 'Block':
            print(m.user.tgname, 'ToBlock')
            user_succ_reply = bot.send_message(m.user.tgid, 'Сообщение не прошло модерацию!')
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.answer_callback_query(call.id)


# Define a dictionary to store user photo information
user_photos = {}
user_videos = {}


@bot.message_handler(content_types=['document', 'audio', 'sticker', 'voice', 'video_note', 'contact', 'location'])
def forbidden_content(message):
    bot.send_message(message.chat.id, config.forbidden_types)
    p = Accounts.objects.get(tgid=message.chat.id)
    p.get_content = False
    p.save()


@bot.message_handler(content_types=['text'])
def text_message(message):
    #   Показываем посты на ПреМодерации админам бота
    p = Accounts.objects.get(tgid=message.chat.id)
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
                                         f'©️{post.user.clubname} <a href="https://vas3k.club/user/{post.user.clublogin}">{post.user.clublogin}</a> — {post.user.tgid}\nТекст: {post.data}\nАнонимно: {"Да" if post.anonym else "Нет"}',
                                         reply_markup=markup,
                                         parse_mode='HTML',
                                         disable_web_page_preview=True)
    remove_reply_markup = types.ReplyKeyboardRemove()
    #   Если нажата кнопка "Запостить"
    if message.text == config.send_to_moderate:
        if p.get_content:
            #   Если отправляется фото, стопка фото
            if message.chat.id in user_photos:
                photos = user_photos[message.chat.id]['photos']
                non_empty_caption = find_non_empty_caption(photos)
                if non_empty_caption == None:
                    bot.send_message(message.chat.id, config.forbidden_types)
                    p.get_content = False
                    p.save()
                else:
                    create_photo_message_record(p, user_photos[message.chat.id]['photos'],
                                                caption=non_empty_caption if non_empty_caption != None else None)
                    first_message_id = photos[0]
                    first_msg_id = first_message_id['message_id']
                    if bot_settings.anonym_func:
                        bot.send_message(message.chat.id,
                                         config.post_sent,
                                         reply_markup=send_posts_markup(message, first_msg_id),
                                         parse_mode='HTML',
                                         disable_web_page_preview=True)
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
                        markup.add(send_post)
                        bot.send_media_group(message.chat.id,
                                             [InputMediaPhoto(media=item, caption=caption if index == 0 else None,
                                                              parse_mode='HTML')
                                              for index, item in enumerate(media_list)])
                        bot.send_message(message.chat.id, 'Это превью поста', reply_markup=markup)
                    user_photos.pop(message.chat.id)
                    p.get_content = False
                    p.save()
            #   Если отправляется видео, стопка видео
            elif message.chat.id in user_videos:
                videos = user_videos[message.chat.id]['videos']
                non_empty_caption = find_non_empty_caption(videos)
                if non_empty_caption == None:
                    bot.send_message(message.chat.id, config.forbidden_types)
                    p.get_content = False
                    p.save()
                else:
                    create_video_message_record(p, user_videos[message.chat.id]['videos'],
                                                caption=non_empty_caption if non_empty_caption != None else None)
                    first_message_id = videos[0]
                    first_msg_id = first_message_id['message_id']
                    bot.send_message(message.chat.id,
                                     config.post_sent,
                                     reply_markup=send_posts_markup(message, first_msg_id))
                    bot.send_message(message.chat.id, ':)', reply_markup=remove_reply_markup)
                    user_videos.pop(message.chat.id)
                    p.get_content = False
                    p.save()
        else:
            print('Photo sending is already disabled.')
    if message.text != config.send_to_moderate and p.get_content:
        p.get_content = False
        p.save()
        UserMessage(
            user=p,
            data=message.text,
            message_id=message.id,
            type='text',
        ).save()
        m = UserMessage.objects.get(message_id=message.id)
        visibility_buttons = bot.send_message(message.chat.id, 'Выберите формат поста',
                                              reply_markup=send_posts_markup(message, message.id))
        bot.send_message(message.chat.id, ':)', reply_markup=remove_reply_markup)
        last_user_message[message.chat.id] = visibility_buttons.message_id


def find_non_empty_caption(photos):
    for photo_info in photos:
        if photo_info['caption']:
            return photo_info['caption']
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
