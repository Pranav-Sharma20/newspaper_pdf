#!/usr/bin/env python3
"""Flask web app for newspaper PDF generation.

Users can upload images, configure options, and download generated PDF.
"""
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
from pathlib import Path
from datetime import date
import re
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['UPLOAD_EXTENSIONS'] = {'.jpg', '.jpeg', '.png'}

EXTS = {'.jpg', '.jpeg', '.png'}
PAGE_RE = re.compile(r'page\s*no\.?\s*(\d+)', re.IGNORECASE)
DEFAULT_PRIORITY = [
    'dainik bhaskar',
    'city bhaskar',
    'rajasthan patrika',
    'first india',
    'sach bedhadak',
]

def load_font(size: int) -> ImageFont.ImageFont:
    for name in ["arial.ttf", "Calibri.ttf", "segoeui.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

def build_sort_key(priority: List[str]):
    priority_l = [p.lower() for p in priority]
    def sort_key(pair):
        idx, path = pair
        name = path.stem.lower()
        pr_rank = len(priority_l) + 1
        for i, kw in enumerate(priority_l):
            if kw in name:
                pr_rank = i
                break
        m = PAGE_RE.search(name)
        page_num = int(m.group(1)) if m else 0
        base = PAGE_RE.sub('', name).strip('- _')
        return (pr_rank, base, page_num, idx)
    return sort_key

def build_sort_key_with_map(priority: List[str], filename_map: dict = None):
    """Build sort key using original filenames from map for accurate matching."""
    priority_l = [p.lower() for p in priority]
    def sort_key(pair):
        idx, path = pair
        # Use original filename if available, otherwise use path stem
        if filename_map and str(path) in filename_map:
            name = filename_map[str(path)].lower()
        else:
            name = path.stem.lower()
        
        pr_rank = len(priority_l) + 1
        for i, kw in enumerate(priority_l):
            if kw in name:
                pr_rank = i
                break
        m = PAGE_RE.search(name)
        page_num = int(m.group(1)) if m else 0
        base = PAGE_RE.sub('', name).strip('- _')
        return (pr_rank, base, page_num, idx)
    return sort_key

def scale_image(im: Image.Image, max_w: Optional[int], max_h: Optional[int]) -> Image.Image:
    if max_w is None and max_h is None:
        return im
    w, h = im.size
    scale = 1.0
    if max_w is not None and w > max_w:
        scale = min(scale, max_w / w)
    if max_h is not None and h > max_h:
        scale = min(scale, max_h / h)
    if scale < 1.0:
        return im.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    return im

def add_label(image: Image.Image, label_text: str, font: ImageFont.ImageFont) -> Image.Image:
    draw_tmp = ImageDraw.Draw(image)
    x0, y0, x1, y1 = draw_tmp.textbbox((0, 0), label_text, font=font)
    text_w, text_h = x1 - x0, y1 - y0
    padding_x = 12
    padding_y = 10
    box_w = text_w + padding_x * 2
    box_h = text_h + padding_y * 2
    new_img = Image.new('RGB', (image.width, image.height + box_h), (255, 255, 255))
    new_img.paste(image, (0, box_h))
    draw = ImageDraw.Draw(new_img)
    draw.rectangle([0, 0, box_w, box_h], fill=(0, 0, 0))
    draw.text((padding_x, padding_y), label_text, font=font, fill=(255, 255, 0))
    return new_img

def generate_pdf(image_paths: List[Path], priority: List[str], all_label: Optional[str], 
                 font_size: int, max_w: Optional[int], max_h: Optional[int], 
                 no_label: bool, output_path: Path, filename_map: dict = None):
    font = load_font(font_size)
    indexed = list(enumerate(image_paths))
    # Sort using original filenames from the map for accurate priority matching
    indexed.sort(key=build_sort_key_with_map(priority, filename_map))
    ordered = [p for _, p in indexed]
    
    processed = []
    for p in ordered:
        try:
            im = Image.open(p).convert('RGB')
            im = scale_image(im, max_w, max_h)
            if not no_label:
                # Use original filename from map if available, otherwise use path stem
                if filename_map and str(p) in filename_map:
                    label = all_label if all_label is not None else filename_map[str(p)]
                else:
                    label = all_label if all_label is not None else p.stem
                im = add_label(im, label, font)
            processed.append(im)
        except Exception as e:
            print(f"Warning: Skipping {p.name}: {e}")
    
    if not processed:
        raise ValueError('No images processed')
    
    first, rest = processed[0], processed[1:]
    first.save(str(output_path), save_all=True, append_images=rest)
    return len(processed)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    # Get options
    priority_str = request.form.get('priority', ','.join(DEFAULT_PRIORITY))
    priority = [p.strip() for p in priority_str.split(',') if p.strip()]
    all_label = request.form.get('all_label', None)
    if all_label == '':
        all_label = None
    font_size = int(request.form.get('font_size', 28))
    max_w = request.form.get('max_width', None)
    max_h = request.form.get('max_height', None)
    max_w = int(max_w) if max_w and max_w != '' else None
    max_h = int(max_h) if max_h and max_h != '' else None
    no_label = request.form.get('no_label', 'false') == 'true'
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Save uploaded files with original names preserved for labels
        image_paths = []
        filename_map = {}  # Map secure filename to original name
        for file in files:
            original_name = file.filename
            filename = secure_filename(original_name)
            ext = Path(filename).suffix.lower()
            if ext in EXTS:
                filepath = Path(temp_dir) / filename
                file.save(str(filepath))
                image_paths.append(filepath)
                # Store original name without extension for labels
                filename_map[str(filepath)] = Path(original_name).stem
        
        if not image_paths:
            return jsonify({'error': 'No valid image files uploaded'}), 400
        
        # Generate PDF
        output_filename = f"newspapers_{date.today().isoformat()}.pdf"
        output_path = Path(temp_dir) / output_filename
        page_count = generate_pdf(image_paths, priority, all_label, font_size, max_w, max_h, no_label, output_path, filename_map)
        
        # Send file
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Cleanup temp directory after a delay
        # Note: In production, use background task or scheduled cleanup
        pass

if __name__ == '__main__':
    # For local testing
    app.run(debug=True, host='0.0.0.0', port=5000)
