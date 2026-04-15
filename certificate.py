# certificate.py
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from datetime import datetime
import os
from flask import send_file, session
import io

# Register fonts (using default if custom not available)
try:
    pdfmetrics.registerFont(TTFont('Poppins', 'static/fonts/Poppins-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Poppins-Bold', 'static/fonts/Poppins-Bold.ttf'))
    FONT_REGULAR = 'Poppins'
    FONT_BOLD = 'Poppins-Bold'
except:
    FONT_REGULAR = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'


def generate_certificate(user, subject, completion_data):
    """Generate PDF certificate for completing a subject"""
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Background - Gold gradient effect
    c.setFillColorRGB(0.98, 0.75, 0.14)  # #fbbf24
    c.rect(0, 0, width, height, fill=1)
    
    # White border
    c.setStrokeColorRGB(1, 1, 1)
    c.setLineWidth(8)
    c.rect(15, 15, width - 30, height - 30)
    
    # Inner border - Navy
    c.setStrokeColorRGB(0.1, 0.17, 0.3)  # #1a2b4c
    c.setLineWidth(2)
    c.rect(25, 25, width - 50, height - 50)
    
    # Decorative lines
    c.setStrokeColorRGB(1, 1, 1)
    c.setLineWidth(1)
    c.line(width/4, height - 80, width * 3/4, height - 80)
    c.line(width/4, 80, width * 3/4, 80)
    
    # Logo / Seal (circular)
    c.setFillColorRGB(0.1, 0.17, 0.3)
    c.circle(width/2, height - 150, 40, fill=1)
    c.setFillColorRGB(0.98, 0.75, 0.14)
    c.setFont(FONT_BOLD, 24)
    c.drawCentredString(width/2, height - 160, "M")
    
    # Title
    c.setFillColorRGB(0.1, 0.17, 0.3)
    c.setFont(FONT_BOLD, 36)
    c.drawCentredString(width/2, height - 230, "CERTIFICATE OF COMPLETION")
    
    c.setFont(FONT_REGULAR, 14)
    c.drawCentredString(width/2, height - 260, "This certificate is proudly presented to")
    
    # User Name
    c.setFont(FONT_BOLD, 28)
    c.setFillColorRGB(0.98, 0.75, 0.14)
    c.drawCentredString(width/2, height - 310, user.username.upper())
    
    # Body text
    c.setFillColorRGB(0.1, 0.17, 0.3)
    c.setFont(FONT_REGULAR, 16)
    c.drawCentredString(width/2, height - 360, f"for successfully completing")
    
    c.setFont(FONT_BOLD, 20)
    c.setFillColorRGB(0.98, 0.75, 0.14)
    c.drawCentredString(width/2, height - 390, f"{subject.name} - Form {subject.form}")
    
    c.setFillColorRGB(0.1, 0.17, 0.3)
    c.setFont(FONT_REGULAR, 14)
    c.drawCentredString(width/2, height - 430, f"Completed on {completion_data['completion_date'].strftime('%d %B %Y')}")
    
    # Stats
    c.setFont(FONT_REGULAR, 12)
    stats_y = height - 480
    c.drawCentredString(width/2, stats_y, f"🎓 {completion_data['completed_lessons']} out of {completion_data['total_lessons']} lessons completed")
    c.drawCentredString(width/2, stats_y - 25, f"⏱️ Total study time: {completion_data['total_hours']} hours")
    c.drawCentredString(width/2, stats_y - 50, f"📅 Certificate ID: {completion_data['certificate_id']}")
    
    # Signatures
    c.setFont(FONT_REGULAR, 10)
    c.drawString(width * 0.2, 70, "_________________________")
    c.drawCentredString(width * 0.2, 55, "Student Signature")
    
    c.drawString(width * 0.65, 70, "_________________________")
    c.drawCentredString(width * 0.65, 55, "Academic Director")
    
    # Footer
    c.setFont(FONT_REGULAR, 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width/2, 30, "myMSCE - Malawi's #1 MSCE Tutoring Platform")
    c.drawCentredString(width/2, 20, f"Certificate generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    c.save()
    buffer.seek(0)
    return buffer


def check_subject_completion(user_id, subject_id):
    """Check if user has completed all lessons in a subject"""
    lessons = Lesson.query.filter_by(subject_id=subject_id).all()
    if not lessons:
        return False, 0, 0
    
    total_lessons = len(lessons)
    completed_lessons = 0
    total_watch_time = 0
    
    for lesson in lessons:
        progress = Progress.query.filter_by(
            user_id=user_id,
            lesson_id=lesson.id
        ).first()
        
        if progress and progress.completed:
            completed_lessons += 1
        if progress:
            total_watch_time += progress.watch_time
    
    is_completed = completed_lessons == total_lessons
    
    return is_completed, completed_lessons, total_lessons, total_watch_time