import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils import get_active_user, get_user_activate_keyboard
from database import AsyncSessionLocal
from database.crud import (
    add_user_to_district,
    get_or_create_user,
    get_users,
    remove_district_from_user,
    set_user_status,
)
from settings import settings

logger = logging.getLogger('uvicorn.error')


async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет приветственное сообщение и инструкции по использованию бота
    """
    welcome_text = (
        "Добро пожаловать в Бот-Фильтр заявок АСУМО!\n"
        "Я помогу вам отслеживать заявки по своим районам.\n\n"
        "Доступные команды:\n"
        "/request_activation - запросить активацию аккаунта\n"
        "/add_district <название> - подписаться на район\n"
        "/remove_district <название> - отписаться от района\n"
        "/my_districts - показать ваши районы\n"
        "/help - показать это сообщение\n\n"
        "Добавьте меня в групповой чат. Когда там появляется заявка, я определю район из текста сообщения "
        "и перешлю её всем пользователям, которые подписаны на этот район."
    )
    await update.message.reply_text(welcome_text)


async def request_activation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрос активации аккаунта у адмистратора
    """
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, update.effective_user.id)

        if not user:
            logger.error(f"Cant create user {update.effective_user.id}")
            return

        if user and user.active:
            await update.message.reply_text("Ваш аккаунт уже активирован.")
            return

        # if user and user.requested_activation:
        #     await update.message.reply_text("Вы уже запросили активацию аккаунта.")
        #     return

        success = await set_user_status(session, user, True, False)

    if success:
        for admin_id in settings.ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"Пользователь {user.tg_link} (ID: {update.effective_user.id}) запросил активацию аккаунта.",
                parse_mode="HTML",
                reply_markup=get_user_activate_keyboard(user),
            )

        await update.message.reply_text(
            "Ваш запрос на активацию аккаунта отправлен администратору."
        )


async def add_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Подписывает пользователя на район
    """
    user = await get_active_user(update)
    if not user:
        return

    district_name = " ".join(context.args or []).strip()
    if not district_name:
        await update.message.reply_text(
            "Укажите название района.\n" "Пример: /add_district Гольяново"
        )
        return

    # Добавление пользователя в район
    async with AsyncSessionLocal() as session:
        session.add(user)
        success = await add_user_to_district(session, user, district_name)

    if success:
        msg = f"Вы успешно подписались на район {district_name.title()}"
    else:
        msg = f"Вы уже подписаны на район {district_name}"
    await update.message.reply_text(msg)


async def remove_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отписывает пользователя от района
    """
    user = await get_active_user(update)
    if not user:
        return

    district_name = " ".join(context.args or []).strip()
    if not district_name:
        await update.message.reply_text(
            "Укажите название района.\n" "Пример: /add_district Гольяново"
        )
        return

    async with AsyncSessionLocal() as session:
        success = await remove_district_from_user(session, user, district_name)
    if success:
        await update.message.reply_text(
            f"Вы успешно отписались от района '{district_name}'!"
        )
    else:
        await update.message.reply_text(
            f"Вы не подписаны на район '{district_name}' или такого района не существует."
        )


async def my_districts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список районов пользователя
    """
    user = await get_active_user(update)
    if not user:
        return

    async with AsyncSessionLocal() as session:
        session.add(user)
        await session.refresh(user, ["districts"])
        districts = user.districts

    if districts:
        district_list = "\n".join(
            [f"- {district.name.title()}" for district in districts]
        )
        response = f"Вы подписаны на районы:\n{district_list}"
    else:
        response = "Вы пока не подписаны ни на один район."
    await update.message.reply_text(response)


async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, является ли пользователь администратором
    admin_ids = settings.ADMIN_IDS
    if admin_ids and update.effective_user.id not in admin_ids:
        return

    active = None
    if context.args:
        if context.args[0].lower() == "active":
            active = True
        elif context.args[0].lower() == "notactive":
            active = False

    async with AsyncSessionLocal() as session:
        user_list = await get_users(session, active)

        msg = f"Список пользователей:\n"
        for user in user_list:
            await session.refresh(user, ["districts"])
            district_names = ", ".join(user.get_district_names())
            msg += f"- {user.tg_link} - {district_names} \n"

    await update.message.reply_text(msg, parse_mode="HTML")
