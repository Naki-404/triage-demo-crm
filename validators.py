"""Customer card IIN validation (legacy single-weight path)."""
import re

W1 = list(range(1, 12))


class InvalidIINError(ValueError):
    pass


def validate_iin(iin: str) -> None:
    if not re.fullmatch(r"\d{12}", iin or ""):
        raise InvalidIINError("IIN must contain 12 digits")
    digits = [int(c) for c in iin]
    month, day = int(iin[2:4]), int(iin[4:6])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        raise InvalidIINError("IIN contains an invalid birth date")
    checksum = sum(d * w for d, w in zip(digits[:11], W1, strict=True)) % 11
    if checksum == 10:
        raise InvalidIINError("Некорректный ИИН: checksum does not match")
    if checksum != digits[11]:
        raise InvalidIINError("Некорректный ИИН: checksum does not match")
