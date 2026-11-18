"""Normalize Iranian mobile numbers to one canonical +989XXXXXXXXX format."""

import re

_IRAN_MOBILE_PATTERN = re.compile(r"\+989[0-9]{9}\Z")
_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def normalize_iranian_mobile(value: str) -> str:
    """Accept 09..., +989..., 00989..., or 989... and return +989..."""
    if not isinstance(value, str):
        raise TypeError("A mobile number must be provided as text.")

    candidate = value.strip().translate(_DIGIT_TRANSLATION)
    candidate = re.sub(r"[\s()\-]", "", candidate)

    if candidate.startswith("0098"):
        candidate = "+" + candidate[2:]
    elif candidate.startswith("98"):
        candidate = "+" + candidate
    elif candidate.startswith("09"):
        candidate = "+98" + candidate[1:]

    if not _IRAN_MOBILE_PATTERN.fullmatch(candidate):
        raise ValueError("Enter a valid Iranian mobile number.")

    return candidate
