import urllib.request

try:
    with urllib.request.urlopen('http://localhost:5179/api/options/META', timeout=10) as r:
        print('STATUS', r.status)
        print(r.read(200).decode('utf-8', errors='replace'))
except Exception as e:
    print('ERROR', type(e).__name__, e)
