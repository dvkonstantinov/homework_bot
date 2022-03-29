import datetime
import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (TokenException, ApiException, DataException,
                        TypeException)

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('logfile.log', maxBytes=10000000, backupCount=3)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - [%(levelname)s] - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправлка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logger.error(f'Сбой при отправке сообщения: {error}')
        raise telegram.TelegramError(f'Сбой при отправке сообщения: {error}')
    else:
        logger.info('Сообщение в телеграм отправлено')


def get_api_answer(current_timestamp):
    """Запрос к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    try:
        response = requests.get(ENDPOINT, headers=headers, params=params)
    except requests.exceptions.Timeout:
        logger.error('Время ожидания соединения вышло')
        raise requests.exceptions.Timeout('Время ожидания соединения вышло')
    except requests.exceptions.TooManyRedirects:
        logger.error('Произошло слишком много редиректов')
        raise requests.exceptions.TooManyRedirects('Слишком много редиректов')
    except requests.exceptions.RequestException:
        logger.error('Произошла ошибка соединения')
        raise requests.exceptions.RequestException('Произошла ошибка '
                                                   'соединения')
    if response.status_code == HTTPStatus.OK:
        try:
            response = response.json()
            return response
        except TypeError as error:
            logger.error(f'Вернувшиеся данные не в формате json: {error}')
            raise TypeError(f'Вернувшиеся данные не в формате json: {error}')

    else:
        logger.error('Недоступен ендпоинт практикума')
        raise ApiException('API практикума недоступно')


def check_response(response):
    """Проверка ответа на корректность."""
    if not isinstance(response, dict):
        logger.error('Неверный тип response')
        raise TypeError('Неверный тип response')
    # Прощу прощения за тупость. Прочитал про все методы у словарей, get при
    # отсутствии значения возвращает None
    homeworks = response.get('homeworks')
    if homeworks:
        return homeworks[0]
    else:
        logger.error('Получен пустой список')
        raise TypeException('Получен пустой список')


def parse_status(homework):
    """Парсинг домашней работы."""
    if 'homework_name' in homework and 'status' in homework:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status in HOMEWORK_STATUSES:
            verdict = HOMEWORK_STATUSES.get(homework_status)
            return (f'Изменился статус проверки работы "{homework_name}". '
                    f' {verdict}')
        else:
            raise DataException('Недокументированный статус домашней работы')
    else:
        raise KeyError("Отсутствует ключи homework_name или status в ответе "
                       "API")


def check_tokens():
    """Проверка токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют переменные окружения!')
        raise TokenException('Отсутствуют переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    time_ago = datetime.datetime.now() - datetime.timedelta(minutes=10)
    current_timestamp = int(time.time()) - int(time_ago.timestamp())
    last_check_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message != last_check_message:
                last_check_message = message
                send_message(bot, message)
            else:
                logger.debug('Нет новых статусов в ответе')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
