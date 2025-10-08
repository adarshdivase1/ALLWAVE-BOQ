# components/product_image_generator.py

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import re

def generate_product_info_card(product_name, brand, model, category, size_inches=None):
    """
    Creates a professional visual info card for products.
    This replaces the need for actual product photos with informative graphics.
    
    Args:
        product_name: Full product name
        brand: Manufacturer brand
        model: Model number
        category: Product category
        size_inches: Display size (for displays only)
    
    Returns:
        BytesIO object containing PNG image
    """
    
    # Image dimensions
    width, height = 300, 200
    
    # Create base image with gradient background
    img = Image.new('RGB', (width, height), color='#f8f9fa')
    draw = ImageDraw.Draw(img)
    
    # Create subtle gradient effect
    for i in range(height):
        # Calculate color transition
        r = 248 - int(i * 0.1)
        g = 249 - int(i * 0.1)
        b = 250 - int(i * 0.05)
        color = (max(230, r), max(235, g), max(240, b))
        draw.rectangle([(0, i), (width, i+1)], fill=color)
    
    # Load fonts (with fallback)
    try:
        # Try to use Arial (available on most systems)
        font_brand = ImageFont.truetype("arial.ttf", 18)
        font_large = ImageFont.truetype("arial.ttf", 16)
        font_medium = ImageFont.truetype("arialbd.ttf", 14)  # Bold
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        # Fallback to default font
        font_brand = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Category color coding (AllWave brand colors)
    category_colors = {
        'Displays': '#2563eb',  # Blue
        'Video Conferencing': '#10b981',  # Green
        'Audio': '#f59e0b',  # Orange
        'Control Systems': '#8b5cf6',  # Purple
        'Signal Management': '#ec4899',  # Pink
        'Cables & Connectivity': '#6b7280',  # Gray
        'Infrastructure': '#ef4444',  # Red
        'Mounts': '#14b8a6',  # Teal
        'Lighting': '#eab308',  # Yellow
        'Software & Services': '#06b6d4',  # Cyan
    }
    
    category_color = category_colors.get(category, '#6b7280')
    
    # Draw colored header bar
    draw.rectangle([(0, 0), (width, 45)], fill=category_color)
    
    # Add main border
    draw.rectangle([(0, 0), (width-1, height-1)], outline=category_color, width=3)
    
    # === CONTENT LAYOUT ===
    y_pos = 12
    
    # Category label (white text on colored background)
    category_text = category[:28] + "..." if len(category) > 28 else category
    draw.text((10, y_pos), category_text, fill='white', font=font_large)
    
    y_pos = 55
    
    # Brand name (prominent)
    brand_text = brand[:25] + "..." if len(brand) > 25 else brand
    draw.text((10, y_pos), brand_text, fill='#1f2937', font=font_brand)
    
    y_pos += 30
    
    # Model number
    model_text = f"Model: {model[:25]}" if model else "Model: N/A"
    if len(model) > 25:
        model_text = f"Model: {model[:22]}..."
    draw.text((10, y_pos), model_text, fill='#4b5563', font=font_medium)
    
    y_pos += 25
    
    # Product name (truncated to fit)
    if product_name:
        product_short = product_name[:35] + "..." if len(product_name) > 35 else product_name
        draw.text((10, y_pos), product_short, fill='#6b7280', font=font_small)
    
    y_pos += 30
    
    # Special feature: Display size badge (if applicable)
    if size_inches and category == 'Displays':
        badge_width = 70
        badge_height = 30
        badge_x = width - badge_width - 10
        badge_y = height - badge_height - 10
        
        # Draw badge background
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            radius=5,
            fill='#dbeafe',
            outline='#3b82f6',
            width=2
        )
        
        # Draw size text
        size_text = f'{size_inches}"'
        # Get text bbox for centering
        bbox = draw.textbbox((0, 0), size_text, font=font_brand)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = badge_x + (badge_width - text_width) // 2
        text_y = badge_y + (badge_height - text_height) // 2 - 2
        
        draw.text((text_x, text_y), size_text, fill='#1e40af', font=font_brand)
    
    # Add "AllWave AV" watermark in bottom left
    watermark_text = "AllWave AV"
    draw.text((10, height - 20), watermark_text, fill='#d1d5db', font=font_small)
    
    # Convert to BytesIO
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG', optimize=True)
    img_buffer.seek(0)
    
    return img_buffer


def extract_display_size(product_name):
    """
    Extracts display size from product name.
    
    Args:
        product_name: Product name string
    
    Returns:
        Integer size in inches, or None if not found
    """
    if not product_name:
        return None
    
    # Look for patterns like: 65", 65-inch, 65 inch, 65"
    patterns = [
        r'(\d{2,3})["\']',  # 65" or 65'
        r'(\d{2,3})-inch',  # 65-inch
        r'(\d{2,3})\s*inch',  # 65 inch
    ]
    
    for pattern in patterns:
        match = re.search(pattern, product_name, re.IGNORECASE)
        if match:
            try:
                size = int(match.group(1))
                # Validate reasonable display sizes
                if 32 <= size <= 120:
                    return size
            except:
                pass
    
    return None
