from pprint import pprint

from environs import env
import requests
import telegram


def check():
	url = 'https://dvmn.org/api/user_reviews/'
	headers = {
		'Authorization': f'Token {DEVMAN_TOKEN}'
	}
	response = requests.get(url, headers=headers)
	response.raise_for_status()
	response_payload = response.json()
	return response_payload

def long_pooling_check(timestamp=None):
	url = 'https://dvmn.org/api/long_polling/'
	headers = {
		'Authorization': f'Token {DEVMAN_TOKEN}'
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


def get_chat_info(bot, chat_id):
	try:
		chat = bot.get_chat(chat_id)
		if chat.first_name:
			user_name = chat.first_name
			return user_name
		return 'пользователь'
	except Exception as e:
		print(f'Не удалось получить имя пользователя.\nОшибка: {e}')
		return 'пользователь'


def send_notification(bot, chat_id, name, text):
	try:
		bot.send_message(chat_id=chat_id, text=text)
	except telegram.error.TimedOut as e:
		print(f'Вышло время ожидания ответа от telegram.\nОшибка: {e}')


if __name__ == '__main__':
	env.read_env()
	DEVMAN_TOKEN = env('DEVMAN_TOKEN')
	BOT_TOKEN = env('TG_BOT_TOKEN')
	CHAT_ID = env('CHAT_ID')
	bot = telegram.Bot(token=BOT_TOKEN)
	timestamp = None

	user_name = get_chat_info(bot, CHAT_ID)

	while True:
		try:
			result, timestamp = long_pooling_check(timestamp)
		except requests.exceptions.ReadTimeout as e:
			print(f'Сервер не ответил, ошибка:\n {e}')
		except requests.exceptions.ConnectionError as e:
			print(f'Отсутствует подключение к сети, ошибка:\n {e}')

		if result:
			attempt_inf = result['new_attempts'][0]
			lesson_title = attempt_inf['lesson_title']
			lesson_url = attempt_inf['lesson_url']
			desicion = not attempt_inf['is_negative']
			text = (
				f'{user_name}, у Вас проверили работу\n'
				f'По уроку: {lesson_title}\n'
				f'Ссылка на урок: {lesson_url}\n\n'
			)

			if desicion is False:
				text += 'Результат: В работе нашлись ошибки, необходимы правки.'
			else:
				text += (
					'Результат: Работа принята,'
					'можно переходить к следующему уроку.'
				)

			send_notification(bot, CHAT_ID, user_name, text)
