from http import HTTPStatus
import logging
import os
import requests
import time

from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Updater

from dotenv import load_dotenv 

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


def send_message(bot, message):
    """отправляет сообщение в Telegram чат"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info(
            f'Сообщение отправленно: {message}'
        )
    except Exception as error:
        logger.error(
            f'Сообщение не отправленно: {error}'
        )


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        status = response.status_code
        logging.error(f'Ошибка {status}')
        raise Exception(f'Ошибка {status}')
    else:
        return response.json()

def check_response(response):
    """проверяет ответ API на корректность"""
    homework = response["homeworks"]
    if type(response) is not dict:
        raise TypeError('Ответ API не словарь')
    if type(response['homeworks']) is not list:
        raise TypeError('Домашнее задание прниходит не в виде списка')
    if ('homeworks') not in response:
        logger.error('Отсутствует ключ homeworks')
        raise TypeError('Отсутствует ключ homeworks')
    if response.get('homeworks') is None:
        raise TypeError('Список homrworks пустой')
    return response.get('homeworks')


def parse_status(homework):
    """извлекает из информации о конкретной домашней работе статус этой работы"""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError(
            'В ответе не содержится ключ homework_name'
        )
    homework_status = homework.get('status')
    if 'status' not in homework:
        raise KeyError(
            'В ответе не содержится ключ status'
        )
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise ValueError(
            f'Статус домашней работы {homework_status} некорректен'
        )
        logger.error(stack_info=True)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'



def check_tokens():
    """проверяет доступность переменных окружения"""
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
            logger.error(error, exc_info=True)
            time.sleep(RETRY_TIME)
        else:
            logging.error('Другие сбои')


if __name__ == '__main__':
    main()
