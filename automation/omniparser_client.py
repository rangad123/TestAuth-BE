import cv2
import re
import traceback
import replicate
import sys
import os
import time
import numpy as np
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site


REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

# Define standard browser UI dimensions for guest mode
# This is the fixed offset that will be used for all guest mode browser coordinates
# It represents the typical height of the address bar and tabs in guest mode
GUEST_MODE_TOP_OFFSET = 120  # Standard height for address bar and tabs in guest mode (without bookmarks)
# No bookmark bar in guest mode, so we don't define its height

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

def detect_browser_ui(img):
    """
    Detect browser UI elements in the screenshot including address bar, 
    navigation buttons, bookmarks bar, and bottom taskbar.
    
    Returns: (top_offset, bookmark_bar_height, bottom_offset, has_bookmark_bar)
    """
    height, width, _ = img.shape
    
    # Convert to grayscale for edge detection
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect top browser chrome (address bar, tabs, etc.)
    address_bar_offset = 0
    
    # Check the top 150px for horizontal lines and color changes
    top_region = gray_img[0:min(150, height//3), :]
    edges_top = cv2.Canny(top_region, 50, 150)
    lines_top = cv2.HoughLinesP(edges_top, 1, np.pi/180, threshold=100, minLineLength=width*0.3, maxLineGap=10)
    
    if lines_top is not None:
        # Find the lowest horizontal line in the top region that could be the address bar
        for line in lines_top:
            x1, y1, x2, y2 = line[0]
            # If it's a relatively horizontal line
            if abs(y1 - y2) < 5:
                address_bar_offset = max(address_bar_offset, y2 + 5)  # Add small padding
    
    # If lines detection didn't work well, use color analysis to find large transitions
    if address_bar_offset < 50:  # Typically browser UI is at least 50px tall
        # Analyze horizontal bands for color differences
        for y in range(50, min(150, height//3), 5):
            upper_region = gray_img[y-10:y, :]
            lower_region = gray_img[y:y+10, :]
            
            upper_mean = np.mean(upper_region)
            lower_mean = np.mean(lower_region)
            
            # If there's a significant color change, it might be where the web content begins
            if abs(upper_mean - lower_mean) > 20:
                address_bar_offset = max(address_bar_offset, y + 5)
    
    # If still no clear detection, use a safe default based on common browser UIs
    if address_bar_offset < 70:
        address_bar_offset = 70  # Default estimate for browser UI height without bookmarks
    
    # Now detect if there's a bookmarks bar below the address bar
    bookmark_bar_height = 0
    has_bookmark_bar = False
    
    # Look for another horizontal line or color transition below the address bar
    bookmark_area_start = address_bar_offset
    bookmark_area_end = min(address_bar_offset + 50, height//2)  # Look up to 50px below address bar
    
    # Extract bookmark bar region for analysis
    bookmark_region = gray_img[bookmark_area_start:bookmark_area_end, :]
    edges_bookmark = cv2.Canny(bookmark_region, 50, 150)
    lines_bookmark = cv2.HoughLinesP(edges_bookmark, 1, np.pi/180, threshold=100, minLineLength=width*0.3, maxLineGap=10)
    
    bookmark_offset = 0
    if lines_bookmark is not None:
        for line in lines_bookmark:
            x1, y1, x2, y2 = line[0]
            # Adjust y-coordinates to account for the region offset
            y1 += bookmark_area_start
            y2 += bookmark_area_start
            
            # If it's a relatively horizontal line and different from address bar line
            if abs(y1 - y2) < 5 and y1 > address_bar_offset + 10:
                bookmark_offset = max(bookmark_offset, y2 + 5)
    
    # If we found a reasonable bookmark bar
    if bookmark_offset > address_bar_offset + 15:
        bookmark_bar_height = bookmark_offset - address_bar_offset
        has_bookmark_bar = True
        top_offset = bookmark_offset  # Total top offset includes both address bar and bookmarks
    else:
        top_offset = address_bar_offset  # No bookmarks bar detected
    
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
    print(f"       - Address bar height: {address_bar_offset}px")
    print(f"       - Bookmarks bar: {'Yes' if has_bookmark_bar else 'No'}, height: {bookmark_bar_height}px")
    print(f"       - Total top UI detected: {top_offset}px")
    print(f"       - Bottom UI detected: {bottom_offset}px")
    
    return top_offset, bookmark_bar_height, bottom_offset, has_bookmark_bar

def get_image_url(image_path):
    """
    Convert an image file path to a URL that can be accessed from the frontend.
    This simply returns the media URL path for the image file.
    """
    # Just return the media URL with the basename of the image
    return f"{settings.MEDIA_URL}{os.path.basename(image_path)}"

def send_to_omniparser(screenshot_path):
    if not REPLICATE_API_TOKEN:
        print("Missing Replicate API Token")
        return None

    try:
        #Time_stamp for the debug image
        timestamp = int(time.time())
        # Read original image
        img = cv2.imread(screenshot_path)

        if img is None:
            return {"error": "Invalid Image Path"}

        # Get original dimensions
        original_height, original_width, _ = img.shape
        print(f"[INFO] Image Loaded: {screenshot_path}")
        print(f"[INFO] Original Image Dimensions: {original_width}x{original_height}")
        
        # Detect browser UI elements (top, bookmarks bar, and bottom)
        top_offset, bookmark_bar_height, bottom_offset, has_bookmark_bar = detect_browser_ui(img)
        
        # Save original image with annotations for verification
        annotated_img = img.copy()
        # Draw red line at top_offset (which includes both address bar and bookmarks if present)
        cv2.line(annotated_img, (0, top_offset), (original_width, top_offset), (0, 0, 255), 2)
        
        # If bookmarks were detected, mark the address bar boundary with a yellow line
        if has_bookmark_bar and bookmark_bar_height > 0:
            address_bar_boundary = top_offset - bookmark_bar_height
            cv2.line(annotated_img, (0, address_bar_boundary), (original_width, address_bar_boundary), (0, 255, 255), 2)
        
        # Draw red line at bottom cutoff
        bottom_cutoff = original_height - bottom_offset
        cv2.line(annotated_img, (0, bottom_cutoff), (original_width, bottom_cutoff), (0, 0, 255), 2)
        
        annotated_path = os.path.join(settings.MEDIA_ROOT, f"detected_browser_ui_{timestamp}.jpg")
        cv2.imwrite(annotated_path, annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[INFO] Annotated image saved to: {annotated_path}")
        
        # Crop the image to remove browser UI
        cropped_path = None
        if top_offset > 0 or bottom_offset > 0:
            # Calculate the new crop boundaries
            end_y = original_height - bottom_offset if bottom_offset > 0 else original_height
            img = img[top_offset:end_y, :, :]
            
            # Save the cropped image with a new name for verification
            cropped_path = os.path.join(settings.MEDIA_ROOT, f"cropped_content_only_{timestamp}.jpg")
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
        resized_path = os.path.join(settings.MEDIA_ROOT, f"enhanced_for_parsing_{timestamp}.jpg")
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
        
        # Always use fixed guest mode offset for consistency
        guest_mode_top_offset = GUEST_MODE_TOP_OFFSET  # Fixed height for address bar in guest mode
        
        # Print adjustment info
        print(f"[INFO] Coordinate mapping for guest mode:")
        print(f"       - User detected top UI height: {top_offset}px")
        print(f"       - User has bookmark bar: {'Yes' if has_bookmark_bar else 'No'}")
        print(f"       - Guest mode fixed top UI height: {guest_mode_top_offset}px")

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

            # The model detected elements in the cropped image (without browser UI)
            # First convert the element coordinates to original screenshot scale
            content_coords = [
                int(bbox[0] * TARGET_WIDTH * scale_x),
                int(bbox[1] * TARGET_HEIGHT * scale_y),
                int(bbox[2] * TARGET_WIDTH * scale_x),
                int(bbox[3] * TARGET_HEIGHT * scale_y)
            ]
            
            # User screen coordinates - how they appeared in the user's original screenshot
            # Add back the original top offset that was cropped
            user_screen_coords = [
                content_coords[0],
                content_coords[1] + top_offset,
                content_coords[2],
                content_coords[3] + top_offset
            ]
            
            # FIXED: Guest mode coordinates - adjust properly for guest mode
            # This is the key change: we need to map content coordinates to guest mode
            # without applying the user's browser UI offset first
            guest_mode_coords = [
                content_coords[0],
                content_coords[1] + guest_mode_top_offset,  # Direct mapping to guest mode
                content_coords[2],
                content_coords[3] + guest_mode_top_offset   # Direct mapping to guest mode
            ]

            # Calculate center point for clicking (using guest mode coordinates)
            center_x = (guest_mode_coords[0] + guest_mode_coords[2]) // 2
            center_y = (guest_mode_coords[1] + guest_mode_coords[3]) // 2

            element = {
                "id": i,
                "name": content,
                "type": element_type,
                "interactivity": interactivity,
                "user_screen_coordinates": user_screen_coords,
                "guest_mode_coordinates": guest_mode_coords,
                "click_point": (center_x, center_y)
            }

            elements.append(element)
            
        # Save visualization image
        viz_path = os.path.join(settings.MEDIA_ROOT, f"element_detection_viz_{timestamp}.jpg")
        cv2.imwrite(viz_path, visualization_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[INFO] Element detection visualization saved to: {viz_path}")

        time.sleep(2)
        
        # Prepare image URLs for frontend
        debug_images = {}
        
        # Generate URLs for the images
        debug_images["detected_browser_ui"] = get_image_url(annotated_path)
        
        # Only include cropped_content_only if it was created
        if cropped_path:
            debug_images["cropped_content_only"] = get_image_url(cropped_path)
        else:
            debug_images["cropped_content_only"] = None
            
        debug_images["enhanced_for_parsing"] = get_image_url(resized_path)
        debug_images["element_detection_viz"] = get_image_url(viz_path)

        # Create a visualization of coordinate mapping
        # Use the original image to show both user and guest mode coordinates
        mapping_img = cv2.imread(screenshot_path)
        
        # Draw on it to show how coordinates are mapped
        for element in elements:
            # Draw original user coordinates in red
            user_x = element["user_screen_coordinates"][0]
            user_y = element["user_screen_coordinates"][1]
            user_x2 = element["user_screen_coordinates"][2]
            user_y2 = element["user_screen_coordinates"][3]
            
            # Draw rectangle for user coords (red)
            cv2.rectangle(mapping_img, (user_x, user_y), (user_x2, user_y2), (0, 0, 255), 2)
            
            # Draw guest mode coordinates in green
            guest_x = element["guest_mode_coordinates"][0]
            guest_y = element["guest_mode_coordinates"][1]
            guest_x2 = element["guest_mode_coordinates"][2]
            guest_y2 = element["guest_mode_coordinates"][3]
            
            # Draw rectangle for guest coords (green)
            cv2.rectangle(mapping_img, (guest_x, guest_y), (guest_x2, guest_y2), (0, 255, 0), 2)
            
            # Draw click points
            cv2.circle(mapping_img, element["click_point"], 5, (255, 255, 0), -1)  # Yellow circle for click point
            
        # Save mapping visualization
        mapping_path = os.path.join(settings.MEDIA_ROOT, f"coordinate_mapping_viz_{timestamp}.jpg")
        cv2.imwrite(mapping_path, mapping_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        debug_images["coordinate_mapping_viz"] = get_image_url(mapping_path)

        # Convert NumPy types before returning the result
        try:
            result = {
                "elements": elements,
                "total_elements": len(elements),
                "interactive_elements": sum(1 for e in elements if e["interactivity"]),
                "response_time": response_time,
                "browser_ui_detected": {
                    "user_top_offset": top_offset,
                    "has_bookmark_bar": has_bookmark_bar,
                    "bookmark_bar_height": bookmark_bar_height,
                    "bottom_offset": bottom_offset,
                    "guest_mode_offset": guest_mode_top_offset
                },
                "debug_images": debug_images
            }
            
            # Convert any NumPy types to native Python types
            return convert_numpy_types(result)
            
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc()}
    
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}