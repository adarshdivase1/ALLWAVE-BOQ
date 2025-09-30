import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
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

def _create_sheet_header(sheet):
    """Creates the standard header with logos for all sheets."""
    # NOTE: Ensure these logo files exist in your 'assets' folder.
    # You may need to combine your PSNI & AVIXA logos into a single image file.
    allwave_logo = 'assets/company_logo.png'
    psni_avixa_logos = 'assets/psni_avixa_combined.png'

    sheet.row_dimensions[1].height = 60
    _add_image_to_cell(sheet, allwave_logo, 'A1', 75)
    _add_image_to_cell(sheet, psni_avixa_logos, 'O1', 75)
    
    sheet.merge_cells('A1:C1')
    sheet.merge_cells('O1:P1')

# --- Sheet Generation Functions ---

def _add_version_control_sheet(workbook, project_details, styles):
    """Creates the Version Control & Contact Details sheet."""
    sheet = workbook.create_sheet(title="Version Control", index=0)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False

    # Version Control Table
    sheet.merge_cells('A3:C3')
    vc_header = sheet['A3']
    vc_header.value = "Version Control"
    vc_header.fill = styles['header_green_fill']
    vc_header.font = styles['white_font']
    vc_header.alignment = Alignment(horizontal='center')

    vc_data = [
        ("Date of First Draft", datetime.now().strftime("%Y-%m-%d")), ("Date of Final Draft", ""),
        ("", ""), ("", ""),
        ("Version No.", "1.0"), ("Published Date", datetime.now().strftime("%Y-%m-%d"))
    ]
    for i, (label, value) in enumerate(vc_data):
        row = i + 4
        cell_a = sheet[f'A{row}']
        cell_a.value = label
        cell_a.fill = styles['header_light_green_fill']
        sheet.merge_cells(f'B{row}:C{row}')
        sheet[f'B{row}'].value = value
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
        sheet.column_dimensions[col].width = 25

def _add_proposal_summary_sheet(workbook, rooms_data, styles):
    """Creates the Proposal Summary sheet with only the dynamic totals table."""
    sheet = workbook.create_sheet(title="Proposal Summary", index=1)
    _create_sheet_header(sheet)
    
    # Summary Table Title
    sheet.merge_cells('A3:G3')
    title_cell = sheet['A3']
    title_cell.value = "Commercial Proposal Summary"
    title_cell.font = Font(size=14, bold=True)
    title_cell.alignment = Alignment(horizontal='center')
    
    # Summary Table Headers
    summary_headers = ["Sr. No", "Description", "Total Qty", "INR Supply Rate w/o TAX", "Amount w/o TAX", "Total TAX Amount", "Amount with Tax"]
    sheet.append([]) # Spacer
    sheet.append(summary_headers)
    header_row = sheet.max_row
    for cell in sheet[header_row]:
        cell.fill = styles['table_header_blue_fill']
        cell.font = styles['white_font']
        cell.border = styles['thin_border']
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Populate Table with Room Data
    grand_total_subtotal, grand_total_gst, grand_total_final = 0, 0, 0
    
    for i, room in enumerate(rooms_data):
        if room.get('total'):
            sheet.append([
                i + 1, room['name'], 1, room.get('subtotal', 0), room.get('subtotal', 0),
                room.get('gst', 0), room.get('total', 0)
            ])
            grand_total_subtotal += room.get('subtotal', 0)
            grand_total_gst += room.get('gst', 0)
            grand_total_final += room.get('total', 0)

    # Grand Total Row
    sheet.append(["", "Grand Total", "", "", grand_total_subtotal, grand_total_gst, grand_total_final])
    
    # Apply formatting to all data rows
    for row in sheet.iter_rows(min_row=header_row + 1, max_row=sheet.max_row):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']
    sheet[f'B{sheet.max_row}'].font = styles['bold_font']
    
    # Set Column Widths
    for i, width in enumerate([8, 40, 10, 20, 20, 20, 20], 1):
        sheet.column_dimensions[get_column_letter(i)].width = width

def _add_scope_of_work_sheet(workbook, styles):
    """Creates a blank Scope of Work sheet with just a header."""
    sheet = workbook.create_sheet(title="Scope of Work", index=2)
    _create_sheet_header(sheet)
    sheet.merge_cells('A3:G3')
    title_cell = sheet['A3']
    title_cell.value = "Scope of Work"
    title_cell.font = Font(size=14, bold=True)
    title_cell.alignment = Alignment(horizontal='center')
    # This sheet is intentionally left blank as per the request.

def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """Creates a fully detailed BOQ sheet for a single room."""
    _create_sheet_header(sheet)

    # Room Info Header
    info_data = [
        ("Room Name / Room Type", room_name),
        ("Floor", "-"), ("Number of Seats", "-"), ("Number of Rooms", "-"),
    ]
    for i, (label, value) in enumerate(info_data):
        row = i + 3
        sheet[f'A{row}'] = label
        sheet[f'A{row}'].font = styles['bold_font']
        sheet.merge_cells(f'B{row}:C{row}')
        sheet[f'B{row}'] = value
        sheet[f'A{row}'].border = sheet[f'B{row}'].border = sheet[f'C{row}'].border = styles['thin_border']

    # Table Headers
    headers1 = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST\n( In Maharastra)', None, 'CGST\n( In Maharastra)', None, 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]
    sheet.append([]); sheet.append([]) # Spacers
    sheet.append(headers1); sheet.append(headers2)
    header_start_row = sheet.max_row - 1

    # Merge header cells and apply styles
    sheet.merge_cells(f'I{header_start_row}:J{header_start_row}')
    sheet.merge_cells(f'K{header_start_row}:L{header_start_row}')
    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row, min_col=1, max_col=len(headers1)):
        for cell in row:
            cell.fill = styles["table_header_blue_fill"]
            cell.font = styles["white_font"]
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = styles['thin_border']

    # Group and add items
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items: grouped_items[cat] = []
        grouped_items[cat].append(item)

    total_before_gst_hardware, total_gst_hardware = 0, 0
    item_s_no = 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    for i, (category, cat_items) in enumerate(grouped_items.items()):
        sheet.append([category_letters[i], category])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=len(headers1))
        sheet[f'A{cat_row_idx}'].font = sheet[f'B{cat_row_idx}'].font = styles['bold_font']
        for cell in sheet[cat_row_idx]: cell.fill = styles['boq_category_fill']

        for item in cat_items:
            unit_price_inr = item.get('price', 0) * usd_to_inr_rate
            subtotal = unit_price_inr * item.get('quantity', 1)
            gst_rate = item.get('gst_rate', gst_rates.get('Electronics', 18))
            sgst_rate, cgst_rate = gst_rate / 2, gst_rate / 2
            sgst_amount, cgst_amount = subtotal * (sgst_rate / 100), subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            total_with_gst = subtotal + total_tax
            total_before_gst_hardware += subtotal
            total_gst_hardware += total_tax

            sheet.append([
                item_s_no, item.get('specifications', item.get('name', '')), "", item.get('brand', 'Unknown'),
                item.get('name', 'Unknown'), item.get('quantity', 1), unit_price_inr, subtotal,
                f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", cgst_amount, total_tax, total_with_gst,
                item.get('justification', ''), ""
            ])
            item_s_no += 1
    
    # Add Services Section
    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    services_letter = chr(ord('A') + len(grouped_items))
    total_before_gst_services, total_gst_services = 0, 0
    services_gst_rate = gst_rates.get('Services', 18)

    if services and total_before_gst_hardware > 0:
        sheet.append([services_letter, "Services"])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=len(headers1))
        for cell in sheet[cat_row_idx]: cell.fill = styles['boq_category_fill']

        for service_name, percentage in services:
            service_amount_inr = total_before_gst_hardware * percentage
            sgst_rate, cgst_rate = services_gst_rate / 2, services_gst_rate / 2
            service_sgst, service_cgst = service_amount_inr * (sgst_rate / 100), service_amount_inr * (cgst_rate / 100)
            service_total_tax = service_sgst + service_cgst
            service_total = service_amount_inr + service_total_tax
            total_before_gst_services += service_amount_inr
            total_gst_services += service_total_tax
            sheet.append([
                item_s_no, "Certified professional service", "", "AllWave AV", service_name, 1,
                service_amount_inr, service_amount_inr, f"{sgst_rate}%", service_sgst,
                f"{cgst_rate}%", service_cgst, service_total_tax, service_total, "As per standard terms", ""
            ])
            item_s_no += 1
    
    # Add Totals and apply formatting
    grand_total = (total_before_gst_hardware + total_gst_hardware) + (total_before_gst_services + total_gst_services)
    
    column_widths = {'A': 8, 'B': 35, 'C': 45, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 10, 'J': 15, 'K': 10, 'L': 15, 'M': 15, 'N': 18, 'O': 40, 'P': 15}
    for col, width in column_widths.items(): sheet.column_dimensions[col].width = width
    
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            if cell.column >= 7 and isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']

# --- Main Entry Point ---

def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """Main function to generate the complete Excel workbook."""
    workbook = openpyxl.Workbook()
    styles = _define_styles()

    # Create the main sheets in the desired order
    _add_version_control_sheet(workbook, project_details, styles)
    # The proposal summary sheet will be populated after room totals are calculated
    _add_scope_of_work_sheet(workbook, styles)
    
    # Calculate totals for each room and create their individual BOQ sheets
    for room in rooms_data:
        if room.get('boq_items'):
            subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in room['boq_items']) * usd_to_inr_rate
            hardware_total = subtotal
            # Simplified service calculation for summary
            services_total = hardware_total * 0.30 # (15% + 5% + 10%)
            total_without_gst = hardware_total + services_total
            
            gst_electronics = hardware_total * (project_details['gst_rates'].get('Electronics', 18) / 100)
            gst_services = services_total * (project_details['gst_rates'].get('Services', 18) / 100)
            total_gst = gst_electronics + gst_services
            
            room['subtotal'] = total_without_gst
            room['gst'] = total_gst
            room['total'] = total_without_gst + total_gst

            # Create the detailed sheet for this room
            safe_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:25]
            room_sheet = workbook.create_sheet(title=f"BOQ - {safe_name}")
            _populate_room_boq_sheet(room_sheet, room['boq_items'], room['name'], styles, usd_to_inr_rate, project_details.get('gst_rates', {}))

    # Now that all room totals are calculated, create the final summary sheet
    _add_proposal_summary_sheet(workbook, rooms_data, styles)

    # Remove the default sheet created by openpyxl and set active sheet
    if "Sheet" in workbook.sheetnames:
        del workbook["Sheet"]
    workbook.active = workbook["Proposal Summary"]

    # Save to memory buffer
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()
