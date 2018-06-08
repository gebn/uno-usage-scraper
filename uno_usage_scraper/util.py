# -*- coding: utf-8 -*-


def format_bytes(num: int) -> str:
    """
    Format a number of bytes in a more readable unit.

    :param num: The number of bytes.
    :return: The number of bytes represented as a base-2 storage quantity.
    """
    num = abs(num)
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB']:
        if num < 1024.0:
            return '{0:.1f} {1}'.format(num, unit)
        num /= 1024.0
    return '{0:.1f} YiB'.format(num)
