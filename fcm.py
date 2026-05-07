import google.auth.transport.requests
from google.oauth2 import service_account

# Path to your Firebase service account JSON file
cred = service_account.Credentials.from_service_account_file(
    'firebase_credentials/serviceAccountKey.json', 
    scopes=['https://www.googleapis.com/auth/firebase.messaging']
)

request = google.auth.transport.requests.Request()
cred.refresh(request)
print("YOUR OAUTH TOKEN IS:\n", cred.token)

