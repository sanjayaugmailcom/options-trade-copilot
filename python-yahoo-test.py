import requests
import re

session = requests.Session()
url = 'https://finance.yahoo.com/quote/META/options?p=META'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://finance.yahoo.com/',
}
print('Fetching', url)
res = session.get(url, headers=headers)
print('Status:', res.status_code)
print('URL:', res.url)
print('Cookies:', session.cookies.get_dict())
print('Content type:', res.headers.get('content-type'))
print('Text preview:')
print(res.text[:2000])

crumb = None
for pattern in [r'"CrumbStore":\{"crumb":"([^\"]+)"\}', r'"crumb":"([^\"]+)"']:
    m = re.search(pattern, res.text)
    if m:
        crumb = m.group(1)
        break
print('Crumb raw:', crumb)

if crumb:
    opts_url = f'https://query2.finance.yahoo.com/v7/finance/options/META?crumb={crumb}'
    print('Fetching options with crumb:', opts_url)
    opts_res = session.get(opts_url, headers={**headers, 'Referer': url})
    print('Status:', opts_res.status_code)
    print('Content type:', opts_res.headers.get('content-type'))
    print('Text preview:', opts_res.text[:1000])
