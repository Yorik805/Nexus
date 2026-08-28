import http.client

for length in [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 50, 60, 70, 80, 90, 100]:
    body = b'x' * length
    conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
    headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    conn.request('POST', '/devices/register', body=body, headers=headers)
    try:
        resp = conn.getresponse()
        print(f'Len={length:3d} -> Status: {resp.status}, Body: {resp.read().decode()[:60]}')
    except Exception as e:
        print(f'Len={length:3d} -> Error: {e}')
    conn.close()
