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
    elif isinstance(obj, (np.float16, np.float32, np.float64)):
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

import cv2
import numpy as np

def detect_browser_ui(img): 
    """
    Detects browser UI elements: top bar, bookmarks bar, and bottom taskbar.
    Returns: top_offset, bookmark_offset, bottom_offset, has_bookmarks
    """
    height, width, _ = img.shape
    print(f"[INFO] Processing image with dimensions: {width}x{height}")

    # Convert to grayscale for analysis
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print("[DEBUG] Converted image to grayscale.")

    # STEP 1: Detect top browser chrome (address bar, tabs, etc.)
    top_offset = detect_top_chrome(gray_img, width, height)
    print(f"[RESULT] Top browser UI offset: {top_offset}")

    # STEP 2: Improved bookmark bar detection
    has_bookmarks, bookmark_offset = detect_bookmarks(gray_img, top_offset, width, height)
    print(f"[RESULT] Bookmark bar: {'Detected' if has_bookmarks else 'Not Detected'}, Offset: {bookmark_offset}")

    # STEP 3: Detect bottom taskbar/UI
    bottom_offset = detect_bottom_taskbar(gray_img, width, height)
    print(f"[RESULT] Bottom taskbar offset: {bottom_offset}")

    return top_offset, bookmark_offset, bottom_offset, has_bookmarks


def detect_top_chrome(gray_img, width, height):
    print("[STEP] Detecting top browser chrome...")
    top_offset = 0
    top_region_height = min(150, height//3)
    top_region = gray_img[0:top_region_height, :]
    print(f"[DEBUG] Top region height: {top_region_height}")

    edges_top = cv2.Canny(top_region, 30, 150)
    lines_top = cv2.HoughLinesP(edges_top, 1, np.pi/180, threshold=100, minLineLength=width*0.25, maxLineGap=20)

    horizontal_lines = []
    if lines_top is not None:
        for line in lines_top:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 5 and abs(x2 - x1) > width * 0.25:
                horizontal_lines.append((min(y1, y2), max(y1, y2)))
        print(f"[DEBUG] Detected {len(horizontal_lines)} horizontal lines in top region.")
    else:
        print("[DEBUG] No horizontal lines detected in top region.")

    horizontal_lines.sort(key=lambda x: x[0])
    h_projection = np.sum(edges_top, axis=1)
    significant_changes = []

    for i in range(1, len(h_projection)-1):
        if h_projection[i] > max(h_projection[i-1], h_projection[i+1]) * 1.5 and h_projection[i] > width * 0.1:
            significant_changes.append(i)
    print(f"[DEBUG] Found {len(significant_changes)} significant horizontal changes.")

    if horizontal_lines:
        last_significant_line = 0
        for line_start, line_end in horizontal_lines:
            if 30 < line_end < top_region_height and line_end > last_significant_line:
                last_significant_line = line_end
        if last_significant_line > 0:
            top_offset = last_significant_line + 5

    if significant_changes:
        for change in significant_changes:
            if 30 < change < top_region_height and change > top_offset - 10:
                top_offset = max(top_offset, change + 5)

    if top_offset < 30:
        gradient = np.gradient(np.mean(top_region, axis=1))
        gradient_peaks = []
        for i in range(10, len(gradient)-10):
            if abs(gradient[i]) > 5 and abs(gradient[i]) > abs(gradient[i-1]) and abs(gradient[i]) > abs(gradient[i+1]):
                gradient_peaks.append((i, abs(gradient[i])))
        gradient_peaks.sort(key=lambda x: x[1], reverse=True)
        if gradient_peaks and gradient_peaks[0][0] > 30:
            top_offset = max(top_offset, gradient_peaks[0][0] + 5)
        print(f"[DEBUG] Top offset from gradient: {top_offset}")

    if top_offset < 60:
        print("[DEBUG] Fallback top offset applied.")
        top_offset = 75

    return top_offset


def detect_bookmarks(gray_img, top_offset, width, height):
    print("[STEP] Detecting bookmarks bar...")
    has_bookmarks = False
    bookmark_offset = 0
    bookmark_region_start = top_offset
    bookmark_region_end = min(top_offset + 50, height//2)

    if bookmark_region_end > bookmark_region_start + 10:
        bookmark_region = gray_img[bookmark_region_start:bookmark_region_end, :]

        edges_bookmark = cv2.Canny(bookmark_region, 30, 100)
        lines_bookmark = cv2.HoughLinesP(edges_bookmark, 1, np.pi/180, threshold=50, minLineLength=width*0.4, maxLineGap=20)

        separator_line_y = 0
        if lines_bookmark is not None:
            for line in lines_bookmark:
                x1, y1, x2, y2 = line[0]
                if abs(y1 - y2) < 3 and abs(x2 - x1) > width * 0.4:
                    separator_line_y = max(separator_line_y, y1)
            print("[DEBUG] Bookmark separator line detected.")
        else:
            print("[DEBUG] No separator line found.")

        bookmark_evidence = 0
        bookmark_candidate_region = bookmark_region[:min(35, bookmark_region.shape[0]), :]
        column_width = width // 20
        column_variances = []

        for i in range(0, width - column_width, column_width):
            column = bookmark_candidate_region[:, i:i+column_width]
            variance = np.var(column)
            column_variances.append(variance)

        if len(column_variances) > 1:
            meta_variance = np.var(column_variances)
            avg_variance = np.mean(column_variances)
            print(f"[DEBUG] Bookmark variance: avg={avg_variance:.2f}, meta={meta_variance:.2f}")
            if meta_variance > 1000 and avg_variance > 300:
                bookmark_evidence += 2

        color_distinctiveness = 0
        content_start = bookmark_region_start + 40
        content_end = min(content_start + 50, height - 1)

        if content_end > content_start:
            content_sample = gray_img[content_start:content_end, :]
            bookmark_sample = gray_img[bookmark_region_start:bookmark_region_start+30, :]
            bookmark_hist = cv2.calcHist([bookmark_sample], [0], None, [64], [0, 256])
            content_hist = cv2.calcHist([content_sample], [0], None, [64], [0, 256])

            cv2.normalize(bookmark_hist, bookmark_hist, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(content_hist, content_hist, 0, 1, cv2.NORM_MINMAX)
            hist_diff = cv2.compareHist(bookmark_hist, content_hist, cv2.HISTCMP_CHISQR)
            print(f"[DEBUG] Bookmark color histogram difference: {hist_diff:.2f}")

            if hist_diff > 0.5:
                color_distinctiveness = 1
                bookmark_evidence += 1

        vertical_edges = cv2.Sobel(bookmark_candidate_region, cv2.CV_64F, 1, 0, ksize=3)
        vertical_edges = cv2.convertScaleAbs(vertical_edges)
        vertical_edge_profile = np.sum(vertical_edges, axis=0)

        kernel_size = width // 50
        if kernel_size % 2 == 0:
            kernel_size += 1
        if kernel_size < 3:
            kernel_size = 3

        vertical_edge_profile_smooth = cv2.GaussianBlur(vertical_edge_profile, (kernel_size, 1), 0)

        peaks = []
        min_distance = width // 30
        threshold = np.max(vertical_edge_profile_smooth) * 0.4

        for i in range(1, len(vertical_edge_profile_smooth) - 1):
            if (vertical_edge_profile_smooth[i] > vertical_edge_profile_smooth[i-1] and
                vertical_edge_profile_smooth[i] > vertical_edge_profile_smooth[i+1] and
                vertical_edge_profile_smooth[i] > threshold):
                if not peaks or i - peaks[-1] > min_distance:
                    peaks.append(i)

        print(f"[DEBUG] Vertical edge peaks detected: {len(peaks)}")

        if len(peaks) >= 4:
            distances = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
            if distances:
                std_dev = np.std(distances)
                mean_dist = np.mean(distances)
                print(f"[DEBUG] Peak spacing std/mean: {std_dev:.2f}/{mean_dist:.2f}")
                if std_dev < mean_dist * 0.4:
                    bookmark_evidence += 2

        if separator_line_y > 5:
            bookmark_evidence += 3
            bookmark_offset = separator_line_y + 5

        if bookmark_evidence >= 5:
            has_bookmarks = True
            if bookmark_offset == 0:
                bookmark_offset = 30
            if bookmark_offset > 40:
                bookmark_offset = 35
            print(f"[INFO] Bookmarks bar detected with height: {bookmark_offset}px (evidence score: {bookmark_evidence})")
        else:
            mean_intensity = np.mean(bookmark_candidate_region)
            std_intensity = np.std(bookmark_candidate_region)
            print(f"[DEBUG] Intensity stats: mean={mean_intensity:.2f}, std={std_intensity:.2f}")
            if mean_intensity > 200 and std_intensity < 15:
                has_bookmarks = True
                bookmark_offset = 30
                print("[INFO] Bookmark fallback triggered (light mode detected via intensity stats)")
            else:
                has_bookmarks = False
                bookmark_offset = 0
                print(f"[INFO] No bookmarks bar detected (evidence score: {bookmark_evidence})")

    return has_bookmarks, bookmark_offset


def detect_bottom_taskbar(gray_img, width, height):
    print("[STEP] Detecting bottom taskbar...")
    bottom_offset = 0
    bottom_region_height = min(70, height//10)
    bottom_region = gray_img[height-bottom_region_height:height, :]

    edges_bottom = cv2.Canny(bottom_region, 30, 150)
    lines_bottom = cv2.HoughLinesP(edges_bottom, 1, np.pi/180, threshold=100, minLineLength=width*0.25, maxLineGap=20)

    horizontal_lines = []
    if lines_bottom is not None:
        for line in lines_bottom:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 5 and abs(x2 - x1) > width * 0.25:
                horizontal_lines.append((min(y1, y2), max(y1, y2)))
        print(f"[DEBUG] Found {len(horizontal_lines)} horizontal lines in bottom region.")
    else:
        print("[DEBUG] No horizontal lines detected in bottom region.")

    if horizontal_lines:
        last_significant_line = 0
        for line_start, line_end in horizontal_lines:
            if 30 < line_end < bottom_region_height and line_end > last_significant_line:
                last_significant_line = line_end
        if last_significant_line > 0:
            bottom_offset = height - last_significant_line

    return bottom_offset


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
        # Time_stamp for the debug image
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
            
            # Ensure we don't try to crop beyond image boundaries
            if total_top_offset >= end_y:
                print("[WARNING] Invalid crop boundaries detected, adjusting...")
                total_top_offset = min(total_top_offset, end_y - 100)  # Ensure at least 100px height
            
            # Perform the crop
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