from environs import env
import requests
from pprint import pprint


env.read_env()

DEVMAN_TOKEN = env('DEVMAN_TOKEN')
BOT_TOKEN = env('TG_BOT_TOKEN')


def checks():
	url = 'https://dvmn.org/api/user_reviews/'
	headers = {
		'Authorization': f'Token {DEVMAN_TOKEN}'
	}
	response = requests.get(url, headers=headers)
	response.raise_for_status()
	response_payload = response.json()
	return response_payload

def long_pooling_checks(timestamp=None):
	url = 'https://dvmn.org/api/long_polling/'
	headers = {
		'Authorization': f'Token {DEVMAN_TOKEN}'
	}

	if timestamp:
		params = {
			'timestamp': timestamp,
		}
		response = requests.get(url, headers=headers, params=params)
	else:
		response = requests.get(url, headers=headers)

	response.raise_for_status()
	response_payload = response.json()

	if response_payload['status'] == 'timeout':
		timestamp = response_payload['timestamp_to_request']
	elif response_payload['status'] == 'found':
		timestamp = response_payload['last_attempt_timestamp']

	return response_payload, timestamp


if __name__ == '__main__':
	result, timestamp = long_pooling_checks()
	pprint(result)
	while True:
		try:
			result, timestamp = long_pooling_checks(timestamp)
			pprint(result)
		except requests.exceptions.ReadTimeout as e:
			print(f'Сервер не ответил, ошибка:\n {e}')
		except requests.exceptions.ConnectionError as e:
			print(f'Отсутствует подключение к сети, ошибка:\n {e}')