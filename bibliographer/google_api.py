"""A wrapper around google translate API."""

import logging
import requests
import os

TRANSLATE_URL = 'https://translation.googleapis.com/language/translate/v2'


def translate(text: str, target: str, source: str = 'en'):
    """Translates the source text into the target language."""

    api_key = os.environ.get('GOOGLE_API_KEY')
    if api_key is None:
        raise ValueError('Missing GOOGLE_API_KEY environment variable.')

    data = {
        'q': text,
        'target': target,
        'source': source,
        'format': 'text',
        'model': 'nmt',
        'key': api_key
    }
    resp = requests.post(TRANSLATE_URL, data=data)
    if not resp.ok:
        message = resp.json()['error']['message']
        logging.error(f'Wrong request: {message}')
        return None

    return resp.json()['data']['translations'][0]['translatedText']

    



