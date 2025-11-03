from pyngrok import ngrok

def start_ngrok(port):
    public_url = ngrok.connect(port)
    print(f"Ngrok URL: {public_url}")
    return public_url