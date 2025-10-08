# components/excel_generator.py
# PRODUCTION VERSION - Matches AllWave AV company format

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter
from io import BytesIO
import re
from datetime import datetime

# Import the image generator
try:
    from components.product_image_generator import generate_product_info_card, extract_display_size
except ImportError:
    # Fallback if import fails
    def generate_product_info_card(*args, **kwargs):
        return None
    def extract_display_size(name):
        return None


# ==================== STYLE DEFINITIONS ====================
def _define_styles():
    """Defines all necessary styles for the professional report."""
    thin_border_side = Side(style='thin')
    thin_border = Border(
        left=thin_border_side, 
        right=thin_border_side, 
        top=thin_border_side, 
        bottom=thin_border_side
    )
    
    return {
        "header_green_fill": PatternFill(start_color="A9D08E", end_color="A9D08E", fill_type="solid"),
        "header_light_green_fill": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        "table_header_blue_fill": PatternFill(start_color="9BC2E6", end_color="9BC2E6", fill_type="solid"),
        "boq_category_fill": PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"),
        "black_bold_font": Font(color="000000", bold=True),
        "bold_font": Font(bold=True),
        "thin_border": thin_border,
        "currency_format": "₹ #,##0.00"
    }


# ==================== HEADER WITH LOGOS ====================
def _add_image_to_cell(sheet, image_path, cell, height_px):
    """Adds a logo to a cell, preserving aspect ratio."""
    try:
        img = ExcelImage(image_path)
        img.height = height_px
        img.width = (img.width / img.height) * height_px
        sheet.add_image(img, cell)
    except FileNotFoundError:
        # Graceful fallback - just put text
        sheet[cell] = f"Logo: {image_path}"
    except Exception as e:
        sheet[cell] = "Logo"


def _create_sheet_header(sheet):
    """Creates the standard header with four logos."""
    sheet.row_dimensions[1].height = 50
    sheet.row_dimensions[2].height = 50

    # Merge cells for logo placement
    sheet.merge_cells('A1:C2')
    sheet.merge_cells('D1:F2')
    sheet.merge_cells('M1:N2')
    sheet.merge_cells('O1:P2')

    # Add logos (will fail gracefully if files don't exist)
    _add_image_to_cell(sheet, 'assets/company_logo.png', 'A1', 95)
    _add_image_to_cell(sheet, 'assets/crestron_logo.png', 'D1', 95)
    _add_image_to_cell(sheet, 'assets/iso_logo.png', 'M1', 95)
    _add_image_to_cell(sheet, 'assets/avixa_logo.png', 'O1', 95)


# ==================== VERSION CONTROL SHEET ====================
def _add_version_control_sheet(workbook, project_details, styles):
    """Creates the Version Control & Contact Details sheet."""
    sheet = workbook.create_sheet(title="Version Control", index=0)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False

    # Set column widths
    sheet.column_dimensions['A'].width = 25
    sheet.column_dimensions['B'].width = 25
    sheet.column_dimensions['D'].width = 5
    sheet.column_dimensions['E'].width = 25
    sheet.column_dimensions['F'].width = 25
    
    # === VERSION CONTROL TABLE ===
    sheet.merge_cells('A3:B3')
    vc_header = sheet['A3']
    vc_header.value = "Version"
    vc_header.fill = styles['header_green_fill']
    vc_header.font = styles['black_bold_font']
    vc_header.alignment = Alignment(horizontal='center')
    vc_header.border = styles['thin_border']
    sheet['B3'].border = styles['thin_border']

    vc_data = [
        ("Date of First Draft", datetime.now().strftime("%d-%b-%Y")),
        ("Date of Final Draft", ""),
        ("Version No.", "1.0"),
        ("Published Date", datetime.now().strftime("%d-%b-%Y"))
    ]
    
    for i, (label, value) in enumerate(vc_data):
        row = i + 4
        for col_letter in ['A', 'B']:
            sheet[f'{col_letter}{row}'].border = styles['thin_border']
        sheet[f'A{row}'].value = label
        sheet[f'A{row}'].fill = styles['header_light_green_fill']
        sheet[f'B{row}'].value = value

    # === CONTACT DETAILS TABLE ===
    sheet.merge_cells('E3:F3')
    cd_header = sheet['E3']
    cd_header.value = "Contact Details"
    cd_header.fill = styles['header_green_fill']
    cd_header.font = styles['black_bold_font']
    cd_header.alignment = Alignment(horizontal='center')
    cd_header.border = styles['thin_border']
    sheet['F3'].border = styles['thin_border']

    contact_data = [
        ("Design Engineer", project_details.get("Design Engineer", "")),
        ("Account Manager", project_details.get("Account Manager", "")),
        ("Client Name", project_details.get("Client Name", "")),
        ("Key Client Personnel", project_details.get("Key Client Personnel", "")),
        ("Location", project_details.get("Location", "")),
        ("Key Comments for this version", project_details.get("Key Comments", ""))
    ]
    
    for i, (label, value) in enumerate(contact_data):
        row = i + 4
        for col_letter in ['E', 'F']:
            sheet[f'{col_letter}{row}'].border = styles['thin_border']
        sheet[f'E{row}'].value = label
        sheet[f'E{row}'].fill = styles['header_light_green_fill']
        sheet[f'F{row}'].value = value
        if label == "Key Comments for this version":
            sheet.row_dimensions[row].height = 40
            sheet[f'F{row}'].alignment = Alignment(wrap_text=True, vertical='top')


# ==================== TERMS & CONDITIONS SHEET ====================
def _add_terms_and_conditions_sheet(workbook, styles):
    """
    Creates comprehensive Terms & Conditions sheet based on AllWave AV standard format.
    """
    sheet = workbook.create_sheet(title="Terms & Conditions")
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False
    
    # Set column widths
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        sheet.column_dimensions[col].width = 20
    
    row_cursor = 4
    
    # === MAIN TITLE ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    title_cell = sheet[f'A{row_cursor}']
    title_cell.value = "Commercial Terms & Conditions"
    title_cell.font = Font(size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="2563eb", end_color="2563eb", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    title_cell.border = styles['thin_border']
    sheet.row_dimensions[row_cursor].height = 25
    row_cursor += 2
    
    # === SECTION A: DELIVERY & INSTALLATION ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "A. Delivery, Installations & Site Schedule"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.alignment = Alignment(horizontal='left')
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    delivery_terms = [
        "All Wave AV Systems undertakes to ensure its best efforts to complete the assignment within the shortest timelines possible.",
        "",
        "Project Schedule:",
        "• Week 1-3: All Wave AV Systems Design & Procurement / Client Site Preparations",
        "• Implementation: Within 12 weeks of advance payment receipt",
        "",
        "Delivery Terms:",
        "• Duty Paid INR: Free delivery at site",
        "• All deliveries within 6-8 weeks of commercially clear Purchase Order",
        "• Equipment delivered in phased manner (max 3 shipments)",
        "",
        "Note: Delay in advance payment may alter project schedule. Beyond 12 weeks delay due to site issues: ₹8,000 + GST per day charge applies."
    ]
    
    for term in delivery_terms:
        sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = term
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = styles['thin_border']
        if term and not term.startswith('•'):
            cell.font = styles['bold_font']
            sheet.row_dimensions[row_cursor].height = 20
        else:
            sheet.row_dimensions[row_cursor].height = 15
        row_cursor += 1
    
    row_cursor += 1
    
    # === SECTION B: PAYMENT TERMS ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "B. Payment Terms"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    payment_terms = [
        "Schedule of Payment:",
        "• Equipment & Materials: 20% Advance with PO",
        "• Installation & Commissioning: Against system installation",
        "• Balance Payment: Within 30 days of ATP sign-off"
    ]
    
    for term in payment_terms:
        sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = term
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = styles['thin_border']
        if not term.startswith('•'):
            cell.font = styles['bold_font']
        sheet.row_dimensions[row_cursor].height = 15
        row_cursor += 1
    
    row_cursor += 1
    
    # === SECTION C: VALIDITY ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "C. Offer Validity"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    cell = sheet[f'A{row_cursor}']
    cell.value = "Offer Valid for 30 Days from date of quotation"
    cell.alignment = Alignment(wrap_text=True)
    cell.border = styles['thin_border']
    row_cursor += 2
    
    # === SECTION D: PURCHASE ORDER DETAILS ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "D. Placing a Purchase Order"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    po_details = [
        "Order should be placed on:",
        "All Wave AV Systems Pvt. Ltd.",
        "420A Shah & Nahar Industrial Estate,",
        "Lower Parel West, Mumbai 400013, INDIA",
        "",
        "GST No: [To be provided]",
        "PAN No: [To be provided]"
    ]
    
    for detail in po_details:
        sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = detail
        cell.border = styles['thin_border']
        if detail and not detail.startswith(' '):
            cell.font = styles['bold_font']
        row_cursor += 1
    
    row_cursor += 1
    
    # === SECTION E: CABLE ESTIMATES ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "E. Cable Estimates"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    cable_terms = [
        "Provisional cable estimate provided. Actual consumption may vary based on finalized layouts.",
        "Invoicing based on actual consumption: Physical measurement + 10% (for bends, curves, termination, wastage)"
    ]
    
    for term in cable_terms:
        sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = term
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = styles['thin_border']
        sheet.row_dimensions[row_cursor].height = 20
        row_cursor += 1
    
    row_cursor += 1
    
    # === SECTION F: ORDER CHANGES ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "F. Order Changes"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    change_terms = [
        "All Wave AV Systems accommodates scope changes as needed.",
        "Changes may require additional resources/time - separate Change Order will be issued.",
        "All Change Orders must be in writing with adjusted price, schedule, and acceptance criteria."
    ]
    
    for term in change_terms:
        sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = term
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = styles['thin_border']
        sheet.row_dimensions[row_cursor].height = 20
        row_cursor += 1
    
    row_cursor += 1
    
    # === SECTION G: CANCELLATION FEES ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "G. Restocking / Cancellation Fees"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    cell = sheet[f'A{row_cursor}']
    cell.value = "Cancellation may involve charges up to 50% restocking/cancellation fees + shipping costs"
    cell.alignment = Alignment(wrap_text=True)
    cell.border = styles['thin_border']
    sheet.row_dimensions[row_cursor].height = 20
    row_cursor += 2
    
    # === SECTION H: WARRANTY ===
    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
    section_cell = sheet[f'A{row_cursor}']
    section_cell.value = "H. Warranty"
    section_cell.fill = styles['table_header_blue_fill']
    section_cell.font = styles['bold_font']
    section_cell.border = styles['thin_border']
    row_cursor += 1
    
    warranty_terms = [
        "All Wave AV Systems provides:",
        "• Comprehensive 12-month warranty on all equipment from handover date",
        "• Limited warranty on consumables (Projector lamps: 450 hours or 90 days, whichever earlier)",
        "• Extended warranty available via separate Maintenance Contract",
        "",
        "Warranty exclusions:",
        "• Power-related damage (equipment must use stabilized power/online UPS)",
        "• Accident, misuse, neglect, alteration, or component substitution",
        "• Fire, flood, weather exposure, force majeure events"
    ]
    
    for term in warranty_terms:
        sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = term
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = styles['thin_border']
        if term and not term.startswith('•'):
            cell.font = styles['bold_font']
            sheet.row_dimensions[row_cursor].height = 15
        else:
            sheet.row_dimensions[row_cursor].height = 15
        row_cursor += 1


# ==================== ROOM BOQ SHEET ====================
def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """
    Creates detailed BOQ sheet with PRODUCT IMAGES and TOP 3 REASONS columns.
    """
    _create_sheet_header(sheet)
    
    # === ROOM INFO SECTION ===
    info_data = [
        ("Room Name / Room Type", room_name),
        ("Floor", "-"),
        ("Number of Seats", "-"),
        ("Number of Rooms", "-")
    ]
    
    for i, (label, value) in enumerate(info_data):
        row = i + 3
        sheet[f'A{row}'].value = label
        sheet[f'A{row}'].font = styles['bold_font']
        sheet.merge_cells(f'B{row}:C{row}')
        sheet[f'B{row}'].value = value
        for col in ['A', 'B', 'C']:
            sheet[f'{col}{row}'].border = styles['thin_border']

    sheet.append([])  # Spacer row

    # === TABLE HEADERS ===
    headers1 = [
        'Sr. No.', 
        'Reference Image',  # NEW COLUMN
        'Description of Goods / Services', 
        'Make', 
        'Model No.', 
        'Qty.',
        'Unit Rate (INR)', 
        'Total', 
        'Warranty', 
        'Lead Time (Days)',
        'SGST\n( In Maharashtra)', None, 
        'CGST\n( In Maharashtra)', None,
        'Total (TAX)', 
        'Total Amount (INR)', 
        'Top 3 Reasons'  # NEW COLUMN
    ]
    
    headers2 = [
        None, None, None, None, None, None, None, None, None, None,
        'Rate', 'Amt', 'Rate', 'Amt', None, None, None
    ]
    
    sheet.append(headers1)
    sheet.append(headers2)
    header_start_row = sheet.max_row - 1

    # Merge GST header cells
    sheet.merge_cells(f'K{header_start_row}:L{header_start_row}')
    sheet.merge_cells(f'M{header_start_row}:N{header_start_row}')

    # Style headers
    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row):
        for cell in row:
            if cell.value is not None:
                cell.fill = styles["table_header_blue_fill"]
                cell.font = styles['bold_font']
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = styles['thin_border']
    
    # === GROUP ITEMS BY CATEGORY ===
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General AV')
        grouped_items.setdefault(cat, []).append(item)

    total_before_gst_hardware = 0
    total_gst_hardware = 0
    item_s_no = 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    # === ADD HARDWARE ITEMS ===
    for i, (category, cat_items) in enumerate(grouped_items.items()):
        # Category header row
        sheet.append([category_letters[i], category])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(f'B{cat_row_idx}:Q{cat_row_idx}')  # Extended to include new column
        for cell in sheet[cat_row_idx]:
            cell.fill = styles['boq_category_fill']
            cell.font = styles['bold_font']
            cell.border = styles['thin_border']
        
        # Individual items
        for item in cat_items:
            unit_price_inr = item.get('price', 0) * usd_to_inr_rate
            subtotal = unit_price_inr * item.get('quantity', 1)
            gst_rate = item.get('gst_rate', gst_rates.get('Electronics', 18))
            sgst_rate = cgst_rate = gst_rate / 2
            sgst_amount = subtotal * (sgst_rate / 100)
            cgst_amount = subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            total_with_gst = subtotal + total_tax
            
            total_before_gst_hardware += subtotal
            total_gst_hardware += total_tax

            # === EXTRACT TOP 3 REASONS ===
            justification = item.get('justification', '')
            # Try to parse numbered list format
            reasons = []
            for line in justification.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                    # Remove numbering/bullets
                    clean_line = re.sub(r'^[\d\.\)•\-]\s*', '', line).strip()
                    if clean_line:
                        reasons.append(clean_line)
            
            # If we didn't get structured reasons, use the full justification
            if not reasons:
                reasons = [justification] if justification else ["Standard component for this room type"]
            
            # Format as "1. Reason\n2. Reason\n3. Reason"
            top_3_reasons = '\n'.join([f"{idx+1}. {reason}" for idx, reason in enumerate(reasons[:3])])

            # Build row data
            row_data = [
                item_s_no,
                '',  # Image column (will be populated separately)
                item.get('name', ''),
                item.get('brand', 'Unknown'),
                item.get('model_number', 'N/A'),
                item.get('quantity', 1),
                unit_price_inr,
                subtotal,
                item.get('warranty', 'Not Specified'),
                item.get('lead_time_days', 14),
                f"{sgst_rate}%", sgst_amount,
                f"{cgst_rate}%", cgst_amount,
                total_tax, 
                total_with_gst,
                top_3_reasons  # NEW COLUMN DATA
            ]
            
            sheet.append(row_data)
            current_row = sheet.max_row
            
            # === ADD PRODUCT IMAGE ===
            try:
                # Extract display size if applicable
                size_inches = None
                if item.get('category') == 'Displays':
                    size_inches = extract_display_size(item.get('name', ''))
                
                # Generate product info card
                img_buffer = generate_product_info_card(
                    product_name=item.get('name', 'Unknown Product'),
                    brand=item.get('brand', 'N/A'),
                    model=item.get('model_number', 'N/A'),
                    category=item.get('category', 'General AV'),
                    size_inches=size_inches
                )
                
                if img_buffer:
                    excel_img = ExcelImage(img_buffer)
                    # Scale to fit Excel cell
                    excel_img.width = 150
                    excel_img.height = 100
                    
                    # Add to 'B' column (Reference Image)
                    sheet.add_image(excel_img, f'B{current_row}')
                    
                    # Increase row height to accommodate image
                    sheet.row_dimensions[current_row].height = 75
            except Exception as e:
                # Fail gracefully - don't break BOQ generation
                print(f"Could not add product image for {item.get('name', 'Unknown')}: {e}")
            
            item_s_no += 1

    # === ADD SERVICES (Installation, Warranty, PM) ===
    services = [
        ("Installation & Commissioning", 0.15),
        ("System Warranty (3 Years)", 0.05),
        ("Project Management", 0.10)
    ]
    services_letter = chr(ord('A') + len(grouped_items))
    services_gst_rate = gst_rates.get('Services', 18)

    if services and total_before_gst_hardware > 0:
        sheet.append([services_letter, "Services"])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(f'B{cat_row_idx}:Q{cat_row_idx}')
        for cell in sheet[cat_row_idx]:
            cell.fill = styles['boq_category_fill']
            cell.font = styles['bold_font']
            cell.border = styles['thin_border']

        for service_name, percentage in services:
            service_amount_inr = total_before_gst_hardware * percentage
            sgst_rate = cgst_rate = services_gst_rate / 2
            service_sgst = service_amount_inr * (sgst_rate / 100)
            service_cgst = service_amount_inr * (cgst_rate / 100)
            service_total_tax = service_sgst + service_cgst
            service_total = service_amount_inr + service_total_tax
            
            service_reasons = {
                "Installation & Commissioning": "1. Professional on-site installation\n2. System configuration and testing\n3. Integration with existing infrastructure",
                "System Warranty (3 Years)": "1. Comprehensive parts and labor coverage\n2. Priority support and rapid response\n3. Regular maintenance and health checks",
                "Project Management": "1. Dedicated project coordinator\n2. Timeline management and progress tracking\n3. Quality assurance and documentation"
            }
            
            row_data = [
                item_s_no, 
                '',  # No image for services
                service_name, 
                "AllWave AV", 
                "Professional Service", 
                1,
                service_amount_inr, 
                service_amount_inr, 
                "As per terms", 
                "N/A",
                f"{sgst_rate}%", service_sgst, 
                f"{cgst_rate}%", service_cgst,
                service_total_tax, 
                service_total,
                service_reasons.get(service_name, "Standard professional service")
            ]
            sheet.append(row_data)
            item_s_no += 1
    
    # === SET COLUMN WIDTHS ===
    column_widths = {
        'A': 8,   # Sr. No
        'B': 22,  # Reference Image (wider for image)
        'C': 45,  # Description
        'D': 20,  # Make
        'E': 30,  # Model No
        'F': 6,   # Qty
        'G': 15,  # Unit Rate
        'H': 15,  # Total
        'I': 15,  # Warranty
        'J': 15,  # Lead Time
        'K': 10,  # SGST Rate
        'L': 15,  # SGST Amt
        'M': 10,  # CGST Rate
        'N': 15,  # CGST Amt
        'O': 15,  # Total Tax
        'P': 18,  # Total Amount
        'Q': 50   # Top 3 Reasons (extra wide)
    }
    
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width
    
    # === APPLY BORDERS AND NUMBER FORMATS ===
    for row in sheet.iter_rows(min_row=header_start_row + 2):
        for cell in row:
            # Currency formatting for price columns
            if cell.column >= 7 and cell.column <= 16 and isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            
            cell.border = styles['thin_border']
            
            # Center align specific columns
            if cell.column in [1, 6]:  # Sr. No and Qty
                cell.alignment = Alignment(horizontal='center', vertical='top')
            elif cell.column == 17:  # Top 3 Reasons - wrap text
                cell.alignment = Alignment(wrap_text=True, vertical='top')
            else:
                cell.alignment = Alignment(vertical='top')


# ==================== MAIN ENTRY POINT ====================
def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """
    Main function to generate the complete Excel workbook.
    
    Args:
        project_details: Dict containing project metadata
        rooms_data: List of room dicts, each with 'name' and 'boq_items'
        usd_to_inr_rate: Exchange rate for currency conversion
    
    Returns:
        bytes: Excel file as byte array
    """
    workbook = openpyxl.Workbook()
    styles = _define_styles()

    # === SHEET 1: VERSION CONTROL ===
    _add_version_control_sheet(workbook, project_details, styles)
    
    # === SHEET 2: TERMS & CONDITIONS ===
    _add_terms_and_conditions_sheet(workbook, styles)
    
    # === SHEET 3+: ROOM BOQ SHEETS ===
    for room in rooms_data:
        if room.get('boq_items'):
            # Calculate room totals for summary
            subtotal = sum(
                item.get('price', 0) * item.get('quantity', 1) 
                for item in room['boq_items']
            ) * usd_to_inr_rate
            
            services_total = subtotal * 0.30  # 30% for services
            total_without_gst = subtotal + services_total
            
            # GST calculation
            gst_electronics = sum(
                (item.get('price', 0) * item.get('quantity', 1) * usd_to_inr_rate) * 
                (item.get('gst_rate', 18) / 100)
                for item in room['boq_items']
            )
            gst_services = services_total * (project_details.get('gst_rates', {}).get('Services', 18) / 100)
            total_gst = gst_electronics + gst_services
            
            room['subtotal'] = total_without_gst
            room['gst'] = total_gst
            room['total'] = total_without_gst + total_gst

            # Create safe sheet name (Excel has 31 char limit)
            safe_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:25]
            room_sheet = workbook.create_sheet(title=f"BOQ - {safe_name}")
            
            _populate_room_boq_sheet(
                room_sheet, 
                room['boq_items'], 
                room['name'], 
                styles,
                usd_to_inr_rate, 
                project_details.get('gst_rates', {})
            )

    # === CLEANUP ===
    # Remove default sheet
    if "Sheet" in workbook.sheetnames:
        del workbook["Sheet"]
    
    # Set active sheet to Version Control
    workbook.active = workbook["Version Control"]

    # === SAVE TO BYTES ===
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer.getvalue()
