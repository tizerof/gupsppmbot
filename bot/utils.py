import logging
import re
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from database import AsyncSessionLocal
from database.crud import get_or_create_user
from database.models import User

logger = logging.getLogger("uvicorn.error")


async def get_active_user(update: Update) -> Optional[User]:
    """
    Проверяет, зарегистрирован ли пользователь.
    Если нет, отправляет сообщение с инструкциями для активации.
    """
    effective_user = update.effective_user
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session,
            effective_user.id,
            username=effective_user.username,
            first_name=effective_user.first_name,
            last_name=effective_user.last_name,
        )
    if not user or not user.active:
        message = (
            "Ваш аккаунт не активирован.\n"
            "Запросите активацию командой /request_activation"
        )
        await update.message.reply_text(message)
        return None
    return user


def get_user_activate_keyboard(user: User) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Активировать пользователя",
                    callback_data=f"activate:{user.telegram_id}",
                ),
                InlineKeyboardButton(
                    "Деактивировать пользователя",
                    callback_data=f"deactivate:{user.telegram_id}",
                ),
            ],
        ]
    )


def extract_district_from_text(text: str) -> Optional[str]:
    """
    Извлекает название районов из текста заявки. Районов может быть несколько.
    Формат заявки:
    - "Район: <название районов>"
    """
    match = re.search(r"Район:\s*(.+)", text)
    if match:
        return match.group(1).strip().lower()

    return None
