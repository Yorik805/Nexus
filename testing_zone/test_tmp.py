import http.client, json
conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=10)
body = b'{\"a\":1}'
headers = {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
conn.request('POST', '/devices/register', body=body, headers=headers)
try:
    resp = conn.getresponse()
    print('Status:', resp.status)
    print('Body:', resp.read().decode())
except Exception as e:
    print('Error:', e)
conn.close()
