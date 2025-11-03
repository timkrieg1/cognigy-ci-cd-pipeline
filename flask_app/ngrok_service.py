from pyngrok import ngrok
from flask_app.app import app


def start_ngrok(port):
    public_url = ngrok.connect(port)
    print(f"Ngrok URL: {public_url}")
    return public_url

if __name__ == "__main__":
    public_url = start_ngrok(5000)
    print(f"Access your app at: {public_url}")
    app.run(host="0.0.0.0", port=5000)