import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter
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
    
    # Add company logo
    # IMPORTANT: Ensure 'allwave_logo.png' is in a folder named 'assets'
    _add_image_to_cell(sheet, 'assets/allwave_logo.png', 'A1', 55)

    # Add taglines
    sheet.merge_cells('M1:P1')
    tagline_cell = sheet['M1']
    tagline_cell.value = "Service     Quality     Innovation"
    tagline_cell.font = Font(size=14, bold=True)
    tagline_cell.alignment = Alignment(horizontal='right', vertical='center')

    # Add "25+ Years" box
    sheet.merge_cells('M2:P2')
    years_cell = sheet['M2']
    years_cell.value = "25+\nYears"
    years_cell.font = Font(size=14, bold=True)
    years_cell.alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
    sheet.row_dimensions[2].height = 30

# --- Sheet Generation Functions ---

def _add_contact_details_sheet(workbook, project_details, styles):
    """Creates the 'Contact Details' sheet as seen on Page 2 of the PDF."""
    sheet = workbook.create_sheet(title="Contact Details", index=0)
    sheet.sheet_view.showGridLines = False

    # Set column widths
    for col in ['A', 'C']:
        sheet.column_dimensions[col].width = 25
    sheet.column_dimensions['B'].width = 40
    
    sheet.row_dimensions[1].height = 30
    sheet['A1'].value = "Contact Details"
    sheet['A1'].font = Font(size=16, bold=True)

    contact_data = [
        ("Design Engineer", project_details.get("Design Engineer", "")),
        ("Account Manager", project_details.get("Account Manager", "")),
        ("Client Name", project_details.get("Client Name", "")),
        ("Key Client Personnel", project_details.get("Key Client Personnel", "")),
        ("Location", project_details.get("Location", "")),
        ("Key Comments for this version", project_details.get("Key Comments", ""))
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
    """Creates the Proposal Summary and Commercial Terms sheet from Pages 7-9 of the PDF."""
    sheet = workbook.create_sheet(title="Proposal Summary & Terms", index=1)
    _create_sheet_header(sheet, styles)
    
    row_cursor = 4

    # --- Proposal Summary Table ---
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
        # Create a summary of room options
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

    # --- Commercial Terms Section (Static Content) ---
    sheet.merge_cells(f'A{row_cursor}:P{row_cursor}')
    sheet[f'A{row_cursor}'].value = "Commercial Terms"
    sheet[f'A{row_cursor}'].font = Font(size=14, bold=True)
    row_cursor += 2
    
    # Use a list to hold all static text sections for easy rendering
    terms_content = [
        ("header", "A. Delivery, Installations & Site Schedule"),
        ("text", "All Wave AV Systems undertake to ensure it's best efforts to complete the assignment for Client within the shortest timelines possible."),
        ("sub_header", "1. Project Schedule & Site Requirements"),
        ("table", [["All Wave AV Systems", "Design & Procurement (Week 1-3)"], ["Client", "Site Preparations"]]),
        ("sub_header", "2. Delivery Terms"),
        ("table", [["Duty Paid INR", "Free delivery at site"], ["Direct Import", "FOB OR Ex-works of CIF"]]),
        ("note", "NOTE: a. In case of Direct Import quoted price is exclusive of custom duty and clearing charges. In case these are applicable (for Direct Import orders) they are to borne by Client. \nb. Cable quantity shown is notional and will be supplied as per site requirement and would be charged Measurement account for bends curves end termination + wastage."),
        ("sub_header", "3. Deliveries Procedures:"),
        ("text", "All deliveries will be completed within 6-8 weeks of the receipt of a commercially clear Purchase Order from Client. All Wave AV Systems will provide a Sales Order Acknowledgement detailing the delivery schedule within 3 days of receipt of this Purchase Order."),
        ("sub_header", "4. Implementation roles:"),
        ("text", "All Wave AV Systems shall complete all aspects of implementation - including design, procurement, installation, programming and documentation - within 12 weeks of release of receipt of advance payment. Client will ensure that the site is dust-free, ready in all respects and is handed over to All Wave AV Systems within 8 weeks of issue of purchase order so that the above schedule can be met."),
        ("header", "B] Payment Terms"),
        ("sub_header", "1. Schedule of Payment"),
        ("table", [["Item", "Advance Payment"], ["For Equipment and Materials (INR)", "20% Advance with PO"]]),
        ("note", "Note: Delay in release of advance payment may alter the project schedule and equipment delivery. In the event the project is delayed beyond 12 weeks on account of site delays etc or any circumstance beyond the direct control of All Wave AV Systems, an additional labour charge @ Rs. 8000 + Service Tax per day will apply."),
        ("header", "C] Validity"),
        ("text", "Offer Validity:- 7 Days"),
        ("header", "D] Placing a Purchase Order"),
        ("text", "a. In case of Duty Paid INR: Order should be placed on All Wave AV Systems Pvt. Ltd. 420A Shah & Nahar Industrial Estate, Lower Parel West Mumbai 400013 INDIA"),
        ("text", "b. In case of Direct Import Orders on Quantum AV Pte Ltd"),
        ("header", "E] Cable Estimates"),
        ("text", "At this time All Wave AV Systems has provided Client with a provisional estimate for the various types of cabling required during the course of the project. However, this estimate can vary slightly or significantly depending upon the finalized layouts. Total Chargeable Cable Quantity = Physical measurement of cable distance + 10% additional cable length on account of bends, curves, end termination etc."),
        ("header", "G] Restocking / Cancellation Fees:"),
        ("text", "Client recognizes that any cancellation of orders already placed may cause an irrecoverable loss to All Wave AV Systems and therefore may involve extra charges: 1. Cancellation may involve a charge of upto 50% re-stocking/cancellation fees + shipping costs and additional charges."),
        ("header", "H] Warranty"),
        ("text", "All Wave AV Systems undertakes to provide Client with a Limited Period Warranty on certain consumables, which includes Warranty on the Projector Lamp (450 hours of use or 90 days from purchase whichever is earlier) and warranty on other consumables like Filters and Touch Panel Battery (90 days)."),
        ("note", "However, Client understands that the warranty cannot be applicable in the following situations:\n1. Power related damage to the system on account of power fluctuations or spikes.\n2. Accident, misuse, neglect, alteration modification or substitution of any component of the equipment.\n3. Any loss or damage resulting from fire, flood, exposure to weather conditions and any other force majeure/ act of god.")
    ]
    
    for item_type, content in terms_content:
        sheet.merge_cells(f'A{row_cursor}:P{row_cursor}')
        cell = sheet[f'A{row_cursor}']
        
        if item_type in ["header", "sub_header", "note"]:
            cell.font = styles['bold_font']
        
        if item_type == "text" or item_type == "note":
             cell.value = content
             cell.alignment = Alignment(wrap_text=True, vertical='top')
             sheet.row_dimensions[row_cursor].height = max(40, 20 * (content.count('\n') + 1))
             row_cursor += 1
        elif item_type == "header":
            cell.value = content
            cell.fill = styles['table_header_blue_fill']
            cell.font = styles['white_bold_font']
            row_cursor += 1
        elif item_type == "sub_header":
             cell.value = content
             row_cursor += 1
        elif item_type == "table":
            table_start_row = row_cursor
            for r_idx, row_data in enumerate(content):
                sheet[f'A{row_cursor}'].value = row_data[0]
                sheet.merge_cells(f'B{row_cursor}:C{row_cursor}')
                sheet[f'B{row_cursor}'].value = row_data[1]
                if r_idx == 0:
                     sheet[f'A{row_cursor}'].font = sheet[f'B{row_cursor}'].font = styles['bold_font']
                row_cursor += 1
            for r in range(table_start_row, row_cursor):
                for c_char in ['A', 'B', 'C']:
                    sheet[f'{c_char}{r}'].border = styles['thin_border']
        row_cursor += 1

def _add_scope_of_work_sheet(workbook, styles):
    """Creates the detailed Scope of Work sheet from Pages 3-4 of the PDF."""
    sheet = workbook.create_sheet(title="Scope of Work", index=2)
    _create_sheet_header(sheet, styles)

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
            (9, "Touch Panel Design & System programming as per design requirement.")
        ],
        "Exclusions and Dependencies": [
            (1, "Civil work like cutting of false ceilings, chipping, etc."),
            (2, "Electrical work like laying of conduits, raceways, and providing stabilised power supply with zero bias between Earth and Neutral to all required locations."),
            (3, "Carpentry work like cutouts on furniture, etc."),
            (4, "Connectivity for electric power, LAN, telephone, IP (1 Mbps), and ISDN (1 Mbps) & cable TV points where necessary and provision of power circuit for AV system on the same phase."),
            (5, "Ballasts (0 to 10 volts) in case of fluorescent dimming for lights."),
            (6, "Shelves for mounting devices (in case the supply of rack isn't in the SOW)."),
            (7, "Adequate cooling/ventilation for all equipment racks and cabinets.")
        ],
        "Storage and Insurance": [
            (1, "Provide storage space for materials in a secure, clean, termite free and dry space. This is essential to protect the equipment during the implementation stage."),
            (2, "Organize Insurance (against theft, loss or damage by third party) of materials at site."),
            (3, "During the period of installation, any shortage of material due to pilferage, misplacement etc. at site would be in client's account."),
        ],
        "Project Commissioning & Documentation": [
            ("ATP and Handover", "ATP and Handover documents to be signed within 3 days of project completion, including resolution of all snags."),
            ("Project Documentation", "All Wave AV Systems will submit comprehensive site documentation containing As-Built Drawings, System Schematics, User Manual and support / escalation related information (1 set hardcopy)."),
            ("Training", "User Training on the features, functions and usage of the installed AV system & Maintenance Training for the appropriate personnel on the first level of maintenance required.")
        ]
    }

    row_cursor = 4
    for section_title, items in scope_data.items():
        sheet.merge_cells(f'A{row_cursor}:P{row_cursor}')
        sec_cell = sheet[f'A{row_cursor}']
        sec_cell.value = section_title
        sec_cell.fill = styles['table_header_blue_fill']
        sec_cell.font = styles['white_bold_font']
        row_cursor += 1
        
        # Headers for the table
        sheet[f'A{row_cursor}'] = "Sr. No"
        sheet.merge_cells(f'B{row_cursor}:P{row_cursor}')
        sheet[f'B{row_cursor}'] = "Particulars"
        sheet[f'A{row_cursor}'].font = sheet[f'B{row_cursor}'].font = styles['bold_font']
        row_cursor += 1

        for sr_no, particular in items:
            sheet[f'A{row_cursor}'].value = sr_no
            sheet.merge_cells(f'B{row_cursor}:P{row_cursor}')
            sheet[f'B{row_cursor}'].value = particular
            sheet[f'B{row_cursor}'].alignment = Alignment(wrap_text=True, vertical='top')
            sheet.row_dimensions[row_cursor].height = 30
            row_cursor += 1
        row_cursor += 1

    sheet.column_dimensions['A'].width = 10
    sheet.column_dimensions['B'].width = 120

def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """Creates a fully detailed BOQ sheet for a single room, matching the PDF format."""
    _create_sheet_header(sheet, styles)
    
    # --- Room Info Section ---
    info_data = [
        ("Room Name / Room Type", room_name), 
        ("Floor", "-"), 
        ("Number of Seats", "-"), 
        ("Number of Rooms", "-")
    ]
    for i, (label, value) in enumerate(info_data):
        row = i + 4
        sheet[f'A{row}'].value = label
        sheet[f'A{row}'].font = styles['bold_font']
        sheet.merge_cells(f'B{row}:D{row}')
        sheet[f'B{row}'].value = value
        for col in ['A', 'B', 'C', 'D']:
            sheet[f'{col}{row}'].border = styles['thin_border']
            sheet[f'A{row}'].fill = styles['header_green_fill']

    # --- BOQ Table Headers (Two Rows) ---
    header_start_row = 9
    headers1 = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST', None, 'CGST', None, 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]
    
    sheet.insert_rows(header_start_row, amount=2)
    for c_idx, val in enumerate(headers1):
        sheet.cell(row=header_start_row, column=c_idx + 1, value=val)
    for c_idx, val in enumerate(headers2):
        sheet.cell(row=header_start_row + 1, column=c_idx + 1, value=val)

    # Merge cells in the first header row
    sheet.merge_cells(start_row=header_start_row, start_column=9, end_row=header_start_row, end_column=10) # SGST
    sheet.merge_cells(start_row=header_start_row, start_column=11, end_row=header_start_row, end_column=12) # CGST
    
    for c in range(1, len(headers1) + 1):
        for r in range(header_start_row, header_start_row + 2):
            cell = sheet.cell(row=r, column=c)
            if cell.value is not None:
                cell.fill = styles["table_header_blue_fill"]
                cell.font = styles['bold_font']
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = styles['thin_border']
            # Also apply border to empty sub-header cells
            sheet.cell(row=r, column=c).border = styles['thin_border']


    # --- Group Items by Category and Populate Table ---
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General')
        if cat not in grouped_items: grouped_items[cat] = []
        grouped_items[cat].append(item)

    row_cursor = header_start_row + 2
    total_before_gst_hardware, item_s_no = 0, 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]

    for i, (category, cat_items) in enumerate(grouped_items.items()):
        sheet.cell(row=row_cursor, column=1, value=category_letters[i])
        sheet.cell(row=row_cursor, column=2, value=category)
        sheet.merge_cells(f'B{row_cursor}:P{row_cursor}')
        for col in range(1, 17):
            cell = sheet.cell(row=row_cursor, column=col)
            cell.fill = styles['boq_category_fill']
            cell.font = styles['bold_font']
        row_cursor += 1
        
        for item in cat_items:
            unit_price_inr = item.get('price', 0) * usd_to_inr_rate
            quantity = item.get('quantity', 1)
            subtotal = unit_price_inr * quantity
            gst_rate = item.get('gst_rate', gst_rates.get('Electronics', 18))
            sgst_rate, cgst_rate = gst_rate / 2, gst_rate / 2
            sgst_amount, cgst_amount = subtotal * (sgst_rate / 100), subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            
            row_data = [
                item_s_no, item.get('description', ''), item.get('specifications', ''), 
                item.get('brand', 'Unknown'), item.get('name', 'Unknown'), quantity, 
                unit_price_inr, subtotal, f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", 
                cgst_amount, total_tax, subtotal + total_tax, item.get('justification', ''), ""
            ]
            sheet.append(row_data)
            total_before_gst_hardware += subtotal
            item_s_no += 1
            row_cursor += 1

    # --- Add Services Section ---
    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    services_gst_rate = gst_rates.get('Services', 18)

    if services and total_before_gst_hardware > 0:
        sheet.cell(row=row_cursor, column=1, value=chr(ord('A') + len(grouped_items)))
        sheet.cell(row=row_cursor, column=2, value="Services")
        sheet.merge_cells(f'B{row_cursor}:P{row_cursor}')
        for col in range(1, 17): sheet.cell(row=row_cursor, column=col).fill = styles['boq_category_fill']
        row_cursor += 1

        for service_name, percentage in services:
            service_amount = total_before_gst_hardware * percentage
            sgst_rate, cgst_rate = services_gst_rate / 2, services_gst_rate / 2
            sgst_amount = service_amount * (sgst_rate / 100)
            cgst_amount = service_amount * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount
            
            row_data = [
                item_s_no, "Certified professional service", "", "AllWave AV", service_name, 1,
                service_amount, service_amount, f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%",
                cgst_amount, total_tax, service_amount + total_tax, "As per standard terms", ""
            ]
            sheet.append(row_data)
            item_s_no += 1
            row_cursor += 1

    # --- Final Formatting and Column Widths ---
    column_widths = {'A': 8, 'B': 35, 'C': 45, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 10, 'J': 15, 'K': 10, 'L': 15, 'M': 15, 'N': 18, 'O': 40, 'P': 15}
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width
    
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            if cell.column >= 7 and isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']
            cell.border = styles['thin_border']
            if cell.column in [1, 6]:
                 cell.alignment = Alignment(horizontal='center')


# --- Main Entry Point ---
def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """Main function to generate the complete Excel workbook in the company format."""
    workbook = openpyxl.Workbook()
    # Remove the default sheet created by openpyxl
    if "Sheet" in workbook.sheetnames:
        del workbook["Sheet"]
        
    styles = _define_styles()

    _add_contact_details_sheet(workbook, project_details, styles)
    _add_summary_and_terms_sheet(workbook, rooms_data, styles)
    _add_scope_of_work_sheet(workbook, styles)
    
    # Create a new BOQ sheet for each room in the data
    for room in rooms_data:
        if room.get('boq_items'):
            # Sanitize room name to be a valid Excel sheet title
            safe_name = re.sub(r'[\\/*?:"<>|]', '_', room['name'])[:25]
            room_sheet = workbook.create_sheet(title=f"BOQ - {safe_name}")
            _populate_room_boq_sheet(
                room_sheet, 
                room['boq_items'], 
                room['name'], 
                styles, 
                usd_to_inr_rate, 
                project_details.get('gst_rates', {})
            )

    workbook.active = workbook["Contact Details"]

    # Save the workbook to a memory buffer
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()

# --- Example Usage ---
if __name__ == '__main__':
    # This is a sample of how to call the function.
    # Replace this with your actual data.

    # 1. Define Project Details
    project_info = {
        "Design Engineer": "Rohan Sharma",
        "Account Manager": "Priya Singh",
        "Client Name": "Global Tech Innovations Ltd.",
        "Key Client Personnel": "Mr. Anand Kumar",
        "Location": "Mumbai",
        "Key Comments": "Initial draft based on the meeting of Oct 1, 2025. Awaiting final floor plans.",
        "gst_rates": {
            "Electronics": 18,
            "Services": 18
        }
    }

    # 2. Define Room Data and BOQ items
    # You can have multiple rooms, even of the same type
    rooms = [
        {
            "name": "Huddle Room - Option 1",
            "boq_items": [
                {'name': 'Logitech Rally Bar Mini', 'description': 'All-in-One Video Bar', 'specifications': '4K, Motorized Pan/Tilt, AI Viewfinder', 'brand': 'Logitech', 'quantity': 1, 'price': 2500, 'category': 'Video Conferencing System'},
                {'name': 'Logitech Tap IP', 'description': 'Touch Controller', 'specifications': '10.1" screen, PoE', 'brand': 'Logitech', 'quantity': 1, 'price': 600, 'category': 'Video Conferencing System'},
                {'name': 'LG Commercial Display', 'description': '4K UHD Display', 'specifications': '55-inch, 24/7 operation', 'brand': 'LG', 'quantity': 1, 'price': 1200, 'category': 'Display System'},
                {'name': 'HDMI Cable', 'description': 'High-Speed HDMI Cable', 'specifications': '4K@60Hz, 5m', 'brand': 'Extron', 'quantity': 2, 'price': 50, 'category': 'Cables & Connectors'}
            ]
        },
        {
            "name": "Boardroom - Executive",
            "boq_items": [
                {'name': 'Crestron Flex C160-T', 'description': 'Video Conference System Integrator Kit', 'specifications': 'Includes UC-ENGINE, 10.1" touch screen', 'brand': 'Crestron', 'quantity': 1, 'price': 8000, 'category': 'Video Conferencing System'},
                {'name': 'Samsung "The Wall"', 'description': 'MicroLED Display', 'specifications': '146-inch, 4K', 'brand': 'Samsung', 'quantity': 1, 'price': 75000, 'category': 'Display System'},
                {'name': 'Shure MXA920', 'description': 'Ceiling Array Microphone', 'specifications': 'Automatic Coverage technology, Dante enabled', 'brand': 'Shure', 'quantity': 2, 'price': 4500, 'category': 'Audio System'},
                 {'name': 'QSC Core 110f', 'description': 'DSP Processor', 'specifications': '12x8 I/O, AEC', 'brand': 'QSC', 'quantity': 1, 'price': 3000, 'category': 'Audio System'}
            ]
        }
    ]

    # 3. Set the USD to INR conversion rate
    usd_inr_rate = 83.50
    
    # 4. Generate the Excel file in memory
    # IMPORTANT: Create a folder named 'assets' in the same directory as your script
    # and place an image named 'allwave_logo.png' inside it.
    excel_data = generate_company_excel(project_info, rooms, usd_inr_rate)

    # 5. Save the generated Excel data to a file
    with open("Generated_Company_BOQ.xlsx", "wb") as f:
        f.write(excel_data)

    print("Successfully generated 'Generated_Company_BOQ.xlsx'")
