import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from database import ClassificationLog


def export_to_csv(logs):
    """Export classifications to CSV format."""
    data = []
    for log in logs:
        data.append({
            'Timestamp': log.timestamp.isoformat(),
            'Label': log.label,
            'Confidence': f"{log.confidence:.2%}",
            'Reasoning': log.reasoning,
            'Latency (ms)': f"{log.latency_ms:.2f}",
            'Tokens Used': log.tokens_used,
            'Email Snippet': log.email_snippet,
            'Success': 'Yes' if log.success else 'No',
        })

    df = pd.DataFrame(data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode('utf-8')


def export_to_pdf(logs, user_name="User", title="Classification Report"):
    """Export classifications to PDF with formatting."""
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Metadata
    meta_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
    )
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
    elements.append(Paragraph(f"User: {user_name}", meta_style))
    elements.append(Paragraph(f"Total Classifications: {len(logs)}", meta_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Statistics
    if logs:
        phishing_count = sum(1 for log in logs if log.label == 'PHISHING')
        spam_count = sum(1 for log in logs if log.label == 'SPAM')
        legitimate_count = sum(1 for log in logs if log.label == 'LEGITIMATE')
        avg_confidence = sum(log.confidence for log in logs) / len(logs)

        stats_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Phishing', str(phishing_count), f"{(phishing_count/len(logs)*100):.1f}%"],
            ['Spam', str(spam_count), f"{(spam_count/len(logs)*100):.1f}%"],
            ['Legitimate', str(legitimate_count), f"{(legitimate_count/len(logs)*100):.1f}%"],
            ['Average Confidence', f"{avg_confidence:.2%}", ''],
        ]

        stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.3 * inch))

    # Classifications table
    if logs:
        elements.append(Paragraph("Recent Classifications", styles['Heading2']))
        elements.append(Spacer(1, 0.15 * inch))

        table_data = [['Timestamp', 'Label', 'Confidence', 'Email Snippet']]
        for log in logs[:20]:  # Show first 20
            table_data.append([
                log.timestamp.strftime('%Y-%m-%d %H:%M'),
                log.label,
                f"{log.confidence:.0%}",
                log.email_snippet[:50] + '...' if len(log.email_snippet) > 50 else log.email_snippet,
            ])

        table = Table(table_data, colWidths=[1.2*inch, 1*inch, 1*inch, 2.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)

    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()
