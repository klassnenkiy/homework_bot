import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import EndpointError, HTTPError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('my_logger.log', maxBytes=5000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Убедитесь, что в функции `check_tokens` есть docstring."""
    check = all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))
    if not check:
        logging.critical('Проверьте переменные окружения', exc_info=False)
    return check


def send_message(bot, message):
    """Убедитесь, что в функции `send_message` есть docstring."""
    logging.debug('Начало отправки сообщения')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение {message} отправлено в {TELEGRAM_CHAT_ID}')
    except telegram.TelegramError as error:
        logging.error(f'Сообщение не отправлено {error}')


def get_api_answer(timestamp):
    """Убедитесь, что в функции `get_api_answer` есть docstring."""
    current_timestamp = timestamp or int(time.time())
    payload = {'from_date': current_timestamp}
    params_api = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': payload
    }
    try:
        response = requests.get(**params_api)
    except Exception as error:
        raise EndpointError(
            'Ошибка в запросе к API {error} с параметрами: '
            '{url}, {headers}, {params}'
            .format(**params_api, error=error)
        )
    if response.status_code != HTTPStatus.OK:
        raise HTTPError(
            'Ошибка соединения: {status}, {text}'.format(
                status=response.status_code,
                text=response.text
            )
        )
    return response.json()


def check_response(response):
    """Убедитесь, что в функции `check_response` есть docstring."""
    if not isinstance(response, dict):
        raise TypeError('структура данных не соответствует ожиданиям')
    if 'homeworks' not in response:
        raise KeyError('в ответе API нет ключа homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('homeworks не список')
    return response['homeworks']


def parse_status(homework):
    """Убедитесь, что в функции `parse_status` есть docstring."""
    if not isinstance(homework, dict):
        raise TypeError('homework не словарь')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('В ответе нет ключа homework_name')
    if not status:
        raise KeyError('В ответе нет ключа status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {status}')
    verdict = HOMEWORK_VERDICTS[homework.get('status')]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Убедитесь, что в функции `main` есть docstring."""
    if not check_tokens():
        logging.critical('Недоступны переменные окружения!')
        sys.exit(
            'Программа принудительно остановлена'
            'Недоступны переменные окружения!'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    old_message = 'messages'
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                status = parse_status(homework)
            else:
                status = (f'За период от {timestamp}, изменений в домашних '
                          'работах нет.')
            if status != old_message:
                send_message(bot=bot, message=status)
                old_message = status
            else:
                logging.debug('Новые статусы отсутствуют')
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != old_message:
                send_message(bot=bot, message=status)
                old_message = status
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
