from enum import IntEnum


class LicenseType(IntEnum):
    НЕТ = 0
    МЕСЯЦ = 1
    ТРИ_МЕСЯЦА = 3
    ШЕСТЬ_МЕСЯЦЕВ = 6
    ГОД = 12
    ПРЕМИУМ = 120


class Role(IntEnum):
    USER = 0
    ADMIN = 7
