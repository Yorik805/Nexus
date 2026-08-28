import http.client, json
conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=10)
body = json.dumps({"device_id": "laptop_1", "device_type": "laptop"}).encode("utf-8")
print("Body:", body)
print("Length:", len(body))
headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
conn.request("POST", "/devices/register", body=body, headers=headers)
try:
    resp = conn.getresponse()
    print("Status:", resp.status)
    print("Body:", resp.read().decode())
except Exception as e:
    print("Error:", e)
conn.close()
