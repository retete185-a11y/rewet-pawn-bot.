import os
import re
import tempfile
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8999035301"))

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# =========================================================
# СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЯ
# =========================================================

STATE_NONE = "none"
STATE_WAIT_PWN = "wait_pwn"
STATE_WAIT_SYSTEM = "wait_system"
STATE_WAIT_SYSTEM_NAME = "wait_system_name"
STATE_WAIT_ERROR_PWN = "wait_error_pwn"
STATE_WAIT_ERROR_TEXT = "wait_error_text"
STATE_SUPPORT = "support"

user_state = {}
user_data = {}


# =========================================================
# МЕНЮ
# =========================================================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🔧 Залить систему в мод",
                callback_data="upload_system"
            )
        ],
        [
            InlineKeyboardButton(
                "📝 Написать систему",
                callback_data="write_system"
            )
        ],
        [
            InlineKeyboardButton(
                "🛠 Помощь с ошибками",
                callback_data="fix_error"
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Поддержка",
                callback_data="support"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def cancel_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="cancel"
            )
        ]
    ])


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    user_state[user.id] = STATE_NONE
    user_data.pop(user.id, None)

    text = (
        "👋 <b>REWET HOST</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 Добро пожаловать!\n\n"
        "Здесь вы можете:\n\n"
        "🔧 Добавить систему в PAWN-мод\n"
        "📝 Получить PAWN-систему\n"
        "🛠 Исправить ошибку компиляции\n"
        "💬 Получить помощь администратора\n\n"
        "Выберите нужный раздел:"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# =========================================================
# КНОПКИ
# =========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user
    uid = user.id

    # -----------------------------------------------------
    # ОТМЕНА
    # -----------------------------------------------------

    if query.data == "cancel":

        user_state[uid] = STATE_NONE
        user_data.pop(uid, None)

        await query.message.reply_text(
            "❌ Действие отменено.",
            reply_markup=main_menu()
        )

        return

    # -----------------------------------------------------
    # ЗАЛИТЬ СИСТЕМУ
    # -----------------------------------------------------

    if query.data == "upload_system":

        user_state[uid] = STATE_WAIT_PWN

        user_data[uid] = {
            "pwn_file": None,
            "system": None,
        }

        await query.message.reply_text(
            "🔧 <b>ЗАЛИТЬ СИСТЕМУ В МОД</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📁 Отправьте мне ваш PAWN-мод "
            "с расширением <code>.pwn</code>.\n\n"
            "После получения файла я попрошу "
            "отправить систему.",
            parse_mode="HTML",
            reply_markup=cancel_menu()
        )

        return

    # -----------------------------------------------------
    # НАПИСАТЬ СИСТЕМУ
    # -----------------------------------------------------

    if query.data == "write_system":

        user_state[uid] = STATE_WAIT_SYSTEM_NAME

        await query.message.reply_text(
            "📝 <b>НАПИСАТЬ СИСТЕМУ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Скажите, какую систему написать.\n\n"
            "Например:\n"
            "<code>/car</code>\n"
            "<code>/house</code>\n"
            "<code>/garage</code>\n\n"
            "Напишите название или команду системы.",
            parse_mode="HTML",
            reply_markup=cancel_menu()
        )

        return

    # -----------------------------------------------------
    # ПОМОЩЬ С ОШИБКАМИ
    # -----------------------------------------------------

    if query.data == "fix_error":

        user_state[uid] = STATE_WAIT_ERROR_PWN

        user_data[uid] = {
            "pwn_file": None,
            "error": None,
        }

        await query.message.reply_text(
            "🛠 <b>ПОМОЩЬ С ОШИБКОЙ КОМПИЛЯЦИИ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📁 Отправьте мне ваш PAWN-мод "
            "с расширением <code>.pwn</code>.\n\n"
            "После этого напишите ошибку.\n\n"
            "Например:\n"
            "<code>Ошибка на 500 строке: "
            "undefined symbol \"PlayerInfo\"</code>\n\n"
            "Я проанализирую мод и подготовлю исправленную версию.",
            parse_mode="HTML",
            reply_markup=cancel_menu()
        )

        return

    # -----------------------------------------------------
    # ПОДДЕРЖКА
    # -----------------------------------------------------

    if query.data == "support":

        user_state[uid] = STATE_SUPPORT

        await query.message.reply_text(
            "💬 <b>ПОДДЕРЖКА</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⬆ По всем вопросам пишите сюда прямо в боте "
            "командой <code>/support</code> и что случилось "
            "и владелец с вами скоро свяжутся.\n\n"
            "Или просто напишите сообщение ниже.",
            parse_mode="HTML",
            reply_markup=cancel_menu()
        )

        return


# =========================================================
# ПОЛУЧЕНИЕ ФАЙЛА
# =========================================================

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    uid = user.id

    state = user_state.get(uid, STATE_NONE)
    document = update.message.document

    filename = document.file_name or ""

    if not filename.lower().endswith(".pwn"):

        await update.message.reply_text(
            "❌ Нужен файл именно с расширением <code>.pwn</code>.",
            parse_mode="HTML"
        )

        return

    # -----------------------------------------------------
    # ЗАЛИВКА СИСТЕМЫ
    # -----------------------------------------------------

    if state == STATE_WAIT_PWN:

        try:

            telegram_file = await document.get_file()

            path = UPLOAD_DIR / f"{uid}_{filename}"

            await telegram_file.download_to_drive(str(path))

            user_data[uid]["pwn_file"] = str(path)

            user_state[uid] = STATE_WAIT_SYSTEM

            await update.message.reply_text(
                "✅ <b>Мод получен!</b>\n\n"
                "Теперь отправьте систему, которую "
                "нужно добавить в мод.\n\n"
                "Можно отправить код обычным сообщением.",
                parse_mode="HTML",
                reply_markup=cancel_menu()
            )

        except Exception as e:

            print("PWN DOWNLOAD ERROR:", e)

            await update.message.reply_text(
                "❌ Не удалось скачать файл. "
                "Попробуйте отправить его ещё раз."
            )

        return

    # -----------------------------------------------------
    # ИСПРАВЛЕНИЕ ОШИБКИ
    # -----------------------------------------------------

    if state == STATE_WAIT_ERROR_PWN:

        try:

            telegram_file = await document.get_file()

            path = UPLOAD_DIR / f"error_{uid}_{filename}"

            await telegram_file.download_to_drive(str(path))

            user_data[uid]["pwn_file"] = str(path)

            user_state[uid] = STATE_WAIT_ERROR_TEXT

            await update.message.reply_text(
                "✅ <b>Мод получен!</b>\n\n"
                "Теперь отправьте текст ошибки компилятора.\n\n"
                "Например:\n"
                "<code>error 017: undefined symbol "
                "\"PlayerInfo\"</code>\n\n"
                "Если знаете строку — обязательно укажите её.",
                parse_mode="HTML",
                reply_markup=cancel_menu()
            )

        except Exception as e:

            print("ERROR MOD DOWNLOAD:", e)

            await update.message.reply_text(
                "❌ Не удалось получить мод."
            )

        return

    await update.message.reply_text(
        "❗ Сейчас бот не ожидает PAWN-файл.",
        reply_markup=main_menu()
    )


# =========================================================
# ТЕКСТ
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    uid = user.id
    text = update.message.text.strip()

    state = user_state.get(uid, STATE_NONE)

    # -----------------------------------------------------
    # СИСТЕМА ДЛЯ МОДА
    # -----------------------------------------------------

    if state == STATE_WAIT_SYSTEM:

        user_data[uid]["system"] = text

        await update.message.reply_text(
            "⏳ <b>Система получена.</b>\n\n"
            "🔍 Анализирую структуру запроса...\n"
            "⚙️ Подготавливаю интеграцию...\n\n"
            "После подключения PAWN-компилятора "
            "бот сможет автоматически проверить "
            "результат компиляции.",
            parse_mode="HTML"
        )

        await send_admin_system_request(
            update,
            context
        )

        user_state[uid] = STATE_NONE

        await update.message.reply_text(
            "📨 Заявка передана в обработку.",
            reply_markup=main_menu()
        )

        return

    # -----------------------------------------------------
    # НАЗВАНИЕ СИСТЕМЫ
    # -----------------------------------------------------

    if state == STATE_WAIT_SYSTEM_NAME:

        system_code = make_system_template(text)

        await update.message.reply_text(
            f"✅ <b>ВОТ ВАША СИСТЕМА {escape_html(text)}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<pre>{escape_html(system_code)}</pre>",
            parse_mode="HTML"
        )

        user_state[uid] = STATE_NONE

        await update.message.reply_text(
            "⬇️ Главное меню:",
            reply_markup=main_menu()
        )

        return

    # -----------------------------------------------------
    # ОШИБКА КОМПИЛЯЦИИ
    # -----------------------------------------------------

    if state == STATE_WAIT_ERROR_TEXT:

        user_data[uid]["error"] = text

        await update.message.reply_text(
            "🔍 <b>АНАЛИЗ МОДА</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📁 Файл получен\n"
            "❗ Ошибка получена\n"
            "🔎 Ищу соответствующее место в коде...\n"
            "🛠 Подготавливаю исправление...",
            parse_mode="HTML"
        )

        await process_error_request(
            update,
            context,
            uid
        )

        return

    # -----------------------------------------------------
    # ПОДДЕРЖКА
    # -----------------------------------------------------

    if state == STATE_SUPPORT:

        await send_support_ticket(
            update,
            context,
            text
        )

        user_state[uid] = STATE_NONE

        return

    # -----------------------------------------------------
    # НЕИЗВЕСТНЫЙ ТЕКСТ
    # -----------------------------------------------------

    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=main_menu()
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if context.args:

        text = " ".join(context.args)

        await send_support_ticket(
            update,
            context,
            text
        )

        return

    user_state[user.id] = STATE_SUPPORT

    await update.message.reply_text(
        "💬 <b>ПОДДЕРЖКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Напишите, что случилось.\n\n"
        "Например:\n"
        "<code>/support Ошибка при компиляции мода</code>",
        parse_mode="HTML"
    )


async def send_support_ticket(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str
):

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "нет username"
    )

    admin_text = (
        "🚨 НОВАЯ ЗАЯВКА В ПОДДЕРЖКУ\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Имя: {user.full_name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        "💬 Сообщение:\n"
        f"{text}"
    )

    try:

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text
        )

        await update.message.reply_text(
            "✅ <b>Заявка отправлена!</b>\n\n"
            "👨‍💻 Владелец получил ваше сообщение "
            "и скоро свяжется с вами.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

    except Exception as e:

        print("SUPPORT ERROR:", e)

        await update.message.reply_text(
            "❌ Не удалось отправить заявку. "
            "Попробуйте позже."
        )


# =========================================================
# ЗАЯВКА НА ДОБАВЛЕНИЕ СИСТЕМЫ
# =========================================================

async def send_admin_system_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    data = user_data.get(user.id, {})

    username = (
        f"@{user.username}"
        if user.username
        else "нет username"
    )

    system = data.get("system", "")

    message = (
        "🔧 НОВАЯ ЗАЯВКА НА ДОБАВЛЕНИЕ СИСТЕМЫ\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {user.full_name}\n"
        f"🔗 {username}\n"
        f"🆔 {user.id}\n\n"
        "📦 Система:\n"
        f"{system[:3500]}"
    )

    try:

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message
        )

        pwn_file = data.get("pwn_file")

        if pwn_file and os.path.exists(pwn_file):

            with open(pwn_file, "rb") as file:

                await context.bot.send_document(
                    chat_id=ADMIN_ID,
                    document=InputFile(
                        file,
                        filename=os.path.basename(pwn_file)
                    ),
                    caption="📁 PAWN-мод пользователя"
                )

    except Exception as e:

        print("SYSTEM REQUEST ERROR:", e)


# =========================================================
# ИСПРАВЛЕНИЕ ОШИБКИ
# =========================================================

async def process_error_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    uid: int
):

    data = user_data.get(uid)

    if not data:
        return

    pwn_file = data.get("pwn_file")
    error_text = data.get("error")

    # Пока AI-компилятор не подключён:
    #
    # Здесь будет:
    #
    # 1. Чтение .pwn
    # 2. Поиск строки ошибки
    # 3. Анализ include/define/stock/enum/new
    # 4. Исправление
    # 5. Запуск pawncc
    # 6. Повторная проверка
    # 7. Отправка исправленного .pwn

    await send_admin_error_request(
        update,
        context,
        pwn_file,
        error_text
    )

    await update.message.reply_text(
        "📨 <b>Мод и ошибка отправлены на обработку.</b>\n\n"
        f"❗ Ошибка:\n<code>{escape_html(error_text)}</code>\n\n"
        "Когда автоматический компилятор будет подключён, "
        "бот сможет сам исправлять код, повторно компилировать "
        "его и отправлять вам готовый `.pwn`.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    user_state[uid] = STATE_NONE


async def send_admin_error_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    pwn_file,
    error_text
):

    user = update.effective_user

    message = (
        "🛠 НОВАЯ ЗАЯВКА НА ИСПРАВЛЕНИЕ МОДА\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {user.full_name}\n"
        f"🆔 {user.id}\n\n"
        "❗ Ошибка:\n"
        f"{error_text}"
    )

    try:

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message
        )

        if pwn_file and os.path.exists(pwn_file):

            with open(pwn_file, "rb") as file:

                await context.bot.send_document(
                    chat_id=ADMIN_ID,
                    document=InputFile(
                        file,
                        filename=os.path.basename(pwn_file)
                    ),
                    caption="📁 Мод для исправления"
                )

    except Exception as e:

        print("ADMIN ERROR REQUEST:", e)


# =========================================================
# ГЕНЕРАТОР СИСТЕМ
# =========================================================

def make_system_template(request: str) -> str:

    command = request.strip()

    if not command.startswith("/"):
        command = "/" + command

    # Базовый пример.
    # Настоящий генератор AI подключим следующим этапом.

    if command.lower() == "/car":

        return """// REWET HOST - /car
// Базовый пример команды

CMD:car(playerid, params[])
{
    if (!IsPlayerConnected(playerid))
        return 0;

    // Здесь будет логика автомобиля.

    SendClientMessage(
        playerid,
        -1,
        "Вы вызвали команду /car."
    );

    return 1;
}"""

    return f"""// REWET HOST
// Запрошенная система: {command}

CMD:{command[1:]}(playerid, params[])
{{
    if (!IsPlayerConnected(playerid))
        return 0;

    // Здесь будет логика системы {command}.

    SendClientMessage(
        playerid,
        -1,
        "Система {command} успешно вызвана."
    );

    return 1;
}}"""


# =========================================================
# HTML ESCAPE
# =========================================================

def escape_html(text: str) -> str:

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    print(
        "BOT ERROR:",
        repr(context.error)
    )


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "Не задан BOT_TOKEN. "
            "Добавьте BOT_TOKEN в Environment Variables Render."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "support",
            support_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    app.add_error_handler(
        error_handler
    )

    print("REWET HOST BOT STARTED")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
