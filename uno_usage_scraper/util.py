# -*- coding: utf-8 -*-
import boto3
import base64

_KMS = boto3.client('kms')


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


def kms_decrypt(ciphertext: str) -> bytes:
    """
    Decrypt a value using KMS.

    :param ciphertext: The base64-encoded ciphertext.
    :return: The plaintext bytestring.
    """
    return _KMS.decrypt(
        CiphertextBlob=base64.b64decode(ciphertext))['Plaintext']


def kms_decrypt_str(ciphertext: str, encoding: str = 'utf-8') -> str:
    """
    Decrypt a piece of text using KMS.

    :param ciphertext: The base64-encoded ciphertext.
    :param encoding: The encoding of the text.
    :return: The plaintext.
    """
    return kms_decrypt(ciphertext).decode(encoding)
