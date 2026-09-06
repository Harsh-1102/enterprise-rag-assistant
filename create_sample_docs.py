"""
create_sample_docs.py - Generates Synthetic Enterprise HR Documents

Creates realistic sample HR policy documents in PDF and DOCX formats:
- data/documents/Leave_Policy.pdf
- data/documents/Employee_Handbook.pdf
- data/documents/Work_From_Home_Policy.pdf
- data/documents/Employee_Benefits.pdf
- data/documents/Attendance_Policy.pdf
- data/documents/Code_of_Conduct.pdf
- data/documents/Resignation_and_Notice_Period.pdf
- data/documents/Attendance_Policy.docx
- data/documents/Code_Of_Conduct.docx

ALL DATA IS COMPLETELY SYNTHETIC AND DESIGNED FOR COLLEGE CAPSTONE DEMONSTRATION.
"""

import os

DOCS_DIR = os.path.join(os.path.dirname(__file__), "data", "documents")
os.makedirs(DOCS_DIR, exist_ok=True)


def create_pdf(file_path: str, title: str, pages_content: list):
    """Generates a multi-page PDF document using ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
    )

    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0F766E'),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )

    story = []

    for page_idx, page_sections in enumerate(pages_content):
        if page_idx == 0:
            story.append(Paragraph(title, title_style))
            story.append(
                Paragraph(
                    "SYNTHETIC SAMPLE DOCUMENT - FOR ACADEMIC RAG "
                    "DEMONSTRATION ONLY",
                    disclaimer_style
                )
            )
            story.append(
                HRFlowable(
                    width="100%", thickness=1,
                    color=colors.HexColor("#CBD5E1"), spaceAfter=14
                )
            )
        else:
            story.append(PageBreak())
            story.append(
                Paragraph(f"{title} (Continued - Page {page_idx + 1})", h2_style)
            )
            story.append(Spacer(1, 10))

        for heading, body in page_sections:
            if heading:
                story.append(Paragraph(heading, h2_style))
            story.append(Paragraph(body, body_style))
            story.append(Spacer(1, 6))

    doc.build(story)
    print(f"Generated PDF: {file_path}")


def create_docx(file_path: str, title: str, sections: list):
    """Generates a structured DOCX document using python-docx."""
    import docx
    from docx.shared import Pt, RGBColor

    doc = docx.Document()

    # Title
    t = doc.add_heading(title, level=0)
    t.runs[0].font.color.rgb = RGBColor(0x0F, 0x76, 0x6E)

    # Synthetic disclaimer
    p_disc = doc.add_paragraph(
        "SYNTHETIC SAMPLE DOCUMENT - FOR ACADEMIC RAG DEMONSTRATION ONLY"
    )
    p_disc.runs[0].font.italic = True
    p_disc.runs[0].font.size = Pt(8.5)
    p_disc.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    for heading, paragraphs in sections:
        h = doc.add_heading(heading, level=1)
        h.runs[0].font.size = Pt(13)
        h.runs[0].font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
        for p_text in paragraphs:
            p = doc.add_paragraph(p_text)
            p.style.font.name = 'Arial'
            p.style.font.size = Pt(10)

    doc.save(file_path)
    print(f"Generated DOCX: {file_path}")


def generate_all_samples():
    print("Generating synthetic enterprise HR documents...")

    # 1. Leave Policy (PDF - 2 pages)
    leave_pages = [
        # Page 1
        [
            ("1. Annual Paid Leave Entitlement",
             "All permanent full-time employees are entitled to 20 days of "
             "paid annual leave per calendar year. Leave accrues on a monthly "
             "pro-rata basis at the rate of 1.67 days per completed calendar "
             "month of active service. Part-time employees receive pro-rated "
             "annual leave calculated according to contracted weekly hours. "
             "Annual leave must be requested at least two weeks in advance "
             "via the HR Portal and approved by the reporting manager."),
            ("2. Sick Leave and Medical Absence",
             "Employees are granted 10 paid sick leave days per calendar year. "
             "Employees may take up to 2 consecutive days of sick leave without "
             "providing a medical certificate. Any medical absence lasting 3 "
             "or more consecutive business days requires a formal medical "
             "certificate issued by a certified healthcare practitioner. "
             "Unused sick leave does not roll over to the subsequent calendar "
             "year and is non-encashable upon departure."),
        ],
        # Page 2
        [
            ("3. Parental and Maternity / Paternity Leave",
             "Female employees who have completed at least 12 months of "
             "continuous service are entitled to 16 weeks of fully paid "
             "maternity leave. Paternity leave is granted at 4 weeks of fully "
             "paid leave for male employees, which can be availed within the "
             "first six months following childbirth or legal adoption. "
             "Employees must notify HR at least 60 days prior to commencing leave."),
            ("4. Bereavement and Compassionate Leave",
             "Employees are eligible for up to 5 consecutive paid days of "
             "compassionate leave in the event of the loss of an immediate family "
             "member (spouse, parent, child, or sibling). For extended relatives, "
             "2 days of paid leave is permitted. Additional unpaid leave may "
             "be requested subject to managerial discretion."),
        ]
    ]
    create_pdf(
        os.path.join(DOCS_DIR, "Leave_Policy.pdf"),
        "Enterprise Leave & Absence Policy",
        leave_pages
    )

    # 2. Employee Handbook (PDF - 3 pages)
    handbook_pages = [
        # Page 1
        [
            ("1. Welcome & Company Mission",
             "Welcome to Apex Enterprise Technologies. Our mission is to engineer "
             "trusted intelligent systems that empower businesses globally. "
             "This Employee Handbook establishes our organizational operating "
             "principles, rights, responsibilities, and employment terms. "
             "Every team member is expected to review, understand, and comply "
             "with these policies throughout their tenure."),
            ("2. Probation Period and Confirmation",
             "All new hires undergo a standard probation period of 90 calendar "
             "days from their effective start date. During probation, employee "
             "performance, cultural alignment, and competency will be reviewed "
             "at 30, 60, and 90-day intervals. The probation period may be "
             "extended once for up to 30 additional days if deemed appropriate "
             "by the department director."),
        ],
        # Page 2
        [
            ("3. Resignation and Notice Period",
             "Permanent confirmed employees wishing to resign must submit written "
             "notice through the enterprise portal. The standard notice period is "
             "30 calendar days for permanent staff, and 60 calendar days for "
             "Lead, Manager, and Director positions. During the probation period, "
             "the required notice period is 15 calendar days. Early release or "
             "payment in lieu of notice requires mutual written agreement."),
            ("4. Performance Appraisal & Career Progression",
             "Formal performance evaluations are conducted bi-annually in June "
             "and December. Appraisals follow an OKR (Objectives and Key Results) "
             "framework combined with 360-degree peer feedback. Promotions, merit "
             "increments, and annual bonus distributions are directly tied to "
             "documented appraisal scores."),
        ],
        # Page 3
        [
            ("5. Company Property and IT Asset Usage",
             "Laptops, security keys, monitors, and company mobile phones remain "
             "the sole property of Apex Enterprise Technologies. All company "
             "hardware must be returned in good working condition within 3 "
             "business days of an employee's final working day. Personal software "
             "installation is prohibited on company-managed devices."),
        ]
    ]
    create_pdf(
        os.path.join(DOCS_DIR, "Employee_Handbook.pdf"),
        "Apex Enterprise Employee Handbook",
        handbook_pages
    )

    # 3. Work From Home Policy (PDF - 2 pages)
    wfh_pages = [
        # Page 1
        [
            ("1. Hybrid Work Framework",
             "Apex Enterprise operates on a flexible hybrid work model. "
             "Eligible employees may work remotely for up to 3 days per week, "
             "with a minimum of 2 mandatory collaborative in-office days per week. "
             "Specific designated in-office days are scheduled by individual "
             "department heads to maximize cross-functional team collaboration."),
            ("2. Core Hours and Communication Standards",
             "Employees working remotely must be active, reachable, and "
             "responsive during standard core business hours: 10:00 AM to "
             "4:00 PM local time. Team members must maintain an updated Slack "
             "status and join scheduled video conferences during team standups."),
        ],
        # Page 2
        [
            ("3. Home Office Equipment Stipend",
             "Full-time remote-eligible employees receive a one-time home office "
             "setup reimbursement of up to $750. Eligible expenses include "
             "ergonomic desk chairs, external monitors, keyboards, noise-canceling "
             "headsets, and desk risers. Receipts must be submitted within 45 days."),
            ("4. Remote Network Security and VPN",
             "All remote network traffic accessing enterprise repositories, "
             "databases, or client systems must route through the corporate VPN. "
             "Working from unsecured public Wi-Fi networks without an active "
             "corporate VPN is strictly prohibited."),
        ]
    ]
    create_pdf(
        os.path.join(DOCS_DIR, "Work_From_Home_Policy.pdf"),
        "Corporate Remote & Hybrid Work Policy",
        wfh_pages
    )

    # 4. Employee Benefits (PDF - 2 pages)
    benefits_pages = [
        # Page 1
        [
            ("1. Comprehensive Health Insurance",
             "The company provides comprehensive medical, dental, and vision "
             "insurance for all full-time employees and eligible dependents. "
             "The plan includes an annual maximum coverage of $500,000 per member, "
             "with 100% preventive care coverage and a low $25 co-pay for general "
             "physician visits. Mental health therapy sessions are covered up to "
             "12 visits per year with zero employee co-pay through our EAP."),
            ("2. Retirement and 401(k) Matching",
             "Employees become eligible for the 401(k) retirement savings plan "
             "starting on the first day of the month following 30 days of service. "
             "The company provides a 100% dollar-for-dollar match on employee "
             "contributions up to 5% of their total annual base salary. "
             "All company matching funds vest immediately with 100% vesting."),
        ],
        # Page 2
        [
            ("3. Professional Development and Tuition Allowance",
             "To encourage continuous technical learning, each employee is "
             "eligible for an annual professional development budget of $1,500. "
             "This budget can be used toward professional certifications (AWS, "
             "GCP, PMP), industry conferences, textbooks, and approved online "
             "courses (Coursera, Udemy, edX). Prior manager approval required."),
            ("4. Wellness and Gym Subsidy",
             "Employees receive a monthly wellness stipend of $60 to cover gym "
             "memberships, yoga studio passes, or fitness subscriptions. "
             "Reimbursements are processed automatically through monthly payroll."),
        ]
    ]
    create_pdf(
        os.path.join(DOCS_DIR, "Employee_Benefits.pdf"),
        "Enterprise Employee Benefits & Perks Guide",
        benefits_pages
    )

    # 5. Attendance Policy (PDF - 2 pages)
    attendance_pages = [
        # Page 1
        [
            ("1. Standard Working Hours and Shift Schedules",
             "The standard workweek consists of 40 hours, scheduled Monday through "
             "Friday from 9:00 AM to 6:00 PM, including a 60-minute unpaid lunch "
             "break. Flexible arrival times are permitted between 8:00 AM and "
             "10:00 AM, provided the employee completes the standard 8-hour workday."),
            ("2. Attendance Tracking and Biometric Logging",
             "All non-exempt employees must record daily attendance using the "
             "biometric terminal or digital HR portal check-in upon arrival and "
             "departure. Manual time adjustments must be approved by supervisors."),
        ],
        # Page 2
        [
            ("3. Grace Periods and Tardiness Discipline",
             "A grace period of 15 minutes is allowed for morning clock-ins (up to "
             "9:15 AM). Arrivals after 9:15 AM without prior notification are "
             "logged as tardy. Accumulating three unexcused tardy instances within "
             "a single calendar month will trigger a formal written counseling from HR."),
            ("4. Unscheduled Absence and Job Abandonment",
             "If an employee is unable to report to work due to emergency, they must "
             "notify their supervisor and HR at least 1 hour prior to their shift. "
             "Failure to report for three consecutive business days without any "
             "communication is classified as Job Abandonment and results in termination."),
        ]
    ]
    create_pdf(
        os.path.join(DOCS_DIR, "Attendance_Policy.pdf"),
        "Enterprise Attendance and Punctuality Policy",
        attendance_pages
    )

    # 6. Code of Conduct (PDF - 2 pages)
    conduct_pages = [
        # Page 1
        [
            ("1. Professional Standards and Workplace Integrity",
             "Apex Enterprise is committed to fostering an inclusive, respectful, "
             "and ethical workplace environment. Every employee must treat "
             "colleagues, clients, and partners with dignity, professionalism, and "
             "honesty regardless of background, gender, or seniority."),
            ("2. Anti-Harassment and Non-Discrimination Policy",
             "We enforce a strict zero-tolerance policy regarding discrimination, "
             "sexual harassment, verbal hostility, or intimidation in any form. "
             "Any employee found guilty of discriminatory conduct will face immediate "
             "termination. Reports can be submitted via our confidential Ethics "
             "Hotline (1-800-ETHIC-HR) 24 hours a day, 7 days a week."),
        ],
        # Page 2
        [
            ("3. Conflict of Interest and Secondary Employment",
             "Employees must not engage in outside business activities, consulting, "
             "or secondary employment that competes with Apex Enterprise or creates "
             "a conflict of interest. Holding secondary employment requires prior "
             "written disclosure and approval by the Chief Legal Officer."),
            ("4. Whistleblower Protection Policy",
             "Apex Enterprise strictly prohibits retaliation of any kind against an "
             "employee who in good faith reports suspected legal violations, fraud, "
             "or ethical breaches. All reports will be promptly investigated with "
             "confidentiality maintained to the highest degree possible."),
        ]
    ]
    create_pdf(
        os.path.join(DOCS_DIR, "Code_of_Conduct.pdf"),
        "Enterprise Code of Conduct & Ethics Manual",
        conduct_pages
    )

    # 7. Resignation and Notice Period (PDF - 2 pages)
    resignation_pages = [
        # Page 1
        [
            ("1. Resignation Notice Periods by Designation",
             "Confirmed permanent employees must submit written resignation notice "
             "through the Enterprise HR Portal. Standard notice periods are:\n"
             "- Individual Contributors & Engineers: 30 calendar days.\n"
             "- Team Leads, Engineering Managers & Directors: 60 calendar days.\n"
             "- Executive & C-Suite Officers: 90 calendar days.\n"
             "During the 90-day probation period, the mandatory notice period "
             "is 15 calendar days for all positions."),
            ("2. Resignation Acceptance and Handover Protocol",
             "Upon resignation submission, the employee and supervisor must draft a "
             "formal Knowledge Transfer (KT) schedule. All project documentation, "
             "code credentials, and active tasks must be handed over to designated "
             "team members at least 5 business days prior to the last working day."),
        ],
        # Page 2
        [
            ("3. Early Release and Notice Period Buyout",
             "Early release or payment in lieu of notice (buyout) is not an "
             "automatic entitlement and requires mutual written agreement between "
             "the employee, department director, and Head of Human Resources. "
             "Any leave accrued cannot be offset against the mandatory notice period."),
            ("4. Exit Formalities and IT Asset Clearance",
             "On or before the last working day, all company-issued laptops, "
             "security tokens, access badges, and hardware peripherals must be "
             "returned to IT Operations. Final settlement and salary processing "
             "will be initiated within 7 business days following IT clearance."),
        ]
    ]
    create_pdf(
        os.path.join(DOCS_DIR, "Resignation_and_Notice_Period.pdf"),
        "Enterprise Resignation & Notice Period Guidelines",
        resignation_pages
    )

    # 8. Attendance Policy (DOCX)
    attendance_sections = [
        ("1. Standard Working Hours and Shift Schedules", [
            "The standard workweek consists of 40 hours, typically scheduled "
            "Monday through Friday from 9:00 AM to 6:00 PM, including a 60-minute "
            "unpaid lunch break.",
            "Flexible arrival times are permitted between 8:00 AM and 10:00 AM, "
            "provided the employee completes the standard 8-hour workday."
        ]),
        ("2. Attendance Tracking and Grace Periods", [
            "All non-exempt employees must record daily attendance using the "
            "biometric terminal or digital HR portal check-in.",
            "A grace period of 15 minutes is allowed for morning clock-ins (up to "
            "9:15 AM). Arrivals after 9:15 AM without prior notification are "
            "logged as tardy.",
            "Accumulating three unexcused tardy instances within a single "
            "calendar month will trigger a formal written counseling from HR."
        ]),
        ("3. Unscheduled Absence and Notification Protocol", [
            "If an employee is unable to report to work due to sudden illness "
            "or emergency, they must notify their immediate supervisor and HR "
            "at least 1 hour prior to their scheduled shift.",
            "Failure to report for three consecutive business days without any "
            "communication is classified as Job Abandonment and results in "
            "immediate administrative termination."
        ])
    ]
    create_docx(
        os.path.join(DOCS_DIR, "Attendance_Policy.docx"),
        "Enterprise Attendance and Punctuality Policy",
        attendance_sections
    )

    # 9. Code of Conduct (DOCX)
    conduct_sections = [
        ("1. Professional Standards and Workplace Integrity", [
            "Apex Enterprise is committed to fostering an inclusive, respectful, "
            "and ethical workplace environment.",
            "Every employee must treat colleagues, clients, and partners with "
            "dignity, professionalism, and honesty regardless of background or status."
        ]),
        ("2. Anti-Harassment and Non-Discrimination Policy", [
            "We enforce a strict zero-tolerance policy regarding discrimination, "
            "sexual harassment, verbal hostility, or intimidation in any form.",
            "Any employee found guilty of discriminatory conduct or harassment "
            "will face immediate disciplinary action, including termination of "
            "employment.",
            "Employees can safely report incidents to HR directly or submit "
            "anonymous reports via our confidential Ethics Hotline (1-800-ETHIC-HR)."
        ]),
        ("3. Conflict of Interest and Secondary Employment", [
            "Employees must not engage in outside business activities, consulting, "
            "or secondary employment that competes with Apex Enterprise or creates "
            "a conflict of interest.",
            "Holding secondary employment or board advisory positions requires "
            "prior written disclosure and approval by the Chief Legal Officer."
        ]),
        ("4. Whistleblower Protection Policy", [
            "Apex Enterprise strictly prohibits retaliation of any kind against an "
            "employee who in good faith reports suspected legal violations, fraud, "
            "or ethical breaches.",
            "All reports will be promptly investigated with confidentiality "
            "maintained to the highest degree possible."
        ])
    ]
    create_docx(
        os.path.join(DOCS_DIR, "Code_Of_Conduct.docx"),
        "Enterprise Code of Conduct & Ethics Manual",
        conduct_sections
    )

    print(f"Successfully generated all synthetic enterprise documents in: {DOCS_DIR}")


if __name__ == "__main__":
    generate_all_samples()
