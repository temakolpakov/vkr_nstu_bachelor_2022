from environs import Env

env = Env()
env.read_env()

LOG_FILE = env.str('LOG_FILE')
BOT_TOKEN = env.str('BOT_TOKEN')