import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton,callback_query, ParseMode, ReplyKeyboardMarkup, \
    KeyboardButton, InputMedia, InputMediaPhoto, CallbackQuery
from aiogram.utils import executor, exceptions
from aiogram.utils.deep_linking import get_start_link, decode_payload
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
import config
from middlewares.logging_middleware import LoggingMiddleware
import logging
from bot_setup import bot, dp, log



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
