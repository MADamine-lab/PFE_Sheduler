import requests
import json

resp = requests.post('http://localhost:8000/api/create-accounts/')
data = resp.json()

print(f'Status: {resp.status_code}')
print(f'\n=== SUMMARY ===')
print(json.dumps(data['summary'], indent=2))

print(f'\n=== FIRST 5 ACCOUNTS ===')
for acc in data['created_accounts'][:5]:
    print(f"  - {acc['type']}: {acc['name']} ({acc['username']}) -> {acc['status']}")

print(f'\n... and {len(data["created_accounts"]) - 5} more accounts')
