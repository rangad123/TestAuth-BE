import cv2
import re
import traceback
import replicate
import sys
import os
import time
from django.conf import settings

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

def send_to_omniparser(screenshot_path):
    if not REPLICATE_API_TOKEN:
        print("Missing Replicate API Token")
        return None

    try:
        # Read original image
        img = cv2.imread(screenshot_path)

        if img is None:
            return {"error": "Invalid Image Path"}

        # Get original dimensions
        original_height, original_width, _ = img.shape
        print(f"[INFO] Image Loaded: {screenshot_path}")
        print(f"[INFO] Original Image Dimensions: {original_width}x{original_height}")

        # Define model's target resolution
        TARGET_WIDTH = 1920
        TARGET_HEIGHT = 1200

        # Resize image to target resolution
        resized_img = cv2.resize(img, (TARGET_WIDTH, TARGET_HEIGHT))
        print(f"[INFO] Image Resized to: {TARGET_WIDTH}x{TARGET_HEIGHT}")

        # Save the resized image to a temporary path
        resized_path = os.path.join(settings.BASE_DIR, "temp_resized_screenshot.jpg")
        cv2.imwrite(resized_path, resized_img)
        screenshot_path = resized_path

        # Calculate scale factors to map back to original
        scale_x = original_width / TARGET_WIDTH
        scale_y = original_height / TARGET_HEIGHT

        # Start Timer
        start_time = time.time()

        model = "microsoft/omniparser-v2:49cf3d41b8d3aca1360514e83be4c97131ce8f0d99abfc365526d8384caa88df"
        input_data = {
            "image": open(screenshot_path, "rb"),
            "confidence": 0.5,
        }

        # Run Replicate API
        output = replicate.run(model, input=input_data)

        # End Timer
        response_time = round(time.time() - start_time, 2)

        # Validate output
        if not isinstance(output, dict) or 'elements' not in output:
            return {"error": "Invalid API response", "response": output}

        elements_str = output['elements']

        if not isinstance(elements_str, str):
            return {"error": "Unexpected 'elements' format", "response": elements_str}

        # Extract UI elements using regex
        elements = []
        pattern = r"icon (\d+): \{'type': '([^']+)', 'bbox': \[([^]]+)\], 'interactivity': ([^,]+), 'content': '([^']+)'\}"
        matches = re.findall(pattern, elements_str)

        for match in matches:
            i = int(match[0])
            element_type = match[1]
            bbox_str = match[2]
            interactivity = match[3] == "True"
            content = match[4]

            # Parse bbox coordinates
            bbox = [float(coord.strip()) for coord in bbox_str.split(',')]

            # Convert bbox from model space to original screen space
            abs_coords = [
                int(bbox[0] * TARGET_WIDTH * scale_x),
                int(bbox[1] * TARGET_HEIGHT * scale_y),
                int(bbox[2] * TARGET_WIDTH * scale_x),
                int(bbox[3] * TARGET_HEIGHT * scale_y)
            ]

            # Calculate center point for clicking
            center_x = (abs_coords[0] + abs_coords[2]) // 2
            center_y = (abs_coords[1] + abs_coords[3]) // 2

            element = {
                "id": i,
                "name": content,
                "type": element_type,
                "interactivity": interactivity,
                "coordinates": abs_coords,
                "click_point": (center_x, center_y)
            }

            elements.append(element)

        return {
            "elements": elements,
            "total_elements": len(elements),
            "interactive_elements": sum(1 for e in elements if e["interactivity"]),
            "response_time": response_time
        }

    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}