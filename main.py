import telebot
from telebot import types
import os
import json
import random
import threading
import time
from telebot.types import ReplyKeyboardRemove

# Инициализация бота
try:
    with open("token.txt", "r") as file:
        API_TOKEN = file.read().strip()
except FileNotFoundError:
    print("Ошибка: файл token.txt не найден.")
    exit()

bot = telebot.TeleBot(API_TOKEN)

# Константы
ADMIN_ID = 11111111 #ид владельца
DIONCHIK_ID = 11111111   #ид друга
TESTER_IDS = {123456789, 987654321}  #ид тестировчиков
ADMINS_FILE = "admins.json"
PROMO_FILE = "promocodes.txt"
USERS_FILE = "users.txt"
ADMIN_PROMO = "CLIFFORD"  # это промо для адмики если че

# Инициализация данных
if os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, "r") as f:
        admins_data = json.load(f)
        SUB_ADMINS = set(admins_data.get("sub_admins", []))
else:
    SUB_ADMINS = set()

# Загрузка пользователей
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    users = {}
    with open(USERS_FILE, "r") as file:
        for line in file:
            parts = line.strip().split(" | ")
            if len(parts) >= 4:
                user_id = int(parts[0])
                users[user_id] = {
                    "age": int(parts[1]),
                    "phone": parts[2],
                    "language": parts[3],
                    "balance": int(parts[4]) if len(parts) > 4 else 0,
                    "active": True
                }
    return users

# Сохранение пользователей
def save_all_users():
    with open(USERS_FILE, "w") as file:
        for user_id, data in user_data.items():
            file.write(f"{user_id} | {data['age']} | {data['phone']} | {data['language']} | {data.get('balance', 0)}\n")

# Загрузка промокодов
def load_promocodes():
    if not os.path.exists(PROMO_FILE):
        return {}
    promos = {}
    with open(PROMO_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and "|" in line:
                code, reward = line.split("|", 1)
                promos[code.strip()] = reward.strip()
    return promos

# Сохранение промокодов
def save_promocodes(promos):
    with open(PROMO_FILE, "w") as f:
        for code, reward in promos.items():
            f.write(f"{code}|{reward}\n")

# Сохранение админов
def save_admins():
    with open(ADMINS_FILE, 'w') as f:
        json.dump({
            "admin": ADMIN_ID,
            "sub_admins": list(SUB_ADMINS)
        }, f)

# Проверка статуса пользователя
def get_user_status(user_id):
    if user_id == ADMIN_ID:
        return "👑 Владелец"
    elif user_id in SUB_ADMINS:
        return "🛡 Администратор"
    elif user_id in TESTER_IDS:
        return "🔧 Тестер"
    elif user_id == DIONCHIK_ID:
        return "OPIUM⛧"
    else:
        return "👤 Обычный"

# Проверка админа
def is_admin(user_id):
    return user_id == ADMIN_ID or user_id in SUB_ADMINS

# Инициализация данных
user_data = load_users()
pending_data = {}
waiting_users = {}
chat_pairs = {}
user_refs = {}
active_promos = {}

# Меню бота
def show_menu(chat_id):
    bot_description = "Добро пожаловать в чат-рулетку!\n\n📌 Используйте меню ниже для взаимодействия."
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("🔍 Поиск", callback_data="search"))
    markup.row(
        types.InlineKeyboardButton("⚙ Настройки", callback_data="settings"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )
    markup.row(
        types.InlineKeyboardButton("📢 Канал", url="https://t.me/wsorion"),
        types.InlineKeyboardButton("🤖 Создать бота", callback_data="create_bot")
    )
    markup.add(types.InlineKeyboardButton("💎 Купить подписку", url="http://t.me/send?start=IVyflPZeWlJi"))
    markup.add(types.InlineKeyboardButton("🤝 Пригласить", callback_data="invite"))
    markup.add(types.InlineKeyboardButton("🎁 Промокод", callback_data="promo_code"))
    
    bot.send_message(chat_id, bot_description, reply_markup=markup)

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # Обработка реферальной ссылки
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        if ref_code.startswith('ref'):
            referrer_id = int(ref_code[3:])
            if referrer_id in user_data and referrer_id != user_id:
                if user_id not in user_refs.get(referrer_id, []):
                    user_refs.setdefault(referrer_id, []).append(user_id)
                    user_data[referrer_id]['balance'] = user_data[referrer_id].get('balance', 0) + 20
                    save_all_users()
                    bot.send_message(referrer_id, f"🎉 Новый реферал! Ваш баланс: {user_data[referrer_id]['balance']} руб")
    
    if user_id not in user_data:
        bot.send_message(message.chat.id, "Введите ваш возраст:")
        pending_data[user_id] = {"state": "waiting_age"}
    else:
        show_menu(message.chat.id)

# Обработка возраста
@bot.message_handler(func=lambda message: message.from_user.id in pending_data and pending_data[message.from_user.id].get("state") == "waiting_age")
def ask_age(message):
    age = message.text.strip()
    if not age.isdigit() or int(age) < 10 or int(age) > 100:
        bot.send_message(message.chat.id, "Введите корректный возраст (10-100).")
        return

    user_id = message.from_user.id
    pending_data[user_id] = {"state": "waiting_phone", "age": int(age)}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Подтвердить аккаунт", request_contact=True))
    bot.send_message(message.chat.id, "Нажмите кнопку ниже, чтобы подтвердить ваш аккаунт:", reply_markup=markup)

# Обработка номера телефона
@bot.message_handler(content_types=['contact'])
def confirm_phone(message):
    if message.contact is not None:
        user_id = message.from_user.id
        if user_id in pending_data and pending_data[user_id].get("state") == "waiting_phone":
            phone = message.contact.phone_number
            age = pending_data[user_id]["age"]
            
            user_data[user_id] = {
                "age": age,
                "phone": phone,
                "language": "ru",
                "balance": 0,
                "active": True
            }
            save_all_users()
            del pending_data[user_id]
            
            bot.send_message(message.chat.id, "Аккаунт подтверждён!", reply_markup=ReplyKeyboardRemove())
            show_menu(message.chat.id)

# Поиск собеседника
@bot.callback_query_handler(func=lambda call: call.data == "search")
def search_handler(call):
    user_id = call.from_user.id
    
    if user_id in chat_pairs:
        bot.answer_callback_query(call.id, "Вы уже в чате! Используйте /stop чтобы выйти", show_alert=True)
        return
    
    if user_id in waiting_users:
        bot.answer_callback_query(call.id, "Вы уже в поиске! Ожидайте...", show_alert=True)
        return
    
    waiting_users[user_id] = True
    bot.edit_message_text("🔍 Ищем собеседника...", call.message.chat.id, call.message.message_id)
    
    # Поиск собеседника в отдельном потоке
    threading.Thread(target=find_companion, args=(user_id, call.message.chat.id, call.message.message_id)).start()

def find_companion(user_id, chat_id, message_id):
    time.sleep(1)  # Имитация поиска
    
    # Ищем другого пользователя в очереди
    for other_user in list(waiting_users.keys()):
        if other_user != user_id and other_user in user_data and user_data[other_user].get('active', True):
            # Нашли пару
            del waiting_users[user_id]
            del waiting_users[other_user]
            
            chat_pairs[user_id] = other_user
            chat_pairs[other_user] = user_id
            
            # Отправляем сообщения обоим пользователям
            bot.edit_message_text("✅ Собеседник найден! Напишите сообщение.\nИспользуйте /stop чтобы завершить диалог", 
                                chat_id, message_id)
            
            bot.send_message(other_user, "✅ Собеседник найден! Напишите сообщение.\nИспользуйте /stop чтобы завершить диалог")
            return
    
    # Если собеседник не найден
    if user_id in waiting_users:
        bot.edit_message_text("⏳ Ожидайте, ищем собеседника...", chat_id, message_id)
        time.sleep(10)
        if user_id in waiting_users:
            del waiting_users[user_id]
            bot.edit_message_text("😕 Не удалось найти собеседника. Попробуйте позже.", chat_id, message_id)

# Обработка сообщений между пользователями
@bot.message_handler(func=lambda message: message.from_user.id in chat_pairs and message.text != '/stop')
def chat_message(message):
    user_id = message.from_user.id
    companion_id = chat_pairs[user_id]
    


    # Отправляем сообщение собеседнику
    try:
        bot.send_message(companion_id, f"👤 Собеседник: {message.text}")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        bot.send_message(user_id, "❌ Не удалось отправить сообщение. Собеседник возможно покинул чат.")
        if user_id in chat_pairs:
            del chat_pairs[user_id]
        if companion_id in chat_pairs:
            del chat_pairs[companion_id]

# Команда для выхода из чата
@bot.message_handler(commands=['stop'])
def stop_chat(message):
    user_id = message.from_user.id
    
    if user_id in chat_pairs:
        companion_id = chat_pairs[user_id]
        
        # Уведомляем обоих пользователей
        bot.send_message(user_id, "❌ Вы вышли из чата", reply_markup=ReplyKeyboardRemove())
        bot.send_message(companion_id, "❌ Собеседник покинул чат", reply_markup=ReplyKeyboardRemove())
        
        # Удаляем пару
        del chat_pairs[user_id]
        del chat_pairs[companion_id]
        
        # Показываем меню
        show_menu(user_id)
        show_menu(companion_id)
    elif user_id in waiting_users:
        del waiting_users[user_id]
        bot.send_message(user_id, "❌ Поиск отменён", reply_markup=ReplyKeyboardRemove())
        show_menu(user_id)
    else:
        bot.send_message(user_id, "Вы не в чате и не в поиске")

# Добавим этот код в раздел с другими обработчиками команд

# Добавьте этот код в раздел с обработчиками команд (обычно в конце файла, но перед запуском бота)

@bot.message_handler(commands=['publ'])
def handle_publish(message):
    user_id = message.from_user.id
    
    # Проверяем статус пользователя
    status = get_user_status(user_id)
    if status not in ["👑 Владелец", "🛡 Администратор"]:
        bot.reply_to(message, "❌ Эта команда доступна только администраторам!")
        return
    
    # Запрашиваем текст для рассылки
    msg = bot.reply_to(message, "📢 Введите текст для рассылки всем пользователям:")
    bot.register_next_step_handler(msg, process_publish_text)

def process_publish_text(message):
    user_id = message.from_user.id
    text_to_publish = message.text
    
    # Создаем клавиатуру подтверждения
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Да, отправить", callback_data="publish_yes"),
        types.InlineKeyboardButton("❌ Нет, отменить", callback_data="publish_no")
    )
    
    # Сохраняем текст для рассылки
    pending_data[user_id] = {
        "action": "confirm_publish",
        "publish_text": text_to_publish
    }
    
    bot.send_message(
        user_id,
        f"📢 Вы уверены, что хотите разослать это сообщение всем пользователям?\n\n{text_to_publish}",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('publish_'))
def handle_publish_decision(call):
    user_id = call.from_user.id
    action = call.data.split('_')[1]
    
    if action == "yes" and user_id in pending_data and "publish_text" in pending_data[user_id]:
        text_to_publish = pending_data[user_id]["publish_text"]
        del pending_data[user_id]
        
        bot.edit_message_text("⏳ Начинаю рассылку...", call.message.chat.id, call.message.message_id)
        
        success = 0
        failed = 0
        total_users = len(user_data)
        
        for uid in user_data:
            try:
                if uid != user_id:  # Не отправляем себе
                    bot.send_message(uid, f"📢 Сообщение от администрации:\n\n{text_to_publish}")
                    success += 1
            except:
                failed += 1
        
        bot.edit_message_text(
            f"✅ Рассылка завершена!\n\n"
            f"Всего пользователей: {total_users}\n"
            f"Успешно: {success}\n"
            f"Не удалось: {failed}",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        if user_id in pending_data:
            del pending_data[user_id]
        bot.edit_message_text("❌ Рассылка отменена", call.message.chat.id, call.message.message_id)





#🟥мембер
@bot.message_handler(commands=['member'])
def handle_member_command(message):
    user_id = message.from_user.id
    
    # Проверка прав доступа (только владелец и Dimonchik)
    if user_id not in {ADMIN_ID, DIONCHIK_ID}:
        bot.reply_to(message, "🚫 Команда только для владельца и Dimonchik!")
        return
    
    # Загрузка пользователей
    users = load_users()
    
    if not users:
        bot.reply_to(message, "📭 В боте пока нет зарегистрированных пользователей")
        return
    
    # Формируем заголовок
    result = "📋 <b>Список пользователей:</b>\n\n"
    
    # Обрабатываем каждого пользователя
    for uid, user_data in users.items():
        try:
            # Получаем информацию о пользователе
            chat = bot.get_chat(uid)
            username = f"@{chat.username}" if chat.username else "—"
            phone = user_data.get('phone', 'не указан')
            
            # Форматируем строку (простой формат)
            result += f"👤 <b>Юзер:</b> {username}\n"
            result += f"🆔 <b>ID:</b> <code>{uid}</code>\n"
            result += f"📞 <b>Телефон:</b> <code>{phone}</code>\n"
            result += "───────────────\n"
            
        except Exception as e:
            # Если не удалось получить информацию
            result += f"❌ Ошибка при получении данных пользователя {uid}\n"
            result += "───────────────\n"
    
    # Добавляем итог
    result += f"\n👥 <b>Всего пользователей:</b> {len(users)}"
    
    # Отправляем частями (если слишком длинное сообщение)
    for i in range(0, len(result), 4000):
        bot.send_message(message.chat.id, result[i:i+4000], parse_mode='HTML')















#ПИСАТЬ ЛИЧНО
@bot.message_handler(commands=['send'])
def handle_send_command(message):
    user_id = message.from_user.id
    
    # Проверяем права пользователя
    if not (user_id == ADMIN_ID or  # Владелец
            user_id == DIONCHIK_ID): 
        bot.reply_to(message, "❌ Эта команда доступна только администраторам!")
        return
    
    # Запрашиваем ID пользователя и сообщение
    msg = bot.reply_to(message, 
                      "✉️ <b>Отправить личное сообщение</b>\n\n"
                      "Введите ID пользователя и сообщение в формате:\n"
                      "<code>ID_пользователя Текст сообщения</code>\n\n"
                      "Пример:\n"
                      "<code>8133981519 Привет! Это тестовое сообщение</code>",
                      parse_mode="HTML")
    bot.register_next_step_handler(msg, process_send_command)

def process_send_command(message):
    try:
        # Разбиваем сообщение на ID и текст
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise ValueError("Неверный формат")
        
        target_id = int(parts[0])
        text = parts[1]
        
        # Проверяем, не пытаются ли отправить сообщение самому себе
        if message.from_user.id == target_id:
            bot.reply_to(message, "❌ Нельзя отправить сообщение самому себе!")
            return
        
        # Пытаемся отправить сообщение
        try:
            # Отправляем сообщение целевому пользователю
            bot.send_message(target_id, f"📨 <b>Личное сообщение от администрации</b>\n\n{text}", parse_mode="HTML")
            
            # Отправляем подтверждение отправителю
            bot.reply_to(message, 
                        f"✅ Сообщение успешно отправлено пользователю {target_id}\n"
                        f"└ Текст: {text}")
            
            # Логируем действие
            sender_status = get_user_status(message.from_user.id)
            print(f"[SEND] {sender_status} {message.from_user.id} отправил сообщение пользователю {target_id}")
            
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось отправить сообщение пользователю {target_id}\nОшибка: {str(e)}")
            
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат. Введите ID (число) и сообщение через пробел")
    except Exception as e:
        bot.reply_to(message, f"❌ Произошла ошибка: {str(e)}")








# Промокоды
@bot.callback_query_handler(func=lambda call: call.data == "promo_code")
def promo_code_menu(call):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🎫 Ввести промокод", callback_data="enter_promo"),
        types.InlineKeyboardButton("❌ Нет промокода", callback_data="no_promo")
    )
    
    if is_admin(call.from_user.id):
        markup.add(types.InlineKeyboardButton("🛠 Создать промокод", callback_data="create_promo"))
    
    bot.edit_message_text(
        "🔹 Выберите действие с промокодом:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# Создание промокода
# Создание промокода (для админов)
@bot.callback_query_handler(func=lambda call: call.data == "create_promo")
def create_promo_handler(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Только для администраторов!", show_alert=True)
        return
    
    instructions = (
        "📝 <b>Создание промокода</b>\n\n"
        "Используйте команду:\n"
        "<code>/newpromo КОД|НАГРАДА</code>\n\n"
        "Примеры:\n"
        "• <code>/newpromo BONUS100|100 рублей</code>\n"
        "• <code>/newpromo VIP|Премиум на 1 день</code>"
    )
    
    bot.edit_message_text(
        instructions,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )

# Команда для создания промокодов
@bot.message_handler(commands=['newpromo'])
def handle_new_promo(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        _, promo_data = message.text.split(maxsplit=1)
        code, reward = promo_data.split("|")
        
        promos = load_promocodes()
        promos[code.upper()] = reward
        save_promocodes(promos)
        
        bot.reply_to(message, f"✅ Промокод {code.upper()} создан!\nНаграда: {reward}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}\nИспользуйте формат: /newpromo КОД|НАГРАДА")



# Настройки
@bot.callback_query_handler(func=lambda call: call.data == "settings")
def settings_menu(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("❓ FAQ", callback_data="faq"),
        types.InlineKeyboardButton("🔍 Поиск", callback_data="search_settings"),
        types.InlineKeyboardButton("🎂 Изменить возраст", callback_data="change_age"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    )
    bot.edit_message_text(
        "⚙ <b>Настройки</b>\n\nВыберите опцию:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

# FAQ
@bot.callback_query_handler(func=lambda call: call.data == "faq")
def show_faq(call):
    faq_text = (
        "❓ <b>FAQ</b>\n\n"
        "1. <b>Как пользоваться ботом?</b>\n"
        "Нажмите кнопку 'Поиск' для поиска собеседника\n\n"
        "2. <b>Как получить статус админа?</b>\n"
        "Нужно активировать специальный промокод\n\n"
        "3. <b>Как приглашать друзей?</b>\n"
        "Используйте кнопку 'Пригласить' в меню"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="settings"))
    
    bot.edit_message_text(
        faq_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

# Изменение возраста
@bot.callback_query_handler(func=lambda call: call.data == "change_age")
def change_age_prompt(call):
    bot.edit_message_text(
        "Введите новый возраст:",
        call.message.chat.id,
        call.message.message_id
    )
    pending_data[call.from_user.id] = {"action": "change_age"}

@bot.message_handler(func=lambda message: message.from_user.id in pending_data and pending_data[message.from_user.id].get("action") == "change_age")
def update_age(message):
    age = message.text.strip()
    if not age.isdigit() or int(age) < 8 or int(age) > 50:
        bot.send_message(message.chat.id, "Введите корректный возраст.")
        return

    user_id = message.from_user.id
    user_data[user_id]["age"] = int(age)
    save_all_users()
    del pending_data[user_id]
    bot.send_message(message.chat.id, "✅ Возраст успешно изменён!")
    show_menu(message.chat.id)

# Поиск в настройках
@bot.callback_query_handler(func=lambda call: call.data == "search_settings")
def search_settings_handler(call):
    bot.answer_callback_query(call.id, "🔍 Эта функция появится в следующем обновлении!", show_alert=True)

# Создать бота
@bot.callback_query_handler(func=lambda call: call.data == "create_bot")
def create_bot_handler(call):
    bot.answer_callback_query(call.id, "🚧 Функция создания ботов скоро будет доступна!", show_alert=True)



# Ввод промокода
@bot.callback_query_handler(func=lambda call: call.data == "enter_promo")
def enter_promo_handler(call):
    bot.edit_message_text(
        "Введите промокод:",
        call.message.chat.id,
        call.message.message_id
    )
    pending_data[call.from_user.id] = {"action": "enter_promo"}

# Обработка введенного промокода
@bot.message_handler(func=lambda message: message.from_user.id in pending_data and pending_data[message.from_user.id].get("action") == "enter_promo")
def process_promo(message):
    user_id = message.from_user.id
    promo_code = message.text.upper().strip()
    promos = load_promocodes()
    
    if promo_code in promos:
        reward = promos[promo_code]
        
        # Особый промокод для админа
        if promo_code == ADMIN_PROMO and not is_admin(user_id):
            SUB_ADMINS.add(user_id)
            save_admins()
            reward = "статус администратора"
        
        # Начисляем награду
        if "рубл" in reward.lower():
            try:
                amount = int(''.join(filter(str.isdigit, reward)))
                user_data[user_id]['balance'] = user_data[user_id].get('balance', 0) + amount
                save_all_users()
            except:
                pass
        
        bot.send_message(message.chat.id, f"✅ Промокод активирован!\nВаша награда: {reward}")
        
        # Удаляем использованный промокод
        if promo_code != ADMIN_PROMO:
            del promos[promo_code]
            save_promocodes(promos)
    else:
        bot.send_message(message.chat.id, "❌ Неверный промокод или срок действия истёк")
    
    del pending_data[user_id]
    show_menu(message.chat.id)

# Нет промокода
@bot.callback_query_handler(func=lambda call: call.data == "no_promo")
def no_promo_handler(call):
    instructions = (
        "📌 <b>Как получить промокод?</b>\n\n"
        "1. Подпишитесь на наш канал: @wsorion\n"
        "2. Участвуйте в конкурсах и акциях\n"
        "3. Приглашайте друзей и получайте бонусы\n"
        "4. Следите за новостями в боте\n\n"
        "🔹 Промокоды дают бонусы: деньги, статусы и другие привилегии!"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="promo_code"))
    
    bot.edit_message_text(
        instructions,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )



#команды админов
@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    user_id = message.from_user.id
    
    # Проверяем права пользователя
    if not (user_id == ADMIN_ID or user_id == DIONCHIK_ID or user_id in SUB_ADMINS):
        bot.reply_to(message, "❌ Эта команда доступна только администраторам!")
        return
    
    # Формируем список команд
    admin_commands = """
<b>👑 Административные команды:</b>

/publ - Сделать рассылку всем пользователям
/send - Отправить личное сообщение пользователю
/newpromo - Создать новый промокод
/member - Все пользователи
"""
    
    # Отправляем сообщение с командами
    bot.reply_to(message, admin_commands, parse_mode='HTML')











# Реферальная система
@bot.callback_query_handler(func=lambda call: call.data == "invite")
def invite_handler(call):
    user_id = call.from_user.id
    ref_link = f"https://t.me/{bot.get_me().username}?start=ref{user_id}"
    
    instructions = (
        f"🤝 <b>Приглашайте друзей и получайте бонусы!</b>\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        f"💎 За каждого приглашённого друга вы получаете <b>20 рублей</b>\n"
        f"👥 Приглашено друзей: <b>{len(user_refs.get(user_id, []))}</b>\n"
        f"💰 Всего заработано: <b>{len(user_refs.get(user_id, [])) * 20} рублей</b>"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        instructions,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

# Профиль пользователя
@bot.callback_query_handler(func=lambda call: call.data == "profile")
def show_profile(call):
    user_id = call.from_user.id
    if user_id in user_data:
        total_users = len(user_data)
        status = get_user_status(user_id)
        
        profile_text = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"🆔 ID: <code>{user_id}</code> \n"
            f"📞 Телефон: {user_data[user_id]['phone']}\n"
            f"🎂 Возраст: {user_data[user_id]['age']}\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"💎 Баланс: {user_data[user_id].get('balance', 0)} руб\n"
            f"🔰 Статус: {status}\n\n"
            f"📊 Рефералов: {len(user_refs.get(user_id, []))}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
        
        bot.edit_message_text(
            profile_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "Профиль не найден")

# Назад в меню
@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    show_menu(call.message.chat.id)

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling()
