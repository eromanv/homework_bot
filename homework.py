"""Импорт данных для проверки домашней работы."""
import json
import logging
import os
import sys
import time
from http import HTTPStatus

from exceptions import (
    NotSentTelegramMessage, NotCorrectStatus, NotValidResponse
)
import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACT_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setStream(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Функция проверяет наличие всех необходимых локальных переменных."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Функция отправляет сообщение в телеграм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения Telegram - {error}')
    except telegram.error:
        raise NotSentTelegramMessage
    else:
        logger.debug('Сообщение успешно отправленно в Telegram')


def get_api_answer(timestamp):
    """Функция делает запрос к API и возвращает ответ в виде объекта python."""
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        raise NotValidResponse
    try:
        return response.json()
    except json.JSONDecodeError:
        raise NotValidResponse


def check_response(response):
    """Функция принимет словарь на вход и проверяет его содержимое."""
    if not isinstance(response, dict):
        raise TypeError
    try:
        homeworks_uploaded = response.get('homeworks')
    except KeyError as error:
        logging.error(f'Ошибка доступа по ключу homeworks: {error}')
        raise KeyError(f'Ошибка доступа по ключу homeworks: {error}')
    if not isinstance(homeworks_uploaded, list):
        logging.error('Ответ в некорректном формате')
        raise TypeError('Ответ в некорректном формате')
    if not homeworks_uploaded:
        return homeworks_uploaded or []
    return homeworks_uploaded


def parse_status(homework):
    """Принимает на вход работу, проверяет статус и возвращает строку."""
    status = homework.get('status')
    if status is None:
        raise TypeError
    if status not in HOMEWORK_VERDICTS:
        raise TypeError
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise TypeError
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise NotCorrectStatus
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует одна из переменных окружения')
        sys.exit('Токены некорректны, программа завершила свою работу')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - RETRY_PERIOD
    prev_message: str = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = prev_message
                logger.debug('Нет изменений')
            if message != prev_message:
                send_message(bot, message)
                prev_message = message
        except NotSentTelegramMessage:
            message = 'Ошибка при отправке сообщения Telegram'
            logger.error(message)
        except NotValidResponse:
            message = 'Сервер вернул некорректный ответ'
            logging.error(message)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != prev_message:
                send_message(bot, message)
                prev_message = message
        finally:
            timestamp += RETRY_PERIOD
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
