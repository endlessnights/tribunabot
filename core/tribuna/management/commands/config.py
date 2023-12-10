ask_password = '''Введите пароль, чтобы начать пользоваться ботом. 
Пароль можно найти в <a href="https://vas3k.club/user/legeminus/">Профиле автора бота</a>
'''
password_is_wrong = 'Пароль введен неверно, нажмите /start , чтобы начать сначала.'

hello_new_user = '''
📨 Здесь вы можете написать в сервис коротких сообщений Вастрик.Клуба — <a href="https://t.me/+LHnmfbNIdM9kNmNi">Вастрик.Трибуна</a>

📝 Поднимите философский или наболевший вопрос, который не вписывается в полноценный пост в Клубе, выскажите мнение, задайте тему для обсуждения с потолка или о мимолетной новости.

🖐️ Для мемов, объявлений и справочных вопросов есть другие места в Вастрик.Клубе

👮 Посты и комментарии модерируются по правилам Клуба и нарушители будут забанены и для постинга или для комментирования постов.

🚫 Не делитесь ссылками на предложку и канал с людьми вне клуба.

💎 Старайтесь быть интересны и адекватны.

🖐 В настоящий момент не поддерживается совмещение видео и фото в одном посте.
'''

hello_registered_user = hello_new_user

start_text_new = hello_new_user

bot_help = '''
/start — перезапустить бота

/new — создать новый пост в канал Вастрик.Трибуна

/about — прочитать информацию о сервисе

/help — прочитать список команд и получить контакты для связи

По любым вопросам и предложениям пишите @zubak или @pycarrot2
'''

bot_help_admin = '''
/start — перезапустить бота

/new — создать новый пост в канал Вастрик.Трибуна

/about — прочитать информацию о сервисе

/help — прочитать список команд и получить контакты для связи

/admin — вызов списка команд для админов бота

По любым вопросам и предложениям пишите @zubak или @pycarrot2
'''


about_bot = '''
📨 Здесь вы можете написать в сервис коротких сообщений Вастрик.Клуба — Вастрик.Трибуна

📝 Поднимите философский или наболевший вопрос, который не вписывается в полноценный пост в Клубе, выскажите мнение, задайте тему для обсуждения с потолка или о мимолетной новости.

🖐️ Для мемов, объявлений и справочных вопросов есть другие места в Вастрик.Клубе

👮 Посты и комментарии модерируются по правилам Клуба и нарушители будут забанены и для постинга или для комментирования постов.

🚫 Не делитесь ссылками на предложку и канал с людьми вне клуба. 

💎 Старайтесь быть интересны и адекватны.

🖐 В настоящий момент не поддерживается совмещение видео и фото в одном посте.

©️ @zubak и @pycarrot2
'''


new_post_tooltip = '''
⬇️ Напишите ваше сообщение длиной не более 560 символов ниже.
✅ Поддерживается простой и форматированный текст, фото с описанием, видео с описанием, опросы.
❌ Не поддерживаются стикеры, GIF, музыка, аудиосообщения, кружочки, файлы.
🖐 В настоящий момент не поддерживается совмещение видео и фото в одном посте.

Если у вас не появляется внизу экрана "Запостить" для отправки записи на канал, после отправки материалов поста нажмите /publish
'''

forbidden_types = '''
😔К сожалению, мы не поддерживаем отправку фото или видео без описания, совмещение фото и видео в одном посте, стикеров, GIF, музыки, аудиосообщений, кружочков, файлов и текста длиной более 560 символов
✅Зато поддерживаются опросы, простой и форматированный текст, фото и видео с описанием.

⬇️Попробуй ещё раз /new
'''

public_text_post = '''
{}
©️<a href="https://t.me/{}">{}</a>
'''
anonym_text_post = '''
{}


'''

ttt = 'Запостить в <a href="https://t.me/instagram_directbot">Вастрик.Трибуну</a>'
moderation_list = 'Модерация постов'
send_to_moderate = 'Запостить'
post_sent = 'Сообщение отправлено в <a href="https://t.me/+LHnmfbNIdM9kNmNi">Вастрик.Трибуна</a>'
photo_limit = 'Максимальное количество фото для отправки за один раз - 10. Для повторной отправки нажмите /now'
video_limit = 'Максимальное количество видео для отправки за один раз - 10. Для повторной отправки нажмите /now'
warn_msg = '''
😔 Ваше сообщение не прошло постмодерацию в канале сервиса Вастрик.Трибуна. Возможно модераторы посчитали, что оно не соответствовало правилам и/или рекомендациям сервиса, Клуба или просто было неуместно по мнению модераторов.

👍 Постарайтесь размещать в Вастрик.Трибуне более качественный контент, который соответствует правилам. Модераторы сервиса оставляют за собой право выдать запрет на публикацию пользователям, которые часто нарушают правила.
'''
block_msg = '''
❌ Модераторы посчитали, что вы слишком часто игнорировали правила сервиса или ваше нарушение было вопиющим.

😔 К сожалению, вы временно не можете размещать посты в канале Вастрик.Трибуна.
'''

unblock_msg = '''
✅ Модераторы посчитали, что вам можно дать ещё один шанс для пользования сервисом Вастрик.Трибуна.

👍 Теперь вы можете размещать посты, но соблюдайте правила и рекомендации сервиса и Клуба.
'''

no_caption = 'Наличие описания к фото и видео обязательны. Максимум 560 символов. Напишите текст следующим сообщением:'

admin_wrong_cmd = '''
Извините, я не смог распознать юзернейм пользователя или его уникальный идентификатор,
пожалуйста, попробуйте ещё раз или перейдите к другой команде из главного меню
'''