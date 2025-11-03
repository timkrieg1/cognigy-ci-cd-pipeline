from flask_app.app import app
from flask_app.ngrok_service import start_ngrok

public_url = start_ngrok(5000)
print(f'Access your app at: {public_url}')
app.run(host='0.0.0.0', port=5000)