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
    """
    height, width, _ = img.shape
    print(f"[INFO] Processing image with dimensions: {width}x{height}")
    
    # Convert to grayscale for edge detection
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect top browser chrome (address bar, tabs, etc.)
    top_offset = 0
    
    # Check the top 150px for horizontal lines and color changes
    top_region = gray_img[0:min(150, height//3), :]
    edges_top = cv2.Canny(top_region, 50, 150)
    lines_top = cv2.HoughLinesP(edges_top, 1, np.pi/180, 
                               threshold=100, 
                               minLineLength=width*0.3, 
                               maxLineGap=10)
    
    horizontal_lines = []
    if lines_top is not None:
        for line in lines_top:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 5:  # Horizontal line
                horizontal_lines.append((min(y1, y2), max(y1, y2)))
                top_offset = max(top_offset, max(y1, y2) + 5)
    
    # Sort horizontal lines by y-position
    horizontal_lines.sort(key=lambda x: x[0])
    
    # Use color analysis if lines detection didn't work well
    if top_offset < 50:
        for y in range(50, min(150, height//3), 5):
            upper_region = gray_img[y-10:y, :]
            lower_region = gray_img[y:y+10, :]
            
            upper_mean = np.mean(upper_region)
            lower_mean = np.mean(lower_region)
            
            if abs(upper_mean - lower_mean) > 20:
                top_offset = max(top_offset, y + 5)
    
    # Default safe browser UI height if no clear detection
    if top_offset < 80:
        top_offset = 80
        print("[INFO] Using default top offset: 80px")
    
    # Improved bookmark detection with stricter criteria
    has_bookmarks = False
    bookmark_offset = 0
    bookmark_confidence = 0
    required_confidence = 2  # Increased threshold to avoid false positives
    
    # Define the region where bookmarks typically appear
    bookmark_region_start = top_offset
    bookmark_region_end = min(top_offset + 40, height//2)
    bookmark_region = gray_img[bookmark_region_start:bookmark_region_end, :]
    
    # 1. Check for bookmark bar indicators
    top_right_region = bookmark_region[:20, int(width*0.7):]
    mean_intensity = np.mean(top_right_region)
    std_intensity = np.std(top_right_region)
    
    # Stricter criteria for text detection
    if std_intensity > 20 and mean_intensity > 30:  # Increased threshold
        text_ratio = np.sum((top_right_region > mean_intensity + std_intensity) | 
                           (top_right_region < mean_intensity - std_intensity)) / top_right_region.size
        if 0.2 < text_ratio < 0.6:  # Text typically has this ratio of light/dark pixels
            bookmark_confidence += 1
            print("[INFO] Detected potential bookmark indicator text")
    
    # 2. Check for consistent bookmark icon patterns
    icon_detected = False
    for y in range(0, bookmark_region.shape[0] - 20, 5):
        row_std = []
        for x in range(0, width - 100, 100):  # Check every 100px
            patch = bookmark_region[y:y+20, x:x+100]
            row_std.append(np.std(patch))
        
        # Look for regular pattern of variations (icons)
        if len(row_std) > 3:
            std_of_stds = np.std(row_std)
            mean_of_stds = np.mean(row_std)
            if std_of_stds > 5 and mean_of_stds > 15:  # Must have significant and regular variations
                icon_detected = True
                bookmark_offset = max(bookmark_offset, y + 20)
                break
    
    if icon_detected:
        bookmark_confidence += 1
        print("[INFO] Detected bookmark icon pattern")
    
    # 3. Check for horizontal separator line
    edges = cv2.Canny(bookmark_region, 30, 100)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 
                           threshold=50,
                           minLineLength=width*0.4,  # Increased length requirement
                           maxLineGap=20)
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 3:  # Stricter horizontal line requirement
                line_length = abs(x2 - x1)
                if line_length > width * 0.5:  # Must span at least half the width
                    bookmark_confidence += 1
                    bookmark_offset = max(bookmark_offset, y1 + 5)
                    print("[INFO] Detected bookmark separator line")
                    break
    
    # Final decision
    has_bookmarks = bookmark_confidence >= required_confidence
    
    # Ensure minimum bookmark bar height if detected
    if has_bookmarks:
        bookmark_offset = max(bookmark_offset, 25)
    else:
        bookmark_offset = 0  # Reset if no bookmarks detected
    
    # Detect bottom taskbar (for Windows)
    bottom_offset = 0
    bottom_region = gray_img[max(0, height-60):height, :]
    edges_bottom = cv2.Canny(bottom_region, 50, 150)
    lines_bottom = cv2.HoughLinesP(edges_bottom, 1, np.pi/180, 
                                  threshold=100, 
                                  minLineLength=width*0.3, 
                                  maxLineGap=10)
    
    if lines_bottom is not None:
        for line in lines_bottom:
            x1, y1, x2, y2 = line[0]
            y1 += max(0, height-60)
            y2 += max(0, height-60)
            
            if abs(y1 - y2) < 5:
                bottom_region_height = height - y1
                bottom_offset = max(bottom_offset, bottom_region_height)
    
    # Check for solid color taskbar
    if bottom_offset == 0:
        bottom_10px = gray_img[height-10:height, :]
        bottom_30px = gray_img[height-30:height-20, :]
        
        if abs(np.mean(bottom_10px) - np.mean(bottom_30px)) > 15:
            bottom_offset = 40  # Default Windows taskbar height
    
    # Print detection results with confidence information
    print(f"[INFO] Browser UI detection results:")
    print(f"       - Top UI detected: {top_offset}px")
    print(f"       - Bookmarks bar: {has_bookmarks} (confidence: {bookmark_confidence}/{required_confidence})")
    print(f"       - Bookmark offset: {bookmark_offset}px")
    print(f"       - Bottom UI detected: {bottom_offset}px")
    
    return top_offset, bookmark_offset, bottom_offset, has_bookmarks


def get_image_url(image_path):
    """
    Convert an image file path to a URL that can be accessed from the frontend.
    This simply returns the media URL path for the image file.
    """
    # Just return the media URL with the basename of the image
    return f"{settings.MEDIA_URL}{os.path.basename(image_path)}"

def write_to_omniparser(screenshot_path):
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
        
        # Detect browser UI elements (top, bookmarks, and bottom)
        top_offset, bookmark_offset, bottom_offset, has_bookmarks = detect_browser_ui(img)
        
        # Calculate total top offset (including bookmarks if present)
        total_top_offset = top_offset
        if has_bookmarks:
            total_top_offset += bookmark_offset
        
        # Save original image with annotations for verification
        annotated_img = img.copy()
        # Draw red line at top_offset (main browser UI)
        cv2.line(annotated_img, (0, top_offset), (original_width, top_offset), (0, 0, 255), 2)
        
        # Draw blue line at bookmarks bar end if present
        if has_bookmarks and bookmark_offset > 0:
            bookmark_end = top_offset + bookmark_offset
            cv2.line(annotated_img, (0, bookmark_end), (original_width, bookmark_end), (255, 0, 0), 2)
            cv2.putText(annotated_img, "Bookmarks Bar", (10, bookmark_end - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Draw red line at bottom cutoff
        bottom_cutoff = original_height - bottom_offset
        cv2.line(annotated_img, (0, bottom_cutoff), (original_width, bottom_cutoff), (0, 0, 255), 2)
        
        # Add labels
        cv2.putText(annotated_img, "Browser UI", (10, top_offset - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(annotated_img, "Taskbar/Bottom UI", (10, bottom_cutoff + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        annotated_path = os.path.join(settings.MEDIA_ROOT, f"detected_browser_ui_{timestamp}.jpg")
        cv2.imwrite(annotated_path, annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[INFO] Annotated image saved to: {annotated_path}")
        
        # Crop the image to remove browser UI (including bookmarks if present)
        cropped_path = None
        if total_top_offset > 0 or bottom_offset > 0:
            # Calculate the new crop boundaries
            end_y = original_height - bottom_offset if bottom_offset > 0 else original_height
            img = img[total_top_offset:end_y, :, :]
            
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
        # Accounting for any cropped browser UI and bookmarks
        cropped_height = original_height - total_top_offset - bottom_offset
        cropped_width = original_width  # Width doesn't change
        
        scale_x = cropped_width / TARGET_WIDTH
        scale_y = cropped_height / TARGET_HEIGHT

        # Store original browser metrics for reference
        browser_metrics = {
            "top_offset": top_offset,
            "bookmark_offset": bookmark_offset if has_bookmarks else 0,
            "total_top_offset": total_top_offset,
            "bottom_offset": bottom_offset,
            "has_bookmarks": has_bookmarks
        }

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

        # Calculate expected top offset for a guest mode browser (without bookmarks)
        # Based on typical browser UI measurements
        guest_mode_top_offset = top_offset  # Guest mode typically only has the top UI without bookmarks
        
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
                int(bbox[1] * TARGET_HEIGHT * scale_y) + total_top_offset,
                int(bbox[2] * TARGET_WIDTH * scale_x),
                int(bbox[3] * TARGET_HEIGHT * scale_y) + total_top_offset
            ]

            # Calculate center point for clicking in original screenshot
            center_x = (abs_coords[0] + abs_coords[2]) // 2
            center_y = (abs_coords[1] + abs_coords[3]) // 2
            
            # Calculate guest mode coordinates (adjusted for absence of bookmarks)
            guest_mode_coords = abs_coords.copy()
            guest_mode_center_y = center_y
            
            # If original had bookmarks but guest mode won't, adjust the y coordinates
            if has_bookmarks:
                bookmark_height = bookmark_offset
                guest_mode_coords[1] = max(guest_mode_top_offset, abs_coords[1] - bookmark_height)
                guest_mode_coords[3] = max(guest_mode_top_offset, abs_coords[3] - bookmark_height)
                guest_mode_center_y = (guest_mode_coords[1] + guest_mode_coords[3]) // 2
            
            element = {
                "id": i,
                "name": content,
                "type": element_type,
                "interactivity": interactivity,
                "coordinates": abs_coords,  # Original coordinates
                "click_point": (center_x, center_y),  # Original click point
                "guest_mode_coordinates": guest_mode_coords,  # Adjusted for guest mode
                "guest_mode_click_point": (center_x, guest_mode_center_y)  # Adjusted click point
            }

            elements.append(element)
            
        # Save visualization image
        viz_path = os.path.join(settings.MEDIA_ROOT, f"element_detection_viz_{timestamp}.jpg")
        cv2.imwrite(viz_path, visualization_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[INFO] Element detection visualization saved to: {viz_path}")

        # Create a visualization of guest mode coordinate mapping
        guest_mode_viz = annotated_img.copy()
        
        # Draw a green horizontal line showing where the content would start in guest mode
        cv2.line(guest_mode_viz, (0, guest_mode_top_offset), (original_width, guest_mode_top_offset), 
                (0, 255, 0), 2)
        cv2.putText(guest_mode_viz, "Guest Mode Content Start", (10, guest_mode_top_offset - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw guest mode click points
        for element in elements:
            if element["interactivity"]:
                gx, gy = element["guest_mode_click_point"]
                # Draw green circle at guest mode click point
                cv2.circle(guest_mode_viz, (gx, gy), 5, (0, 255, 0), -1)
                # Draw original click point in red for comparison
                ox, oy = element["click_point"]
                cv2.circle(guest_mode_viz, (ox, oy), 5, (0, 0, 255), -1)
                # Draw line connecting them if they're different
                if oy != gy:
                    cv2.line(guest_mode_viz, (ox, oy), (gx, gy), (255, 0, 255), 1)
        
        # Add legend
        cv2.putText(guest_mode_viz, "Original Click Points", (10, original_height - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(guest_mode_viz, "Guest Mode Click Points", (10, original_height - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        guest_viz_path = os.path.join(settings.MEDIA_ROOT, f"guest_mode_mapping_viz_{timestamp}.jpg")
        cv2.imwrite(guest_viz_path, guest_mode_viz, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[INFO] Guest mode coordinate mapping visualization saved to: {guest_viz_path}")

        time.sleep(2)
        
        # Prepare image URLs for frontend
        debug_images = {}
        
        # Generate URLs for the images
        debug_images["detected_browser_ui"] = get_image_url(annotated_path)
        debug_images["guest_mode_mapping"] = get_image_url(guest_viz_path)
        
        # Only include cropped_content_only if it was created
        if cropped_path:
            debug_images["cropped_content_only"] = get_image_url(cropped_path)
        else:
            debug_images["cropped_content_only"] = None
            
        debug_images["enhanced_for_parsing"] = get_image_url(resized_path)
        debug_images["element_detection_viz"] = get_image_url(viz_path)

        # Convert NumPy types before returning the result
        try:
            result = {
                "elements": elements,
                "total_elements": len(elements),
                "interactive_elements": sum(1 for e in elements if e["interactivity"]),
                "response_time": response_time,
                "browser_ui_detected": browser_metrics,
                "guest_mode_top_offset": guest_mode_top_offset,
                "debug_images": debug_images
            }
            
            # Convert any NumPy types to native Python types
            return convert_numpy_types(result)
            
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc()}
    
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}
    

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