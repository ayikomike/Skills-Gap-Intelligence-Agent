"""Builds a synthetic graduation-list PDF (fake names) to test the counting logic."""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def build(path):
    c = canvas.Canvas(path, pagesize=A4); y = 800
    def line(t):
        nonlocal y
        c.drawString(40, y, t); y -= 14
        if y < 60: c.showPage(); y = 800
    line("TEST UNIVERSITY - FINAL LIST OF GRADUANDS")
    line("Bachelor of Science in Computer Science")
    for i in range(1, 6): line(f"{i} Testname{i} Surname{i} F Ugandan")
    line("Bachelor of Laws")
    for i in range(1, 4): line(f"{i} Lawname{i} Surname{i} M Ugandan")
    line("Diploma in Business Studies")
    c.save()

if __name__ == "__main__":
    build(sys.argv[1])
