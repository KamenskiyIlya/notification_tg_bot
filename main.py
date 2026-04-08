from time import sleep
import logging
from logging.handlers import RotatingFileHandler

from environs import env
import requests
import telegram


class TelegramLogsHandler(logging.Handler):
    
    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.bot = telegram.Bot(token=bot_token)
        self.chat_id = chat_id
    
    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.bot.send_message(chat_id=self.chat_id, text=log_entry)
        except:
            pass
        

def configuration_logger(bot_token, chat_id):
    logger = logging.getLogger('tg_bot_logger')
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s: %(levelname)s: %(message)s '
    )
    
    file_handler = RotatingFileHandler(
        'tg_bot.log',
        maxBytes= 10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'        
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    tg_handler = TelegramLogsHandler(bot_token, chat_id)
    tg_handler.setFormatter(formatter)
    logger.addHandler(tg_handler)
    
    return logger

def get_latest_checks(devman_token):
    url = 'https://dvmn.org/api/user_reviews/'
    headers = {
        'Authorization': f'Token {devman_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_payload = response.json()
    return response_payload


def get_new_checks(devman_token, timestamp=None):
    url = 'https://dvmn.org/api/long_polling/'
    headers = {
        'Authorization': f'Token {devman_token}'
    }
    params = {}

    if timestamp:
        params['timestamp'] = timestamp

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    response_payload = response.json()

    if response_payload['status'] == 'timeout':
        new_timestamp = response_payload['timestamp_to_request']
        return None, new_timestamp
    elif response_payload['status'] == 'found':
        new_timestamp = response_payload['last_attempt_timestamp']

    return response_payload, timestamp


def generate_notification_text(result):
    attempt_inf = result['new_attempts'][0]
    lesson_title = attempt_inf['lesson_title']
    lesson_url = attempt_inf['lesson_url']
    desicion = not attempt_inf['is_negative']
    text = (
        'У Вас проверили работу\n'
        f'По уроку: {lesson_title}\n'
        f'Ссылка на урок: {lesson_url}\n\n'
    )

    if not desicion:
        text += (
            'Результат: В работе нашлись ошибки,'
            'необходимы правки.'
        )
    else:
        text += (
            'Результат: Работа принята,'
            'можно переходить к следующему уроку.'
        )

    return text


def main():
    env.read_env()
    DEVMAN_TOKEN = env('DEVMAN_TOKEN')
    BOT_TOKEN = env('TG_BOT_TOKEN')
    LOG_BOT_TOKEN = env('LOG_BOT_TOKEN')
    CHAT_ID = env('CHAT_ID')
    ADMIN_CHAT_ID = env('ADMIN_CHAT_ID')
    REQUESTS_DELAY = env.int('REQUESTS_DELAY', default=600)
    
    logger = configuration_logger(LOG_BOT_TOKEN, ADMIN_CHAT_ID)

    bot = telegram.Bot(token=BOT_TOKEN)
    timestamp = None
    
    logger.info('Бот запущен')

    while True:
        for attempt in range(3):
            try:
                devman_response, timestamp = get_new_checks(
                    DEVMAN_TOKEN,
                    timestamp
                )

                if devman_response:
                    text = generate_notification_text(devman_response)
                    bot.send_message(chat_id=CHAT_ID, text=text)
            except telegram.error.TimedOut as e:
                logger.warning(
                    'Вышло время ожидания ответа от telegram. '
                    f'Ошибка: {e}.'
                )
            except requests.exceptions.ReadTimeout:
                logger.warning('Вышло время ожидания ответа от сайта.')
            except requests.exceptions.ConnectionError as e:
                logger.error(f'Отсутствует подключение к сети, ошибка: {e}')
            except Exception:
                logger.exception('Произошла неожиданная ошибка')

        sleep(REQUESTS_DELAY)


if __name__ == '__main__':
    main()
