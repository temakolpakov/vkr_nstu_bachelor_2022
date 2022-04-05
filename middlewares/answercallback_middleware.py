from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
import messages.ru_messages as msgs


message_ids = {}

excluded_from_middleware = ['global_back']

excluded_from_answer = ['']

async def set_message_id(message: types.Message):
    message_ids[message.chat.id] = message.message_id


class AnswerCallbackMiddleware(BaseMiddleware):
    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        if callback_query.data == ' ':
            await callback_query.answer(msgs.not_active)
        if not any([i in callback_query.data for i in excluded_from_middleware]):
            if callback_query.message.message_id != message_ids.get(callback_query.message.chat.id):
                await callback_query.answer(msgs.alert, show_alert=True)
                raise CancelHandler()
        if not any([i in callback_query.data for i in excluded_from_answer]):
            await callback_query.answer()
