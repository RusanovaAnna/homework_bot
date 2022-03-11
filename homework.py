import logging
import os
import requests
import time
import telegram
import telegram.ext
from http import HTTPStatus
from dotenv import load_dotenv
try:
    from simplejson.errors import JSONDecodeError
except ImportError:
    from json.decoder import JSONDecodeError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class Error(Exception):
    """Base class for other exceptions"""
    pass


class ErrorNotCorrectStatusCode(Error):
    """
    Свой тип исключений.
    """
    pass


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    logger = logging.getLogger(__name__)
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info(
            f'Сообщение отправленно: {message}'
        )
    except Exception as error:
        logging.error(
            f'Сообщение не отправленно: {error}'
        )
        raise telegram.TelegramError(f'Ошибка {error}')


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе: {error}')
    if response.status_code != HTTPStatus.OK:
        status = response.status_code
        logging.error(f'Ошибка {status}')
        raise ErrorNotCorrectStatusCode(f'Ошибка {status}')
    else:
        try:
            res = response.json()
        except JSONDecodeError:
            logging.error("Ошибка преобразования в JSON")
        return res


def check_response(response):
    """проверяет ответ API на корректность."""
    if type(response) is not dict:
        raise TypeError('Ответ API не словарь')
    if 'homeworks' not in response:
        logging.error('Отсутствует ключ homeworks')
        raise KeyError('Отсутствует ключ homeworks')
    if type(response['homeworks']) is not list:
        raise TypeError('Домашнее задание прниходит не в виде списка')
    if response.get('homeworks') is None:
        raise TypeError('Список homrworks пустой')
    return response.get('homeworks')


def parse_status(homework):
    """извлекает из информации о домашней работе статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError(
            'В ответе не содержится ключ homework_name'
        )
    homework_name = homework.get('homework_name')
    if 'status' not in homework:
        raise KeyError(
            'В ответе не содержится ключ status'
        )
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES.keys():
        verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """проверяет доступность переменных окружения."""
    tokens_evn_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_CHAT_ID,
        TELEGRAM_TOKEN,
    ]
    for var in tokens_evn_list:
        if var is None:
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствуют обязательные переменные окружения')
        raise ValueError('Отсутствуют обязательные переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)[0]
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error, exc_info=True)
            time.sleep(RETRY_TIME)
        else:
            logging.error('Другие сбои')


if __name__ == '__main__':
    main()
