import re
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator


class CardDetails(BaseModel):
    number: str
    month: int
    year: int
    cvv: str

    @field_validator("number", mode="before")
    def clean_number(cls, v):
        # просто убираем пробелы, никакой проверки длины / алгоритма
        return re.sub(r"\s+", "", str(v))

    @field_validator("month")
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("expiration_month должен быть в диапазоне 1..12")
        return v

    @field_validator("year")
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < current_year:
            raise ValueError(f"expiration_year не может быть меньше {current_year}")
        if v > current_year + 25:
            raise ValueError("expiration_year выглядит слишком далеким")
        return v

    @field_validator("cvv", mode="before")
    def validate_cvv(cls, v):
        s = str(v).strip()
        if not re.fullmatch(r"\d{3}", s):
            raise ValueError("security_code должен состоять ровно из 3 цифр")
        return s

    @model_validator(mode="after")
    def check_not_expired(self):
        now = datetime.now()
        if (self.expiration_year, self.expiration_month) < (now.year, now.month):
            raise ValueError("Карта просрочена")
        return self
