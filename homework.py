import logging
import os
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv

from exceptions import (EndpointError,
                        HavingStatusError)

import requests

import telegram

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


def check_tokens():
    """Проверяет доступность переменных окружения."""
    list_token = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID]
    return all(list_token)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат.
    определяемый переменной окружения TELEGRAM_CHAT_ID.
    """
    try:
        logging.debug(f'Бот отправил сообщение {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту.
    API-сервиса Практикум.Домашка.
    """
    params = {'from_date': timestamp}
    logging.info(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise EndpointError(response)
    except requests.RequestException as error:
        logging.error(error)
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not response:
        message = 'В ответе пришел пустой словарь.'
        logging.error(message)
        raise KeyError(message)

    if not isinstance(response, dict):
        message = 'Тип ответа не соответствует "dict".'
        logging.error(message)
        raise TypeError(message)

    if 'homeworks' not in response:
        message = 'В ответе отсутствует ключ "homeworks".'
        logging.error(message)
        raise KeyError(message)

    if not isinstance(response.get('homeworks'), list):
        message = 'Формат ответа не соответствует списку.'
        logging.error(message)
        raise TypeError(message)

    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней.
    работе статус этой работы.
    """
    if homework.get('homework_name'):
        homework_name = homework.get('homework_name')
    else:
        homework_name = 'XXX'
        logging.warning('Отсутствует такое имя домашней работы.')
        raise KeyError(homework_name)

    homework_status = homework.get('status')
    if 'status' not in homework:
        message = 'В домашней работе отсутствует статус.'
        logging.error(message)
        raise HavingStatusError(message)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Неизвестный статус домашней работы.'
        logging.error(message)
        raise KeyError(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствуют токены.'
            'Программа была принудительно остановлена.')
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, 'Я включился, отслеживаю изменения.')
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logging.debug('Домашних работ нет.')
                send_message(bot, 'Изменений нет.')
                break
            for homework in homeworks:
                message = parse_status(homework)
                if last_message != message:
                    send_message(bot, message)
                    last_message = message
            timestamp = response.get('current_date')

        except Exception as error:
            if last_message != message:
                message = f'Ошибка в работе программы: {error}'
                send_message(bot, message)
                last_message = message
        else:
            last_message = ''
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        stream=sys.stdout)
    main()
