import re
import unicodedata


def sanitize_cell_name(value: str, allow_unicode: bool = False) -> str:
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.

    :param value: String to sanitize.
    :param allow_unicode: Allow unicode characters in name.
    :returns: Sanitized string.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)

    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')

    value = re.sub(r'[^\w\s-]', '', value.lower())
    sanitized_name = re.sub(r'[-\s]+', '-', value).strip('-_')
    if len(sanitized_name) > 64:
        sanitized_name = sanitized_name[0:63]

    return sanitized_name