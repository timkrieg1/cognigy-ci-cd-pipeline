import functools
import requests 
import re  
import time  

# --- Decorator for retrying on 500 server errors ---
def retry_on_500(max_retries=3, wait_seconds=5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except requests.HTTPError as e:
                    if e.response is not None and e.response.status_code == 500:
                        retries += 1
                        if retries > max_retries:
                            print(f"Max retries reached for {func.__name__}. Raising error.", flush=True)
                            raise
                        print(f"500 Server Error encountered in {func.__name__}, retrying in {wait_seconds} seconds... (Attempt {retries}/{max_retries})", flush=True)
                        time.sleep(wait_seconds)
                    else:
                        raise
        return wrapper
    return decorator

def clean_base_url(base_url: str) -> str:
    """
    Cleans the base URL by removing trailing slashes.
    """
    # --- Remove trailing slashes and '/new' from base URL ---
    return re.sub(r'/new/?$|/$', '', base_url.strip())