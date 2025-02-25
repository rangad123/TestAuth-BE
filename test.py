import time
import pyautogui
import requests

# URL of the Flask server
API_URL = "http://127.0.0.1:7861/process"

# Send a request to the Flask server (replace with the actual image path)
image_path = "imgs/saved_image_demo.png" # Change this to the actual image file

with open(image_path, "rb") as img_file:
    response = requests.post(API_URL, files={"image": img_file})

# Check if request was successful
if response.status_code == 200:
    data = response.json()

    # Find element with ID 3
    element_to_click = next((elem for elem in data["elements"] if elem["id"] == 11), None)

    if element_to_click:
        click_x, click_y = element_to_click["click_point"]
        
        # Click on the element using pyautogui
        pyautogui.click(click_x, click_y)
        print(f"Clicked on {element_to_click['name']} at {click_x}, {click_y}")

        # Wait for 2 seconds
        time.sleep(2)
    else:
        print("Element with ID 3 not found.")
else:
    print("Failed to get a response from the server:", response.text)
