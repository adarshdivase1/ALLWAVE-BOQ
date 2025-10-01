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
    # Set the height for the two rows that will form the header area
    sheet.row_dimensions[1].height = 50
    sheet.row_dimensions[2].height = 50

    # Merge cells on the left to create containers for the first two logos
    sheet.merge_cells('A1:C2')
    sheet.merge_cells('D1:F2')

    # Merge cells on the right for the other two logos
    sheet.merge_cells('M1:N2')
    sheet.merge_cells('O1:P2')

    # Place each logo in the top-left corner of its merged container
    _add_image_to_cell(sheet, 'assets/company_logo.png', 'A1', 95)
    _add_image_to_cell(sheet, 'assets/crestron_logo.png', 'D1', 95)
    _add_image_to_cell(sheet, 'assets/iso_logo.png', 'M1', 95)
    _add_image_to_cell(sheet, 'assets/avixa_logo.png', 'O1', 95)
    
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
    
    # Version Control Table
    sheet.merge_cells('A3:B3')
    vc_header = sheet['A3']
    vc_header.value = "Version Control"
    vc_header.fill = styles['header_green_fill']
    vc_header.font = styles['black_bold_font']
    vc_header.alignment = Alignment(horizontal='center')
    vc_header.border = styles['thin_border']
    sheet['B3'].border = styles['thin_border']

    vc_data = [
        ("Date of First Draft", datetime.now().strftime("%d-%b-%Y")), 
        ("Date of Final Draft", ""),
        ("", ""), 
        ("", ""),
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

def _add_scope_of_work_sheet(workbook, styles):
    """Creates the detailed Scope of Work sheet with static content matching the template."""
    sheet = workbook.create_sheet(title="Scope of Work", index=2)
    _create_sheet_header(sheet)
    
    # Add title
    sheet.merge_cells('A3:C3')
    title_cell = sheet['A3']
    title_cell.value = "Scope of Work"
    title_cell.font = Font(size=14, bold=True)
    title_cell.alignment = Alignment(horizontal='center')

    # Note section
    row_cursor = 5
    sheet.merge_cells(f'A{row_cursor}:C{row_cursor}')
    note_cell = sheet[f'A{row_cursor}']
    note_cell.value = "Note: This SoW describes the Scope of the Assignment, the Terms, and the Timelines for delivery in order to formalize this assignment. It also intends to share with you the processes and systems that we follow in our engagements with Client."
    note_cell.alignment = Alignment(wrap_text=True, vertical='top')
    sheet.row_dimensions[row_cursor].height = 30
    row_cursor += 2

    sheet.merge_cells(f'A{row_cursor}:C{row_cursor}')
    intro_cell = sheet[f'A{row_cursor}']
    intro_cell.value = "All Wave AV Systems Pvt Ltd (All Wave AV Systems) undertakes to provide the following services to Client as part of the project."
    intro_cell.alignment = Alignment(wrap_text=True, vertical='top')
    sheet.row_dimensions[row_cursor].height = 25
    row_cursor += 2

    scope_data = {
        "Scope of Work": [
            (1, "Site Coordination and Prerequisites Clearance."),
            (2, "Detailed schematic drawings according to the design."),
            (3, "Conduit layout drawings/equipment layout drawings, showing mounting location."),
            (4, "Laying of all AV Cables."),
            (5, "Termination of cables with respective connectors."),
            (6, "Installation of all AV equipment in rack as per layout."),
            (7, "Configuration of Audio/Video Switcher."),
            (8, "Configuration of DSP mixer."),
            (9, "Touch Panel Design."),
            (10, "System programming as per design requirement.")
        ],
        "Exclusions and Dependencies": [
            (1, "Civil work like cutting of false ceilings, chipping, etc."),
            (2, "Electrical work like laying of conduits, raceways, and providing stabilised power supply with zero bias between Earth and Neutral to all required locations"),
            (3, "Carpentry work like cutouts on furniture, etc."),
            (4, "Connectivity for electric power, LAN, telephone, IP (1 Mbps), and ISDN (1 Mbps) & cable TV points where necessary and provision of power circuit for AV system on the same phase"),
            (5, "Ballasts (0 to 10 volts) in case of fluorescent dimming for lights"),
            (6, "Shelves for mounting devices (in case the supply of rack isn't in the SOW)"),
            (7, "Adequate cooling/ventilation for all equipment racks and cabinets")
        ]
    }

    for section_title, items in scope_data.items():
        sheet.merge_cells(f'A{row_cursor}:C{row_cursor}')
        sec_cell = sheet[f'A{row_cursor}']
        sec_cell.value = section_title
        sec_cell.fill = styles['table_header_blue_fill']
        sec_cell.font = styles['bold_font']
        sec_cell.border = styles['thin_border']
        row_cursor += 1
        
        # Header row
        sheet[f'A{row_cursor}'] = "Sr. No"
        sheet[f'A{row_cursor}'].font = styles['bold_font']
        sheet[f'A{row_cursor}'].border = styles['thin_border']
        sheet.merge_cells(f'B{row_cursor}:C{row_cursor}')
        sheet[f'B{row_cursor}'] = "Particulars"
        sheet[f'B{row_cursor}'].font = styles['bold_font']
        sheet[f'B{row_cursor}'].border = styles['thin_border']
        sheet[f'C{row_cursor}'].border = styles['thin_border']
        row_cursor += 1

        for sr_no, particular in items:
            sheet[f'A{row_cursor}'].value = sr_no
            sheet[f'A{row_cursor}'].alignment = Alignment(horizontal='center')
            sheet[f'A{row_cursor}'].border = styles['thin_border']
            sheet.merge_cells(f'B{row_cursor}:C{row_cursor}')
            sheet[f'B{row_cursor}'].value = particular
            sheet[f'B{row_cursor}'].alignment = Alignment(wrap_text=True, vertical='top')
            sheet[f'B{row_cursor}'].border = styles['thin_border']
            sheet[f'C{row_cursor}'].border = styles['thin_border']
            row_cursor += 1
        row_cursor += 1

    sheet.column_dimensions['A'].width = 10
    sheet.column_dimensions['B'].width = 100
    sheet.column_dimensions['C'].width = 20

def _add_proposal_summary_sheet(workbook, rooms_data, styles):
    """Creates the Proposal Summary sheet matching the template format."""
    sheet = workbook.create_sheet(title="Proposal Summary", index=1)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False
    
    # Proposal Summary Table
    row_cursor = 4
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Proposal Summary"
    sheet[f'A{row_cursor}'].font = Font(size=12, bold=True)
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
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

    grand_total_subtotal, grand_total_gst, grand_total_final = 0, 0, 0
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
                grand_total_subtotal += room.get('subtotal', 0)
                grand_total_gst += room.get('gst', 0)
                grand_total_final += room.get('total', 0)
        
        # Grand Total row
        sheet.append(["", "Grand Total", "", "", grand_total_subtotal, grand_total_gst, grand_total_final])

    for row in sheet.iter_rows(min_row=header_row + 1, max_row=sheet.max_row):
        for cell in row:
            if isinstance(cell.value, (int, float)) and cell.column > 3:
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']
            cell.alignment = Alignment(horizontal='center' if cell.column <= 3 else 'right')
    
    # Commercial Terms Section
    row_cursor = sheet.max_row + 3
    
    # Section A: Delivery, Installations & Site Schedule
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Commercial Terms"
    sheet[f'A{row_cursor}'].font = Font(size=12, bold=True)
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
    row_cursor += 2

    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "A. Delivery, Installations & Site Schedule"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    row_cursor += 1

    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "All Wave AV Systems undertake to ensure it's best efforts to complete the assignment for Client within the shortest timelines possible."
    sheet[f'A{row_cursor}'].alignment = Alignment(wrap_text=True)
    row_cursor += 2

    # 1. Project Schedule & Site Requirements
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "1. Project Schedule & Site Requirements"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
    row_cursor += 1

    schedule_data = [
        ("Week 1-3", ""),
        ("All Wave AV Systems", "Design & Procurement"),
        ("Client", "Site Preparations")
    ]
    for label, value in schedule_data:
        sheet[f'B{row_cursor}'].value = label
        sheet.merge_cells(f'C{row_cursor}:D{row_cursor}')
        sheet[f'C{row_cursor}'].value = value
        if label == "Week 1-3":
            sheet[f'B{row_cursor}'].font = sheet[f'C{row_cursor}'].font = styles['bold_font']
        row_cursor += 1
    row_cursor += 1

    # 2. Delivery Terms
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "2. Delivery Terms"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
    row_cursor += 1

    delivery_terms = [
        "Duty Paid INR- Free delivery at site",
        "Direct Import- FOB OR Ex-works of CIF"
    ]
    for term in delivery_terms:
        sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
        sheet[f'A{row_cursor}'].value = term
        row_cursor += 1
    row_cursor += 1

    # NOTE section
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "NOTE"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    row_cursor += 1

    note_items = [
        "a. In case of Direct Import quoted price is exclusive of custom duty and clearing charges. In case these are applicable (for Direct Import orders) they are to borne by Client",
        "b. Cable quantity shown is notional and will be supplied as per site requirement and would be charged Measurement + 10% which will account for bends curves end termination + wastage."
    ]
    for note in note_items:
        sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
        sheet[f'A{row_cursor}'].value = note
        sheet[f'A{row_cursor}'].alignment = Alignment(wrap_text=True)
        sheet.row_dimensions[row_cursor].height = 30
        row_cursor += 1
    row_cursor += 1

    # 3. Deliveries Procedures
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "3. Deliveries Procedures:"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
    row_cursor += 1

    delivery_procedures = [
        "All deliveries will be completed within 6-8 weeks of the receipt of a commercially clear Purchase Order from Client.",
        "All Wave AV Systems will provide a Sales Order Acknowledgement detailing the delivery schedule within 3 days of receipt of this Purchase Order.",
        "Equipment will be delivered in a phased manner as delivery times for various vendors/products differ. However All Wave AV Systems will make all efforts to complete delivery of all INR items within a max of 3 shipments.",
        "Multiple Way bills If required to be given along with the P.O."
    ]
    for procedure in delivery_procedures:
        sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
        sheet[f'A{row_cursor}'].value = procedure
        sheet[f'A{row_cursor}'].alignment = Alignment(wrap_text=True)
        sheet.row_dimensions[row_cursor].height = 25
        row_cursor += 1
    row_cursor += 1

    # 4. Implementation roles
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "4. Implementation roles:"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
    row_cursor += 1

    implementation_roles = [
        "All Wave AV Systems shall complete all aspects of implementation – including design, procurement, installation, programming and documentation – within 12 weeks of release of receipt of advance payment.",
        "Client will ensure that the site is dust-free, ready in all respects and is handed over to All Wave AV Systems within 8 weeks of issue of purchase order so that the above schedule can be met."
    ]
    for role in implementation_roles:
        sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
        sheet[f'A{row_cursor}'].value = role
        sheet[f'A{row_cursor}'].alignment = Alignment(wrap_text=True)
        sheet.row_dimensions[row_cursor].height = 30
        row_cursor += 1
    row_cursor += 1

    # B] Payment Terms
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "B] Payment Terms"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    row_cursor += 2

    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "1. Schedule of Payment"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    sheet[f'A{row_cursor}'].fill = styles['table_header_blue_fill']
    row_cursor += 1

    payment_schedule = [
        ("Item", "Advance Payment"),
        ("For Equipment and Materials (INR)", "20% Advance with PO"),
        ("Installation and Commissioning", "Against system installation")
    ]
    for item, payment in payment_schedule:
        sheet[f'B{row_cursor}'].value = item
        sheet.merge_cells(f'C{row_cursor}:D{row_cursor}')
        sheet[f'C{row_cursor}'].value = payment
        if item == "Item":
            sheet[f'B{row_cursor}'].font = sheet[f'C{row_cursor}'].font = styles['bold_font']
        row_cursor += 1
    row_cursor += 1

    # Note about delays
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Note: Delay in release of advance payment may alter the project schedule and equipment delivery. In the event the project is delayed beyond 12 weeks on account of site delays etc or any circumstance beyond the direct control of All Wave AV Systems, an additional labour charge @ Rs. 8000 + Service Tax per day will apply."
    sheet[f'A{row_cursor}'].alignment = Alignment(wrap_text=True)
    sheet.row_dimensions[row_cursor].height = 40
    row_cursor += 2

    # C] Validity
    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "C] Validity"
    sheet[f'A{row_cursor}'].font = styles['bold_font']
    row_cursor += 1

    sheet.merge_cells(f'A{row_cursor}:G{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Offer Validity :- 7 Days"
    row_cursor += 2

    # Set column widths
    sheet.column_dimensions['A'].width = 12
    sheet.column_dimensions['B'].width = 35
    sheet.column_dimensions['C'].width = 20
    sheet.column_dimensions['D'].width = 20
    sheet.column_dimensions['E'].width = 18
    sheet.column_dimensions['F'].width = 18
    sheet.column_dimensions['G'].width = 18

def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """Creates a fully detailed BOQ sheet for a single room matching the template format."""
    _create_sheet_header(sheet)
    
    # Room Information Section
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
        sheet[f'A{row}'].border = styles['thin_border']
        sheet[f'A{row}'].fill = styles['header_light_green_fill']
        sheet.merge_cells(f'B{row}:C{row}')
        sheet[f'B{row}'].value = value
        sheet[f'B{row}'].border = styles['thin_border']
        sheet[f'C{row}'].border = styles['thin_border']

    # BOQ Table Headers
    headers1 = [
        'Sr. No.', 
        'Description of Goods / Services', 
        'Specifications', 
        'Make', 
        'Model No.', 
        'Qty.', 
        'Unit Rate (INR)', 
        'Total', 
        'SGST\n( In Maharastra)', 
        None, 
        'CGST\n( In Maharastra)', 
        None, 
        'Total (TAX)', 
        'Total Amount (INR)', 
        'Remarks', 
        'Reference image'
    ]
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]
    
    sheet.append([])  # Empty row
    sheet.append([])  # Empty row
    sheet.append(headers1)
    sheet.append(headers2)
    header_start_row = sheet.max_row - 1

    # Merge cells for SGST and CGST headers
    sheet.merge_cells(f'I{header_start_row}:J{header_start_row}')
    sheet.merge_cells(f'K{header_start_row}:L{header_start_row}')
    
    # Format header rows
    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row, min_col=1, max_col=len(headers1)):
        for cell in row:
            cell.fill = styles["table_header_blue_fill"]
            cell.font = styles['bold_font']
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = styles['thin_border']

    # Group items by category
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items:
            grouped_items[cat] = []
        grouped_items[cat].append(item)

    total_before_gst_hardware, total_gst_hardware, item_s_no = 0, 0, 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    # Add items by category
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
            gst_rate = item.get('gst_rate', gst_rates.get('Electronics', 18))
            sgst_rate, cgst_rate = gst_rate / 2, gst_rate / 2
            sgst_amount, cgst_amount = subtotal * (sgst_rate / 100), subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            total_with_gst = subtotal + total_tax
            total_before_gst_hardware += subtotal
            total_gst_hardware += total_tax

            row_data = [
                item_s_no, 
                item.get('specifications', item.get('name', '')), 
                "", 
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
                ""
            ]
            sheet.append(row_data)
            item_s_no += 1

    # Add Services Category
    services = [
        ("Installation & Commissioning", 0.15), 
        ("System Warranty (3 Years)", 0.05), 
        ("Project Management", 0.10)
    ]
    services_letter = chr(ord('A') + len(grouped_items))
    total_before_gst_services, total_gst_services = 0, 0
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
            sgst_amount, cgst_amount = service_amount_inr * (sgst_rate / 100), service_amount_inr * (cgst_rate / 100)
            total_tax_service = sgst_amount + cgst_amount
            total_with_gst_service = service_amount_inr + total_tax_service
            total_before_gst_services += service_amount_inr
            total_gst_services += total_tax_service

            row_data = [
                item_s_no, 
                service_name, 
                "", 
                "", 
                "", 
                1, 
                service_amount_inr, 
                service_amount_inr, 
                f"{sgst_rate}%", 
                sgst_amount, 
                f"{cgst_rate}%", 
                cgst_amount, 
                total_tax_service, 
                total_with_gst_service, 
                "", 
                ""
            ]
            sheet.append(row_data)
            item_s_no += 1

    # Grand Total Row
    grand_total_before_gst = total_before_gst_hardware + total_before_gst_services
    grand_total_gst = total_gst_hardware + total_gst_services
    grand_total_with_gst = grand_total_before_gst + grand_total_gst

    sheet.append([
        "", 
        "Grand Total", 
        "", 
        "", 
        "", 
        "", 
        "", 
        grand_total_before_gst, 
        "", 
        "", 
        "", 
        "", 
        grand_total_gst, 
        grand_total_with_gst, 
        "", 
        ""
    ])

    # Format all data rows
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            cell.border = styles['thin_border']
            if cell.column in [7, 8, 10, 12, 13, 14]:  # Currency columns
                if isinstance(cell.value, (int, float)):
                    cell.number_format = styles['currency_format']
                    cell.alignment = Alignment(horizontal='right')
            elif cell.column in [1, 6]:  # Sr. No and Qty columns
                cell.alignment = Alignment(horizontal='center')
            else:
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)

    # Set column widths
    column_widths = {
        'A': 8, 'B': 35, 'C': 30, 'D': 15, 'E': 20, 'F': 8, 
        'G': 15, 'H': 15, 'I': 8, 'J': 12, 'K': 8, 'L': 12, 
        'M': 12, 'N': 15, 'O': 25, 'P': 15
    }
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width

    return {
        'subtotal': grand_total_before_gst,
        'gst': grand_total_gst,
        'total': grand_total_with_gst
    }


def generate_company_excel(rooms_data, project_details, usd_to_inr_rate=83.0, gst_rates=None):
    """
    Main function to generate the complete professional BOQ Excel workbook.
    
    Args:
        rooms_data: List of dicts with 'name' and 'items' (list of equipment)
        project_details: Dict with project metadata
        output_path: Where to save the Excel file
        usd_to_inr_rate: USD to INR conversion rate
        gst_rates: Dict of GST rates by category
    """
    if gst_rates is None:
        gst_rates = {'Electronics': 18, 'Services': 18}
    
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)  # Remove default sheet
    styles = _define_styles()

    # Add Version Control sheet
    _add_version_control_sheet(workbook, project_details, styles)

    # Add Proposal Summary sheet (placeholder, will update after room sheets)
    room_summaries = []

    # Create BOQ sheets for each room
    for room in rooms_data:
        room_name = room.get('name', 'Room')
        sheet = workbook.create_sheet(title=room_name[:31])  # Excel sheet name limit
        room_summary = _populate_room_boq_sheet(
            sheet, 
            room.get('items', []), 
            room_name, 
            styles, 
            usd_to_inr_rate, 
            gst_rates
        )
        room_summaries.append({
            'name': room_name,
            'subtotal': room_summary['subtotal'],
            'gst': room_summary['gst'],
            'total': room_summary['total']
        })

    # Update Proposal Summary with calculated totals
    _add_proposal_summary_sheet(workbook, room_summaries, styles)
    
    # Add Scope of Work sheet
    _add_scope_of_work_sheet(workbook, styles)

    workbook.save(output_path)
    return output_path
