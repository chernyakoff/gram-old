"""
{"id":359107176,"first_name":"М","last_name":"С","username":"chernyakoff","photo_url":"https://t.me/i/userpic/320/E5CF1DXAc92hvxFoNm0Z4y4Z4ycjpk6DqbKdvmjyVyw.jpg","auth_date":1757345190,"hash":"b09c726668a5133137a61de81ec7e62d4d57f37c3e4221816d9f860c6c7ee00e"}

{
  "id": 359107176,
  "auth_date": 1757345190,
  "hash": "58bb826023940f8a3248dd1f172df8661e04804a88ffe1aee81dd3f93e331333",
  "first_name": "M",
  "last_name": "C",
  "username": "chernyakoff",
  "photo_url": "https://t.me/i/userpic/320/"
}

как быстро развернуть фронт на реакт с авторизацией (есть бек на fastapi с телеграм авторизацией, access и refresh токенами и ручкой me - в токенах зашифровано только user id )
какие библиотеки компонентов посоветуешь и как сделать авторизацию и стейт

"""

import uvicorn

from app.config import config

if __name__ == "__main__":
    uvicorn.run(
        "app.app:app",
        host=config.api.host,
        port=config.api.port,
        reload=True,
    )
