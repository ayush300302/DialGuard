"""Generate a polished, professional PDF Technical Project Report for DialGuard."""

import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and display total page numbers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress headers/footers on the title cover page
            return

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header
        self.drawString(
            40,
            758,
            "DialGuard — SmartDialer Architecture & Technical Project Report",
        )
        self.drawRightString(
            letter[0] - 40, 758, "Author: Ayush Patil | DialGuard"
        )
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(40, 750, letter[0] - 40, 750)

        # Running Footer
        self.line(40, 45, letter[0] - 40, 45)
        self.drawString(
            40, 32, "https://github.com/ayush300302/DialGuard"
        )
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 32, page_str)
        self.restoreState()


def create_report(output_filename="DialGuard_Technical_Project_Report.pdf"):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#0F172A")  # Deep Navy
    ACCENT = colors.HexColor("#1E40AF")  # Cobalt Blue
    SECONDARY = colors.HexColor("#334155")  # Slate
    MUTED = colors.HexColor("#64748B")  # Muted Gray
    BG_LIGHT = colors.HexColor("#F8FAFC")  # Off-white
    BG_CARD = colors.HexColor("#F1F5F9")  # Card tint
    BORDER_COLOR = colors.HexColor("#CBD5E1")

    # Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=30,
        leading=36,
        textColor=PRIMARY,
        alignment=1,  # Center
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=17,
        textColor=ACCENT,
        alignment=1,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=SECONDARY,
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.white,
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=SECONDARY,
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
        textColor=PRIMARY,
    )

    table_cell_center = ParagraphStyle(
        "TableCellCenter",
        parent=table_cell_style,
        alignment=1,
    )

    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E293B"),
    )

    story = []

    def make_callout(text, border_color=ACCENT, bg_color=BG_LIGHT):
        content = [Paragraph(text, callout_style)]
        t = Table([[content]], colWidths=[letter[0] - 80])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LINEBEFORE", (0, 0), (0, -1), 4, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ])
        )
        return t

    def make_header_banner(title_text):
        content = Paragraph(
            f"<b><font color='white'>{title_text}</font></b>",
            ParagraphStyle("HB", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.white),
        )
        t = Table([[content]], colWidths=[letter[0] - 80])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        return t

    # =========================================================================
    # 1. TITLE PAGE (COVER)
    # =========================================================================
    story.append(Spacer(1, 35))

    # Top Brand Pill
    pill_text = Paragraph(
        "<b><font color='#1E40AF'>SYSTEM ARCHITECTURE & TECHNICAL SPECIFICATION REPORT</font></b>",
        ParagraphStyle("Pill", fontName="Helvetica-Bold", fontSize=9, alignment=1, textColor=ACCENT),
    )
    pill_table = Table([[pill_text]], colWidths=[380])
    pill_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#DBEAFE")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93C5FD")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )
    story.append(pill_table)
    story.append(Spacer(1, 22))

    story.append(Paragraph("DialGuard", title_style))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Intelligent Predictive SmartDialer Prototype for Collections Operations<br/>"
            "<font size=9.5 color='#64748B'>Deterministic Safety Controls • High-Concurrency Atomic Allocation • Fault-Tolerant Telecom Lifecycle</font>",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 16))

    story.append(
        HRFlowable(
            width="80%", thickness=1.5, color=ACCENT, spaceBefore=4, spaceAfter=18
        )
    )

    # Core Engineering Axiom Box on Title Page
    quote_text = (
        "<b>Core Engineering Principle:</b><br/>"
        "<i>\"Optimization is strictly subordinate to safety. While predictive pacing statistically forecasts "
        "call completions to maximize human agent utilization, the deterministic Safety Controller retains "
        "absolute non-bypassable authority to throttle or halt dials whenever capacity or carrier health degrades.\"</i>"
    )
    story.append(make_callout(quote_text, border_color=ACCENT, bg_color=BG_CARD))
    story.append(Spacer(1, 30))

    # Metadata Card
    meta_data = [
        [
            Paragraph("<b>Project:</b>", table_cell_bold),
            Paragraph("DialGuard Prototype", table_cell_style),
            Paragraph("<b>Author / Engineer:</b>", table_cell_bold),
            Paragraph("Ayush Patil", table_cell_style),
        ],
        [
            Paragraph("<b>Language / Stack:</b>", table_cell_bold),
            Paragraph("Python 3.12 (Standard Library)", table_cell_style),
            Paragraph("<b>Concurrency Model:</b>", table_cell_bold),
            Paragraph("Thread-Safe In-Memory Store (RLock)", table_cell_style),
        ],
        [
            Paragraph("<b>Test Suite:</b>", table_cell_bold),
            Paragraph("96 / 96 Pytest Unit & Load Tests Passing", table_cell_style),
            Paragraph("<b>Repository:</b>", table_cell_bold),
            Paragraph("<font color='#1E40AF'><u>https://github.com/ayush300302/DialGuard</u></font>", table_cell_style),
        ],
        [
            Paragraph("<b>Core Modules:</b>", table_cell_bold),
            Paragraph("State Machines, Allocator, Telecom, Safety, Pacing, Recovery, Simulation", table_cell_style),
            Paragraph("<b>Date:</b>", table_cell_bold),
            Paragraph("August 2026", table_cell_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[90, 150, 105, 187])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 28))

    toc_summary = (
        "<b>Report Contents:</b> 1. Problem Statement • 2. System Architecture • 3. Domain State Machines • "
        "4. End-to-End Call Lifecycle • 5. Progressive vs Predictive Dialing • 6. Deterministic Safety Controller • "
        "7. Atomic Concurrency & Allocation • 8. Telecom Carrier Faults & Idempotency • 9. Failure Recovery Supervisor • "
        "10. Simulation Benchmarks • 11. Verification & Test Suite • 12. Trade-offs & Roadmap"
    )
    story.append(Paragraph(toc_summary, ParagraphStyle("TOC", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED, alignment=1)))

    story.append(PageBreak())

    # =========================================================================
    # 2. PROBLEM STATEMENT
    # =========================================================================
    story.append(make_header_banner("1. PROBLEM STATEMENT & DOMAIN CONTEXT"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "Collections contact operations handle high volumes of outbound phone interactions to recover debt. "
        "The operation relies on two critical entities:", body_style
    ))
    story.append(Paragraph(
        "• <b>Borrowers:</b> The individuals being contacted regarding outstanding accounts.<br/>"
        "• <b>Collections Agents:</b> Human employees who converse with borrowers once a live call is established. "
        "This system does <i>not</i> utilize AI/LLM conversational agents; human labor is the primary high-cost bottleneck.",
        bullet_style
    ))
    story.append(Paragraph(
        "<b>The Operational Trade-off:</b><br/>"
        "1. <i>Under-Dialing (Manual / Slow Progressive):</i> Outbound dials are placed conservatively. With typical borrower answer rates "
        "often hovering between 15% and 35%, human agents spend up to 70–85% of their working hours idling in silence waiting for a connection.<br/>"
        "2. <i>Over-Dialing (Unconstrained Predictive):</i> The dialer aggressively places numerous calls anticipating high drop-offs. If multiple "
        "borrowers pick up simultaneously, answered calls exceed available agents, causing <b>abandoned calls</b> (silent drops), severe regulatory "
        "penalties (e.g. TCPA/FTC 3% maximum abandon rate limits), and hostile borrower experiences.",
        body_style
    ))
    story.append(Paragraph(
        "<b>DialGuard Objective:</b> Build a deterministic SmartDialer prototype that dynamically maximizes agent utilization via "
        "statistical predictive pacing while guaranteeing deterministic, non-bypassable safety controls and complete fault tolerance.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # =========================================================================
    # 3. SYSTEM ARCHITECTURE
    # =========================================================================
    story.append(make_header_banner("2. SYSTEM ARCHITECTURE & PIPELINE FLOW"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "DialGuard enforces a strict, layered uni-directional pipeline. The Predictive Pacing Engine produces advisory recommendations, "
        "but is structurally decoupled from call dispatching. All requests must pass through the Safety Controller.",
        body_style
    ))

    arch_diagram_data = [
        [Paragraph("<b>Pipeline Stage</b>", table_header_style), Paragraph("<b>Component</b>", table_header_style), Paragraph("<b>Core Responsibility & Operational Role</b>", table_header_style)],
        [
            Paragraph("<b>1. Input Metrics</b>", table_cell_bold),
            Paragraph("Historical State Store", code_style),
            Paragraph("Tracks active agents, in-flight ringing calls, historical answer rates, and average call duration.", table_cell_style),
        ],
        [
            Paragraph("<b>2. Advisory Pacing</b>", table_cell_bold),
            Paragraph("Predictive Pacing Engine", code_style),
            Paragraph("Statistically estimates target dial count using answer rates and Little's Law completion lookahead. <i>Advisory only.</i>", table_cell_style),
        ],
        [
            Paragraph("<b>3. Safety Gatekeeper</b>", table_cell_bold),
            Paragraph("Safety Controller", code_style),
            Paragraph("<b>Non-bypassable arbiter.</b> Enforces hard capacity caps (available agents, max overdial ratio, carrier health fallbacks).", table_cell_style),
        ],
        [
            Paragraph("<b>4. Atomic Allocation</b>", table_cell_bold),
            Paragraph("Call Allocator", code_style),
            Paragraph("Atomically queries and reserves available agents and queued calls with time-bounded leases under <code>RLock</code>.", table_cell_style),
        ],
        [
            Paragraph("<b>5. Carrier Dispatch</b>", table_cell_bold),
            Paragraph("Telecom Provider", code_style),
            Paragraph("Dispatches outbound calls to carriers (simulated via <code>ReliableProvider</code> and <code>FlakyProvider</code>).", table_cell_style),
        ],
        [
            Paragraph("<b>6. Event Ingestion</b>", table_cell_bold),
            Paragraph("Provider Event Handler", code_style),
            Paragraph("Idempotently processes carrier signals (<code>INITIATED</code>, <code>RINGING</code>, <code>ANSWERED</code>, <code>COMPLETED</code>) with deduplication.", table_cell_style),
        ],
        [
            Paragraph("<b>7. Fault Recovery</b>", table_cell_bold),
            Paragraph("Recovery Supervisor", code_style),
            Paragraph("Asynchronously sweeps expired worker leases and stuck in-flight calls, returning orphaned records to clean pools.", table_cell_style),
        ],
    ]
    arch_table = Table(arch_diagram_data, colWidths=[85, 140, 307])
    arch_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ])
    )
    story.append(arch_table)

    story.append(PageBreak())

    # =========================================================================
    # 4. DOMAIN STATE MACHINES
    # =========================================================================
    story.append(make_header_banner("3. DOMAIN STATE MACHINES"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "State transitions are strictly centralized, immutable, and deterministic. Invalid transitions immediately raise domain exceptions "
        "(<code>InvalidStateTransitionError</code> or <code>TerminalStateError</code>) and guarantee that entity state remains untouched.",
        body_style
    ))
    story.append(Spacer(1, 2))

    story.append(Paragraph("<b>A. Collections Agent State Machine</b>", ParagraphStyle("SubH", parent=body_style, fontName="Helvetica-Bold", textColor=ACCENT)))
    agent_state_data = [
        [Paragraph("<b>Agent State</b>", table_header_style), Paragraph("<b>Permitted Next States</b>", table_header_style), Paragraph("<b>Business & Operational Rationale</b>", table_header_style)],
        [Paragraph("<code>OFFLINE</code>", code_style), Paragraph("<code>AVAILABLE, PAUSED</code>", code_style), Paragraph("Agent logs in ready to accept calls or logs in directly on break/meeting.", table_cell_style)],
        [Paragraph("<code>AVAILABLE</code>", code_style), Paragraph("<code>RESERVED, PAUSED, OFFLINE</code>", code_style), Paragraph("Agent is idle in queue; can be reserved by allocator, take a break, or log off.", table_cell_style)],
        [Paragraph("<code>RESERVED</code>", code_style), Paragraph("<code>DIALING, AVAILABLE, OFFLINE</code>", code_style), Paragraph("Locked for outbound dial. Moves to DIALING on carrier dial, or AVAILABLE on timeout.", table_cell_style)],
        [Paragraph("<code>DIALING</code>", code_style), Paragraph("<code>CONNECTED, WRAP_UP, AVAILABLE, OFFLINE</code>", code_style), Paragraph("Call placed. Moves to CONNECTED on pickup, WRAP_UP/AVAILABLE on no-answer/busy.", table_cell_style)],
        [Paragraph("<code>CONNECTED</code>", code_style), Paragraph("<code>WRAP_UP, OFFLINE</code>", code_style), Paragraph("Active conversation with borrower. Concludes into post-call disposition wrap-up.", table_cell_style)],
        [Paragraph("<code>WRAP_UP</code>", code_style), Paragraph("<code>AVAILABLE, PAUSED, OFFLINE</code>", code_style), Paragraph("Agent logging notes/disposition. Returns to active queue, takes a break, or logs out.", table_cell_style)],
        [Paragraph("<code>PAUSED</code>", code_style), Paragraph("<code>AVAILABLE, OFFLINE</code>", code_style), Paragraph("Agent on break or meeting. Resumes availability or logs off.", table_cell_style)],
    ]
    agent_table = Table(agent_state_data, colWidths=[85, 160, 287])
    agent_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ])
    )
    story.append(agent_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>B. Call Lifecycle State Machine</b>", ParagraphStyle("SubH2", parent=body_style, fontName="Helvetica-Bold", textColor=PRIMARY)))
    call_state_data = [
        [Paragraph("<b>Call State</b>", table_header_style), Paragraph("<b>Permitted Next States</b>", table_header_style), Paragraph("<b>Terminal?</b>", table_header_style), Paragraph("<b>Carrier & Lifecycle Meaning</b>", table_header_style)],
        [Paragraph("<code>QUEUED</code>", code_style), Paragraph("<code>RESERVED, CANCELLED</code>", code_style), Paragraph("No", table_cell_center), Paragraph("Scheduled for dialing; reserved by allocator or cancelled (e.g. DNC).", table_cell_style)],
        [Paragraph("<code>RESERVED</code>", code_style), Paragraph("<code>INITIATED, QUEUED, CANCELLED</code>", code_style), Paragraph("No", table_cell_center), Paragraph("Locked for agent. Moves to INITIATED on dial, QUEUED on lease expiry.", table_cell_style)],
        [Paragraph("<code>INITIATED</code>", code_style), Paragraph("<code>RINGING, ANSWERED, FAILED, CANCELLED</code>", code_style), Paragraph("No", table_cell_center), Paragraph("Dial request dispatched to carrier. Awaits network ringing or failure.", table_cell_style)],
        [Paragraph("<code>RINGING</code>", code_style), Paragraph("<code>ANSWERED, FAILED, CANCELLED</code>", code_style), Paragraph("No", table_cell_center), Paragraph("Handset ringing. Advances to ANSWERED on pickup, FAILED on busy/timeout.", table_cell_style)],
        [Paragraph("<code>ANSWERED</code>", code_style), Paragraph("<code>CONNECTED, COMPLETED, FAILED</code>", code_style), Paragraph("No", table_cell_center), Paragraph("Borrower answered. Bridges to agent (CONNECTED) or IVR (COMPLETED).", table_cell_style)],
        [Paragraph("<code>CONNECTED</code>", code_style), Paragraph("<code>COMPLETED, FAILED</code>", code_style), Paragraph("No", table_cell_center), Paragraph("Active conversation. Terminates normally (COMPLETED) or drops (FAILED).", table_cell_style)],
        [Paragraph("<code>COMPLETED</code>", code_style), Paragraph("<i>None (Terminal)</i>", table_cell_style), Paragraph("<b>YES</b>", table_cell_center), Paragraph("Successful call conclusion. Locked against all further transitions.", table_cell_style)],
        [Paragraph("<code>FAILED</code>", code_style), Paragraph("<i>None (Terminal)</i>", table_cell_style), Paragraph("<b>YES</b>", table_cell_center), Paragraph("Unanswered, busy, invalid number, carrier timeout, or network drop.", table_cell_style)],
        [Paragraph("<code>CANCELLED</code>", code_style), Paragraph("<i>None (Terminal)</i>", table_cell_style), Paragraph("<b>YES</b>", table_cell_center), Paragraph("Aborted prior to connection (campaign stop, DNC match, initiation drop).", table_cell_style)],
    ]
    call_table = Table(call_state_data, colWidths=[75, 160, 50, 247])
    call_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ])
    )
    story.append(call_table)

    story.append(PageBreak())

    # =========================================================================
    # 5. END-TO-END CALL FLOW
    # =========================================================================
    story.append(make_header_banner("4. END-TO-END CALL FLOW TRACE"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "The following concrete lifecycle trace illustrates how a single call (<code>C1</code>) and borrower (<code>B1</code>) "
        "interact with human Collections Agent (<code>A1</code>) across all system boundaries:",
        body_style
    ))

    flow_data = [
        [Paragraph("<b>Step & Event</b>", table_header_style), Paragraph("<b>Agent State</b>", table_header_style), Paragraph("<b>Call State</b>", table_header_style), Paragraph("<b>Governing Component & Action Description</b>", table_header_style)],
        [
            Paragraph("1. Initial State", table_cell_bold),
            Paragraph("<code>AVAILABLE</code>", code_style),
            Paragraph("<code>QUEUED</code>", code_style),
            Paragraph("Agent is idle in queue; Call C1 is scheduled in repository.", table_cell_style),
        ],
        [
            Paragraph("2. Allocation", table_cell_bold),
            Paragraph("<code>RESERVED</code>", code_style),
            Paragraph("<code>RESERVED</code>", code_style),
            Paragraph("<b>Call Allocator:</b> Atomically reserves A1 and C1 under lock; assigns 30s lease timestamp.", table_cell_style),
        ],
        [
            Paragraph("3. Provider Dial", table_cell_bold),
            Paragraph("<code>DIALING</code>", code_style),
            Paragraph("<code>INITIATED</code>", code_style),
            Paragraph("<b>Telecom Provider:</b> Dispatches carrier request; emits <code>INITIATED</code> event.", table_cell_style),
        ],
        [
            Paragraph("4. Carrier Ringing", table_cell_bold),
            Paragraph("<code>DIALING</code>", code_style),
            Paragraph("<code>RINGING</code>", code_style),
            Paragraph("<b>Provider Event Handler:</b> Receives <code>RINGING</code> event; transitions C1 state.", table_cell_style),
        ],
        [
            Paragraph("5. Borrower Pickup", table_cell_bold),
            Paragraph("<code>CONNECTED</code>", code_style),
            Paragraph("<code>CONNECTED</code>", code_style),
            Paragraph("<b>Provider Event Handler:</b> Receives <code>ANSWERED</code>, immediately bridges call to Agent A1.", table_cell_style),
        ],
        [
            Paragraph("6. Call Termination", table_cell_bold),
            Paragraph("<code>WRAP_UP</code>", code_style),
            Paragraph("<code>COMPLETED</code>", code_style),
            Paragraph("<b>Carrier & Handler:</b> Call ends. C1 enters terminal <code>COMPLETED</code>; A1 enters post-call notes.", table_cell_style),
        ],
        [
            Paragraph("7. Notes Finished", table_cell_bold),
            Paragraph("<code>AVAILABLE</code>", code_style),
            Paragraph("<code>COMPLETED</code>", code_style),
            Paragraph("<b>Agent UI / Workflow:</b> Agent completes disposition notes and returns to active queue.", table_cell_style),
        ],
    ]
    flow_table = Table(flow_data, colWidths=[90, 85, 85, 272])
    flow_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ])
    )
    story.append(flow_table)
    story.append(Spacer(1, 8))

    # =========================================================================
    # 6. PROGRESSIVE VS PREDICTIVE DIALING
    # =========================================================================
    story.append(make_header_banner("5. PROGRESSIVE VS. PREDICTIVE DIALING"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "<b>Progressive Dialing (1:1 Ratio):</b><br/>"
        "Strict rule: <code>available agents = maximum number of agent-bound outbound calls allowed at that moment</code>.<br/>"
        "If 10 agents are available, exactly 10 outbound calls are placed. This mode guarantees zero abandoned calls, but in low answer-rate "
        "environments (e.g. 20%), human agents remain idle waiting for lines to connect.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Predictive Pacing Engine (Statistical Forecasting):</b><br/>"
        "Estimates required dial volume based on real-time empirical signals without deploying heavyweight machine learning models:",
        body_style
    ))

    formula_text = (
        "<b>Pacing Formula:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Target Answers</b> = max(0, (Available Agents + Expected Wrap-ups) - (In-flight Calls × Answer Rate))<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Recommended Dials</b> = Target Answers / Effective Answer Rate<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Little's Law Lookahead:</b> Expected Wrap-ups = (Connected Calls / Avg Talk Time) × Dial Latency Window (5.0s)"
    )
    story.append(make_callout(formula_text, border_color=ACCENT, bg_color=BG_LIGHT))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "<b>Crucial Design Distinction:</b> The Predictive Pacing Engine produces <i>recommendations only</i>. It has zero authority to dispatch "
        "calls or allocate resources directly. Its recommendation is passed to the Safety Controller for validation.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # =========================================================================
    # 7. DETERMINISTIC SAFETY CONTROLLER
    # =========================================================================
    story.append(make_header_banner("6. DETERMINISTIC SAFETY CONTROLLER"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "The Safety Controller is the non-bypassable guardian of the dialing system. It evaluates operational state and returns a binding decision:",
        body_style
    ))
    story.append(Paragraph(
        "1. <b>Zero Available Capacity:</b> If 0 agents are <code>AVAILABLE</code>, all dials are strictly rejected (approved = 0).<br/>"
        "2. <b>Overdial Ceiling:</b> Total in-flight dials + new dials cannot exceed <code>available_agents × max_overdial_ratio</code> (default: 3.0).<br/>"
        "3. <b>Abandonment Risk Cap:</b> Expected answered calls are constrained so they never exceed available agent capacity.<br/>"
        "4. <b>Carrier Health Degradation Fallback:</b> If carrier health drops below <code>0.70</code>, predictive dialing is automatically throttled and "
        "forced back to 1:1 progressive dialing.<br/>"
        "5. <b>Critical Carrier Failure:</b> If carrier health falls below <code>0.30</code>, all dials are halted completely.",
        body_style
    ))
    story.append(Paragraph(
        "<i>Note: Numerical thresholds (3.0 overdial ratio, 0.70 degradation fallback, 0.30 critical cutoff) are configurable implementation parameters, "
        "not hardcoded assignment mandates.</i>",
        ParagraphStyle("NoteText", parent=body_style, fontName="Helvetica-Oblique", fontSize=8, textColor=MUTED)
    ))

    story.append(PageBreak())

    # =========================================================================
    # 8. CONCURRENCY & ATOMIC ALLOCATION
    # =========================================================================
    story.append(make_header_banner("7. CONCURRENCY & ATOMIC ALLOCATION"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "In a multi-worker contact center, multiple background worker processes concurrently attempt to match available agents with queued calls. "
        "Without concurrency controls, race conditions lead to <b>double-booking agents</b> (two calls connecting to the same agent) or "
        "<b>double-dialing borrowers</b>.",
        body_style
    ))

    # Concurrency Diagram Box using clean structured table formatting
    concurrency_diag_data = [
        [
            Paragraph("<b>Concurrent Contention</b><br/><br/>• <b>Worker 1</b> (Thread A)<br/>• <b>Worker 2</b> (Thread B)<br/><br/><i>Both attempt to allocate Agent A1 simultaneously</i>", table_cell_style),
            Paragraph("<b>[ RLock Critical Section ]</b><br/><br/>1. Atomically verify Agent A1 <code>AVAILABLE</code><br/>2. Atomically verify Call C1 <code>QUEUED</code><br/>3. Verify Borrower has no other active calls", table_cell_style),
            Paragraph("<b>Deterministic Resolution</b><br/><br/>• <b>Worker 1:</b> Acquires lock, reserves A1 & C1 (<b>SUCCESS</b>)<br/><br/>• <b>Worker 2:</b> Sees A1 already <code>RESERVED</code>, gracefully skips (<b>SAFE</b>)", table_cell_style),
        ]
    ]
    diag_table = Table(concurrency_diag_data, colWidths=[165, 185, 182])
    diag_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(diag_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Concurrency Implementation (Prototype Design):</b><br/>"
        "• Uses <code>threading.RLock</code> protecting all read-modify-write operations inside <code>InMemoryRepository</code>.<br/>"
        "• <code>reserve_agent_and_call()</code> atomically checks that the agent is <code>AVAILABLE</code>, call is <code>QUEUED</code>, "
        "and borrower has no other active calls before simultaneously transitioning both entities to <code>RESERVED</code>.<br/>"
        "• <b>Stress Test Validation:</b> 30 concurrent worker threads attempting rapid allocations across 500 calls and 50 agents achieved "
        "<b>0 double-bookings</b> and <b>0 duplicate borrower allocations</b> (verified in <code>test_load_concurrency.py</code>).",
        body_style
    ))
    story.append(Spacer(1, 8))

    # =========================================================================
    # 9. PROVIDER FAILURE & IDEMPOTENCY
    # =========================================================================
    story.append(make_header_banner("8. TELECOM PROVIDER FAULTS & IDEMPOTENCY"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "Real-world telecom carriers frequently exhibit erratic behaviors. DialGuard models two carrier implementations to validate resilience:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Provider 1 (<code>ReliableProvider</code>):</b> Fast, deterministic, orderly event flow.<br/>"
        "• <b>Provider 2 (<code>FlakyProvider</code>):</b> Injects realistic anomalies including network timeouts, duplicate transmissions, "
        "inverted out-of-order deliveries (e.g. <code>ANSWERED</code> before <code>RINGING</code>), and dynamic health score degradation.",
        bullet_style
    ))
    story.append(Paragraph(
        "<b>Idempotency & Resilience Mechanisms:</b><br/>"
        "1. <i>Event ID Deduplication:</i> Every incoming event has a unique <code>event_id</code> cached in memory. Duplicate events are silently ignored.<br/>"
        "2. <i>Milestone Deduplication:</i> <code>(call_id, event_type)</code> milestones prevent re-executing identical state transitions.<br/>"
        "3. <i>Terminal State Lockdown:</i> Calls in <code>COMPLETED</code>, <code>FAILED</code>, or <code>CANCELLED</code> strictly reject subsequent late-arriving carrier events, preventing state corruption.<br/>"
        "4. <i>Direct Answer Progression:</i> If carrier skips ringing and reports <code>ANSWERED</code> directly from <code>INITIATED</code>, the state machine advances smoothly without error.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # =========================================================================
    # 10. FAILURE RECOVERY SUPERVISOR
    # =========================================================================
    story.append(make_header_banner("9. FAILURE RECOVERY SUPERVISOR"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "Worker state is never the sole source of truth. If a worker process crashes after reserving an agent and call, "
        "the <code>RecoverySupervisor</code> automatically recovers orphaned resources:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Lease Expiration Sweeps:</b> Each reservation attaches a 30s lease timestamp (<code>lease_expires_at</code>). "
        "The supervisor periodically sweeps the repository, returning expired <code>RESERVED</code> calls to <code>QUEUED</code> and orphaned agents to <code>AVAILABLE</code>.<br/>"
        "• <b>Stuck In-Flight Recovery:</b> Calls stuck in <code>INITIATED</code> or <code>RINGING</code> beyond the timeout threshold (60s) without carrier updates "
        "are transitioned to <code>FAILED</code>, freeing the assigned agent back to <code>AVAILABLE</code>.",
        bullet_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # 11. SIMULATION RESULTS
    # =========================================================================
    story.append(make_header_banner("10. SIMULATION RESULTS & BENCHMARKS"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "DialGuard includes a discrete-event campaign simulator benchmarking <b>Progressive vs. Predictive Dialing</b> across the four standard scenarios. "
        "Below are the actual results from the latest execution:",
        body_style
    ))

    sim_data = [
        [
            Paragraph("<b>Scenario & Context</b>", table_header_style),
            Paragraph("<b>Mode</b>", table_header_style),
            Paragraph("<b>Dials</b>", table_header_style),
            Paragraph("<b>Answered</b>", table_header_style),
            Paragraph("<b>Completed</b>", table_header_style),
            Paragraph("<b>Failed / Unans.</b>", table_header_style),
            Paragraph("<b>Agent Util.</b>", table_header_style),
            Paragraph("<b>Safety Caps</b>", table_header_style),
            Paragraph("<b>Fallback Cycles</b>", table_header_style),
        ],
        [
            Paragraph("<b>Scenario A</b><br/><font size=7 color='#64748B'>Low Answer: 20%<br/>Avg Talk: 120s</font>", table_cell_style),
            Paragraph("Progressive<br/>Predictive", table_cell_style),
            Paragraph("200<br/>200", table_cell_center),
            Paragraph("43<br/>42", table_cell_center),
            Paragraph("43<br/>42", table_cell_center),
            Paragraph("157<br/>158", table_cell_center),
            Paragraph("40.8%<br/><b>44.3%</b>", table_cell_center),
            Paragraph("0<br/>60", table_cell_center),
            Paragraph("N/A<br/>0", table_cell_center),
        ],
        [
            Paragraph("<b>Scenario B</b><br/><font size=7 color='#64748B'>Moderate Answer: 50%<br/>Avg Talk: 90s</font>", table_cell_style),
            Paragraph("Progressive<br/>Predictive", table_cell_style),
            Paragraph("200<br/>200", table_cell_center),
            Paragraph("101<br/>90", table_cell_center),
            Paragraph("101<br/>90", table_cell_center),
            Paragraph("99<br/>110", table_cell_center),
            Paragraph("<b>55.5%</b><br/>52.7%", table_cell_center),
            Paragraph("0<br/>51", table_cell_center),
            Paragraph("N/A<br/>0", table_cell_center),
        ],
        [
            Paragraph("<b>Scenario C</b><br/><font size=7 color='#64748B'>High Answer: 70%<br/>Avg Talk: 180s</font>", table_cell_style),
            Paragraph("Progressive<br/>Predictive", table_cell_style),
            Paragraph("103<br/>103", table_cell_center),
            Paragraph("72<br/>74", table_cell_center),
            Paragraph("66<br/>66", table_cell_center),
            Paragraph("31<br/>29", table_cell_center),
            Paragraph("<b>82.8%</b><br/><b>82.8%</b>", table_cell_center),
            Paragraph("0<br/>59", table_cell_center),
            Paragraph("N/A<br/>0", table_cell_center),
        ],
        [
            Paragraph("<b>Scenario D</b><br/><font size=7 color='#64748B'>Dynamic Shift: 40%→15%<br/>Flaky Carrier Degradation</font>", table_cell_style),
            Paragraph("Progressive<br/>Predictive", table_cell_style),
            Paragraph("173<br/>169", table_cell_center),
            Paragraph("58<br/>64", table_cell_center),
            Paragraph("58<br/>64", table_cell_center),
            Paragraph("115<br/>105", table_cell_center),
            Paragraph("44.5%<br/>41.2%", table_cell_center),
            Paragraph("0<br/>60", table_cell_center),
            Paragraph("N/A<br/><b>59</b>", table_cell_center),
        ],
    ]
    sim_table = Table(sim_data, colWidths=[108, 56, 50, 50, 52, 50, 52, 54, 60])
    sim_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ])
    )
    story.append(sim_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Technical Interpretation:</b><br/>"
        "• <i>Stochastic Realities:</i> Predictive pacing is not guaranteed to outperform progressive dialing in every random distribution. In Scenario B, progressive achieved slightly higher utilization due to random cluster pickups.<br/>"
        "• <i>Low-Answer Regimes (Scenario A):</i> Predictive pacing improved agent utilization (+3.5%) by forecasting completions and buffering in-flight dials.<br/>"
        "• <i>Dynamic Carrier Degradation (Scenario D):</i> When carrier health degraded, the Safety Controller actively intervened, executing <b>59 progressive fallback cycles</b> to shield human agents from carrier dropouts.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # =========================================================================
    # 12. TESTING & VERIFICATION
    # =========================================================================
    story.append(make_header_banner("11. VERIFICATION & TEST SUITE COVERAGE"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "<b>100% Passing Test Suite:</b> The test suite consists of <b>96 automated tests</b> executed via Pytest in <b>0.19 seconds</b>:",
        body_style
    ))

    test_data = [
        [Paragraph("<b>Test Module & File</b>", table_header_style), Paragraph("<b>Tests</b>", table_header_style), Paragraph("<b>Key Behaviors & Invariants Covered</b>", table_header_style)],
        [
            Paragraph("<code>test_agent_state.py</code>", code_style),
            Paragraph("35", table_cell_center),
            Paragraph("All 19 valid transitions, illegal jumps, self-transitions, state immutability on failure, full shift lifecycles.", table_cell_style),
        ],
        [
            Paragraph("<code>test_call_state.py</code>", code_style),
            Paragraph("29", table_cell_center),
            Paragraph("Happy path, direct answer, terminal state lockdown (<code>COMPLETED/FAILED/CANCELLED</code>), out-of-order rejection.", table_cell_style),
        ],
        [
            Paragraph("<code>test_allocator.py</code>", code_style),
            Paragraph("5", table_cell_center),
            Paragraph("Atomic reservations, multi-worker agent double-booking prevention, duplicate borrower call rejection.", table_cell_style),
        ],
        [
            Paragraph("<code>test_telecom.py</code>", code_style),
            Paragraph("7", table_cell_center),
            Paragraph("<code>ReliableProvider</code> event flow, <code>FlakyProvider</code> timeout, duplicate, and out-of-order injection.", table_cell_style),
        ],
        [
            Paragraph("<code>test_event_handler.py</code>", code_style),
            Paragraph("5", table_cell_center),
            Paragraph("Event deduplication cache, milestone filtering, terminal call protection, agent-call synchronization.", table_cell_style),
        ],
        [
            Paragraph("<code>test_safety_controller.py</code>", code_style),
            Paragraph("6", table_cell_center),
            Paragraph("Hard capacity limits, overdial ratio caps, zero agent rejection, critical cutoff, progressive fallback.", table_cell_style),
        ],
        [
            Paragraph("<code>test_pacing_engine.py</code>", code_style),
            Paragraph("4", table_cell_center),
            Paragraph("Pacing formulas, Little's Law wrap-up lookahead, in-flight deductions, carrier health scaling.", table_cell_style),
        ],
        [
            Paragraph("<code>test_dialers.py</code>", code_style),
            Paragraph("2", table_cell_center),
            Paragraph("Progressive 1:1 agent limit enforcement, Predictive dialer pipeline orchestration.", table_cell_style),
        ],
        [
            Paragraph("<code>test_recovery.py</code>", code_style),
            Paragraph("2", table_cell_center),
            Paragraph("Worker crash simulation, reservation lease expiration sweeps, stuck in-flight call timeouts.", table_cell_style),
        ],
        [
            Paragraph("<code>test_load_concurrency.py</code>", code_style),
            Paragraph("1", table_cell_center),
            Paragraph("<b>High-concurrency stress test:</b> 30 threads, 500 calls, 50 agents -> 0 double allocations, intact invariants.", table_cell_style),
        ],
    ]
    test_table = Table(test_data, colWidths=[140, 45, 347])
    test_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ])
    )
    story.append(test_table)

    story.append(PageBreak())

    # =========================================================================
    # 13. DESIGN DECISIONS & TRADE-OFFS
    # =========================================================================
    story.append(make_header_banner("12. DESIGN DECISIONS & ARCHITECTURAL TRADE-OFFS"))
    story.append(Spacer(1, 5))

    decisions_data = [
        [Paragraph("<b>Architectural Decision</b>", table_header_style), Paragraph("<b>Implementation Choice</b>", table_header_style), Paragraph("<b>Trade-off & Engineering Rationale</b>", table_header_style)],
        [
            Paragraph("<b>In-Memory Store vs Real DB</b>", table_cell_bold),
            Paragraph("<code>InMemoryRepository</code> with <code>threading.RLock</code>", code_style),
            Paragraph("Zero external dependencies (no Postgres/Redis); ultra-fast execution. Trade-off: volatile state on process termination.", table_cell_style),
        ],
        [
            Paragraph("<b>Advisory Pacing Engine</b>", table_cell_bold),
            Paragraph("Pacing recommends; Safety decides", code_style),
            Paragraph("Separates statistical heuristic optimization from safety invariant enforcement. Pacing can never bypass safety.", table_cell_style),
        ],
        [
            Paragraph("<b>Deterministic Safety Gate</b>", table_cell_bold),
            Paragraph("Hard mathematical capacity checks", code_style),
            Paragraph("Deterministic behavior is auditable and explainable in technical reviews, avoiding opaque ML hallucinations.", table_cell_style),
        ],
        [
            Paragraph("<b>Lease-Based Crash Recovery</b>", table_cell_bold),
            Paragraph("Time-bounded reservation leases (30s)", code_style),
            Paragraph("Prevents orphaned locks when workers crash without requiring heavyweight distributed consensus.", table_cell_style),
        ],
        [
            Paragraph("<b>Telecom Provider Mocks</b>", table_cell_bold),
            Paragraph("<code>ReliableProvider</code> & <code>FlakyProvider</code>", code_style),
            Paragraph("Allows deterministic simulation of network chaos (timeouts, duplicates, out-of-order events) without telephony costs.", table_cell_style),
        ],
    ]
    decisions_table = Table(decisions_data, colWidths=[120, 150, 262])
    decisions_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ])
    )
    story.append(decisions_table)
    story.append(Spacer(1, 8))

    # =========================================================================
    # 14. LIMITATIONS & PRODUCTION ROADMAP
    # =========================================================================
    story.append(make_header_banner("13. LIMITATIONS & PRODUCTION ROADMAP"))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "DialGuard was intentionally constructed as a self-contained local prototype. To transition from prototype to an enterprise-grade "
        "telecom platform, the following enhancements represent the production roadmap (<i>none of which are currently claimed as implemented</i>):",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Distributed Persistence & Storage:</b> Transitioning from in-memory dictionaries to PostgreSQL with row-level locks (<code>FOR UPDATE SKIP LOCKED</code>) or Redis distributed locks (Redlock).<br/>"
        "• <b>Real Telephony Gateway:</b> Integrating SIP trunking, Webhooks, or Asterisk/FreeSWITCH / Twilio Voice APIs with Answering Machine Detection (AMD).<br/>"
        "• <b>Regulatory Compliance Engine (TCPA / TSR):</b> Hard enforcement of the FTC 3% maximum call abandonment safe harbor rule and geographic calling time windows (8:00 AM – 9:00 PM local borrower time).<br/>"
        "• <b>Streaming Event Bus:</b> Decoupling provider event handling via Kafka or RabbitMQ event streams for horizontal worker scalability.<br/>"
        "• <b>Bayesian Pacing Models:</b> Upgrading statistical pacing with online Bayesian updates for dynamic multi-campaign answer rate forecasting.",
        bullet_style
    ))
    story.append(Spacer(1, 8))

    # =========================================================================
    # 15. CONCLUSION
    # =========================================================================
    story.append(make_header_banner("14. CONCLUSION & KEY ENGINEERING TAKEAWAYS"))
    story.append(Spacer(1, 5))

    conclusion_box = (
        "<b>Summary Axiom: \"Optimization is Subordinate to Safety\"</b><br/><br/>"
        "DialGuard demonstrates that high collections-agent productivity does not require risky, unconstrained dialing or opaque machine learning models. "
        "By enforcing deterministic domain state machines, atomic reservation locks, and a non-bypassable Safety Controller, the system maintains "
        "ironclad operational safety while dynamically optimizing outbound call throughput."
    )
    story.append(make_callout(conclusion_box, border_color=PRIMARY, bg_color=BG_CARD))
    story.append(Spacer(1, 10))

    footer_p = Paragraph(
        "<b>DialGuard Prototype</b> • Repository: <font color='#1E40AF'><u>https://github.com/ayush300302/DialGuard</u></font> • Author: Ayush Patil",
        ParagraphStyle("FP", fontName="Helvetica", fontSize=8.5, leading=12, alignment=1, textColor=MUTED),
    )
    story.append(footer_p)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Successfully generated: {output_filename}")


if __name__ == "__main__":
    create_report()
