import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional

from tortoise import timezone as tz

from app.utils.logger import Logger


class SessionTimer:
    """Таймер обратного отсчёта для управления сессией диалога"""

    def __init__(
        self, initial_minutes: int, on_timeout: Callable[[], None], logger: Logger
    ):
        self.logger = logger
        self.on_timeout = on_timeout
        self.expires_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self._cancelled = False

        # Запускаем с начальным таймаутом
        self.reset(initial_minutes)

    def reset(self, minutes: int):
        """Сбросить таймер на X минут от текущего момента"""
        if self._cancelled:
            return

        self.expires_at = tz.now() + timedelta(minutes=minutes)
        self.logger.info(
            f"⏱️  Таймер сброшен: +{minutes}м (до {self.expires_at.strftime('%H:%M:%S')})"
        )

        # Перезапускаем задачу отсчёта
        self._restart_countdown()

    def add(self, minutes: int):
        """Добавить X минут к текущему таймеру"""
        if self._cancelled or not self.expires_at:
            return

        self.expires_at += timedelta(minutes=minutes)
        self.logger.info(
            f"⏱️  Таймер продлён: +{minutes}м (до {self.expires_at.strftime('%H:%M:%S')})"
        )

    def remove(self, minutes: int):
        """Убрать X минут от текущего таймера"""
        if self._cancelled or not self.expires_at:
            return

        self.expires_at -= timedelta(minutes=minutes)
        self.logger.info(
            f"⏱️  Таймер сокращён: -{minutes}м (до {self.expires_at.strftime('%H:%M:%S')})"
        )

    def get_remaining_seconds(self) -> float:
        """Получить оставшееся время в секундах"""
        if not self.expires_at or self._cancelled:
            return 0

        remaining = (self.expires_at - tz.now()).total_seconds()
        return max(0, remaining)

    def cancel(self):
        """Остановить таймер"""
        self._cancelled = True
        if self._task and not self._task.done():
            self._task.cancel()
        self.logger.info("⏱️  Таймер остановлен")

    def _restart_countdown(self):
        """Перезапустить задачу отсчёта"""
        # Отменяем старую задачу
        if self._task and not self._task.done():
            self._task.cancel()

        # Создаём новую
        self._task = asyncio.create_task(self._countdown())

    async def _countdown(self):
        """Основная задача отсчёта времени"""
        try:
            while not self._cancelled:
                if not self.expires_at:
                    await asyncio.sleep(1)
                    continue

                remaining = self.get_remaining_seconds()

                if remaining <= 0:
                    self.logger.info("⏱️  Таймер истёк - вызываем callback")
                    self.on_timeout()
                    break

                # Логируем каждые 30 секунд
                if int(remaining) % 30 == 0:
                    self.logger.info(f"⏱️  Осталось: {int(remaining)}с")

                # Спим до следующей проверки
                await asyncio.sleep(min(5, remaining))

        except asyncio.CancelledError:
            self.logger.info("⏱️  Задача таймера отменена")
        except Exception as e:
            self.logger.error(f"⏱️  Ошибка в таймере: {e}")
