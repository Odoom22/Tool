import requests

resp = requests.post(
    "http://127.0.0.1:8000/audit",
    json={"domain": "hubtel.com"},
    timeout= 240
)

print("Status code:", resp.status_code)
print("Response JSON:", resp.json())
