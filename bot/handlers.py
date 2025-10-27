import logging

from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

from bot.utils import extract_district_from_text, get_user_activate_keyboard
from database import AsyncSessionLocal
from database.crud import (
    get_active_users_by_district_name,
    get_or_create_user,
    set_user_status,
)
from settings import settings

logger = logging.getLogger('uvicorn.error')


async def forward_message_to_districts(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Пересылает сообщение пользователям в соответствующих районах
    Только для групповых чатов
    """
    message = update.message
    if not message or message.chat and message.chat.type not in ["group", "supergroup"]:
        return

    district_name = None
    if message.text:
        district_name = extract_district_from_text(message.text)
    elif message.caption:
        district_name = extract_district_from_text(message.caption)

    if not district_name:
        return

    logger.info(
        f'Найдено сообщение по районам: "{district_name}" '
        f'в группе "{message.chat.title}" #{message.chat.id}'
    )

    async with AsyncSessionLocal() as session:
        users = await get_active_users_by_district_name(session, district_name)
        active_users = [user for user in users if user.active]

    for user in active_users:
        try:
            await message.forward(chat_id=user.telegram_id)
        except Exception as e:
            logger.error(
                f"Не удалось переслать сообщение пользователю {user.telegram_id}: {e}"
            )


async def private_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я пересылаю сообщения только из групповых чатов.\n"
        "Добавьте меня в групповой чат, чтобы я мог пересылать сообщения по районам.\n"
        "Используйте команды /help для получения дополнительной информации."
    )


async def change_user_activation(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
):
    data = query.data

    # Проверяем, является ли пользователь администратором
    admin_ids = settings.ADMIN_IDS
    if admin_ids and query.from_user.id not in admin_ids:
        return

    if data.startswith("activate:"):
        active = True
    elif data.startswith("deactivate:"):
        active = False
    else:
        return

    target_user_id = int(data.split(":")[1])

    async with AsyncSessionLocal() as session:
        target_user = await get_or_create_user(session, target_user_id)
        if not target_user:
            return

        if target_user.active == active:
            return

        success = await set_user_status(session, target_user, True, active)

    user_link = target_user.tg_link
    if success:
        if active:
            msg = f"Пользователь {user_link} активирован"
            target_msg = (
                "Ваш аккаунт активирован, добавьте районы командой /add_district"
            )
        else:
            msg = f"Пользователь {user_link} деактивирован"
            target_msg = "Ваш аккаунт деактивирован"

        await context.bot.send_message(chat_id=target_user_id, text=target_msg)
    else:
        msg = f"Не удалось изменить статус пользователя {user_link}"
        logger.error(f"Не удалось изменить статус пользователя с ID {target_user_id}")

    await query.edit_message_text(
        text=msg,
        reply_markup=get_user_activate_keyboard(target_user),
        parse_mode="HTML",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатий на кнопки
    """
    query = update.callback_query
    await query.answer()

    # Обрабатываем данные callback
    data = query.data
    if data.startswith("activate:") or data.startswith("deactivate:"):
        await change_user_activation(query, context)
