import http.client

body = b'x' * 24
conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
conn.request('POST', '/devices/register', body=body, headers=headers)
try:
    resp = conn.getresponse()
    print(f'Len={len(body)} -> Status: {resp.status}, Body: {resp.read().decode()[:100]}')
except Exception as e:
    print(f'Len={len(body)} -> Error: {e}')
conn.close()
