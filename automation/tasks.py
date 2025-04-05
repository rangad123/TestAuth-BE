import threading
import time
import replicate
import os
import requests
from io import BytesIO

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
last_warmup_time = 0  # Track the last warm-up time
WARMUP_INTERVAL = 600  # 10 minutes

def keep_omniparser_alive():
    global last_warmup_time
    if not REPLICATE_API_TOKEN:
        print("[ERROR] Missing Replicate API Token")
        return

    while True:
        current_time = time.time()
        
        # Check if the model needs to be warmed up
        if current_time - last_warmup_time < WARMUP_INTERVAL:
            print("[INFO] Model is already warm, skipping API call")
        else:
            model = "microsoft/omniparser-v2:49cf3d41b8d3aca1360514e83be4c97131ce8f0d99abfc365526d8384caa88df"
            sample_image_url = "https://www.w3.org/MarkUp/Test/xhtml-print/20050519/tests/jpeg420exif.jpg"

            try:
                response = requests.get(sample_image_url)
                response.raise_for_status()
                image_data = BytesIO(response.content)

                output = replicate.run(model, input={"image": image_data})
                last_warmup_time = current_time  # Update last successful warm-up time
                print("[INFO] Model Warm-Up Successful")

            except Exception as e:
                print(f"[ERROR] Warm-Up Failed: {e}")

        time.sleep(60)  # Check every minute but call API only when needed

def start_keep_alive_thread():
    thread = threading.Thread(target=keep_omniparser_alive, daemon=True)
    thread.start()
