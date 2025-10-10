# components/product_image_generator.py

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import re

# ==============================================================================
# === FIX: ADDED THE MISSING HELPER FUNCTION ===================================
# ==============================================================================
def extract_display_size(product_name):
    """
    Extracts the screen size in inches from a product name using regex.
    
    Args:
        product_name (str): The full name of the product.
    
    Returns:
        int or None: The extracted size in inches, or None if not found.
    """
    if not isinstance(product_name, str):
        return None
        
    # Regex to find numbers (typically 2 digits) followed by inch symbols or words.
    # Examples it matches: "85-inch", "75in", "65\"", "98' '", " 85 "
    patterns = [
        r'(\d{2,3})[\s-]?("|\'\'|inch|in)\b',  # e.g., 85", 75-inch, 65in
        r'\b(\d{2,3})[\s-]?inch\b'              # e.g., 85 inch
    ]
    
    for pattern in patterns:
        match = re.search(pattern, product_name, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None
# ==============================================================================
# === END OF FIX ===============================================================
# ==============================================================================


def generate_category_icon(draw, icon_area, category, sub_category):
    """
    Draws a simple iconic representation of the product category.
    
    Args:
        draw: ImageDraw object
        icon_area: Tuple (x, y, width, height) defining the drawing area
        category: Primary category
        sub_category: Sub-category
    """
    x, y, w, h = icon_area
    cx, cy = x + w // 2, y + h // 2  # Center point
    
    # Color scheme
    primary_color = '#2563eb'
    secondary_color = '#60a5fa'
    accent_color = '#1e40af'
    
    # === DISPLAYS & PROJECTORS ===
    if category == 'Displays':
        if 'LED' in sub_category or 'Video Wall' in sub_category:
            # LED Wall - Grid pattern
            grid_size = 6
            cell_w = w // grid_size
            cell_h = h // grid_size
            for i in range(grid_size):
                for j in range(grid_size):
                    cell_x = x + i * cell_w + 2
                    cell_y = y + j * cell_h + 2
                    draw.rectangle(
                        [(cell_x, cell_y), (cell_x + cell_w - 4, cell_y + cell_h - 4)],
                        fill=primary_color if (i + j) % 2 == 0 else secondary_color,
                        outline=accent_color
                    )
        elif 'Interactive' in sub_category:
            # Interactive Display - Screen with touch points
            draw.rectangle([(x+10, y+10), (x+w-10, y+h-10)], outline=primary_color, width=3)
            draw.rectangle([(x+15, y+15), (x+w-15, y+h-15)], fill=secondary_color)
            # Touch points
            for px, py in [(cx-15, cy-15), (cx+15, cy-15), (cx, cy+15)]:
                draw.ellipse([(px-5, py-5), (px+5, py+5)], fill='white', outline=accent_color, width=2)
        elif 'Projector' in sub_category:
            # Projector - Lens and light beam
            draw.rectangle([(x+10, y+20), (x+w-20, y+h-20)], fill=primary_color, outline=accent_color, width=2)
            draw.ellipse([(x+w-35, y+h//2-15), (x+w-5, y+h//2+15)], fill=secondary_color, outline=accent_color, width=2)
            # Light beam
            draw.polygon([(x+w-5, y+h//2), (x+w+30, y+h//2-25), (x+w+30, y+h//2+25)], fill=secondary_color, outline=None)
        else:
            # Standard Display - Monitor/TV
            draw.rectangle([(x+10, y+10), (x+w-10, y+h-15)], outline=primary_color, width=3)
            draw.rectangle([(x+15, y+15), (x+w-15, y+h-20)], fill=secondary_color)
            # Stand
            draw.rectangle([(cx-15, y+h-15), (cx+15, y+h-5)], fill=primary_color)
            draw.rectangle([(cx-25, y+h-5), (cx+25, y+h)], fill=accent_color)
    
    # === VIDEO CONFERENCING ===
    elif category == 'Video Conferencing':
        if 'Camera' in sub_category or 'PTZ' in sub_category:
            # Camera - Lens and body
            draw.ellipse([(x+15, y+15), (x+w-15, y+h-15)], fill=primary_color, outline=accent_color, width=2)
            draw.ellipse([(x+25, y+25), (x+w-25, y+h-25)], fill=secondary_color, outline=accent_color, width=2)
            draw.ellipse([(x+35, y+35), (x+w-35, y+h-35)], fill='white')
            # Direction indicator
            if 'PTZ' in sub_category:
                draw.polygon([(cx, y+5), (cx-8, y+15), (cx+8, y+15)], fill='white')
        elif 'Video Bar' in sub_category or 'Bar' in sub_category:
            # Video Bar - Horizontal soundbar with camera
            draw.rounded_rectangle([(x+5, cy-12), (x+w-5, cy+12)], radius=5, fill=primary_color, outline=accent_color, width=2)
            # Camera lens
            draw.ellipse([(cx-10, cy-8), (cx+10, cy+8)], fill=secondary_color, outline='white', width=2)
            # Speaker grilles
            for i in range(-3, 4):
                if i != 0:
                    sx = cx + i * 15
                    draw.line([(sx, cy-8), (sx, cy+8)], fill=secondary_color, width=1)
        elif 'Touch' in sub_category or 'Controller' in sub_category:
            # Touch Controller - Tablet shape
            draw.rounded_rectangle([(x+10, y+15), (x+w-10, y+h-15)], radius=8, fill=primary_color, outline=accent_color, width=2)
            draw.rounded_rectangle([(x+15, y+20), (x+w-15, y+h-20)], radius=5, fill=secondary_color)
            # Grid lines
            for i in range(1, 3):
                lx = x + 15 + i * (w - 30) // 3
                draw.line([(lx, y+20), (lx, y+h-20)], fill=accent_color, width=1)
                ly = y + 20 + i * (h - 40) // 3
                draw.line([(x+15, ly), (x+w-15, ly)], fill=accent_color, width=1)
        else:
            # Room Kit / Codec - Box with ports
            draw.rounded_rectangle([(x+10, y+20), (x+w-10, y+h-20)], radius=5, fill=primary_color, outline=accent_color, width=2)
            # Front panel indicators
            for i, px in enumerate([x+20, x+35, x+50]):
                draw.ellipse([(px, cy-3), (px+6, cy+3)], fill=secondary_color if i == 1 else accent_color)
    
    # === AUDIO ===
    elif category == 'Audio':
        if 'Microphone' in sub_category or 'Mic' in sub_category:
            if 'Ceiling' in sub_category:
                # Ceiling Mic - Circular array
                draw.ellipse([(x+15, y+15), (x+w-15, y+h-15)], fill=primary_color, outline=accent_color, width=2)
                # Mic array pattern
                import math
                for angle in [0, 60, 120, 180, 240, 300]:
                    mx = cx + int(20 * math.cos(math.radians(angle)))
                    my = cy + int(20 * math.sin(math.radians(angle)))
                    draw.ellipse([(mx-4, my-4), (mx+4, my+4)], fill=secondary_color)
            elif 'Gooseneck' in sub_category:
                # Gooseneck - Flexible stem
                draw.arc([(x+20, y+30), (x+w-20, y+h-10)], start=180, end=0, fill=primary_color, width=4)
                draw.ellipse([(cx-8, y+25), (cx+8, y+35)], fill=secondary_color, outline=accent_color, width=2)
            else:
                # Standard Mic - Classic microphone
                draw.ellipse([(cx-15, y+10), (cx+15, y+40)], fill=primary_color, outline=accent_color, width=2)
                draw.rectangle([(cx-5, y+40), (cx+5, y+h-10)], fill=accent_color)
                draw.rectangle([(cx-20, y+h-10), (cx+20, y+h-5)], fill=primary_color)
        elif 'Speaker' in sub_category or 'Loudspeaker' in sub_category:
            if 'Ceiling' in sub_category:
                # Ceiling Speaker - Circular with grille
                draw.ellipse([(x+10, y+10), (x+w-10, y+h-10)], fill=primary_color, outline=accent_color, width=2)
                for r in range(15, min(w, h)//2 - 10, 8):
                    draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], outline=secondary_color, width=1)
            else:
                # Standard Speaker - Box with cone
                draw.rounded_rectangle([(x+15, y+10), (x+w-15, y+h-10)], radius=5, fill=primary_color, outline=accent_color, width=2)
                draw.ellipse([(x+25, y+25), (x+w-25, y+h-25)], fill=secondary_color, outline=accent_color, width=2)
                for r in range(10, min(w, h)//3, 6):
                    draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], outline=accent_color, width=1)
        elif 'DSP' in sub_category or 'Processor' in sub_category or 'Mixer' in sub_category:
            # DSP/Mixer - Rack unit with knobs
            draw.rounded_rectangle([(x+5, y+20), (x+w-5, y+h-20)], radius=3, fill=primary_color, outline=accent_color, width=2)
            # Knobs/controls
            for i, kx in enumerate([x+20, x+40, x+60, x+80]):
                if kx < x+w-10:
                    draw.ellipse([(kx-6, cy-6), (kx+6, cy+6)], fill=secondary_color, outline=accent_color, width=2)
                    draw.line([(kx, cy-4), (kx, cy)], fill=accent_color, width=2)
        elif 'Amplifier' in sub_category:
            # Power Amplifier - Rack with VU meters
            draw.rounded_rectangle([(x+5, y+20), (x+w-5, y+h-20)], radius=3, fill=primary_color, outline=accent_color, width=2)
            # VU meter arcs
            draw.arc([(x+15, y+30), (x+w//2-5, y+h-30)], start=180, end=0, fill=secondary_color, width=3)
            draw.arc([(x+w//2+5, y+30), (x+w-15, y+h-30)], start=180, end=0, fill=secondary_color, width=3)
        else:
            # Generic Audio - Waveform
            draw.line([(x+10, cy), (x+w-10, cy)], fill=accent_color, width=2)
            import math
            points = []
            for i in range(0, w-20, 5):
                wave_y = cy + int(15 * math.sin(i * 0.3))
                points.append((x+10+i, wave_y))
            if len(points) > 1:
                draw.line(points, fill=secondary_color, width=3)
    
    # === SIGNAL MANAGEMENT ===
    elif category == 'Signal Management':
        if 'Matrix' in sub_category or 'Switcher' in sub_category:
            # Matrix Switcher - Grid with connections
            draw.rounded_rectangle([(x+10, y+15), (x+w-10, y+h-15)], radius=5, fill=primary_color, outline=accent_color, width=2)
            # Input/Output grid
            for i in range(3):
                for j in range(3):
                    px, py = x+20+i*20, y+25+j*20
                    if px < x+w-20 and py < y+h-25:
                        draw.rectangle([(px, py), (px+12, py+12)], fill=secondary_color if (i+j)%2==0 else accent_color)
        elif 'Extender' in sub_category:
            # Extender TX/RX - Two boxes with connection
            box_w = (w - 35) // 2
            draw.rounded_rectangle([(x+5, y+20), (x+5+box_w, y+h-20)], radius=3, fill=primary_color, outline=accent_color, width=2)
            draw.rounded_rectangle([(x+w-5-box_w, y+20), (x+w-5, y+h-20)], radius=3, fill=primary_color, outline=accent_color, width=2)
            # Connection line
            draw.line([(x+5+box_w, cy), (x+w-5-box_w, cy)], fill=secondary_color, width=3)
            # Arrow
            draw.polygon([(x+w-5-box_w-5, cy-5), (x+w-5-box_w-5, cy+5), (x+w-5-box_w, cy)], fill=secondary_color)
        elif 'Scaler' in sub_category or 'Converter' in sub_category:
            # Scaler/Converter - Box with signal transformation
            draw.rounded_rectangle([(x+15, y+20), (x+w-15, y+h-20)], radius=5, fill=primary_color, outline=accent_color, width=2)
            # Input signal (small)
            draw.rectangle([(x+25, cy-8), (x+35, cy+8)], fill=secondary_color)
            # Arrow
            draw.polygon([(x+40, cy-6), (x+50, cy), (x+40, cy+6)], fill=secondary_color)
            # Output signal (large)
            draw.rectangle([(x+55, cy-12), (x+w-25, cy+12)], fill=accent_color)
        else:
            # Generic Signal - Flow diagram
            draw.ellipse([(x+10, cy-10), (x+30, cy+10)], fill=primary_color, outline=accent_color, width=2)
            draw.line([(x+30, cy), (x+w-30, cy)], fill=secondary_color, width=3)
            draw.polygon([(x+w-35, cy-5), (x+w-35, cy+5), (x+w-30, cy)], fill=secondary_color)
            draw.ellipse([(x+w-30, cy-10), (x+w-10, cy+10)], fill=primary_color, outline=accent_color, width=2)
    
    # === CONTROL SYSTEMS ===
    elif category == 'Control Systems':
        if 'Touch Panel' in sub_category:
            # Touch Panel - Screen with UI
            draw.rounded_rectangle([(x+10, y+10), (x+w-10, y+h-10)], radius=8, fill=primary_color, outline=accent_color, width=3)
            draw.rounded_rectangle([(x+15, y+15), (x+w-15, y+h-15)], radius=5, fill=secondary_color)
            # UI elements
            for i in range(2):
                for j in range(2):
                    bx, by = x+22+i*30, y+22+j*25
                    if bx < x+w-30 and by < y+h-30:
                        draw.rounded_rectangle([(bx, by), (bx+20, by+15)], radius=3, fill=accent_color)
        elif 'Keypad' in sub_category:
            # Keypad - Button grid
            draw.rounded_rectangle([(x+10, y+15), (x+w-10, y+h-15)], radius=5, fill=primary_color, outline=accent_color, width=2)
            for i in range(3):
                for j in range(4):
                    bx, by = x+18+i*20, y+23+j*18
                    if bx < x+w-20 and by < y+h-20:
                        draw.rounded_rectangle([(bx, by), (bx+12, by+12)], radius=2, fill=secondary_color, outline=accent_color)
        else:
            # Control Processor - Rack with indicators
            draw.rounded_rectangle([(x+8, y+20), (x+w-8, y+h-20)], radius=3, fill=primary_color, outline=accent_color, width=2)
            # Status LEDs
            for i, led_x in enumerate([x+20, x+35, x+50, x+65]):
                if led_x < x+w-15:
                    draw.ellipse([(led_x, cy-4), (led_x+8, cy+4)], fill=secondary_color if i%2==0 else accent_color)
    
    # === MOUNTS ===
    elif category == 'Mounts':
        if 'Display' in sub_category or 'TV' in sub_category:
            # Display Mount - Wall bracket
            draw.rectangle([(x+10, y+15), (x+20, y+h-15)], fill=primary_color)  # Wall
            draw.polygon([(x+20, cy-20), (x+40, cy-15), (x+40, cy+15), (x+20, cy+20)], fill=accent_color)  # Arm
            draw.rounded_rectangle([(x+40, y+20), (x+w-10, y+h-20)], radius=3, fill=secondary_color, outline=primary_color, width=2)  # Screen
        elif 'Camera' in sub_category:
            # Camera Mount - Bracket with camera
            draw.rectangle([(x+15, y+h-25), (x+25, y+h-10)], fill=primary_color)
            draw.ellipse([(x+10, y+20), (x+w-10, y+h-30)], fill=secondary_color, outline=accent_color, width=2)
        elif 'Rack' in sub_category:
            # Rack Mount - Shelf with holes
            draw.rectangle([(x+5, y+25), (x+w-5, y+h-25)], fill=primary_color, outline=accent_color, width=2)
            for hole_x in [x+12, x+w-18]:
                for hole_y in [y+32, y+h-32]:
                    draw.ellipse([(hole_x-3, hole_y-3), (hole_x+3, hole_y+3)], fill=accent_color)
        else:
            # Generic Mount - Bracket
            draw.rectangle([(x+10, y+15), (x+20, y+h-15)], fill=primary_color)
            draw.polygon([(x+20, cy-15), (x+w-20, cy-5), (x+w-20, cy+5), (x+20, cy+15)], fill=accent_color)
    
    # === CABLES & CONNECTIVITY ===
    elif category == 'Cables & Connectivity':
        if 'Cable' in sub_category:
            # Cable - Coiled wire
            import math
            cable_points = []
            for i in range(0, w-20, 3):
                cx_offset = x + 10 + i
                cy_offset = cy + int(8 * math.sin(i * 0.5))
                cable_points.append((cx_offset, cy_offset))
            if len(cable_points) > 1:
                draw.line(cable_points, fill=primary_color, width=4)
            # Connectors
            draw.rectangle([(x+5, cy-6), (x+15, cy+6)], fill=accent_color, outline=secondary_color, width=2)
            draw.rectangle([(x+w-15, cy-6), (x+w-5, cy+6)], fill=accent_color, outline=secondary_color, width=2)
        elif 'Adapter' in sub_category or 'Connector' in sub_category:
            # Adapter/Connector
            draw.rectangle([(x+15, cy-12), (x+35, cy+12)], fill=primary_color, outline=accent_color, width=2)
            draw.rectangle([(x+w-35, cy-12), (x+w-15, cy+12)], fill=primary_color, outline=accent_color, width=2)
            draw.line([(x+35, cy), (x+w-35, cy)], fill=secondary_color, width=3)
        elif 'Fiber' in sub_category:
            # Fiber Optic - Thin line with light
            draw.line([(x+15, cy), (x+w-15, cy)], fill=secondary_color, width=2)
            for i in range(3):
                glow_x = x+20+i*20
                draw.ellipse([(glow_x-4, cy-4), (glow_x+4, cy+4)], fill='white', outline=secondary_color)
        else:
            # Wall Plate - Outlet
            draw.rounded_rectangle([(x+15, y+15), (x+w-15, y+h-15)], radius=5, fill=primary_color, outline=accent_color, width=2)
            draw.rounded_rectangle([(x+25, y+30), (x+w-25, y+h-30)], radius=3, fill=secondary_color)
    
    # === INFRASTRUCTURE ===
    elif category == 'Infrastructure':
        if 'Rack' in sub_category:
            # Equipment Rack - Front view with rails
            draw.rectangle([(x+15, y+10), (x+w-15, y+h-10)], outline=accent_color, width=3)
            # Rails with holes
            for rail_x in [x+18, x+w-18]:
                draw.line([(rail_x, y+10), (rail_x, y+h-10)], fill=primary_color, width=4)
                for hole_y in range(y+20, y+h-10, 12):
                    draw.ellipse([(rail_x-2, hole_y-2), (rail_x+2, hole_y+2)], fill=secondary_color)
        elif 'Power' in sub_category or 'PDU' in sub_category:
            # PDU - Power strip with outlets
            draw.rounded_rectangle([(x+10, y+25), (x+w-10, y+h-25)], radius=3, fill=primary_color, outline=accent_color, width=2)
            for i, outlet_x in enumerate([x+20, x+40, x+60, x+80]):
                if outlet_x < x+w-15:
                    draw.rectangle([(outlet_x-3, cy-6), (outlet_x+3, cy+6)], fill=secondary_color, outline=accent_color)
        else:
            # Generic Infrastructure - Box/Enclosure
            draw.rounded_rectangle([(x+12, y+18), (x+w-12, y+h-18)], radius=5, fill=primary_color, outline=accent_color, width=2)
            draw.line([(x+12, cy), (x+w-12, cy)], fill=secondary_color, width=2)
    
    # === LIGHTING ===
    elif category == 'Lighting':
        # Light fixture with rays
        draw.ellipse([(cx-15, y+15), (cx+15, y+35)], fill=primary_color, outline=accent_color, width=2)
        import math
        for angle in [-30, -15, 0, 15, 30]:
            rad = math.radians(90 + angle)
            ex = cx + int(25 * math.sin(rad))
            ey = y + 25 + int(25 * math.cos(rad))
            draw.line([(cx, y+35), (ex, ey)], fill=secondary_color, width=2)
    
    # === SOFTWARE & SERVICES ===
    elif category == 'Software & Services':
        # Cloud/Service icon
        draw.ellipse([(x+15, cy-8), (x+35, cy+8)], fill=primary_color)
        draw.ellipse([(x+30, cy-12), (x+55, cy+4)], fill=primary_color)
        draw.ellipse([(x+50, cy-8), (x+70, cy+8)], fill=primary_color)
        draw.rectangle([(x+15, cy), (x+70, cy+8)], fill=primary_color)
        # Checkmark
        draw.line([(cx-8, cy+2), (cx-3, cy+7), (cx+8, cy-7)], fill='white', width=3)
    
    # === NETWORKING ===
    elif category == 'Networking':
        # Network Switch - Box with ports
        draw.rounded_rectangle([(x+10, y+20), (x+w-10, y+h-20)], radius=3, fill=primary_color, outline=accent_color, width=2)
        # Port indicators
        for i in range(8):
            port_x = x + 15 + i * 10
            if port_x < x+w-15:
                draw.rectangle([(port_x, cy-4), (port_x+6, cy+4)], fill=secondary_color if i%2==0 else accent_color)
    
    # === COMPUTERS ===
    elif category == 'Computers':
        if 'Tablet' in sub_category:
            # Tablet
            draw.rounded_rectangle([(x+15, y+10), (x+w-15, y+h-10)], radius=8, fill=primary_color, outline=accent_color, width=2)
            draw.rounded_rectangle([(x+20, y+15), (x+w-20, y+h-15)], radius=5, fill=secondary_color)
        else:
            # Desktop PC - Tower
            draw.rounded_rectangle([(x+20, y+15), (x+w-20, y+h-15)], radius=5, fill=primary_color, outline=accent_color, width=2)
            # Front panel
            draw.ellipse([(cx-6, y+30), (cx+6, y+42)], fill=secondary_color, outline=accent_color)
            draw.rectangle([(cx-15, y+50), (cx+15, y+58)], fill=secondary_color)
    
    # === FURNITURE ===
    elif category == 'Furniture':
        # Podium/Stand
        draw.polygon([(x+20, y+h-10), (x+30, y+20), (x+w-30, y+20), (x+w-20, y+h-10)], fill=primary_color, outline=accent_color, width=2)
        draw.rectangle([(x+25, y+35), (x+w-25, y+50)], fill=secondary_color)
    
    # === DEFAULT/FALLBACK ===
    else:
        # Generic AV - Box with icon
        draw.rounded_rectangle([(x+15, y+15), (x+w-15, y+h-15)], radius=5, fill=primary_color, outline=accent_color, width=2)
        try:
            font_small = ImageFont.truetype("arial.ttf", 16)
        except:
            font_small = ImageFont.load_default()
        draw.text((cx-12, cy-8), "AV", fill='white', font=font_small)


def generate_product_info_card(product_name, brand, model, category, sub_category=None, size_inches=None):
    """
    Creates a professional visual info card for products with category-specific icons.
    
    Args:
        product_name: Full product name
        brand: Manufacturer brand
        model: Model number
        category: Product category
        sub_category: Product sub-category (optional, enhances icon accuracy)
        size_inches: Display size (for displays only)
    
    Returns:
        BytesIO object containing PNG image
    """
    
    # Image dimensions
    width, height = 400, 250
    
    # Create base image with gradient background
    img = Image.new('RGB', (width, height), color='#f8f9fa')
    draw = ImageDraw.Draw(img)
    
    # Create subtle gradient effect
    for i in range(height):
        r = 248 - int(i * 0.1)
        g = 249 - int(i * 0.1)
        b = 250 - int(i * 0.05)
        color = (max(230, r), max(235, g), max(240, b))
        draw.rectangle([(0, i), (width, i+1)], fill=color)
    
    # Load fonts (with fallback)
    try:
        font_brand = ImageFont.truetype("arial.ttf", 18)
        font_large = ImageFont.truetype("arial.ttf", 16)
        font_medium = ImageFont.truetype("arialbd.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_brand = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Category color coding
    category_colors = {
        'Displays': '#2563eb',
        'Video Conferencing': '#10b981',
        'Audio': '#f59e0b',
        'Control Systems': '#8b5cf6',
        'Signal Management': '#ec4899',
        'Cables & Connectivity': '#6b7280',
        'Infrastructure': '#ef4444',
        'Mounts': '#14b8a6',
        'Lighting': '#eab308',
        'Software & Services': '#06b6d4',
        'Networking': '#3b82f6',
        'Computers': '#84cc16',
        'Furniture': '#a855f7',
    }
    
    category_color = category_colors.get(category, '#6b7280')
    
    # Draw colored header bar
    draw.rectangle([(0, 0), (width, 45)], fill=category_color)
    
    # Add main border
    draw.rectangle([(0, 0), (width-1, height-1)], outline=category_color, width=3)
    
    # === BRAND/CATEGORY HEADER ===
    # Brand name (white text on colored header)
    draw.text((15, 12), brand.upper(), fill='white', font=font_brand)
    
    # Category badge (right side of header)
    category_text = category
    try:
        bbox = draw.textbbox((0, 0), category_text, font=font_small)
        cat_width = bbox[2] - bbox[0]
    except:
        cat_width = len(category_text) * 7
    
    badge_x = width - cat_width - 25
    draw.rounded_rectangle(
        [(badge_x, 10), (width - 10, 35)],
        radius=5,
        fill='white',
        outline='white'
    )
    draw.text((badge_x + 8, 15), category_text, fill=category_color, font=font_small)
    
    # === ICON SECTION (Left side) ===
    icon_size = 100
    icon_margin = 20
    icon_area = (icon_margin, 60, icon_size, icon_size)
    
    # Draw icon background
    icon_bg_x = icon_margin - 5
    icon_bg_y = 55
    draw.rounded_rectangle(
        [(icon_bg_x, icon_bg_y), (icon_bg_x + icon_size + 10, icon_bg_y + icon_size + 10)],
        radius=8,
        fill='white',
        outline=category_color,
        width=2
    )
    
    # Generate category-specific icon
    generate_category_icon(draw, icon_area, category, sub_category or '')
    
    # === PRODUCT INFO SECTION (Right side) ===
    info_x = icon_margin + icon_size + 30
    info_y = 60
    
    # Product name (truncated if too long)
    max_name_length = 35
    display_name = product_name[:max_name_length] + '...' if len(product_name) > max_name_length else product_name
    
    draw.text((info_x, info_y), display_name, fill='#1f2937', font=font_large)
    
    # Model number
    draw.text((info_x, info_y + 28), f"Model: {model}", fill='#4b5563', font=font_medium)
    
    # Sub-category (if available)
    if sub_category:
        draw.text((info_x, info_y + 50), f"Type: {sub_category}", fill='#6b7280', font=font_small)
    
    # Size info for displays
    if size_inches and category == 'Displays':
        draw.text((info_x, info_y + 70), f"Size: {size_inches}\"", fill='#6b7280', font=font_small)
    
    # === FOOTER ===
    footer_y = height - 35
    draw.line([(15, footer_y), (width - 15, footer_y)], fill=category_color, width=1)
    
    # Footer text
    draw.text((15, footer_y + 8), "Professional AV Equipment", fill='#9ca3af', font=font_small)
    
    # Convert to BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer


# Example usage function
def create_sample_cards():
    """
    Generates sample product cards for demonstration
    """
    sample_products = [
        {
            'name': 'UltraSharp Conference Display',
            'brand': 'Samsung',
            'model': 'QM85R-B',
            'category': 'Displays',
            'sub_category': 'Interactive Display',
            'size_inches': 85
        },
        {
            'name': 'RoomKit Pro PTZ Camera',
            'brand': 'Cisco',
            'model': 'CS-KIT-K9',
            'category': 'Video Conferencing',
            'sub_category': 'PTZ Camera'
        },
        {
            'name': 'Professional Ceiling Microphone Array',
            'brand': 'Shure',
            'model': 'MXA910',
            'category': 'Audio',
            'sub_category': 'Ceiling Microphone'
        },
        {
            'name': 'Digital Matrix Switcher 16x16',
            'brand': 'Crestron',
            'model': 'DM-MD16X16',
            'category': 'Signal Management',
            'sub_category': 'Matrix Switcher'
        },
        {
            'name': 'Touch Panel Controller',
            'brand': 'Extron',
            'model': 'TLP Pro 1025T',
            'category': 'Control Systems',
            'sub_category': 'Touch Panel'
        }
    ]
    
    images = []
    for product in sample_products:
        img_buffer = generate_product_info_card(
            product_name=product['name'],
            brand=product['brand'],
            model=product['model'],
            category=product['category'],
            sub_category=product.get('sub_category'),
            size_inches=product.get('size_inches')
        )
        images.append(img_buffer)
    
    return images


if __name__ == "__main__":
    # Test the generator
    print("Generating sample product cards...")
    cards = create_sample_cards()
    print(f"Generated {len(cards)} product cards successfully!")

    # Test the new function
    test_names = [
        "Samsung 85-inch 4K Display",
        "LG 75\" Commercial Screen",
        "Sony 65in Bravia",
        "NEC Display 98' '",
        "Generic 55 inch monitor",
        "Projector Screen (120-inch)"
    ]
    for name in test_names:
        size = extract_display_size(name)
        print(f"'{name}' -> Size: {size}")
