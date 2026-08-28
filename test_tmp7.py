import http.client

for length in [24, 25, 26]:
    body = b'x' * length
    conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
    headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    conn.request('POST', '/devices/register', body=body, headers=headers)
    try:
        resp = conn.getresponse()
        print(f'Len={length:2d} -> Status: {resp.status}, Body: {resp.read().decode()[:80]}')
    except Exception as e:
        print(f'Len={length:2d} -> Error: {e}')
    conn.close()
