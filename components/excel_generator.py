# components/excel_generator.py
# PRODUCTION VERSION - Matches AllWave AV company format
# Revised and Improved for Styling Consistency and Complete Content

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter
from io import BytesIO
import re
from datetime import datetime

# Import the image generator (with robust fallback)
try:
    from components.product_image_generator import generate_product_info_card, extract_display_size
except ImportError:
    print("WARNING: product_image_generator not found. Images will not be generated.")
    def generate_product_info_card(*args, **kwargs):
        return None
    def extract_display_size(name):
        return None

# ==================== STYLE DEFINITIONS ====================
def _define_styles():
    """Defines all necessary styles for the professional report."""
    thin_border_side = Side(style='thin')
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    return {
        # Fills
        "header_green_fill": PatternFill(start_color="A9D08E", end_color="A9D08E", fill_type="solid"),
        "header_light_green_fill": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        "table_header_blue_fill": PatternFill(start_color="9BC2E6", end_color="9BC2E6", fill_type="solid"),
        "boq_category_fill": PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"),
        "main_title_fill": PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"), # Darker blue for main titles
        "grand_total_fill": PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid"),
        
        # Fonts
        "main_title_font": Font(size=14, bold=True, color="FFFFFF"),
        "black_bold_font": Font(color="000000", bold=True),
        "bold_font": Font(bold=True),
        "total_row_font": Font(bold=True, size=12),

        # Borders & Formats
        "thin_border": thin_border,
        "currency_format": "₹ #,##0.00",

        # Alignments
        "align_center_center": Alignment(horizontal='center', vertical='center'),
        "align_center_wrap": Alignment(horizontal='center', vertical='center', wrap_text=True),
        "align_top_wrap": Alignment(vertical='top', wrap_text=True),
        "align_left_top": Alignment(horizontal='left', vertical='top'),
        "align_right_center": Alignment(horizontal='right', vertical='center')
    }


# ==================== HEADER WITH LOGOS ====================
def _add_image_to_cell(sheet, image_path, cell, height_px):
    """Adds a logo to a cell, preserving aspect ratio."""
    try:
        img = ExcelImage(image_path)
        img.height = height_px
        img.width = (img.width / img.height) * height_px
        sheet.add_image(img, cell)
    except Exception:
        # Graceful fallback - just put text
        sheet[cell] = f"Logo: {image_path}"
        sheet[cell].font = Font(color="FF0000") # Red font to indicate missing image


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


# ==================== HELPER FUNCTIONS ====================
def _apply_style_to_range(sheet, cell_range, style_dict):
    """Applies a dictionary of styles to all cells in a range."""
    for row in sheet[cell_range]:
        for cell in row:
            if "font" in style_dict: cell.font = style_dict["font"]
            if "fill" in style_dict: cell.fill = style_dict["fill"]
            if "border" in style_dict: cell.border = style_dict["border"]
            if "alignment" in style_dict: cell.alignment = style_dict["alignment"]
            if "number_format" in style_dict: cell.number_format = style_dict["number_format"]

def _add_titled_section(sheet, row_cursor, title, columns, styles):
    """Helper to create a formatted title row spanning specified columns."""
    start_col, end_col = columns
    merge_range = f'{start_col}{row_cursor}:{end_col}{row_cursor}'
    sheet.merge_cells(merge_range)
    cell = sheet[f'{start_col}{row_cursor}']
    cell.value = title
    _apply_style_to_range(sheet, merge_range, {
        "font": styles["main_title_font"],
        "fill": styles["main_title_fill"],
        "border": styles["thin_border"],
        "alignment": styles["align_center_center"]
    })
    sheet.row_dimensions[row_cursor].height = 25
    return row_cursor + 2

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
    _apply_style_to_range(sheet, 'A3:B3', {
        "fill": styles['header_green_fill'],
        "font": styles['black_bold_font'],
        "alignment": styles['align_center_center'],
        "border": styles['thin_border']
    })

    vc_data = [
        ("Date of First Draft", datetime.now().strftime("%d-%b-%Y")),
        ("Date of Final Draft", ""),
        ("Version No.", "1.0"),
        ("Published Date", datetime.now().strftime("%d-%b-%Y"))
    ]
    
    for i, (label, value) in enumerate(vc_data, start=4):
        sheet[f'A{i}'].value, sheet[f'B{i}'].value = label, value
        _apply_style_to_range(sheet, f'A{i}', {"fill": styles['header_light_green_fill'], "border": styles['thin_border']})
        _apply_style_to_range(sheet, f'B{i}', {"border": styles['thin_border']})

    # === CONTACT DETAILS TABLE ===
    sheet.merge_cells('E3:F3')
    cd_header = sheet['E3']
    cd_header.value = "Contact Details"
    _apply_style_to_range(sheet, 'E3:F3', {
        "fill": styles['header_green_fill'],
        "font": styles['black_bold_font'],
        "alignment": styles['align_center_center'],
        "border": styles['thin_border']
    })

    contact_data = [
        ("Design Engineer", project_details.get("Design Engineer", "")),
        ("Account Manager", project_details.get("Account Manager", "")),
        ("Client Name", project_details.get("Client Name", "")),
        ("Key Client Personnel", project_details.get("Key Client Personnel", "")),
        ("Location", project_details.get("Location", "")),
        ("Key Comments for this version", project_details.get("Key Comments", ""))
    ]
    
    for i, (label, value) in enumerate(contact_data, start=4):
        sheet[f'E{i}'].value, sheet[f'F{i}'].value = label, value
        _apply_style_to_range(sheet, f'E{i}', {"fill": styles['header_light_green_fill'], "border": styles['thin_border']})
        _apply_style_to_range(sheet, f'F{i}', {"border": styles['thin_border']})
        if label == "Key Comments for this version":
            sheet.row_dimensions[i].height = 40
            sheet[f'F{i}'].alignment = styles['align_top_wrap']

# ==================== TERMS & CONDITIONS SHEET ====================
def _add_terms_and_conditions_sheet(workbook, styles):
    """Creates comprehensive Terms & Conditions sheet with improved formatting."""
    sheet = workbook.create_sheet(title="Terms & Conditions")
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False
    
    # Set column widths
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        sheet.column_dimensions[col].width = 20
    
    row_cursor = 4
    
    # === MAIN TITLE ===
    row_cursor = _add_titled_section(sheet, row_cursor, "Commercial Terms & Conditions", ('A', 'F'), styles)

    terms_data = {
        "A. Delivery, Installations & Site Schedule": [
            "All Wave AV Systems undertakes to ensure its best efforts to complete the assignment within the shortest timelines possible.",
            "",
            ("Project Schedule:", [
                "Week 1-3: All Wave AV Systems Design & Procurement / Client Site Preparations",
                "Implementation: Within 12 weeks of advance payment receipt",
            ]),
            ("Delivery Terms:", [
                "Duty Paid INR: Free delivery at site",
                "All deliveries within 6-8 weeks of commercially clear Purchase Order",
                "Equipment delivered in phased manner (max 3 shipments)",
            ]),
            "Note: Delay in advance payment may alter project schedule. Beyond 12 weeks delay due to site issues: ₹8,000 + GST per day charge applies."
        ],
        "B. Payment Terms": [
            ("Schedule of Payment:", [
                "Equipment & Materials: 20% Advance with PO",
                "Installation & Commissioning: Against system installation",
                "Balance Payment: Within 30 days of ATP sign-off"
            ])
        ],
        "C. Offer Validity": [
            "Offer Valid for 30 Days from date of quotation"
        ],
        "D. Placing a Purchase Order": [
            "Order should be placed on:",
            "All Wave AV Systems Pvt. Ltd.",
            "420A Shah & Nahar Industrial Estate,",
            "Lower Parel West, Mumbai 400013, INDIA",
            "",
            "GST No: [To be provided]",
            "PAN No: [To be provided]"
        ],
        "E. Cable Estimates": [
            "Provisional cable estimate provided. Actual consumption may vary based on finalized layouts.",
            "Invoicing based on actual consumption: Physical measurement + 10% (for bends, curves, termination, wastage)"
        ],
        "F. Order Changes": [
            "All Wave AV Systems accommodates scope changes as needed.",
            "Changes may require additional resources/time - a separate Change Order will be issued.",
            "All Change Orders must be in writing with adjusted price, schedule, and acceptance criteria."
        ],
        "G. Restocking / Cancellation Fees": [
            "Cancellation may involve charges up to 50% restocking/cancellation fees + shipping costs."
        ],
        "H. Warranty": [
            "All Wave AV Systems provides:",
            ("Warranty Inclusions:", [
                "Comprehensive 12-month warranty on all equipment from handover date",
                "Limited warranty on consumables (Projector lamps: 450 hours or 90 days, whichever earlier)",
                "Extended warranty available via separate Maintenance Contract",
            ]),
            ("Warranty Exclusions:", [
                "Power-related damage (equipment must use stabilized power/online UPS)",
                "Accident, misuse, neglect, alteration, or component substitution",
                "Fire, flood, weather exposure, force majeure events"
            ])
        ]
    }

    for title, points in terms_data.items():
        # Add section header
        sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
        section_cell = sheet[f'A{row_cursor}']
        section_cell.value = title
        _apply_style_to_range(sheet, f'A{row_cursor}:F{row_cursor}', {
            "fill": styles['table_header_blue_fill'],
            "font": styles['bold_font'],
            "border": styles['thin_border']
        })
        row_cursor += 1

        # Add points
        for point in points:
            sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
            cell = sheet[f'A{row_cursor}']
            
            if isinstance(point, tuple): # Sub-heading with bullet points
                cell.value = point[0]
                cell.font = styles['bold_font']
                _apply_style_to_range(sheet, f'A{row_cursor}:F{row_cursor}', {"border": styles['thin_border'], "alignment": styles['align_top_wrap']})
                row_cursor += 1
                for sub_point in point[1]:
                    sheet.merge_cells(f'A{row_cursor}:F{row_cursor}')
                    sub_cell = sheet[f'A{row_cursor}']
                    sub_cell.value = f"•  {sub_point}"
                    _apply_style_to_range(sheet, f'A{row_cursor}:F{row_cursor}', {"border": styles['thin_border'], "alignment": styles['align_top_wrap']})
                    row_cursor += 1
            elif point == "": # Spacer
                row_cursor += 1
            else:
                cell.value = point
                _apply_style_to_range(sheet, f'A{row_cursor}:F{row_cursor}', {"border": styles['thin_border'], "alignment": styles['align_top_wrap']})
                if point in ["Note:", "Order should be placed on:"]:
                    cell.font = styles['bold_font']
                row_cursor += 1
        row_cursor += 1 # Spacer between sections

# ==================== ROOM BOQ SHEET ====================
def _populate_room_boq_sheet(sheet, items, room_name, styles, usd_to_inr_rate, gst_rates):
    """Creates detailed BOQ sheet with PRODUCT IMAGES and TOP 3 REASONS columns."""
    _create_sheet_header(sheet)
    
    # === ROOM INFO SECTION ===
    info_data = [
        ("Room Name / Room Type", room_name),
        ("Floor", "-"),
        ("Number of Seats", "-"),
        ("Number of Rooms", "-")
    ]
    
    for i, (label, value) in enumerate(info_data, start=3):
        sheet[f'A{i}'].value, sheet[f'B{i}'].value = label, value
        sheet[f'A{i}'].font = styles['bold_font']
        sheet.merge_cells(f'B{i}:C{i}')
        _apply_style_to_range(sheet, f'A{i}:C{i}', {"border": styles['thin_border']})

    # === TABLE HEADERS ===
    header_start_row = 7
    headers1 = ['Sr. No.', 'Reference Image', 'Description of Goods / Services', 'Make', 'Model No.', 'Qty.',
                'Unit Rate (INR)', 'Total', 'Warranty', 'Lead Time (Days)', 'SGST\n(In Maharashtra)', None,
                'CGST\n(In Maharashtra)', None, 'Total (TAX)', 'Total Amount (INR)', 'Top 3 Reasons']
    headers2 = [None] * 10 + ['Rate', 'Amt', 'Rate', 'Amt', None, None, None]
    
    sheet.cell(row=header_start_row, column=1).value = headers1[0] # To anchor the append
    sheet.append(headers1[1:]) # Append remaining
    sheet.append(headers2)

    # Merge GST header cells
    sheet.merge_cells(f'K{header_start_row}:L{header_start_row}')
    sheet.merge_cells(f'M{header_start_row}:N{header_start_row}')
    # Merge non-GST cells in header
    for col_letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'O', 'P', 'Q']:
        sheet.merge_cells(f'{col_letter}{header_start_row}:{col_letter}{header_start_row+1}')

    _apply_style_to_range(sheet, f'A{header_start_row}:Q{header_start_row+1}', {
        "fill": styles["table_header_blue_fill"],
        "font": styles['bold_font'],
        "alignment": styles['align_center_wrap'],
        "border": styles['thin_border']
    })

    # === GROUP ITEMS BY CATEGORY ===
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General AV')
        grouped_items.setdefault(cat, []).append(item)

    total_before_gst_hardware = 0
    item_s_no = 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]
    current_row = header_start_row + 2

    # === ADD HARDWARE ITEMS ===
    for i, (category, cat_items) in enumerate(grouped_items.items()):
        sheet.cell(row=current_row, column=1).value = category_letters[i]
        sheet.cell(row=current_row, column=2).value = category
        sheet.merge_cells(f'B{current_row}:Q{current_row}')
        _apply_style_to_range(sheet, f'A{current_row}:Q{current_row}', {
            "fill": styles['boq_category_fill'],
            "font": styles['bold_font'],
            "border": styles['thin_border']
        })
        current_row += 1

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

            reasons = item.get('top_3_reasons', ["Standard component for this room type."])
            top_3_reasons = '\n'.join([f"{idx+1}. {reason}" for idx, reason in enumerate(reasons)])

            row_data = [item_s_no, '', item.get('name', ''), item.get('brand', 'Unknown'), 
                        item.get('model_number', 'N/A'), item.get('quantity', 1), unit_price_inr,
                        subtotal, item.get('warranty', '1 Year'), item.get('lead_time_days', 21),
                        f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", cgst_amount, total_tax,
                        total_with_gst, top_3_reasons]
            
            for col_idx, value in enumerate(row_data, 1):
                sheet.cell(row=current_row, column=col_idx, value=value)
            
            # === ADD PRODUCT IMAGE ===
            try:
                size_inches = extract_display_size(item.get('name', '')) if item.get('category') == 'Displays' else None
                img_buffer = generate_product_info_card(
                    product_name=item.get('name', 'Unknown Product'),
                    brand=item.get('brand', 'N/A'),
                    model=item.get('model_number', 'N/A'),
                    category=item.get('category', 'General AV'),
                    size_inches=size_inches
                )
                if img_buffer:
                    img_buffer.seek(0)
                    excel_img = ExcelImage(img_buffer)
                    excel_img.width, excel_img.height = 150, 100
                    sheet.add_image(excel_img, f'B{current_row}')
                    sheet.row_dimensions[current_row].height = 80
            except Exception as e:
                print(f"ERROR: Could not add product image for {item.get('name', 'Unknown')}: {e}")
            
            item_s_no += 1
            current_row += 1
    
    # === ADD SERVICES ===
    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    services_letter = chr(ord('A') + len(grouped_items))
    services_gst_rate = gst_rates.get('Services', 18)

    if services and total_before_gst_hardware > 0:
        sheet.cell(row=current_row, column=1).value = services_letter
        sheet.cell(row=current_row, column=2).value = "Services"
        sheet.merge_cells(f'B{current_row}:Q{current_row}')
        _apply_style_to_range(sheet, f'A{current_row}:Q{current_row}', {
            "fill": styles['boq_category_fill'],
            "font": styles['bold_font'],
            "border": styles['thin_border']
        })
        current_row += 1

        service_reasons = {
            "Installation & Commissioning": "1. Professional on-site installation\n2. System configuration and testing\n3. Integration with existing infrastructure",
            "System Warranty (3 Years)": "1. Comprehensive parts and labor coverage\n2. Priority support and rapid response\n3. Regular maintenance and health checks",
            "Project Management": "1. Dedicated project coordinator\n2. Timeline management and tracking\n3. Quality assurance and documentation"
        }

        for service_name, percentage in services:
            service_amount_inr = total_before_gst_hardware * percentage
            sgst_rate = cgst_rate = services_gst_rate / 2
            service_total_tax = service_amount_inr * (services_gst_rate / 100)
            service_total = service_amount_inr + service_total_tax

            row_data = [item_s_no, '', service_name, "AllWave AV", "Professional Service", 1,
                        service_amount_inr, service_amount_inr, "As per terms", "N/A",
                        f"{sgst_rate}%", service_total_tax / 2, f"{cgst_rate}%", service_total_tax / 2,
                        service_total_tax, service_total, service_reasons.get(service_name, "")]
            for col_idx, value in enumerate(row_data, 1):
                sheet.cell(row=current_row, column=col_idx, value=value)
            
            item_s_no += 1
            current_row += 1

    # === SET COLUMN WIDTHS AND FINAL STYLES ===
    column_widths = {'A': 8, 'B': 22, 'C': 45, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 15,
                     'J': 15, 'K': 10, 'L': 15, 'M': 10, 'N': 15, 'O': 15, 'P': 18, 'Q': 50}
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width
    
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=current_row - 1):
        for cell in row:
            cell.border = styles['thin_border']
            if cell.column in [1, 6, 9, 10, 11, 13]: cell.alignment = Alignment(horizontal='center', vertical='top')
            elif cell.column == 17: cell.alignment = styles['align_top_wrap']
            else: cell.alignment = Alignment(vertical='top')

            if cell.column in [7, 8, 12, 14, 15, 16] and isinstance(cell.value, (int, float)):
                cell.number_format = styles['currency_format']


# ==================== SCOPE OF WORK SHEET ====================
def _add_scope_of_work_sheet(workbook, styles):
    """Creates the Scope of Work sheet with comprehensive static text."""
    sheet = workbook.create_sheet(title="Scope of Work", index=1)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False
    
    sheet.column_dimensions['A'].width = 8
    sheet.column_dimensions['B'].width = 100
    
    row_cursor = 4
    
    # === TITLE ===
    row_cursor = _add_titled_section(sheet, row_cursor, "Scope of Work", ('A', 'B'), styles)

    # === SCOPE ITEMS ===
    scope_sections = {
        "AllWave AV Scope of Work": [
            "Site Coordination and Prerequisites Clearance.",
            "Supply of all equipment as per the Bill of Quantities (BOQ).",
            "Detailed schematic drawings according to the approved design.",
            "Conduit layout drawings and equipment layout drawings, showing mounting locations.",
            "Laying of all AV Cables (Signal, Control, Audio, Video).",
            "Termination of cables with respective connectors and professional labeling.",
            "Installation of all AV equipment (e.g., displays, speakers, microphones) at designated locations.",
            "Installation and dressing of equipment in the AV rack as per layout.",
            "Configuration of Audio/Video Switchers, Routers, and Scalers.",
            "Configuration and calibration of the Digital Signal Processor (DSP) for optimal audio performance.",
            "User Interface (UI) design and programming for the Touch Panel.",
            "System programming for integrated control as per design requirements.",
            "System Testing, Commissioning, and Handover.",
            "Provide basic user training on system operation.",
            "Submission of 'As-Built' drawings and user manuals upon project completion."
        ],
        "Exclusions (Client's Scope)": [
            "Any civil work, including but not limited to cutting of false ceilings, wall chipping, core cutting, masonry, or painting.",
            "Any electrical work, including laying of conduits, raceways, junction boxes, and providing stabilized 230V AC, 50Hz power supply points with proper earthing for all AV equipment.",
            "Any carpentry or interior work, such as cutouts on furniture, fabrication of custom mounts, or paneling.",
            "Provision of network infrastructure, including LAN points, network switches, cabling, and IP addresses for all network-enabled AV devices.",
            "Provision of required internet bandwidth and any necessary ISP coordination.",
            "Provision of any third-party services like telephone lines, ISDN, or cable TV points.",
            "Mounts, brackets, or ceiling poles unless explicitly mentioned in the BOQ.",
            "Adequate cooling, ventilation, and dust-free environment for all equipment racks and cabinets.",
            "Secure storage space for materials and tools on-site during the project execution phase."
        ]
    }

    for title, items in scope_sections.items():
        sheet.merge_cells(f'A{row_cursor}:B{row_cursor}')
        section_cell = sheet[f'A{row_cursor}']
        section_cell.value = title
        _apply_style_to_range(sheet, f'A{row_cursor}:B{row_cursor}', {
            "fill": styles['table_header_blue_fill'],
            "font": styles['bold_font'],
            "border": styles['thin_border']
        })
        row_cursor += 1

        for idx, item in enumerate(items, 1):
            sheet[f'A{row_cursor}'].value = idx
            sheet[f'B{row_cursor}'].value = item
            _apply_style_to_range(sheet, f'A{row_cursor}', {"alignment": styles['align_center_center'], "border": styles['thin_border']})
            _apply_style_to_range(sheet, f'B{row_cursor}', {"alignment": styles['align_top_wrap'], "border": styles['thin_border']})
            sheet.row_dimensions[row_cursor].height = 30
            row_cursor += 1
        row_cursor += 1


# ==================== PROPOSAL SUMMARY SHEET ====================
def _add_proposal_summary_sheet(workbook, rooms_data, styles):
    """Creates the Proposal Summary sheet with full calculations and commercial terms."""
    sheet = workbook.create_sheet(title="Proposal Summary", index=2)
    _create_sheet_header(sheet)
    sheet.sheet_view.showGridLines = False
    
    column_widths = {'A': 8, 'B': 50, 'C': 12, 'D': 18, 'E': 18, 'F': 18, 'G': 18}
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width
    
    row_cursor = 4
    
    # === TITLE ===
    row_cursor = _add_titled_section(sheet, row_cursor, "Proposal Summary", ('A', 'G'), styles)
    
    # === TABLE HEADERS ===
    headers_row1 = ['Sr. No', 'Description', 'Total Qty', 'INR Supply', None, None, None]
    headers_row2 = [None, None, None, 'Rate w/o TAX', 'Amount w/o TAX', 'Total TAX Amount', 'Amount with Tax']
    
    sheet.append(headers_row1)
    sheet.append(headers_row2)
    header_start_row = sheet.max_row - 1
    
    sheet.merge_cells(f'D{header_start_row}:G{header_start_row}')
    _apply_style_to_range(sheet, f'A{header_start_row}:G{header_start_row+1}', {
        "fill": styles['table_header_blue_fill'],
        "font": styles['bold_font'],
        "alignment": styles['align_center_wrap'],
        "border": styles['thin_border']
    })
    sheet.row_dimensions[header_start_row+1].height = 30
    row_cursor = sheet.max_row + 1

    # === ROOM DATA WITH CALCULATIONS ===
    grand_subtotal, grand_tax, grand_total = 0, 0, 0
    
    for idx, room in enumerate(rooms_data, 1):
        room_subtotal = room.get('subtotal', 0)
        room_tax = room.get('gst', 0)
        room_total = room.get('total', 0)
        
        grand_subtotal += room_subtotal
        grand_tax += room_tax
        grand_total += room_total
        
        total_qty = sum(item.get('quantity', 1) for item in room.get('boq_items', []))
        avg_rate = room_subtotal / total_qty if total_qty > 0 else 0
        
        row_data = [idx, room.get('name', f'Room {idx}'), total_qty, avg_rate, room_subtotal, room_tax, room_total]
        sheet.append(row_data)

    # === GRAND TOTAL ROW ===
    sheet.append([]) # Spacer
    total_row_idx = sheet.max_row + 1
    sheet.merge_cells(f'A{total_row_idx}:C{total_row_idx}')
    sheet[f'A{total_row_idx}'].value = "GRAND TOTAL"
    
    grand_total_data = [grand_subtotal, grand_tax, grand_total]
    sheet.cell(row=total_row_idx, column=5).value = grand_total_data[0]
    sheet.cell(row=total_row_idx, column=6).value = grand_total_data[1]
    sheet.cell(row=total_row_idx, column=7).value = grand_total_data[2]
    
    _apply_style_to_range(sheet, f'A{total_row_idx}:G{total_row_idx}', {
        "font": styles['total_row_font'],
        "fill": styles['grand_total_fill'],
        "border": styles['thin_border']
    })
    sheet[f'A{total_row_idx}'].alignment = styles['align_center_center']
    for col in ['E', 'F', 'G']:
        cell = sheet[f'{col}{total_row_idx}']
        cell.number_format = styles['currency_format']
        cell.alignment = styles['align_right_center']
    sheet.row_dimensions[total_row_idx].height = 25
    
    # === FORMAT DATA ROWS ===
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=total_row_idx - 2):
        for cell in row:
            cell.border = styles['thin_border']
            if cell.column in [1, 3]: cell.alignment = styles['align_center_center']
            elif cell.column >= 4:
                cell.number_format = styles['currency_format']
                cell.alignment = styles['align_right_center']
            else: cell.alignment = Alignment(horizontal='left', vertical='center')


# ==================== MAIN ENTRY POINT ====================
def generate_company_excel(project_details, rooms_data, usd_to_inr_rate):
    """Main function to generate the complete Excel workbook."""
    workbook = openpyxl.Workbook()
    styles = _define_styles()

    # === CALCULATE ROOM TOTALS FIRST ===
    gst_rates = project_details.get('gst_rates', {'Electronics': 18, 'Services': 18})
    for room in rooms_data:
        if room.get('boq_items'):
            subtotal_hardware = sum(item.get('price', 0) * item.get('quantity', 1) for item in room['boq_items']) * usd_to_inr_rate
            services_total = subtotal_hardware * 0.30  # 15% (Install) + 10% (PM) + 5% (Warranty)
            total_without_gst = subtotal_hardware + services_total
            
            gst_electronics = sum(
                (item.get('price', 0) * item.get('quantity', 1) * usd_to_inr_rate) * (item.get('gst_rate', gst_rates['Electronics']) / 100)
                for item in room['boq_items']
            )
            gst_services = services_total * (gst_rates['Services'] / 100)
            total_gst = gst_electronics + gst_services
            
            room['subtotal'] = total_without_gst
            room['gst'] = total_gst
            room['total'] = total_without_gst + total_gst

    # === GENERATE SHEETS ===
    _add_version_control_sheet(workbook, project_details, styles)
    _add_scope_of_work_sheet(workbook, styles)
    _add_proposal_summary_sheet(workbook, rooms_data, styles)
    _add_terms_and_conditions_sheet(workbook, styles)
    
    for room in rooms_data:
        if room.get('boq_items'):
            safe_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:25]
            room_sheet = workbook.create_sheet(title=f"BOQ - {safe_name}")
            _populate_room_boq_sheet(
                room_sheet, room['boq_items'], room['name'], styles,
                usd_to_inr_rate, gst_rates
            )

    # === CLEANUP AND SAVE ===
    if "Sheet" in workbook.sheetnames:
        del workbook["Sheet"]
    workbook.active = workbook["Version Control"]

    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer.getvalue()
