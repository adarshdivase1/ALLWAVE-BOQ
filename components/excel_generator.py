# components/excel_generator.py

import openpyxl
import re
import requests
import io
from datetime import datetime
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from PIL import Image as PILImage
from io import BytesIO

# --- Currency Conversion (scoped for this module) ---
def get_usd_to_inr_rate():
    """Centralized currency rate for Excel generation."""
    try:
        # Replace with a real API for production
        return 83.5
    except:
        return 83.5

def convert_currency(amount_usd, to_currency="INR"):
    """Convert USD amount to specified currency."""
    if to_currency == "INR":
        rate = get_usd_to_inr_rate()
        return amount_usd * rate
    return amount_usd

# --- Styling and Image Handling ---
def _define_styles():
    """Defines reusable styles for the Excel sheet."""
    return {
        "header": Font(size=16, bold=True, color="FFFFFF"),
        "header_fill": PatternFill(start_color="002060", end_color="002060", fill_type="solid"),
        "table_header": Font(bold=True, color="FFFFFF"),
        "table_header_fill": PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"),
        "bold": Font(bold=True),
        "group_header_fill": PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid"),
        "total_fill": PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"),
        "grand_total_font": Font(size=12, bold=True, color="FFFFFF"),
        "grand_total_fill": PatternFill(start_color="002060", end_color="002060", fill_type="solid"),
        "currency_format": "₹ #,##0",
        "thin_border": Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    }

def _add_product_image_to_excel(sheet, row_num, image_url, column='P'):
    """Add product image to Excel cell if URL is valid."""
    if not image_url or not isinstance(image_url, str) or image_url.strip() == '':
        return

    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            pil_image = PILImage.open(io.BytesIO(response.content))
            pil_image.thumbnail((100, 100), PILImage.Resampling.LANCZOS)

            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            excel_img = ExcelImage(img_buffer)
            excel_img.width = 80
            excel_img.height = 80

            sheet.add_image(excel_img, f'{column}{row_num}')
            sheet.row_dimensions[row_num].height = 60

    except Exception as e:
        print(f"Failed to add image {image_url}: {e}")
        sheet[f'{column}{row_num}'] = "Image unavailable"

# --- Sheet Population ---
def _populate_company_boq_sheet(sheet, items, room_details, styles, gst_rates):
    """Helper function to populate a single Excel sheet with BOQ data."""
    room_name = room_details.get('name', 'N/A')
    
    # Static Headers
    sheet.merge_cells('A3:P3')
    header_cell = sheet['A3']
    header_cell.value = "All Wave AV Systems Pvt. Ltd."
    header_cell.font = styles["header"]
    header_cell.fill = styles["header_fill"]
    header_cell.alignment = Alignment(horizontal='center', vertical='center')

    # Project Info
    sheet['C5'] = "Room Name / Room Type"
    sheet['E5'] = room_name
    sheet['C6'] = "Floor"
    sheet['E6'] = room_details.get('floor', 'TBD')
    sheet['C7'] = "Number of Seats"
    sheet['E7'] = room_details.get('seats', 'TBD')
    sheet['C8'] = "Number of Rooms"
    sheet['E8'] = 1

    # Table Headers
    headers1 = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST\n( In Maharastra)', None, 'CGST\n( In Maharastra)', None, 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]
    sheet.append(headers1)
    sheet.append(headers2)
    header_start_row = sheet.max_row - 1

    sheet.merge_cells(start_row=header_start_row, start_column=9, end_row=header_start_row, end_column=10)
    sheet.merge_cells(start_row=header_start_row, start_column=11, end_row=header_start_row, end_column=12)

    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row, min_col=1, max_col=len(headers1)):
        for cell in row:
            cell.font = styles["table_header"]
            cell.fill = styles["table_header_fill"]
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items: grouped_items[cat] = []
        grouped_items[cat].append(item)

    total_before_gst_hardware, total_gst_hardware, item_s_no = 0, 0, 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    for i, (category, cat_items) in enumerate(grouped_items.items()):
        cat_header_row = [f"{category_letters[i]}", category]
        sheet.append(cat_header_row)
        cat_row_idx = sheet.max_row
        sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=16)
        sheet[f'A{cat_row_idx}'].font = styles['bold']
        sheet[f'B{cat_row_idx}'].font = styles['bold']
        for col_letter in 'ABCDEFGHIJKLMNOP':
            sheet[f'{col_letter}{cat_row_idx}'].fill = styles['group_header_fill']

        for item in cat_items:
            unit_price_inr = convert_currency(item.get('price', 0), 'INR')
            subtotal = unit_price_inr * item.get('quantity', 1)
            gst_rate = item.get('gst_rate', gst_rates.get('Electronics', 18))
            sgst_rate, cgst_rate = gst_rate / 2, gst_rate / 2
            sgst_amount, cgst_amount = subtotal * (sgst_rate / 100), subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            total_with_gst = subtotal + total_tax
            total_before_gst_hardware += subtotal
            total_gst_hardware += total_tax

            row_data = [item_s_no, None, item.get('specifications', item.get('name', '')), item.get('brand', 'Unknown'), item.get('name', 'Unknown'), item.get('quantity', 1), unit_price_inr, subtotal, f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", cgst_amount, total_tax, total_with_gst, item.get('justification', ''), None]
            sheet.append(row_data)
            _add_product_image_to_excel(sheet, sheet.max_row, item.get('image_url', ''), 'P')
            item_s_no += 1
    
    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    services_letter = chr(ord('A') + len(grouped_items))
    sheet.append([services_letter, "Services"])
    cat_row_idx = sheet.max_row
    sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=16)
    sheet[f'A{cat_row_idx}'].font = styles['bold']
    sheet[f'B{cat_row_idx}'].font = styles['bold']
    for col_letter in 'ABCDEFGHIJKLMNOP':
        sheet[f'{col_letter}{cat_row_idx}'].fill = styles['group_header_fill']
    
    total_before_gst_services, total_gst_services = 0, 0
    services_gst_rate = gst_rates.get('Services', 18)
    for name, percentage in services:
        amount_inr = total_before_gst_hardware * percentage
        sgst_rate, cgst_rate = services_gst_rate / 2, services_gst_rate / 2
        sgst, cgst = amount_inr * (sgst_rate / 100), amount_inr * (cgst_rate / 100)
        total_tax, total = sgst + cgst, amount_inr + sgst + cgst
        total_before_gst_services += amount_inr
        total_gst_services += total_tax
        sheet.append([item_s_no, None, "Certified professional service for system deployment", "AllWave AV", name, 1, amount_inr, amount_inr, f"{sgst_rate}%", sgst, f"{cgst_rate}%", cgst, total_tax, total, "As per standard terms", ""])
        item_s_no += 1

    sheet.append([])
    hardware_total_row = ["", "Total for Hardware (A)", "", "", "", "", "", total_before_gst_hardware, "", "", "", "", total_gst_hardware, total_before_gst_hardware + total_gst_hardware]
    sheet.append(hardware_total_row)
    for cell in sheet[sheet.max_row]: cell.font = styles['bold']; cell.fill = styles['total_fill']
    services_total_row = ["", f"Total for Services ({services_letter})", "", "", "", "", "", total_before_gst_services, "", "", "", "", total_gst_services, total_before_gst_services + total_gst_services]
    sheet.append(services_total_row)
    for cell in sheet[sheet.max_row]: cell.font = styles['bold']; cell.fill = styles['total_fill']
    
    grand_total = (total_before_gst_hardware + total_gst_hardware) + (total_before_gst_services + total_gst_services)
    sheet.append([])
    grand_total_row_idx = sheet.max_row + 1
    sheet[f'M{grand_total_row_idx}'], sheet[f'N{grand_total_row_idx}'] = "Grand Total (INR)", grand_total
    for cell_id in [f'M{grand_total_row_idx}', f'N{grand_total_row_idx}']:
        sheet[cell_id].font = styles["grand_total_font"]; sheet[cell_id].fill = styles["grand_total_fill"]; sheet[cell_id].alignment = Alignment(horizontal='center')

    column_widths = {'A': 8, 'B': 35, 'C': 45, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 10, 'J': 15, 'K': 10, 'L': 15, 'M': 15, 'N': 18, 'O': 40, 'P': 20}
    for col, width in column_widths.items(): sheet.column_dimensions[col].width = width
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            if cell.value is not None: cell.border = styles['thin_border']
            if 7 <= cell.column <= 14: cell.number_format = styles['currency_format']
    
    return total_before_gst_hardware + total_before_gst_services, total_gst_hardware + total_gst_services, grand_total

def add_proposal_summary_sheet(workbook, rooms_data, styles):
    """Adds the Proposal Summary sheet."""
    sheet = workbook.create_sheet("Proposal Summary")
    sheet.merge_cells('A3:G3')
    header_cell = sheet['A3']
    header_cell.value, header_cell.font, header_cell.fill, header_cell.alignment = "Proposal Summary", styles["header"], styles["header_fill"], Alignment(horizontal='center')
    
    headers = ["Sr. No", "Description", "Total Qty", "Rate w/o TAX", "Amount w/o TAX", "Total TAX Amount", "Amount with Tax"]
    sheet.append(headers)
    for cell in sheet[sheet.max_row]: cell.font, cell.fill = styles["bold"], styles["group_header_fill"]

    grand_total_with_tax = 0
    for i, room in enumerate(rooms_data, 1):
        if room.get('boq_items'):
            subtotal, gst, total = room.get('subtotal', 0), room.get('gst', 0), room.get('total', 0)
            grand_total_with_tax += total
            sheet.append([i, room['name'], 1, subtotal, subtotal, gst, total])

    total_row = sheet.max_row + 2
    sheet[f'F{total_row}'], sheet[f'G{total_row}'] = "GRAND TOTAL (INR)", grand_total_with_tax
    for cell_id in [f'F{total_row}', f'G{total_row}']:
        sheet[cell_id].font, sheet[cell_id].fill = styles["grand_total_font"], styles["grand_total_fill"]
    for col in ['D', 'E', 'F', 'G']:
        for cell in sheet[col]: cell.number_format = styles['currency_format']

def add_scope_of_work_sheet(workbook):
    """Adds the static Scope of Work sheet."""
    sheet = workbook.create_sheet("Scope of Work")
    sheet['A1'].value, sheet['A1'].font = "Scope of Work", Font(size=16, bold=True)
    scope_items = ["Site Coordination and Prerequisites Clearance.", "Detailed schematic drawings according to the design.", "Supply of all equipment as per the BOQ.", "Installation of equipment including mounting, racking, and cabling.", "System programming and configuration.", "Testing and commissioning of the complete system.", "User training and handover.", "As-built documentation and warranty support."]
    for i, item in enumerate(scope_items, 3):
        sheet[f'A{i}'] = f"{i-2}. {item}"

def add_version_control_sheet(workbook, project_details, client_name):
    """Adds the Version Control sheet."""
    sheet = workbook.create_sheet("Version Control")
    sheet['B4'], sheet['E4'] = "Version Control", "Contact Details"
    sheet['B6'], sheet['C6'] = "Date of First Draft", datetime.now().strftime('%Y-%m-%d')
    sheet['E6'] = "Design Engineer"
    sheet['B8'], sheet['C8'] = "Project Name", project_details.get('project_name', 'N/A')
    sheet['E8'], sheet['F8'] = "Client Name", client_name
    sheet['B10'], sheet['C10'] = "Version No.", "1.0"

def add_terms_conditions_sheet(workbook):
    """Add Terms & Conditions sheet with standard clauses."""
    sheet = workbook.create_sheet("Terms & Conditions")
    terms_content = [("COMMERCIAL TERMS & CONDITIONS", "header"), ("", ""), ("1. VALIDITY", "section"), ("This quotation is valid for 30 days from the date of issue.", "text"), ("", ""), ("2. PAYMENT TERMS", "section"), ("• 30% advance payment with purchase order", "text"), ("• 40% payment on material delivery at site", "text"), ("• 30% payment on completion of installation & commissioning", "text"), ("", ""), ("3. DELIVERY & INSTALLATION", "section"), ("• Delivery: 4-6 weeks from receipt of advance payment", "text"), ("• Installation will be completed within 2 weeks of delivery", "text"), ("• Site readiness as per AllWave AV specifications required", "text"), ("", ""), ("4. WARRANTY", "section"), ("• 3 years comprehensive warranty on all equipment", "text"), ("• On-site support within 24-48 hours", "text"), ("• Remote support available 24x7", "text"), ("", ""), ("5. SCOPE EXCLUSIONS", "section"), ("• Civil work, false ceiling, electrical work", "text"), ("• Furniture & interior modifications", "text"), ("• Network infrastructure beyond AV requirements", "text"), ("• Permits & approvals from authorities", "text")]
    for i, (content, style_type) in enumerate(terms_content, 1):
        cell = sheet[f'A{i}']
        cell.value = content
        if style_type == "header": cell.font, cell.fill, cell.alignment = Font(size=16, bold=True, color="FFFFFF"), PatternFill(start_color="002060", fill_type="solid"), Alignment(horizontal='center')
        elif style_type == "section": cell.font = Font(size=12, bold=True, color="002060")
        else: cell.font = Font(size=11)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
    sheet.column_dimensions['A'].width = 80

# --- Main Entry Point ---
def generate_company_excel(project_details, rooms_data, gst_rates):
    """Generate Excel file in the new company standard format."""
    if not rooms_data: return None
    workbook = openpyxl.Workbook()
    styles = _define_styles()
    client_name = project_details.get('client_name', 'Valued Client')

    for room in rooms_data:
        if room.get('boq_items'):
            safe_room_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:30]
            room_sheet = workbook.create_sheet(title=safe_room_name)
            subtotal, gst, total = _populate_company_boq_sheet(room_sheet, room['boq_items'], room, styles, gst_rates)
            room['subtotal'], room['gst'], room['total'] = subtotal, gst, total

    add_proposal_summary_sheet(workbook, rooms_data, styles)
    add_scope_of_work_sheet(workbook)
    add_version_control_sheet(workbook, project_details, client_name)
    add_terms_conditions_sheet(workbook)
    
    if "Sheet" in workbook.sheetnames and len(workbook.sheetnames) > 1:
        del workbook["Sheet"]

    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()
