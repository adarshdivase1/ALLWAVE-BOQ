import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils.units import pixels_to_EMU
from openpyxl.utils import get_column_letter
from io import BytesIO
import re
from datetime import datetime

# --- Style Definitions ---
def _define_styles():
    """Defines all necessary styles for the professional report."""
    thin_border_side = Side(style='thin')
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    return {
        "header_green_fill": PatternFill(start_color="00B050", end_color="00B050", fill_type="solid"),
        "header_light_green_fill": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        "header_dark_blue_fill": PatternFill(start_color="002060", end_color="002060", fill_type="solid"),
        "table_header_blue_fill": PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid"),
        "boq_category_fill": PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"),
        "white_font": Font(color="FFFFFF", bold=True),
        "bold_font": Font(bold=True),
        "thin_border": thin_border,
        "currency_format": "₹ #,##0"
    }

# --- Header & Image Helpers ---
def _add_image_to_cell(sheet, image_path, cell, height_px):
    """Adds a logo to a cell, preserving aspect ratio."""
    try:
        img = openpyxl.drawing.image.Image(image_path)
        img.height = height_px
        img.width = (img.width / img.height) * height_px
        sheet.add_image(img, cell)
    except FileNotFoundError:
        sheet[cell] = f"Logo not found: {image_path}"

def _create_sheet_header(sheet, styles):
    """Creates the standard header with logos for all sheets."""
    # Ensure asset paths are correct
    allwave_logo = 'assets/company_logo.png'
    psni_avixa_logos = 'assets/psni_avixa_combined.png' # You might need to combine these into one image

    sheet.row_dimensions[1].height = 60
    _add_image_to_cell(sheet, allwave_logo, 'A1', 75)
    
    # Placeholder for combined PSNI/AVIXA logo - adjust cell and path as needed
    _add_image_to_cell(sheet, 'assets/psni_avixa_combined.png', 'O1', 75)
    
    # Merge cells to create space and prevent overlap
    sheet.merge_cells('A1:C1')
    sheet.merge_cells('O1:P1')

# --- Sheet Generation Functions ---

def _add_version_control_sheet(workbook, project_details, styles):
    """Creates the Version Control & Contact Details sheet."""
    sheet = workbook.create_sheet(title="Version Control", index=0)
    _create_sheet_header(sheet, styles)
    sheet.sheet_view.showGridLines = False

    # Version Control Table
    sheet.merge_cells('A3:C3')
    vc_header = sheet['A3']
    vc_header.value = "Version Control"
    vc_header.fill = styles['header_green_fill']
    vc_header.font = styles['white_font']
    vc_header.alignment = Alignment(horizontal='center')

    vc_data = [
        ("Date of First Draft", ""), ("Date of Final Draft", ""),
        ("", ""), ("", ""),
        ("Version No.", ""), ("Published Date", "")
    ]
    for i, (label, value) in enumerate(vc_data):
        row = i + 4
        cell_a = sheet[f'A{row}']
        cell_a.value = label
        cell_a.fill = styles['header_light_green_fill']
        sheet.merge_cells(f'B{row}:C{row}')
        sheet[f'A{row}'].border = sheet[f'B{row}'].border = styles['thin_border']

    # Contact Details Table
    sheet.merge_cells('E3:G3')
    cd_header = sheet['E3']
    cd_header.value = "Contact Details"
    cd_header.fill = styles['header_green_fill']
    cd_header.font = styles['white_font']
    cd_header.alignment = Alignment(horizontal='center')
    
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
        cell_e = sheet[f'E{row}']
        cell_e.value = label
        cell_e.fill = styles['header_light_green_fill']
        sheet.merge_cells(f'F{row}:G{row}')
        cell_f = sheet[f'F{row}']
        cell_f.value = value
        sheet[f'E{row}'].border = sheet[f'F{row}'].border = styles['thin_border']

    # Column Widths
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        sheet.column_dimensions[col].width = 20

def _add_proposal_sheet(workbook, rooms_data, styles):
    """Creates the detailed Proposal Summary sheet."""
    sheet = workbook.create_sheet(title="Proposal Summary", index=1)
    _create_sheet_header(sheet, styles)
    
    # Summary Table
    row_cursor = 4
    sheet[f'A{row_cursor}'] = "Proposal Summary"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    row_cursor += 1
    
    summary_headers = ["Sr. No", "Description", "Total Qty", "INR Supply Rate w/o TAX", "Amount w/o TAX", "Total TAX Amount", "Amount with Tax"]
    sheet.append(summary_headers)
    header_row = sheet.max_row
    for cell in sheet[header_row]:
        cell.fill = styles['table_header_blue_fill']
        cell.font = styles['white_font']
        cell.border = styles['thin_border']

    grand_total_subtotal = 0
    grand_total_gst = 0
    grand_total_final = 0
    
    for i, room in enumerate(rooms_data):
        if room.get('total'):
            sheet.append([
                i + 1, room['name'], 1, room.get('subtotal', 0), room.get('subtotal', 0),
                room.get('gst', 0), room.get('total', 0)
            ])
            grand_total_subtotal += room.get('subtotal', 0)
            grand_total_gst += room.get('gst', 0)
            grand_total_final += room.get('total', 0)

    sheet.append(["", "Grand Total", "", "", grand_total_subtotal, grand_total_gst, grand_total_final])
    
    # Apply formatting
    for row in sheet.iter_rows(min_row=header_row, max_row=sheet.max_row):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']
    
    # Static Content (Commercial Terms, etc.)
    row_cursor = sheet.max_row + 2
    static_content = [
        ("Commercial Terms", "This proposal outlines the pricing and best efforts to complete the assignment for Client within the shortest timelines possible."),
        ("1. Project Schedule & Site Requirements", ""),
        ("All Wave AV Systems", "Design & Procurement"),
        ("Client", "Site Readiness"),
        ("2. Delivery Terms", "All deliveries are Ex-works at All Wave AV Systems office."),
        ("3. Delivers Procedures", "All deliveries will be completed within 6-8 weeks..."),
        # Add all other static text sections from your image here in the same format
    ]

    for title, text in static_content:
        sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = title
        cell.fill = styles['table_header_blue_fill']
        cell.font = styles['white_font']
        row_cursor += 1
        if text:
            sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
            text_cell = sheet[f'A{row_cursor}']
            text_cell.value = text
            text_cell.alignment = Alignment(wrap_text=True)
            row_cursor += 1
        row_cursor +=1 # Spacer

    for col in sheet.columns:
        sheet.column_dimensions[get_column_letter(col[0].column)].width = 25
        
def _add_scope_of_work_sheet(workbook, styles):
    """Creates the detailed Scope of Work sheet."""
    # This function would be very long. You would create a large data structure
    # (list of dictionaries) with all the text from your screenshot and loop through it,
    # applying styles, similar to the _add_proposal_sheet.
    sheet = workbook.create_sheet(title="Scope of Work", index=2)
    _create_sheet_header(sheet, styles)
    sheet['A3'] = "Scope of Work" # Simplified for brevity
    # In a full implementation, you'd populate all sections from your image.

def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """Creates an individual room's BOQ sheet."""
    _create_sheet_header(sheet, styles)

    # Simplified Room Info Header
    info_data = [
        ("Room Name / Room Type", room_name),
        ("Floor", "-"),
        ("Number of Seats", "-"),
        ("Number of Rooms", "-"),
    ]
    for i, (label, value) in enumerate(info_data):
        row = i + 3
        sheet[f'A{row}'] = label
        sheet[f'B{row}'] = value
        sheet[f'A{row}'].border = sheet[f'B{row}'].border = styles['thin_border']

    # Table Headers
    headers = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST Rate', 'SGST Amt', 'CGST Rate', 'CGST Amt', 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    sheet.append([])
    sheet.append(headers)
    header_row = sheet.max_row
    for cell in sheet[header_row]:
        cell.fill = styles['table_header_blue_fill']
        cell.font = styles['white_font']
        cell.border = styles['thin_border']

    # Item processing (simplified for this example)
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items: grouped_items[cat] = []
        grouped_items[cat].append(item)

    sr_no = 'A'
    for category, cat_items in grouped_items.items():
        sheet.append([sr_no, category])
        cat_row = sheet.max_row
        for cell in sheet[cat_row]:
            cell.fill = styles['boq_category_fill']
            cell.border = styles['thin_border']
        # Here you would loop through cat_items and append each product row
        # with full calculations, similar to your original generator.
        sr_no = chr(ord(sr_no) + 1)
        
    for col in sheet.columns:
        sheet.column_dimensions[get_column_letter(col[0].column)].width = 20

# --- Main Entry Point ---

def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """Main function to generate the complete Excel workbook."""
    workbook = openpyxl.Workbook()
    styles = _define_styles()

    # Create the main sheets in the desired order
    _add_version_control_sheet(workbook, project_details, styles)
    _add_proposal_sheet(workbook, rooms_data, styles)
    _add_scope_of_work_sheet(workbook, styles)
    
    # Populate totals for the proposal summary
    for room in rooms_data:
        if room.get('boq_items'):
            # This is a simplified calculation. A full implementation would be more robust.
            subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in room['boq_items']) * usd_to_inr_rate
            gst = subtotal * 0.18 # Assuming flat 18% GST
            room['subtotal'] = subtotal
            room['gst'] = gst
            room['total'] = subtotal + gst

    # Re-populate summary sheet now that totals are calculated
    _add_proposal_sheet(workbook, rooms_data, styles)
    
    # Create a detailed sheet for each room
    for room in rooms_data:
        if room.get('boq_items'):
            safe_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:25]
            room_sheet = workbook.create_sheet(title=f"BOQ - {safe_name}")
            # NOTE: Your full _populate_company_boq_sheet logic would go here.
            # This is a placeholder call.
            _populate_room_boq_sheet(room_sheet, room['boq_items'], room['name'], styles, usd_to_inr_rate, project_details.get('gst_rates', {}))

    # Remove the default sheet created by openpyxl
    if "Sheet" in workbook.sheetnames:
        del workbook["Sheet"]

    # Save to memory buffer
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()
