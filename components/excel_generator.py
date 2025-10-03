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
        "header_green_fill": PatternFill(start_color="A9D08E", end_color="A9D08E", fill_type="solid"),
        "header_light_green_fill": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        "table_header_blue_fill": PatternFill(start_color="9BC2E6", end_color="9BC2E6", fill_type="solid"),
        "boq_category_fill": PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"),
        "black_bold_font": Font(color="000000", bold=True),
        "bold_font": Font(bold=True),
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
        sheet[cell] = f"Logo missing: {image_path}"

def _create_sheet_header(sheet):
    """Creates the standard header with four logos contained within merged cells."""
    sheet.row_dimensions[1].height = 50
    sheet.row_dimensions[2].height = 50

    sheet.merge_cells('A1:C2')
    sheet.merge_cells('D1:F2')
    sheet.merge_cells('M1:N2')
    sheet.merge_cells('O1:P2')

    _add_image_to_cell(sheet, 'assets/company_logo.png', 'A1', 95)
    _add_image_to_cell(sheet, 'assets/crestron_logo.png', 'D1', 95)
    _add_image_to_cell(sheet, 'assets/iso_logo.png', 'M1', 95)
    _add_image_to_cell(sheet, 'assets/avixa_logo.png', 'O1', 95)
    
def _add_version_control_sheet(workbook, project_details, styles):
    """Creates the Version Control & Contact Details sheet."""
    sheet = workbook.create_sheet(title="Version Control", index=0)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False

    sheet.column_dimensions['A'].width = 25
    sheet.column_dimensions['B'].width = 25
    sheet.column_dimensions['D'].width = 5
    sheet.column_dimensions['E'].width = 25
    sheet.column_dimensions['F'].width = 25
    
    # Version Control Table
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

    # Contact Details Table
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

def _add_proposal_summary_sheet(workbook, rooms_data, styles):
    """Creates the Proposal Summary sheet with company format."""
    sheet = workbook.create_sheet(title="Proposal Summary", index=1)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False
    
    # Simple room summary table
    row_cursor = 4
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Proposal Summary"
    sheet[f'A{row_cursor}'].font = Font(size=12, bold=True)
    sheet[f'A{row_cursor}'].alignment = Alignment(horizontal='center')
    row_cursor += 1
    
    summary_headers = ["Sr. No", "Description", "Total Qty", "INR Supply Rate w/o TAX", "Amount w/o TAX", "Total TAX Amount", "Amount with Tax"]
    sheet.append(summary_headers)
    header_row = sheet.max_row
    for cell in sheet[header_row]:
        cell.fill = styles['table_header_blue_fill']
        cell.font = styles['bold_font']
        cell.border = styles['thin_border']
        cell.alignment = Alignment(horizontal='center', wrap_text=True)

    if rooms_data:
        for i, room in enumerate(rooms_data):
            if room.get('total'):
                sheet.append([
                    i + 1,
                    room['name'],
                    1,
                    room.get('subtotal', 0),
                    room.get('subtotal', 0),
                    room.get('gst', 0),
                    room.get('total', 0)
                ])

    for row in sheet.iter_rows(min_row=header_row + 1, max_row=sheet.max_row):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']
    
    # Commercial Terms Section
    row_cursor = sheet.max_row + 3
    
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    cell = sheet[f'A{row_cursor}']
    cell.value = "Commercial Terms"
    cell.fill = styles['table_header_blue_fill']
    cell.font = Font(bold=True, size=12)
    cell.alignment = Alignment(horizontal='center')
    row_cursor += 2
    
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    cell = sheet[f'A{row_cursor}']
    cell.value = "A. Delivery, Installations & Site Schedule"
    cell.fill = styles['table_header_blue_fill']
    cell.font = styles['bold_font']
    row_cursor += 1
    
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "All Wave AV Systems undertake to ensure it's best efforts to complete the assignment for Client within the shortest timelines possible."
    sheet[f'A{row_cursor}'].alignment = Alignment(wrap_text=True)
    row_cursor += 2
    
    remaining_sections = [
        ("D] Placing a Purchase Order", ["Order should be placed on All Wave AV Systems Pvt. Ltd. 420A Shah & Nahar Industrial Estate, Lower Parel West Mumbai 400013 INDIA"]),
        ("E] Cable Estimates", ["At this time All Wave AV Systems has provided Client with a provisional estimate for the various types of cabling required during the course of the project."]),
        ("F] Order Changes", ["All Wave AV Systems appreciates that there may be some changes required by Client to the Scope of Work outlined in this document at a later stage and is committed to meeting these requirements."]),
        ("G] Restocking / Cancellation Fees", ["Cancellation may involve a charge of upto 50% re-stocking / cancellation fees + shipping costs and additional charges."]),
        ("H] Warranty", ["All Wave AV Systems is committed to replace or repair any defective part that needs replacement or repair by the reason of defective workmanship or defects, brought to our notice during the warranty period."])
    ]
    
    for section_title, points in remaining_sections:
        sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        cell.value = section_title
        cell.fill = styles['table_header_blue_fill']
        cell.font = styles['bold_font']
        row_cursor += 1
        
        for point in points:
            sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
            sheet[f'A{row_cursor}'].value = point
            sheet[f'A{row_cursor}'].alignment = Alignment(wrap_text=True)
            sheet.row_dimensions[row_cursor].height = 25
            row_cursor += 1
        row_cursor += 1

def _add_scope_of_work_sheet(workbook, styles):
    """Creates the comprehensive Scope of Work sheet."""
    sheet = workbook.create_sheet(title="Scope of Work", index=2)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False
    
    sheet.merge_cells('A3:C3')
    title_cell = sheet['A3']
    title_cell.value = "Scope of Work"
    title_cell.font = Font(size=14, bold=True)
    title_cell.alignment = Alignment(horizontal='center')
    
    row_cursor = 5
    
    sheet.merge_cells(f'A{row_cursor}:C{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Scope of Work"
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    row_cursor += 1
    
    # ... (Rest of the static content for this sheet can be added here if needed) ...

def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """
    Creates a fully detailed BOQ sheet for a single room, now with more columns
    and item-specific GST rates.
    """
    _create_sheet_header(sheet)
    
    info_data = [("Room Name / Room Type", room_name), ("Floor", "-"), ("Number of Seats", "-"), ("Number of Rooms", "-")]
    for i, (label, value) in enumerate(info_data):
        row = i + 3
        sheet[f'A{row}'].value = label
        sheet[f'A{row}'].font = styles['bold_font']
        sheet.merge_cells(f'B{row}:C{row}')
        sheet[f'B{row}'].value = value
        for col in ['A', 'B', 'C']:
            sheet[f'{col}{row}'].border = styles['thin_border']

    sheet.append([]) # Spacer

    headers1 = [
        'Sr. No.', 'Description of Goods / Services', 'Make', 'Model No.', 'Qty.',
        'Unit Rate (INR)', 'Total', 'Warranty', 'Lead Time (Days)',
        'SGST\n( In Maharastra)', None, 'CGST\n( In Maharastra)', None,
        'Total (TAX)', 'Total Amount (INR)', 'Remarks'
    ]
    headers2 = [
        None, None, None, None, None, None, None, None, None,
        'Rate', 'Amt', 'Rate', 'Amt', None, None, None
    ]
    
    sheet.append(headers1)
    sheet.append(headers2)
    header_start_row = sheet.max_row - 1

    sheet.merge_cells(f'J{header_start_row}:K{header_start_row}')
    sheet.merge_cells(f'L{header_start_row}:M{header_start_row}')

    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row):
        for cell in row:
            if cell.value is not None:
                cell.fill = styles["table_header_blue_fill"]
                cell.font = styles['bold_font']
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = styles['thin_border']
    
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General AV')
        grouped_items.setdefault(cat, []).append(item)

    total_before_gst_hardware, total_gst_hardware, item_s_no = 0, 0, 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    for i, (category, cat_items) in enumerate(grouped_items.items()):
        sheet.append([category_letters[i], category])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(f'B{cat_row_idx}:P{cat_row_idx}')
        for cell in sheet[cat_row_idx]:
            cell.fill = styles['boq_category_fill']
            cell.font = styles['bold_font']
            cell.border = styles['thin_border']
        
        for item in cat_items:
            unit_price_inr = item.get('price', 0) * usd_to_inr_rate
            subtotal = unit_price_inr * item.get('quantity', 1)
            gst_rate = item.get('gst_rate', gst_rates.get('Electronics', 18)) # Use item's GST rate
            sgst_rate, cgst_rate = gst_rate / 2, gst_rate / 2
            sgst_amount, cgst_amount = subtotal * (sgst_rate / 100), subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            total_with_gst = subtotal + total_tax
            
            total_before_gst_hardware += subtotal
            total_gst_hardware += total_tax

            row_data = [
                item_s_no,
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
                total_tax, total_with_gst,
                item.get('justification', '')
            ]
            sheet.append(row_data)
            item_s_no += 1

    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    services_letter = chr(ord('A') + len(grouped_items))
    services_gst_rate = gst_rates.get('Services', 18)

    if services and total_before_gst_hardware > 0:
        sheet.append([services_letter, "Services"])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(f'B{cat_row_idx}:P{cat_row_idx}')
        for cell in sheet[cat_row_idx]:
            cell.fill = styles['boq_category_fill']
            cell.font = styles['bold_font']
            cell.border = styles['thin_border']

        for service_name, percentage in services:
            service_amount_inr = total_before_gst_hardware * percentage
            sgst_rate, cgst_rate = services_gst_rate / 2, services_gst_rate / 2
            service_sgst = service_amount_inr * (sgst_rate / 100)
            service_cgst = service_amount_inr * (cgst_rate / 100)
            service_total_tax = service_sgst + service_cgst
            service_total = service_amount_inr + service_total_tax
            row_data = [
                item_s_no, service_name, "AllWave AV", "Professional Service", 1,
                service_amount_inr, service_amount_inr, "As per terms", "N/A",
                f"{sgst_rate}%", service_sgst, f"{cgst_rate}%", service_cgst,
                service_total_tax, service_total, ""
            ]
            sheet.append(row_data)
            item_s_no += 1
    
    column_widths = {
        'A': 8, 'B': 45, 'C': 20, 'D': 30, 'E': 6, 'F': 15, 'G': 15, 'H': 15, 'I': 15,
        'J': 10, 'K': 15, 'L': 10, 'M': 15, 'N': 15, 'O': 18, 'P': 40
    }
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width
    
    for row in sheet.iter_rows(min_row=header_start_row + 2):
        for cell in row:
            if cell.column >= 6 and isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']
            if cell.column in [1, 5]:
                cell.alignment = Alignment(horizontal='center')

# --- Main Entry Point ---
def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """Main function to generate the complete Excel workbook."""
    workbook = openpyxl.Workbook()
    styles = _define_styles()

    _add_version_control_sheet(workbook, project_details, styles)
    # _add_scope_of_work_sheet(workbook, styles) # Can be re-enabled if needed
    
    for room in rooms_data:
        if room.get('boq_items'):
            # Calculate room totals for the summary sheet
            subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in room['boq_items']) * usd_to_inr_rate
            services_total = subtotal * 0.30  # Assuming 30% for services
            total_without_gst = subtotal + services_total
            
            gst_electronics = sum(
                (item.get('price', 0) * item.get('quantity', 1) * usd_to_inr_rate) * (item.get('gst_rate', 18) / 100)
                for item in room['boq_items']
            )
            gst_services = services_total * (project_details.get('gst_rates', {}).get('Services', 18) / 100)
            total_gst = gst_electronics + gst_services
            
            room['subtotal'], room['gst'], room['total'] = total_without_gst, total_gst, total_without_gst + total_gst

            safe_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:25]
            room_sheet = workbook.create_sheet(title=f"BOQ - {safe_name}")
            _populate_room_boq_sheet(
                room_sheet, room['boq_items'], room['name'], styles,
                usd_to_inr_rate, project_details.get('gst_rates', {})
            )

    # _add_proposal_summary_sheet(workbook, rooms_data, styles) # Can be re-enabled if needed

    if "Sheet" in workbook.sheetnames:
        del workbook["Sheet"]
    workbook.active = workbook["Version Control"]

    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()
