import sys
import subprocess
import os

def install_dependencies():
    try:
        import reportlab
    except ImportError:
        print("Installing reportlab...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "markdown"])

install_dependencies()

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

def create_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=HexColor('#1E3A8A'), spaceAfter=20)
    h1_style = ParagraphStyle('H1Style', parent=styles['Heading1'], fontSize=16, textColor=HexColor('#2563EB'), spaceAfter=15, spaceBefore=20)
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=14, textColor=HexColor('#3B82F6'), spaceAfter=10, spaceBefore=15)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=11, leading=16, spaceAfter=8)
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontSize=11, leading=16, spaceAfter=8, fontName='Helvetica-Bold')

    story = []

    # Title
    story.append(Paragraph("CallQ System Analysis Report", title_style))
    story.append(Paragraph("Complete end-to-end understanding of the backend, API flow, data relationships, and UI behaviors.", normal_style))
    story.append(Spacer(1, 20))

    # Part 1
    story.append(Paragraph("PART 1: HIGH-LEVEL SYSTEM OVERVIEW", h1_style))
    story.append(Paragraph("<b>System Purpose:</b> CallQ is an enterprise queue and token management system that maps hardware devices (Token Dispensers, Keypads, LED displays, TVs, Brokers) to logical entities (Counters, Groups) across companies and their physical branches.", normal_style))
    story.append(Paragraph("<b>Main Modules:</b>", bold_style))
    modules = [
        "<b>Customers:</b> Divided into Company (Direct Customer) and DealerCustomer (managed by Dealers). Companies define branch configurations, device license counts, and feature flags (e.g., ads_enabled).",
        "<b>Branches:</b> Physical location divisions of a company where devices are actively deployed.",
        "<b>Users:</b> Managed with role-based access control (Super Admin, Dealer Admin, Company Admin, Branch Admin).",
        "<b>Devices:</b> Physical hardware endpoints. Types include TV, TOKEN_DISPENSER, KEYPAD, BROKER, LED, and CONFIG_APK. Devices require license approval and map to specific customers.",
        "<b>Grouping:</b> Logically ties devices together via GroupMapping. Dispensers, Keypads, and LEDs are exclusive to one group, while TVs and Brokers can span multiple groups. Supports Normal mode and Pool mode.",
        "<b>Counters:</b> Logical representations of service desks (CounterConfig). Possess prefixes, numeric limits, and map to token dispensers or keypads.",
        "<b>Token Flow:</b> Hardware button presses generate tokens -> Sent via MQTT Broker -> Parsed by Backend -> Displayed on TVs/LEDs -> Announcements triggered."
    ]
    for item in modules:
        story.append(Paragraph(f"• {item}", normal_style))

    # Part 2
    story.append(Paragraph("PART 2: DATA FLOW ANALYSIS", h1_style))
    flow_steps = [
        "<b>1. User Action (UI/Hardware):</b> A customer presses a button on a Token Dispenser to get a token, or an employee presses 'Next' (Button A) on their Keypad.",
        "<b>2. API Call:</b> Hardware communicates via an MQTT Broker, which forwards the payload to the backend via POST /api/external/token-report.",
        "<b>3. Backend Processing:</b> The backend decodes the payload (e.g., $0PABAeCAL0K0001lo-0011*). It extracts the keypad serial, keypad slot index, and dispenser index. It maps this data to a database CounterConfig using complex cascade logic (TVKeypadMapping -> GroupDispenser -> CounterTokenDispenser). Duplicates within 10 seconds are filtered out.",
        "<b>4. Database Interaction:</b> The token is logged into MQTTTokenLog and TokenReport for tracking. VIP ranges use VipTokenCounter to track running totals.",
        "<b>5. Response Generation:</b> The backend returns a detailed parsed JSON report to the MQTT Broker.",
        "<b>6. UI Update:</b> TV devices running the Android APK pull the config, listen for new tokens via FCM/WebSockets, display the active tokens, and play audio announcements."
    ]
    for item in flow_steps:
        story.append(Paragraph(item, normal_style))

    # Part 3
    story.append(Paragraph("PART 3: MODULE-WISE BREAKDOWN", h1_style))
    
    story.append(Paragraph("<b>Customers & Licenses:</b>", h2_style))
    story.append(Paragraph("Companies are the root entity. If created by a dealer, they are assigned as DealerCustomer. Licenses are managed via Batch limits and explicitly tracked on the Company model (e.g., noof_keypad_devices). Batch constraints block new devices from registering if the limit is exceeded.", normal_style))
    
    story.append(Paragraph("<b>Branches:</b>", h2_style))
    story.append(Paragraph("Companies operate in SINGLE or MULTIPLE branch configurations. Devices and Counters are scoped down to specific Branches for localized operations.", normal_style))

    story.append(Paragraph("<b>Users & Permissions:</b>", h2_style))
    story.append(Paragraph("Role-based architecture restricts visibility. Super Admins see everything. Dealer Admins see their assigned DealerCustomers. Company/Branch Admins only manage their localized devices and counters.", normal_style))

    story.append(Paragraph("<b>Devices:</b>", h2_style))
    story.append(Paragraph("Device Registration Flow: When an unknown Android TV starts, it requests its config. The backend checks license limits. If within bounds, it auto-creates a Pending Device record. An Admin must approve it via the UI to activate the license.", normal_style))

    story.append(Paragraph("<b>Grouping:</b>", h2_style))
    story.append(Paragraph("Groups unify devices for a single operational zone. Normal Mode maps Keypads to Dispenser slots. Pool Mode maps Counters directly to Keypads, allowing dynamic pooling without rigid dispenser ties.", normal_style))

    # Part 4
    story.append(PageBreak())
    story.append(Paragraph("PART 4: KEY LOGIC FLOWS", h1_style))
    
    story.append(Paragraph("<b>1. Keypad Index Logic:</b>", h2_style))
    story.append(Paragraph("Indexes are generated using ASCII characters starting from chr(0x31) ('1') to chr(0x7A) ('z'), giving 74 unique slots. These map a physical hardware button slot to a logical database entity (keypad_index, dispenser_button_index). They ensure global uniqueness within a group and are pushed to embedded devices as their identity.", normal_style))

    story.append(Paragraph("<b>2. Mapping Logic:</b>", h2_style))
    story.append(Paragraph("• <i>Normal Mode:</i> Token Dispenser holds the Counters. Keypads are mapped to Dispenser slots. Pressing 'A' on a Keypad triggers the Counter bound to that Dispenser slot.<br/>• <i>Pool Mode:</i> Token Dispensers are bypassed. Counters are mapped directly to Keypads (KeypadCounterMapping).", normal_style))

    story.append(Paragraph("<b>3. Token Flow (MQTT -> DB -> UI):</b>", h2_style))
    story.append(Paragraph("Hardware emits an encoded string containing the message type (Normal, Transfer, VIP), serial number, and slot index. The backend logs the exact arrival time, resolves the Counter, and transitions the token state from received -> displayed -> announced.", normal_style))

    # Part 5
    story.append(Paragraph("PART 5: API ANALYSIS", h1_style))
    
    story.append(Paragraph("<b>TV Config API (/api/android/config):</b>", h2_style))
    story.append(Paragraph("Provides Android TVs with UI configuration (colors, font size, layouts, ads). It enforces device limits on the fly. Returns a deep nested JSON mapping of all Token Dispensers, Keypads, and Counters assigned to the TV.", normal_style))

    story.append(Paragraph("<b>Android Config API (get_embedded_config):</b>", h2_style))
    story.append(Paragraph("Serves configuration strings to non-TV hardware (Keypads, Dispensers, LEDs). Outputs hardware-specific comma-separated strings (e.g., $1,SETTINGS,XXXX,Welcome...#). These strings encode ASCII slots, IP addresses, and behavioral flags.", normal_style))

    story.append(Paragraph("<b>Token Report API (/api/external/token-report):</b>", h2_style))
    story.append(Paragraph("The central nervous system for live data. Receives MQTT webhook payloads. Resolves Keypad Serials to Counters using a complex fallback tree: TVKeypadMapping -> GroupDispenserMapping -> CounterTokenDispenserMapping. Deduplicates identical signals within a 10-second window.", normal_style))

    # Part 6
    story.append(PageBreak())
    story.append(Paragraph("PART 6: UI BEHAVIOR", h1_style))
    story.append(Paragraph("• <b>Forms:</b> Used to construct Companies, define Counters, and perform basic CRUD operations.<br/>• <b>Mapping Screens:</b> Complex interfaces utilizing Many-to-Many relationships to group devices. Built-in validation prevents Keypads/Dispensers from belonging to multiple groups.<br/>• <b>Dashboard:</b> Heavily customized per Role. Filters location data strictly based on active branches/companies.<br/>• <b>Reports:</b> The Token Report UI filters MQTTTokenLog records by user scope, rendering operational history, token counts, and validity metrics.", normal_style))

    # Part 7
    story.append(Paragraph("PART 7: RELATIONSHIP MAPPING", h1_style))
    story.append(Paragraph("• <b>Company -> Branch -> User:</b> A Company entity holds multiple Branches. Users belong to a Company and optionally a localized Branch.<br/>• <b>Device -> Group -> Counter:</b> Devices are aggregated in GroupMapping. Counters map to Devices within these groups.<br/>• <b>Keypad -> Dispenser -> Counter:</b> In standard configurations, Keypads are linked to a specific button slot on a Dispenser (DispenserKeypadMapping), and that slot is tied to a specific Counter (GroupCounterButtonMapping).", normal_style))

    # Part 8
    story.append(Paragraph("PART 8: EDGE CASE HANDLING", h1_style))
    story.append(Paragraph("• <b>Missing Mapping:</b> If the API receives a token from a Keypad but the mapping is incomplete, it uses a fallback cascade to guess the assignment. If it fails entirely, it marks the token as is_valid=False but still logs it.<br/>• <b>Multiple Keypads:</b> The system handles identical counters across desks by mapping multiple Keypads to a single Dispenser button index.<br/>• <b>License Overflow:</b> Batch limits actively block TV registration. If a limit is hit, get_android_tv_config halts and returns a 403 Forbidden.<br/>• <b>VIP Overflow:</b> VIP tokens have fixed boundaries (vip_from, vip_to). The VipTokenCounter automatically wraps back to the start when the limit is breached.", normal_style))

    # Part 9
    story.append(Paragraph("PART 9: END-TO-END FLOW", h1_style))
    e2e = [
        "1. Super Admin creates a Company and assigns License limits.",
        "2. Hardware is installed. Android TV calls for config, creates a Pending record, Admin approves it.",
        "3. Admin maps the system: Creates a Group -> Associates Token Dispenser, Keypad, and TV -> Assigns Counters to the Dispenser.",
        "4. Keypad pulls its config string, learning its unique keypad_index and parent Dispenser.",
        "5. A Customer enters the Branch, presses the Token Dispenser, and receives a printed token.",
        "6. An Employee presses 'Button A' on their Keypad. The MQTT broker fires the payload to the Backend.",
        "7. Backend Token Report API decodes the index, associates it with the Counter, filters duplicates, and saves to DB.",
        "8. Android TV receives the live update, renders the Token + Counter on screen, and plays a voice announcement."
    ]
    for step in e2e:
        story.append(Paragraph(step, normal_style))

    doc.build(story)
    print(f"Successfully generated {filename}")

if __name__ == '__main__':
    create_pdf('CallQ_System_Analysis.pdf')
