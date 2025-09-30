import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter
import requests
from PIL import Image as PILImage
from io import BytesIO
import re
from datetime import datetime

# --- Helper Functions ---

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

def _add_image_to_cell(sheet, image_path, cell, height, width):
    """Helper to add an image to a specific cell with error handling."""
    try:
        img = ExcelImage(image_path)
        img.height = height
        img.width = width
        sheet.add_image(img, cell)
    except FileNotFoundError:
        sheet[cell] = f"Missing: {image_path}"

def _create_sheet_header(sheet, styles):
    """Creates the standard header with logos and title for a sheet."""
    sheet.row_dimensions[1].height = 65

    # Main logo on the left
    # NOTE: Ensure 'company_logo.png', etc. are in the same directory as your app script.
    _add_image_to_cell(sheet, 'assets/company_logo.png', 'A1', 60, 120)
    
    # Crestron logo next to the main logo
    _add_image_to_cell(sheet, 'assets/crestron_logo.png', 'C1', 55, 100)

    # Certification logos on the far right
    _add_image_to_cell(sheet, 'assets/iso_logo.png', 'N1', 55, 55)
    _add_image_to_cell(sheet, 'assets/avixa_logo.png', 'O1', 55, 100)

    # Main title bar below the logos
    sheet.merge_cells('A3:P3')
    header_cell = sheet['A3']
    header_cell.value = "All Wave AV Systems Pvt. Ltd."
    header_cell.font = styles["header"]
    header_cell.fill = styles["header_fill"]
    header_cell.alignment = Alignment(horizontal='center', vertical='center')


def _add_product_image_to_excel(sheet, row_num, image_url, column='P'):
    """Add product image from a URL to an Excel cell."""
    if not isinstance(image_url, str) or not image_url.strip():
        return
    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            pil_image = PILImage.open(BytesIO(response.content))
            pil_image.thumbnail((100, 100), PILImage.Resampling.LANCZOS)

            img_buffer = BytesIO()
            pil_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            excel_img = ExcelImage(img_buffer)
            excel_img.width = 80
            excel_img.height = 80

            sheet.add_image(excel_img, f'{column}{row_num}')
            sheet.row_dimensions[row_num].height = 60
    except Exception:
        sheet[f'{column}{row_num}'] = "Image unavailable"

# --- Sheet Population Functions ---

def _populate_company_boq_sheet(sheet, items, room_name, project_details, styles, usd_to_inr_rate, gst_rates):
    """Populates a single Excel sheet with detailed BOQ data."""
    _create_sheet_header(sheet, styles)
    
    # Project & Contact Info Section
    sheet['C5'] = "Project Name"; sheet['E5'] = project_details.get('Project Name', 'N/A')
    sheet['C6'] = "Client Name"; sheet['E6'] = project_details.get('Client Name', 'N/A')
    sheet['C7'] = "Location"; sheet['E7'] = project_details.get('Location', 'N/A')
    sheet['C8'] = "Room Name / Type"; sheet['E8'] = room_name

    sheet['I5'] = "Design Engineer"; sheet['K5'] = project_details.get('Design Engineer', 'N/A')
    sheet['I6'] = "Account Manager"; sheet['K6'] = project_details.get('Account Manager', 'N/A')
    sheet['I7'] = "Key Client Personnel"; sheet['K7'] = project_details.get('Key Client Personnel', 'N/A')
    sheet['I8'] = "Key Comments"; sheet['K8'] = project_details.get('Key Comments', 'N/A')

    # Apply bold style to all labels and values
    info_cells = ['C5', 'E5', 'C6', 'E6', 'C7', 'E7', 'C8', 'E8', 
                  'I5', 'K5', 'I6', 'K6', 'I7', 'K7', 'I8', 'K8']
    for cell_ref in info_cells:
        sheet[cell_ref].font = styles['bold']
    sheet['K8'].alignment = Alignment(wrap_text=True) # Wrap comments text

    # Table Headers
    headers1 = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST\n( In Maharastra)', None, 'CGST\n( In Maharastra)', None, 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]

    sheet.append([]); sheet.append([]); sheet.append([]) # Spacers
    sheet.append(headers1)
    sheet.append(headers2)
    header_start_row = sheet.max_row - 1

    # Merge header cells and apply styles
    sheet.merge_cells(start_row=header_start_row, start_column=9, end_row=header_start_row, end_column=10)
    sheet.merge_cells(start_row=header_start_row, start_column=11, end_row=header_start_row, end_column=12)
    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row, min_col=1, max_col=16):
        for cell in row:
            if cell.value is not None:
                cell.font = styles["table_header"]
                cell.fill = styles["table_header_fill"]
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Group and add items
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items:
            grouped_items[cat] = []
        grouped_items[cat].append(item)

    total_before_gst_hardware, total_gst_hardware = 0, 0
    item_s_no = 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    for i, (category, cat_items) in enumerate(grouped_items.items()):
        sheet.append([f"{category_letters[i]}", category])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=16)
        sheet[f'A{cat_row_idx}'].font = sheet[f'B{cat_row_idx}'].font = styles['bold']
        sheet[f'A{cat_row_idx}'].fill = sheet[f'B{cat_row_idx}'].fill = styles['group_header_fill']

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
                item_s_no, None, item.get('specifications', item.get('name', '')), item.get('brand', 'Unknown'),
                item.get('name', 'Unknown'), item.get('quantity', 1), unit_price_inr, subtotal,
                f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", cgst_amount, total_tax, total_with_gst,
                item.get('justification', ''), None
            ])
            _add_product_image_to_excel(sheet, sheet.max_row, item.get('image_url', ''))
            item_s_no += 1
    
    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    services_letter = chr(ord('A') + len(grouped_items))
    total_before_gst_services, total_gst_services = 0, 0
    services_gst_rate = gst_rates.get('Services', 18)

    if services and total_before_gst_hardware > 0:
        sheet.append([services_letter, "Services"])
        cat_row_idx = sheet.max_row
        sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=16)
        
        for service_name, percentage in services:
            service_amount_inr = total_before_gst_hardware * percentage
            sgst_rate, cgst_rate = services_gst_rate / 2, services_gst_rate / 2
            service_sgst, service_cgst = service_amount_inr * (sgst_rate / 100), service_amount_inr * (cgst_rate / 100)
            service_total_tax = service_sgst + service_cgst
            service_total = service_amount_inr + service_total_tax
            total_before_gst_services += service_amount_inr
            total_gst_services += service_total_tax
            sheet.append([
                item_s_no, None, "Certified professional service", "AllWave AV", service_name, 1,
                service_amount_inr, service_amount_inr, f"{sgst_rate}%", service_sgst,
                f"{cgst_rate}%", service_cgst, service_total_tax, service_total, "As per standard terms", ""
            ])
            item_s_no += 1
    
    sheet.append([])
    if total_before_gst_hardware > 0:
      sheet.append(["", "Total for Hardware", "", "", "", "", "", total_before_gst_hardware, "", "", "", "", total_gst_hardware, total_before_gst_hardware + total_gst_hardware])
    if total_before_gst_services > 0:
      sheet.append(["", "Total for Services", "", "", "", "", "", total_before_gst_services, "", "", "", "", total_gst_services, total_before_gst_services + total_gst_services])
    grand_total = (total_before_gst_hardware + total_gst_hardware) + (total_before_gst_services + total_gst_services)
    sheet.append([])
    grand_total_row_idx = sheet.max_row + 1
    sheet[f'M{grand_total_row_idx}'] = "Grand Total (INR)"
    sheet[f'N{grand_total_row_idx}'] = grand_total
    
    column_widths = {'A': 8, 'B': 35, 'C': 45, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 10, 'J': 15, 'K': 10, 'L': 15, 'M': 15, 'N': 18, 'O': 40, 'P': 15}
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width
    
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            if cell.column >= 7 and isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']

    return total_before_gst_hardware + total_before_gst_services, total_gst_hardware + total_gst_services, grand_total

def _add_proposal_summary_sheet(workbook, rooms_data, styles):
    """Adds the Proposal Summary sheet."""
    if "Proposal Summary" in workbook.sheetnames:
        summary_sheet = workbook["Proposal Summary"]
        for row in range(summary_sheet.max_row, 6, -1):
            summary_sheet.delete_rows(row, 1)
    else:
        summary_sheet = workbook.create_sheet(title="Proposal Summary", index=0)
        _create_sheet_header(summary_sheet, styles)
    
        summary_sheet.merge_cells('A5:D5')
        sub_header = summary_sheet['A5']
        sub_header.value = "Commercial Proposal Summary"
        sub_header.font = Font(size=14, bold=True)
        sub_header.alignment = Alignment(horizontal='center')

        headers = ["Description", "Amount (INR) Without Tax", "GST Amount (INR)", "Total Amount (INR) With Tax"]
        summary_sheet.append([])
        summary_sheet.append(headers)
        
        header_row_idx = summary_sheet.max_row
        for cell in summary_sheet[header_row_idx]:
            cell.fill = styles['table_header_fill']
            cell.font = styles['table_header']

    grand_total = 0
    for room in rooms_data:
        if room.get('total'):
            summary_sheet.append([
                room['name'], room.get('subtotal', 0),
                room.get('gst', 0), room.get('total', 0)
            ])
            grand_total += room.get('total', 0)

    summary_sheet.append([])
    summary_sheet.append(["Grand Total", "", "", grand_total])
    total_row_idx = summary_sheet.max_row

    for row in summary_sheet.iter_rows(min_row=8, max_row=total_row_idx):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
    summary_sheet[f'A{total_row_idx}'].font = styles['bold']
    summary_sheet[f'D{total_row_idx}'].font = styles['bold']
    
    for col in ['A', 'B', 'C', 'D']:
        summary_sheet.column_dimensions[col].width = 30


def _add_scope_of_work_sheet(workbook, styles):
    """Adds the static Scope of Work sheet."""
    sow_sheet = workbook.create_sheet(title="Scope of Work")
    _create_sheet_header(sow_sheet, styles)
    sow_sheet.merge_cells('A5:D5')
    sow_sheet['A5'] = "Scope of Work"
    sow_sheet['A5'].font = Font(size=14, bold=True)
    sow_sheet['A5'].alignment = Alignment(horizontal='center')
    
    scope = {
        "INCLUSIONS": ["Supply of Equipment as per the Bill of Quantity.", "Installation & Commissioning of the specified AV equipment.", "System integration and programming as required.", "Basic user training and system handover."],
        "EXCLUSIONS": ["Any Civil Work, Masonry, Carpentry, POP, False Ceiling, Painting, etc.", "Electrical Work including Raw Power, Cabling, Conduits, Raceways.", "Network infrastructure including switches, routers, and cabling not specified in the BOQ.", "Any software, licenses, or subscriptions not explicitly mentioned.", "Coordination with any third-party vendors not under our direct scope."]
    }
    row = 7
    for section, points in scope.items():
        sow_sheet[f'A{row}'] = section
        sow_sheet[f'A{row}'].font = Font(bold=True)
        row += 1
        for point in points:
            sow_sheet[f'B{row}'] = point
            row += 1
        row += 1
    sow_sheet.column_dimensions['A'].width = 25
    sow_sheet.column_dimensions['B'].width = 100


def _add_version_control_sheet(workbook, project_name, client_name, styles):
    """Adds the Version Control sheet."""
    vc_sheet = workbook.create_sheet(title="Version Control")
    _create_sheet_header(vc_sheet, styles)
    
    vc_sheet['A5'] = "Project Name:"; vc_sheet['B5'] = project_name
    vc_sheet['A6'] = "Client Name:"; vc_sheet['B6'] = client_name
    
    headers = ["Version", "Date", "Description", "Author"]
    vc_sheet.append([]); vc_sheet.append([]); 
    vc_sheet.append(headers)
    header_row = vc_sheet.max_row
    
    vc_sheet.append(["1.0", datetime.now().strftime("%Y-%m-%d"), "Initial Proposal", "System"])
    
    for cell in vc_sheet[header_row]: cell.font = Font(bold=True); cell.fill = styles['group_header_fill']
    for col in ['A', 'B', 'C', 'D']: vc_sheet.column_dimensions[col].width = 25


def _add_terms_conditions_sheet(workbook, styles):
    """Adds a static Terms & Conditions sheet."""
    tc_sheet = workbook.create_sheet(title="Terms & Conditions")
    _create_sheet_header(tc_sheet, styles)
    tc_sheet.merge_cells('A5:D5')
    tc_sheet['A5'] = "Commercial Terms & Conditions"
    tc_sheet['A5'].font = Font(size=14, bold=True)
    tc_sheet['A5'].alignment = Alignment(horizontal='center')

    terms = [
        ("Payment Terms", "50% Advance with Purchase Order, 40% on Delivery of Material, 10% on Handover."),
        ("Validity", "This proposal is valid for 30 days from the date of submission."),
        ("Taxes", "All prices are exclusive of GST, which will be charged as applicable at the time of billing."),
        ("Warranty", "Standard manufacturer's warranty applies to all hardware components. A 3-year system warranty is included as part of the service charges."),
        ("Delivery", "4-6 weeks from the date of receipt of advance payment and confirmed purchase order."),
    ]
    row = 7
    for title, text in terms:
        tc_sheet[f'A{row}'] = title
        tc_sheet[f'A{row}'].font = Font(bold=True)
        tc_sheet[f'B{row}'] = text
        tc_sheet.row_dimensions[row].height = 30
        tc_sheet[f'B{row}'].alignment = Alignment(wrap_text=True, vertical='top')
        row += 1
    tc_sheet.column_dimensions['A'].width = 25
    tc_sheet.column_dimensions['B'].width = 100

# --- Main Public Function ---

def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """
    Generate a complete, multi-sheet Excel file in the company standard format.
    """
    if not rooms_data: return None

    workbook = openpyxl.Workbook()
    styles = _define_styles()

    project_name = project_details.get('Project Name', 'AV Installation Project')
    client_name = project_details.get('Client Name', 'Valued Client')
    gst_rates = project_details.get('gst_rates', {'Electronics': 18, 'Services': 18})

    # Add standard sheets first
    _add_proposal_summary_sheet(workbook, [], styles) 
    _add_scope_of_work_sheet(workbook, styles)
    _add_version_control_sheet(workbook, project_name, client_name, styles)
    _add_terms_conditions_sheet(workbook, styles)
    
    # Generate sheets for each room and store their totals
    for room in rooms_data:
        if room.get('boq_items'):
            safe_room_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:30]
            room_sheet = workbook.create_sheet(title=safe_room_name)
            subtotal, gst, total = _populate_company_boq_sheet(
                room_sheet, room['boq_items'], room['name'], project_details, styles, usd_to_inr_rate, gst_rates
            )
            room['subtotal'], room['gst'], room['total'] = subtotal, gst, total
    
    # Re-populate the summary sheet with the final data
    _add_proposal_summary_sheet(workbook, rooms_data, styles)

    # Remove the default sheet
    if "Sheet" in workbook.sheetnames:
        del workbook["Sheet"]

    # Save to a memory buffer
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer.getvalue()
