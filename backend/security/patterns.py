import re

EMAIL_PATTERN = re.compile(
    r"(?<![\w.+%-])[A-Z0-9._%+-]+@[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)+(?=$|[^\w-])",
    re.IGNORECASE | re.ASCII,
)

SIN_PATTERN = re.compile(
    r"(?<![\w])(?:[0-9]{3}([ -])[0-9]{3}\1[0-9]{3}|[0-9]{9})(?![\w])",
    re.ASCII,
)

PHONE_PATTERN = re.compile(
    r"(?<![\w])(?:\+1[ .-]?|1[ .-])?"
    r"(?:\([2-9][0-9]{2}\)|[2-9][0-9]{2})[ .-]?"
    r"[2-9][0-9]{2}[ .-]?[0-9]{4}(?![\w])",
    re.ASCII,
)

PII_PATTERN = re.compile(
    rf"(?:{EMAIL_PATTERN.pattern})|(?:{PHONE_PATTERN.pattern})|(?:{SIN_PATTERN.pattern})",
    re.IGNORECASE | re.ASCII,
)