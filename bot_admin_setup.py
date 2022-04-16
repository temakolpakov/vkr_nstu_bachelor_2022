from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.files import JSONStorage
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import config
from middlewares.logging_middleware import LoggingMiddleware
from middlewares.answercallback_middleware import AnswerCallbackMiddleware
from middlewares.onlyprivate_middleware import OnlyPrivateMiddleware
from aiogram import types

from loguru import logger

fmt = "{time} - {name} - {level} - {message}"

logger.remove()

logger.add(config.LOG_FILE, level='INFO', rotation='00:00')

bot = Bot(config.BOT_TOKEN_ADMIN)
# storage = RedisStorage2(config.REDIS_HOST, config.REDIS_PORT, config.REDIS_DB, config.REDIS_PASSWORD)
# storage = JSONStorage(config.STATES_FILE)  # внутреннее хранилище бота, позволяющее отслеживать FMS (Finite State Maschine)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware(logger))
dp.middleware.setup(OnlyPrivateMiddleware())
dp.middleware.setup(AnswerCallbackMiddleware())
