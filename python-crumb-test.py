import re
import requests

url = 'https://finance.yahoo.com/quote/META/options'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}
res = requests.get(url, headers=headers)
print('Status', res.status_code)
print('Cookies:', res.cookies)
text = res.text
crumb = None
match = re.search(r'"CrumbStore":\{"crumb":"([^"]+)"\}', text)
if not match:
    match = re.search(r'"crumb":"([^"]+)"', text)
if match:
    crumb = match.group(1)
    crumb = crumb.replace('\\u002F', '/')
print('Crumb:', crumb)
print('Preview:', text[:2000])
