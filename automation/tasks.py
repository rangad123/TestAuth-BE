# import threading
# import time
# import replicate
# import os
# import requests
# import cv2
# import numpy as np
# from io import BytesIO

# REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
# last_warmup_time = 0  # Track the last warm-up time
# WARMUP_INTERVAL = 600  # 10 minutes

# def keep_omniparser_alive():
#     global last_warmup_time
#     if not REPLICATE_API_TOKEN:
#         print("[ERROR] Missing Replicate API Token")
#         return

#     while True:
#         current_time = time.time()
        
#         if current_time - last_warmup_time < WARMUP_INTERVAL:
#             print("[INFO] Model is already warm, skipping API call")
#         else:
#             model = "microsoft/omniparser-v2:49cf3d41b8d3aca1360514e83be4c97131ce8f0d99abfc365526d8384caa88df"
#             sample_image_url = " http://127.0.0.1:8000/media/screenshots/user_uid1_1744001582.png?t=1744001582"

#             try:
#                 # Download image from URL
#                 response = requests.get(sample_image_url)
#                 response.raise_for_status()

#                 # Convert to numpy image using OpenCV
#                 img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
#                 img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

#                 if img is None:
#                     raise ValueError("Downloaded image could not be decoded.")

#                 height, width, _ = img.shape
#                 print(f"[INFO] Original size: {width}x{height}")

#                 # Only pad if it's 1920x1080
#                 if width == 1920 and height == 1080:
#                     padding_height = 120
#                     black_padding = np.zeros((padding_height, width, 3), dtype=np.uint8)
#                     padded_img = cv2.vconcat([img, black_padding])
#                     height += padding_height
#                     print(f"[INFO] Padded to: {width}x{height}")
#                 else:
#                     padded_img = img  # use as-is

#                 # Encode padded image back to JPEG in memory
#                 success, buffer = cv2.imencode('.jpg', padded_img)
#                 if not success:
#                     raise Exception("Failed to encode image")

#                 image_bytes = BytesIO(buffer.tobytes())

#                 # Call the replicate API
#                 output = replicate.run(model, input={"image": image_bytes})
#                 last_warmup_time = current_time
#                 print("[INFO] Model Warm-Up Successful")
                

#             except Exception as e:
#                 print(f"[ERROR] Warm-Up Failed: {e}")

#         time.sleep(60)

# def start_keep_alive_thread():
#     thread = threading.Thread(target=keep_omniparser_alive, daemon=True)
#     thread.start()


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
