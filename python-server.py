from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import re

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://finance.yahoo.com/',
}


def fetch_crumb_and_cookies(symbol: str):
    session = requests.Session()
    url = f'https://finance.yahoo.com/quote/{symbol}/options?p={symbol}'
    response = session.get(url, headers=HEADERS, timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f'Failed to fetch options page: {response.status_code}')

    text = response.text
    crumb = None
    for pattern in [r'"CrumbStore":\{"crumb":"([^\"]+)"\}', r'"crumb":"([^\"]+)"']:
        match = re.search(pattern, text)
        if match:
            crumb = match.group(1)
            break

    if not crumb:
        raise RuntimeError('Failed to extract crumb from Yahoo options page')

    cookies = session.cookies.get_dict()
    return crumb, cookies


def fetch_options(symbol: str, crumb: str, cookies: dict, date: str | None = None):
    url = f'https://query2.finance.yahoo.com/v7/finance/options/{symbol}?crumb={requests.utils.requote_uri(crumb)}'
    if date:
        url += f'&date={requests.utils.requote_uri(date)}'

    headers = {**HEADERS, 'Referer': f'https://finance.yahoo.com/quote/{symbol}/options?p={symbol}'}
    response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f'Yahoo options endpoint returned {response.status_code}')

    return response.json()


@app.route('/api/options/<symbol>')
def options(symbol):
    expiry_date = request.args.get('date')
    try:
        crumb, cookies = fetch_crumb_and_cookies(symbol)
        data = fetch_options(symbol, crumb, cookies, expiry_date)
        return jsonify(data)
    except Exception as err:
        return jsonify({'error': 'Backend request failed', 'details': str(err)}), 500


if __name__ == '__main__':
    app.run(port=5179, debug=True)
