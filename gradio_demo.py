'''
from typing import Optional
import torch
from PIL import Image
import io
import base64
from flask import Flask, request, jsonify
from util.utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img

# Initialize Flask app
app = Flask(__name__)

# Initialize models (keep the same initialization as before)
yolo_model = get_yolo_model(model_path='weights/icon_detect/model.pt')
caption_model_processor = get_caption_model_processor(model_name="florence2", model_name_or_path="weights/icon_caption_florence")
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

@app.route('/process', methods=['POST'])
def process():
    try:
        # Get image from request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        image_input = Image.open(image_file)
        
        # Get parameters from request with default values
        box_threshold = float(request.form.get('box_threshold', 0.05))
        iou_threshold = float(request.form.get('iou_threshold', 0.1))
        use_paddleocr = request.form.get('use_paddleocr', 'true').lower() == 'true'
        imgsz = int(request.form.get('imgsz', 640))

        # Process image (same logic as before)
        image_save_path = image_input
        image_input.save(image_save_path)
        
        image = Image.open(image_save_path)
        box_overlay_ratio = image.size[0] / 3200
        draw_bbox_config = {
            'text_scale': 0.8 * box_overlay_ratio,
            'text_thickness': max(int(2 * box_overlay_ratio), 1),
            'text_padding': max(int(3 * box_overlay_ratio), 1),
            'thickness': max(int(3 * box_overlay_ratio), 1),
        }

        ocr_bbox_rslt, is_goal_filtered = check_ocr_box(
            image_save_path, 
            display_img=False, 
            output_bb_format='xyxy', 
            goal_filtering=None, 
            easyocr_args={'paragraph': False, 'text_threshold':0.9}, 
            use_paddleocr=use_paddleocr
        )
        
        text, ocr_bbox = ocr_bbox_rslt
        
        dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
            image_save_path,
            yolo_model,
            BOX_TRESHOLD=box_threshold,
            output_coord_in_ratio=True,
            ocr_bbox=ocr_bbox,
            draw_bbox_config=draw_bbox_config,
            caption_model_processor=caption_model_processor,
            ocr_text=text,
            iou_threshold=iou_threshold,
            imgsz=imgsz,
        )

        # Format the parsed content list
        formatted_content = [f'icon {i}: {str(v)}' for i, v in enumerate(parsed_content_list)]

        return jsonify({
            'processed_image': dino_labled_img,  # This is already base64 encoded
            'parsed_content': formatted_content,
            'coordinates': label_coordinates
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7861)


    
'''


















from typing import Optional
import torch
from PIL import Image
import io
import base64
from flask import Flask, request, jsonify
import pyautogui
from util.utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img

# Initialize Flask app
app = Flask(__name__)

# Initialize models
yolo_model = get_yolo_model(model_path='weights/icon_detect/model.pt')
caption_model_processor = get_caption_model_processor(model_name="florence2", model_name_or_path="weights/icon_caption_florence")
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

@app.route('/process', methods=['POST'])
def process():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        image_input = Image.open(image_file)
        width, height = image_input.size  # Get image dimensions
        
        box_threshold = float(request.form.get('box_threshold', 0.05))
        iou_threshold = float(request.form.get('iou_threshold', 0.1))
        use_paddleocr = request.form.get('use_paddleocr', 'true').lower() == 'true'
        imgsz = int(request.form.get('imgsz', 640))

        image_save_path = "imgs/saved_image_demo.png"
        image_input.save(image_save_path)
        
        image = Image.open(image_save_path)

        ocr_bbox_rslt, is_goal_filtered = check_ocr_box(
            image_save_path, 
            display_img=False, 
            output_bb_format='xyxy', 
            goal_filtering=None, 
            easyocr_args={'paragraph': False, 'text_threshold':0.9}, 
            use_paddleocr=use_paddleocr
        )
        
        text, ocr_bbox = ocr_bbox_rslt
        
        dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
            image_save_path,
            yolo_model,
            BOX_TRESHOLD=box_threshold,
            output_coord_in_ratio=True,
            ocr_bbox=ocr_bbox,
            caption_model_processor=caption_model_processor,
            ocr_text=text,
            iou_threshold=iou_threshold,
            imgsz=imgsz,
        )

        elements = []
        for i, content in enumerate(parsed_content_list):
            bbox = content.get("bbox", [])
            if len(bbox) == 4:
                abs_coords = [int(bbox[0] * width), int(bbox[1] * height), int(bbox[2] * width), int(bbox[3] * height)]
                center_x = (abs_coords[0] + abs_coords[2]) // 2
                center_y = (abs_coords[1] + abs_coords[3]) // 2
                elements.append({
                    "id": i,
                    "name": content.get("content", f"icon {i}"),
                    "coordinates": abs_coords,
                    "click_point": (center_x, center_y)  # Central point for pyautogui click
                })

        return jsonify({
            "elements": elements
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7861)