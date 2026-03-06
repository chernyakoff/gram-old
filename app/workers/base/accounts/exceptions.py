class SessionExpiredError(Exception):
    """Пользователь вылетел из сессии в Telegram"""

    def __init__(self, phone: str):
        self.phone = phone
        super().__init__(f"{phone} вылетел из сессии")
