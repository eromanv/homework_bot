"""Задаем исключения для бота."""


class NotSentTelegramMessage(Exception):
    """Определяем исключение для отправки сообщения."""

    pass


class NotCorrectStatus(Exception):
    """Статус работы при запросе к API."""

    pass


class NotValidResponse(Exception):
    """Невалидный JSON при запросе."""

    pass
