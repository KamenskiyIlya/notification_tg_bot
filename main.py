from time import sleep

from environs import env
import requests
import telegram


def get_latest_checks(devman_token):
    url = 'https://dvmn.org/api/user_reviews/'
    headers = {
        'Authorization': f'Token {devman_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_payload = response.json()
    return response_payload


def checking_for_new_checks(devman_token, timestamp=None):
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
    CHAT_ID = env('CHAT_ID')
    REQUESTS_DELAY = env.int('REQUESTS_DELAY', default=600)
    bot = telegram.Bot(token=BOT_TOKEN)
    timestamp = None

    while True:
        for attempt in range(3):
            try:
                result, timestamp = checking_for_new_checks(DEVMAN_TOKEN, timestamp)

                if result:
                    text = generate_notification_text(result)
                    bot.send_message(chat_id=CHAT_ID, text=text)
            except telegram.error.TimedOut as e:
                    print(f'Вышло время ожидания ответа от telegram.\nОшибка: {e}')
            except requests.exceptions.ReadTimeout as e:
                pass
            except requests.exceptions.ConnectionError as e:
                print(f'Отсутствует подключение к сети, ошибка:\n {e}')

        sleep(REQUESTS_DELAY)


if __name__ == '__main__':
    main()
