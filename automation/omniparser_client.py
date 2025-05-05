import cv2
import re
import traceback
import replicate
import sys
import base64
import os
import time
import numpy as np
from django.http import JsonResponse
from django.conf import settings

     
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

def convert_numpy_types(obj):
    """
    Convert NumPy types to native Python types for JSON serialization.
    This function can be used recursively for nested data structures.
    """
    import numpy as np

    if isinstance(obj, (np.integer, np.intc, np.intp, np.int8, np.int16, np.int32, 
                        np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float16, np.float32, np.float64)):  # Removed np.float_
        return float(obj)
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj



def encode_image_to_base64(image_path):
    """
    Convert an image file to base64 encoded string
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        print(f"Error encoding image {image_path}: {str(e)}")
        return None
   

def detect_browser_ui(img):
    """
    Detect browser UI elements in the screenshot including address bar, 
    navigation buttons, bookmarks bar, and bottom taskbar.
    
    Returns: (top_offset, bottom_offset)
    """
    height, width, _ = img.shape
    
    # Convert to grayscale for edge detection
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect top browser chrome (address bar, tabs, etc.)
    top_offset = 0
    
    # Check the top 150px for horizontal lines and color changes
    top_region = gray_img[0:min(150, height//3), :]
    edges_top = cv2.Canny(top_region, 50, 150)
    lines_top = cv2.HoughLinesP(edges_top, 1, np.pi/180, threshold=100, minLineLength=width*0.3, maxLineGap=10)
    
    if lines_top is not None:
        # Find the lowest horizontal line in the top region
        for line in lines_top:
            x1, y1, x2, y2 = line[0]
            # If it's a relatively horizontal line
            if abs(y1 - y2) < 5:
                top_offset = max(top_offset, y2 + 5)  # Add small padding
    
    # If lines detection didn't work well, use color analysis to find large transitions
    if top_offset < 50:  # Typically browser UI is at least 50px tall
        # Analyze horizontal bands for color differences
        for y in range(50, min(150, height//3), 5):
            upper_region = gray_img[y-10:y, :]
            lower_region = gray_img[y:y+10, :]
            
            upper_mean = np.mean(upper_region)
            lower_mean = np.mean(lower_region)
            
            # If there's a significant color change, it might be where the web content begins
            if abs(upper_mean - lower_mean) > 20:
                top_offset = max(top_offset, y + 5)
    
    # If still no clear detection, use a safe default based on common browser UIs
    if top_offset < 80:
        top_offset = 80  # Default estimate for browser UI height
    
    # Detect bottom taskbar (for Windows)
    bottom_offset = 0
    
    # Look at bottom 60px for potential taskbar
    bottom_region = gray_img[max(0, height-60):height, :]
    edges_bottom = cv2.Canny(bottom_region, 50, 150)
    lines_bottom = cv2.HoughLinesP(edges_bottom, 1, np.pi/180, threshold=100, minLineLength=width*0.3, maxLineGap=10)
    
    if lines_bottom is not None:
        for line in lines_bottom:
            x1, y1, x2, y2 = line[0]
            # Adjust y-coordinates to account for the region offset
            y1 += max(0, height-60)
            y2 += max(0, height-60)
            
            # If it's a relatively horizontal line in the bottom area
            if abs(y1 - y2) < 5:
                bottom_region_height = height - y1
                bottom_offset = max(bottom_offset, bottom_region_height)
    
    # If no clear taskbar detection but dark/solid color at bottom, it's likely taskbar
    if bottom_offset == 0:
        bottom_10px = gray_img[height-10:height, :]
        bottom_30px = gray_img[height-30:height-20, :]
        
        if abs(np.mean(bottom_10px) - np.mean(bottom_30px)) > 15:
            bottom_offset = 40  # Default Windows taskbar height
    
    # Print detection results
    print(f"[INFO] Browser UI detection results:")
    print(f"       - Top UI detected: {top_offset}px")
    print(f"       - Bottom UI detected: {bottom_offset}px")
    
    return top_offset, bottom_offset

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
        
        # Detect browser UI elements (top and bottom)
        top_offset, bottom_offset = detect_browser_ui(img)
        
        # Save original image with annotations for verification
        annotated_img = img.copy()
        # Draw red line at top_offset
        cv2.line(annotated_img, (0, top_offset), (original_width, top_offset), (0, 0, 255), 2)
        # Draw red line at bottom cutoff
        bottom_cutoff = original_height - bottom_offset
        cv2.line(annotated_img, (0, bottom_cutoff), (original_width, bottom_cutoff), (0, 0, 255), 2)
        
        annotated_path = os.path.join(settings.BASE_DIR, "detected_browser_ui.jpg")
        cv2.imwrite(annotated_path, annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[INFO] Annotated image saved to: {annotated_path}")
        
        # Crop the image to remove browser UI
        if top_offset > 0 or bottom_offset > 0:
            # Calculate the new crop boundaries
            end_y = original_height - bottom_offset if bottom_offset > 0 else original_height
            img = img[top_offset:end_y, :, :]
            
            # Save the cropped image with a new name for verification
            cropped_path = os.path.join(settings.BASE_DIR, "cropped_content_only.jpg")
            cv2.imwrite(cropped_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"[INFO] Browser UI removed. Cropped image saved to: {cropped_path}")
            print(f"[INFO] Cropped dimensions: {img.shape[1]}x{img.shape[0]}")

        # Define model's target resolution
        TARGET_WIDTH = 1920
        TARGET_HEIGHT = 1200

        # Resize image to target resolution
        resized_img = cv2.resize(img, (TARGET_WIDTH, TARGET_HEIGHT))
        print(f"[INFO] Image Resized to: {TARGET_WIDTH}x{TARGET_HEIGHT}")

        # Improve image quality if needed
        # Apply slight sharpening to enhance edges for better element detection
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        enhanced_img = cv2.filter2D(resized_img, -1, kernel)
        
        # Adjust contrast and brightness
        alpha = 1.2  # Contrast control (1.0 means no change)
        beta = 5     # Brightness control (0 means no change)
        enhanced_img = cv2.convertScaleAbs(enhanced_img, alpha=alpha, beta=beta)
        
        # Save the enhanced image
        resized_path = os.path.join(settings.BASE_DIR, "enhanced_for_parsing.jpg")
        cv2.imwrite(resized_path, enhanced_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        # Calculate scale factors to map back to original screen coordinates
        # Accounting for any cropped browser UI
        cropped_height = original_height - top_offset - bottom_offset
        cropped_width = original_width  # Width doesn't change
        
        scale_x = cropped_width / TARGET_WIDTH
        scale_y = cropped_height / TARGET_HEIGHT

        # Start Timer
        start_time = time.time()

        model = "microsoft/omniparser-v2:49cf3d41b8d3aca1360514e83be4c97131ce8f0d99abfc365526d8384caa88df"
        input_data = {
            "image": open(resized_path, "rb"),
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

        # Create a copy of the enhanced image to draw detected elements for verification
        visualization_img = enhanced_img.copy()
        colors = {
            'button': (0, 255, 0),  # Green for buttons
            'text': (255, 0, 0),    # Red for text
            'image': (0, 0, 255),   # Blue for images
            'link': (255, 255, 0),  # Yellow for links
            'default': (255, 0, 255) # Magenta for other elements
        }

        for match in matches:
            i = int(match[0])
            element_type = match[1]
            bbox_str = match[2]
            interactivity = match[3] == "True"
            content = match[4]

            # Parse bbox coordinates
            bbox = [float(coord.strip()) for coord in bbox_str.split(',')]

            # Draw the bounding box on the visualization image
            color = colors.get(element_type.lower(), colors['default'])
            pt1 = (int(bbox[0] * TARGET_WIDTH), int(bbox[1] * TARGET_HEIGHT))
            pt2 = (int(bbox[2] * TARGET_WIDTH), int(bbox[3] * TARGET_HEIGHT))
            cv2.rectangle(visualization_img, pt1, pt2, color, 2)
            
            # Add element ID and type
            label = f"{i}: {element_type} - {content[:15]}..."
            cv2.putText(visualization_img, label, (pt1[0], pt1[1]-5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Convert bbox from model space to original screen space
            # Add the top_offset to the y-coordinates to account for the cropped area
            abs_coords = [
                int(bbox[0] * TARGET_WIDTH * scale_x),
                int(bbox[1] * TARGET_HEIGHT * scale_y) + top_offset,
                int(bbox[2] * TARGET_WIDTH * scale_x),
                int(bbox[3] * TARGET_HEIGHT * scale_y) + top_offset
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
            
        # Save visualization image
        viz_path = os.path.join(settings.BASE_DIR, "element_detection_viz.jpg")
        cv2.imwrite(viz_path, visualization_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[INFO] Element detection visualization saved to: {viz_path}")
        
        # Prepare debug images for frontend
        debug_images = {}
        try:
            # Original image with UI detection annotations
            debug_images["detected_browser_ui"] = encode_image_to_base64(annotated_path)
            
            # Cropped image with UI removed
            debug_images["cropped_content_only"] = encode_image_to_base64(cropped_path) if top_offset > 0 or bottom_offset > 0 else None
            
            # Enhanced image sent to omniparser
            debug_images["enhanced_for_parsing"] = encode_image_to_base64(resized_path)
            
            # Visualization of detected elements
            debug_images["element_detection_viz"] = encode_image_to_base64(viz_path)
        except Exception as e:
            print(f"[WARNING] Error encoding debug images: {str(e)}")
            debug_images["error"] = str(e)

        # Convert NumPy types before returning the result
        try:
            result = {
                "elements": elements,
                "total_elements": len(elements),
                "interactive_elements": sum(1 for e in elements if e["interactivity"]),
                "response_time": response_time,
                "browser_ui_detected": {
                    "top_offset": top_offset,
                    "bottom_offset": bottom_offset
                },
                "debug_images": debug_images
            }
            
            # Convert any NumPy types to native Python types
            return convert_numpy_types(result)
            
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc()}
    
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}