import http.client, json

for body_str in [
    '{"a":1}',
    '{"b":2}',
    '{"c":3}',
    '{"ab":12}',
    '{"abc":123}',
    '{"abcd":1234}',
    '{"abcde":12345}',
    '{"abcdef":123456}',
    '{"abcdefg":1234567}',
    '{"abcdefgh":12345678}',
    '{"abcdefghi":123456789}',
]:
    conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
    body = body_str.encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    conn.request('POST', '/devices/register', body=body, headers=headers)
    try:
        resp = conn.getresponse()
        print(f'Len={len(body_str):2d} -> Status: {resp.status}, Body: {resp.read().decode()[:60]}')
    except Exception as e:
        print(f'Len={len(body_str):2d} -> Error: {e}')
    conn.close()
