from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

group_commands = []

class OnlyPrivateMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.type != 'private':
            if not any([message.text.startswith(i) for i in group_commands]):
                raise CancelHandler()

    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        if callback_query.message.chat.type != 'private':
            if not any([callback_query.data.startswith(i) for i in group_commands]):
                raise CancelHandler()