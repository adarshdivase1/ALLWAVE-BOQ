# components/excel_generator.py

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from io import BytesIO
import re
from datetime import datetime

# --- Style Definitions ---
def _define_styles():
    """Defines all necessary styles to match the company's PDF format."""
    thin_border_side = Side(style='thin', color="000000")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    return {
        "header_green_fill": PatternFill(start_color="A9D08E", end_color="A9D08E", fill_type="solid"),
        "table_header_blue_fill": PatternFill(start_color="9BC2E6", end_color="9BC2E6", fill_type="solid"),
        "boq_category_fill": PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"),
        "bold_font": Font(bold=True, color="000000"),
        "white_bold_font": Font(bold=True, color="FFFFFF"),
        "thin_border": thin_border,
        "currency_format": "₹ #,##0.00"
    }

# --- Header & Image Helpers ---
def _add_image_to_cell(sheet, image_path, cell, height_px):
    """Adds a logo to a cell, preserving aspect ratio."""
    try:
        img = ExcelImage(image_path)
        img.height = height_px
        img.width = (img.width / img.height) * height_px
        sheet.add_image(img, cell)
    except FileNotFoundError:
        sheet[cell] = f"Logo Missing: {image_path}"
        
def _create_sheet_header(sheet, styles):
    """Creates the standard 'all-waveav' header from the PDF."""
    sheet.row_dimensions[1].height = 45
    
    # IMPORTANT: Ensure 'company_logo.png' is in the 'assets' folder at the root of your app.
    _add_image_to_cell(sheet, 'assets/company_logo.png', 'A1', 55)

    sheet.merge_cells('M1:P1')
    tagline_cell = sheet['M1']
    tagline_cell.value = "Service     Quality     Innovation"
    tagline_cell.font = Font(size=14, bold=True)
    tagline_cell.alignment = Alignment(horizontal='right', vertical='center')

    sheet.merge_cells('M2:P2')
    years_cell = sheet['M2']
    years_cell.value = "25+\nYears"
    years_cell.font = Font(size=14, bold=True)
    years_cell.alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    sheet.row_dimensions[2].height = 30

# --- Sheet Generation Functions ---

def _add_contact_details_sheet(workbook, project_details, styles):
    """Creates the 'Contact Details' sheet using data from the app's sidebar."""
    sheet = workbook.create_sheet(title="Contact Details", index=0)
    sheet.sheet_view.showGridLines = False

    sheet.column_dimensions['A'].width = 25
    sheet.column_dimensions['B'].width = 40
    
    sheet.row_dimensions[1].height = 30
    sheet['A1'].value = "Contact Details"
    sheet['A1'].font = Font(size=16, bold=True)

    # **FIX**: This now maps directly to the keys used in your ui_components.py
    contact_data = [
        ("Design Engineer", project_details.get("Design Engineer", "")),
        ("Account Manager", project_details.get("Account Manager", "")),
        ("Client Name", project_details.get("Client Name", "")),
        ("Key Client Personnel", project_details.get("Key Client Personnel", "")),
        ("Location", project_details.get("Location", "")),
        ("Key Comments for this version", project_details.get("Key Comments", "")) # Key changed here
    ]
    
    row_cursor = 3
    for label, value in contact_data:
        cell_label = sheet[f'A{row_cursor}']
        cell_value = sheet[f'B{row_cursor}']
        
        cell_label.value = label
        cell_value.value = value
        
        cell_label.fill = styles['header_green_fill']
        cell_label.font = styles['bold_font']
        cell_label.border = styles['thin_border']
        cell_value.border = styles['thin_border']
        
        if "Key Comments" in label:
            sheet.row_dimensions[row_cursor].height = 60
            cell_value.alignment = Alignment(wrap_text=True, vertical='top')
        
        row_cursor += 1

def _add_summary_and_terms_sheet(workbook, rooms_data, styles):
    """Creates the Proposal Summary and static Commercial Terms sheet."""
    sheet = workbook.create_sheet(title="Proposal Summary & Terms", index=1)
    _create_sheet_header(sheet, styles)
    
    row_cursor = 4
    sheet.merge_cells(f'A{row_cursor}:C{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Proposal Summary"
    sheet[f'A{row_cursor}'].font = Font(size=14, bold=True)
    row_cursor += 2

    summary_headers = ["Sr. No", "Description", "Total"]
    sheet.append(summary_headers)
    for cell in sheet[sheet.max_row]:
        cell.fill = styles['table_header_blue_fill']
        cell.font = styles['bold_font']
        cell.border = styles['thin_border']
    
    if rooms_data:
        option_counts = {}
        for room in rooms_data:
            option_name = room.get('name', 'Unnamed Room')
            option_counts[option_name] = option_counts.get(option_name, 0) + 1
        for i, (name, count) in enumerate(option_counts.items()):
             sheet.append([i + 1, name, count])

    for row in sheet.iter_rows(min_row=row_cursor, max_row=sheet.max_row):
        for cell in row:
            cell.border = styles['thin_border']

    row_cursor = sheet.max_row + 3
    sheet.merge_cells(f'A{row_cursor}:P{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Commercial Terms"
    sheet[f'A{row_cursor}'].font = Font(size=14, bold=True)
    row_cursor += 2
    
    # Static commercial terms from the PDF
    terms_content = [
        ("header", "A. Delivery, Installations & Site Schedule"),
        ("text", "All Wave AV Systems undertake to ensure it's best efforts to complete the assignment for Client within the shortest timelines possible."),
        ("header", "B] Payment Terms"),
        ("sub_header", "1. Schedule of Payment"),
        ("table", [["Item", "Advance Payment"], ["For Equipment and Materials (INR)", "20% Advance with PO"]]),
        ("header", "C] Validity"),
        ("text", "Offer Validity:- 7 Days"),
        ("header", "H] Warranty"),
        ("text", "All Wave AV Systems undertakes to provide Client with a Limited Period Warranty on certain consumables, which includes Warranty on the Projector Lamp (450 hours of use or 90 days from purchase whichever is earlier) and warranty on other consumables like Filters and Touch Panel Battery (90 days).")
    ]
    
    for item_type, content in terms_content:
        sheet.merge_cells(f'A{row_cursor}:P{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        if item_type in ["header", "sub_header"]: cell.font = styles['bold_font']
        if item_type == "text":
             cell.value = content
             cell.alignment = Alignment(wrap_text=True, vertical='top')
             row_cursor += 1
        elif item_type == "header":
            cell.value = content; cell.fill = styles['table_header_blue_fill']; cell.font = styles['white_bold_font']; row_cursor += 1
        elif item_type == "sub_header":
             cell.value = content; row_cursor += 1
        elif item_type == "table":
            for r_idx, row_data in enumerate(content):
                sheet[f'A{row_cursor}'].value = row_data[0]
                sheet.merge_cells(f'B{row_cursor}:C{row_cursor}')
                sheet[f'B{row_cursor}'].value = row_data[1]
                if r_idx == 0: sheet[f'A{row_cursor}'].font = sheet[f'B{row_cursor}'].font = styles['bold_font']
                row_cursor += 1
        row_cursor += 1

def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """Creates a detailed BOQ sheet for a single room, mapping app data to the correct columns."""
    _create_sheet_header(sheet, styles)
    
    info_data = [("Room Name / Room Type", room_name), ("Floor", "-"), ("Number of Seats", "-"), ("Number of Rooms", "-")]
    for i, (label, value) in enumerate(info_data):
        row = i + 4
        sheet[f'A{row}'].value = label; sheet[f'A{row}'].font = styles['bold_font']
        sheet.merge_cells(f'B{row}:D{row}'); sheet[f'B{row}'].value = value
        for col in ['A', 'B', 'C', 'D']: sheet[f'{col}{row}'].border = styles['thin_border']
        sheet[f'A{row}'].fill = styles['header_green_fill']

    header_start_row = 9
    headers1 = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST', None, 'CGST', None, 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]
    
    sheet.insert_rows(header_start_row, amount=2)
    for c_idx, val in enumerate(headers1): sheet.cell(row=header_start_row, column=c_idx + 1, value=val)
    for c_idx, val in enumerate(headers2): sheet.cell(row=header_start_row + 1, column=c_idx + 1, value=val)

    sheet.merge_cells(f'I{header_start_row}:J{header_start_row}'); sheet.merge_cells(f'K{header_start_row}:L{header_start_row}')
    for r in range(header_start_row, header_start_row + 2):
        for c in range(1, len(headers1) + 1):
            cell = sheet.cell(row=r, column=c)
            cell.fill = styles["table_header_blue_fill"]; cell.font = styles['bold_font']
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True); cell.border = styles['thin_border']

    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items: grouped_items[cat] = []
        grouped_items[cat].append(item)

    total_before_gst_hardware, item_s_no = 0, 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    for i, (category, cat_items) in enumerate(grouped_items.items()):
        row_cursor = sheet.max_row + 1
        sheet.cell(row=row_cursor, column=1, value=category_letters[i]); sheet.cell(row=row_cursor, column=2, value=category)
        sheet.merge_cells(f'B{row_cursor}:P{row_cursor}')
        for col in range(1, 17): sheet.cell(row=row_cursor, column=col).fill = styles['boq_category_fill']

        for item in cat_items:
            unit_price_inr = item.get('price', 0) * usd_to_inr_rate
            quantity = item.get('quantity', 1); subtotal = unit_price_inr * quantity
            gst_rate = item.get('gst_rate', gst_rates.get('Electronics', 18))
            sgst_rate, cgst_rate = gst_rate / 2, gst_rate / 2
            sgst_amount, cgst_amount = subtotal * (sgst_rate / 100), subtotal * (cgst_rate / 100)
            
            # **FIX**: This mapping now correctly uses the keys from your boq_generator
            row_data = [
                item_s_no, item.get('specifications', ''), "", item.get('brand', 'Unknown'),
                item.get('name', 'Unknown'), quantity, unit_price_inr, subtotal,
                f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", cgst_amount,
                sgst_amount + cgst_amount, subtotal + sgst_amount + cgst_amount,
                item.get('justification', ''), ""
            ]
            sheet.append(row_data)
            total_before_gst_hardware += subtotal; item_s_no += 1

    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    if services and total_before_gst_hardware > 0:
        row_cursor = sheet.max_row + 1
        sheet.cell(row=row_cursor, column=1, value=chr(ord('A') + len(grouped_items)))
        sheet.cell(row=row_cursor, column=2, value="Services")
        sheet.merge_cells(f'B{row_cursor}:P{row_cursor}')
        for col in range(1, 17): sheet.cell(row=row_cursor, column=col).fill = styles['boq_category_fill']
        
        services_gst_rate = gst_rates.get('Services', 18)
        for service_name, percentage in services:
            service_amount = total_before_gst_hardware * percentage
            sgst_rate, cgst_rate = services_gst_rate / 2, services_gst_rate / 2
            sgst_amount = service_amount * (sgst_rate / 100); cgst_amount = service_amount * (cgst_rate / 100)
            sheet.append([
                item_s_no, "Certified professional service", "", "AllWave AV", service_name, 1,
                service_amount, service_amount, f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", cgst_amount,
                sgst_amount + cgst_amount, service_amount + sgst_amount + cgst_amount, "As per standard terms", ""
            ])
            item_s_no += 1

    column_widths = {'A': 8, 'B': 35, 'C': 30, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 10, 'J': 15, 'K': 10, 'L': 15, 'M': 15, 'N': 18, 'O': 40, 'P': 15}
    for col, width in column_widths.items(): sheet.column_dimensions[col].width = width
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            if cell.column >= 7 and isinstance(cell.value, (int, float)): cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']

# --- Main Entry Point ---
def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """Main function to generate the complete Excel workbook in the company format."""
    workbook = openpyxl.Workbook()
    if "Sheet" in workbook.sheetnames: del workbook["Sheet"]
    styles = _define_styles()

    # Create the static and summary sheets
    _add_contact_details_sheet(workbook, project_details, styles)
    _add_summary_and_terms_sheet(workbook, rooms_data, styles)
    # The Scope of Work sheet can be added here if needed, or omitted for brevity

    # Create a detailed BOQ sheet for each room
    for room in rooms_data:
        # Use boq_items from the room data passed from the app
        if room.get('boq_items'):
            safe_name = re.sub(r'[\\/*?:"<>|]', '_', room['name'])[:25]
            room_sheet = workbook.create_sheet(title=f"BOQ - {safe_name}")
            _populate_room_boq_sheet(
                room_sheet, room['boq_items'], room['name'], styles, 
                usd_to_inr_rate, project_details.get('gst_rates', {})
            )

    workbook.active = workbook["Contact Details"]
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()
