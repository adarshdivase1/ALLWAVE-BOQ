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

# --- All Excel-related functions from app.py are moved here ---

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
    sheet['E8'] = 1 # This sheet is for a single room

    # Table Headers
    headers1 = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST\n( In Maharastra)', None, 'CGST\n( In Maharastra)', None, 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]

    sheet.append(headers1)
    sheet.append(headers2)
    header_start_row = sheet.max_row - 1

    # Merge header cells
    sheet.merge_cells(start_row=header_start_row, start_column=9, end_row=header_start_row, end_column=10) # SGST
    sheet.merge_cells(start_row=header_start_row, start_column=11, end_row=header_start_row, end_column=12) # CGST

    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row, min_col=1, max_col=len(headers1)):
        for cell in row:
            cell.font = styles["table_header"]
            cell.fill = styles["table_header_fill"]
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Group items by category
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items:
            grouped_items[cat] = []
        grouped_items[cat].append(item)

    # Add Items
    total_before_gst_hardware = 0
    total_gst_hardware = 0
    item_s_no = 1

    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    for i, (category, cat_items) in enumerate(grouped_items.items()):
        # Category Header
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
            sgst_rate = gst_rate / 2
            cgst_rate = gst_rate / 2
            sgst_amount = subtotal * (sgst_rate / 100)
            cgst_amount = subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            total_with_gst = subtotal + total_tax

            total_before_gst_hardware += subtotal
            total_gst_hardware += total_tax

            row_data = [
                item_s_no,
                None,
                item.get('specifications', item.get('name', '')),
                item.get('brand', 'Unknown'),
                item.get('name', 'Unknown'),
                item.get('quantity', 1),
                unit_price_inr,
                subtotal,
                f"{sgst_rate}%",
                sgst_amount,
                f"{cgst_rate}%",
                cgst_amount,
                total_tax,
                total_with_gst,
                item.get('justification', ''),
                None
            ]
            sheet.append(row_data)
            current_row = sheet.max_row
            _add_product_image_to_excel(sheet, current_row, item.get('image_url', ''), 'P')
            item_s_no += 1

    # Add Services
    services = [
        ("Installation & Commissioning", 0.15),
        ("System Warranty (3 Years)", 0.05),
        ("Project Management", 0.10)
    ]

    if services:
        services_letter = chr(ord('A') + len(grouped_items))
        sheet.append([services_letter, "Services"])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=16)
        sheet[f'A{cat_row_idx}'].font = styles['bold']
        sheet[f'B{cat_row_idx}'].font = styles['bold']
        for col_letter in 'ABCDEFGHIJKLMNOP':
            sheet[f'{col_letter}{cat_row_idx}'].fill = styles['group_header_fill']

    total_before_gst_services = 0
    total_gst_services = 0
    services_gst_rate = gst_rates.get('Services', 18)

    for service_name, percentage in services:
        service_amount_inr = total_before_gst_hardware * percentage
        sgst_rate = services_gst_rate / 2
        cgst_rate = services_gst_rate / 2
        service_sgst = service_amount_inr * (sgst_rate / 100)
        service_cgst = service_amount_inr * (cgst_rate / 100)
        service_total_tax = service_sgst + service_cgst
        service_total = service_amount_inr + service_total_tax

        total_before_gst_services += service_amount_inr
        total_gst_services += service_total_tax

        sheet.append([
            item_s_no, None, "Certified professional service for system deployment", "AllWave AV", service_name, 1,
            service_amount_inr, service_amount_inr,
            f"{sgst_rate}%", service_sgst,
            f"{cgst_rate}%", service_cgst,
            service_total_tax, service_total, "As per standard terms", ""
        ])
        item_s_no += 1

    # Totals Section
    sheet.append([]) # Spacer

    hardware_total_row = ["", "Total for Hardware (A)", "", "", "", "", "", total_before_gst_hardware, "", "", "", "", total_gst_hardware, total_before_gst_hardware + total_gst_hardware]
    sheet.append(hardware_total_row)
    for cell in sheet[sheet.max_row]:
        cell.font = styles['bold']
        cell.fill = styles['total_fill']

    services_total_row = ["", f"Total for Services ({services_letter})", "", "", "", "", "", total_before_gst_services, "", "", "", "", total_gst_services, total_before_gst_services + total_gst_services]
    sheet.append(services_total_row)
    for cell in sheet[sheet.max_row]:
        cell.font = styles['bold']
        cell.fill = styles['total_fill']

    grand_total = (total_before_gst_hardware + total_gst_hardware) + (total_before_gst_services + total_gst_services)
    sheet.append([])
    grand_total_row_idx = sheet.max_row + 1
    sheet[f'M{grand_total_row_idx}'] = "Grand Total (INR)"
    sheet[f'N{grand_total_row_idx}'] = grand_total
    sheet[f'M{grand_total_row_idx}'].font = styles["grand_total_font"]
    sheet[f'N{grand_total_row_idx}'].font = styles["grand_total_font"]
    sheet[f'M{grand_total_row_idx}'].fill = styles["grand_total_fill"]
    sheet[f'N{grand_total_row_idx}'].fill = styles["grand_total_fill"]
    sheet[f'M{grand_total_row_idx}'].alignment = Alignment(horizontal='center')
    sheet[f'N{grand_total_row_idx}'].alignment = Alignment(horizontal='center')

    # Final Formatting
    column_widths = {'A': 8, 'B': 35, 'C': 45, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 10, 'J': 15, 'K': 10, 'L': 15, 'M': 15, 'N': 18, 'O': 40, 'P': 20}
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width

    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            if cell.value is not None:
                cell.border = styles['thin_border']
            if cell.column >= 7 and cell.column <= 14:
                cell.number_format = styles['currency_format']

    return total_before_gst_hardware + total_before_gst_services, total_gst_hardware + total_gst_services, grand_total

# ... (rest of the Excel functions: add_proposal_summary_sheet, add_scope_of_work_sheet, etc.) ...
# NOTE: The other excel helper functions (_define_styles, etc.) would be pasted here as well.
# For brevity, I'm showing the main generate_company_excel function which is the entry point.

def generate_company_excel(project_details, rooms_data, gst_rates):
    """Generate Excel file in the new company standard format."""
    if not rooms_data:
        return None

    workbook = openpyxl.Workbook()
    styles = _define_styles()

    client_name = project_details.get('client_name', 'Valued Client')
    
    # Create a detailed BOQ sheet for each room
    for room in rooms_data:
        if room.get('boq_items'):
            safe_room_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:30]
            room_sheet = workbook.create_sheet(title=safe_room_name)
            subtotal, gst, total = _populate_company_boq_sheet(room_sheet, room['boq_items'], room, styles, gst_rates)
            # Store calculated totals back into the room dict for the summary sheet
            room['subtotal'] = subtotal
            room['gst'] = gst
            room['total'] = total

    # Add other standard sheets (Summary, Scope, Terms, Version)
    add_proposal_summary_sheet(workbook, rooms_data, styles)
    add_scope_of_work_sheet(workbook)
    add_version_control_sheet(workbook, project_details, client_name)
    add_terms_conditions_sheet(workbook)
    
    # Remove the default sheet
    if "Sheet" in workbook.sheetnames and len(workbook.sheetnames) > 1:
        del workbook["Sheet"]

    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer.getvalue()

# --- All other helper functions for excel generation should be pasted here ---
# add_proposal_summary_sheet, add_scope_of_work_sheet, add_version_control_sheet, add_terms_conditions_sheet
# (They remain largely unchanged from your original code, so I'm omitting them for brevity)
