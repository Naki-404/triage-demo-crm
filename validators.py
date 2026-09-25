"""Customer card validation of the demo CRM.

Contains a DELIBERATE BUG for the triage demo: when the weighted sum with the first weight set gives 10,
the IIN standard says to recompute with the second weight set. This implementation rejects such IINs
instead, so roughly one valid IIN in eleven is refused as "Некорректный ИИН".
"""
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
        raise InvalidIINError("Некорректный ИИН: checksum does not match")  # BUG: second weight set skipped
    if checksum != digits[11]:
        raise InvalidIINError("Некорректный ИИН: checksum does not match")
