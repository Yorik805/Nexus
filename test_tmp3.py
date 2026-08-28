import http.client, json

for body_str in [
    '{"a":1}',
    '{"device_id":"laptop_1"}',
    '{"device_id": "laptop_1"}',
    '{"device_id": "laptop_1", "device_type": "laptop"}',
    '{"device_id": "laptop_1", "device_type": "laptop", "extra": "data"}',
]:
    conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
    body = body_str.encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    conn.request('POST', '/devices/register', body=body, headers=headers)
    try:
        resp = conn.getresponse()
        print(f'Body: {body_str[:40]:40s} -> Status: {resp.status}, Body: {resp.read().decode()[:80]}')
    except Exception as e:
        print(f'Body: {body_str[:40]:40s} -> Error: {e}')
    conn.close()
