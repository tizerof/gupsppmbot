from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from .commands import (
    add_district,
    my_districts,
    remove_district,
    request_activation,
    send_welcome,
    show_users_list,
)
from .handlers import button_handler, forward_message_to_districts, private_chat_message


async def register_handlers(application: Application):
    commands = [
        ("start", "Начать работу", send_welcome),
        ("help", "Помощь", send_welcome),
        (
            "request_activation",
            "Запросить активацию у администратора",
            request_activation,
        ),
        ("add_district", "Подписаться на район", add_district),
        ("remove_district", "Отписаться от района", remove_district),
        ("my_districts", "Мои районы", my_districts),
    ]

    for command, _, callback in commands:
        application.add_handler(CommandHandler(command, callback))

    await application.bot.set_my_commands(
        [BotCommand(command, description) for command, description, _ in commands]
    )

    # Скрытая команда для админа
    application.add_handler(CommandHandler("users", show_users_list))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & (filters.TEXT | filters.PHOTO | filters.Document.ALL),
            forward_message_to_districts,
        )
    )
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE, private_chat_message)
    )
