import http.client

test_bodies = [
    b'{\"device_id\":\"laptop_1\"}',
    b'{\"device_id\": \"laptop_1\"}',
    b'{\"device_id\": \"laptop_1\", \"device_type\": \"laptop\"}',
    b'{\"device_id\":\"laptop_1\",\"device_type\":\"laptop\"}',
    b'{\"device_id\":\"laptop_1\", \"device_type\":\"laptop\"}',
]

for body in test_bodies:
    conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
    headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    conn.request('POST', '/devices/register', body=body, headers=headers)
    try:
        resp = conn.getresponse()
        print(f'Body={body.decode()!r:40s} Len={len(body):2d} -> Status: {resp.status}, Body: {resp.read().decode()[:80]}')
    except Exception as e:
        print(f'Body={body.decode()!r:40s} Len={len(body):2d} -> Error: {e}')
    conn.close()
