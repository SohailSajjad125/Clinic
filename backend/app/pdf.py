from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ST = getSampleStyleSheet()


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F6F4")), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4C8")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def _build(story) -> bytes:
    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm).build(story)
    return buf.getvalue()


def prescription_pdf(clinic: str, patient: str, doctor: str | None, c) -> bytes:
    p = lambda t, s="BodyText": Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), ST[s])
    story = [p(clinic, "Title"), p(f"Prescription · {c.created_at:%d %b %Y}"), Spacer(1, 8), p(f"Patient: {patient}"), p(f"Doctor: {doctor or '-'}")]
    if c.assessment:
        story.append(p(f"Assessment: {c.assessment}"))
    story.append(Spacer(1, 10))
    rows = [["Medicine", "Dose", "Frequency", "Duration", "Instructions"]] + [[p(r.get("medicine", "")), r.get("dose", ""), r.get("frequency", ""), r.get("duration", ""), p(r.get("instructions", ""))] for r in (c.prescription or [])]
    story.append(_table(rows, [48 * mm, 22 * mm, 28 * mm, 25 * mm, 51 * mm]))
    if c.follow_up_on:
        story += [Spacer(1, 10), p(f"Follow-up: {c.follow_up_on:%d %b %Y}")]
    return _build(story)


def receipt_pdf(clinic: str, inv, status: str) -> bytes:
    p = lambda t, s="BodyText": Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), ST[s])
    rows = [["Description", "Qty", "Price", "Amount"]] + [[p(i["description"]), i["qty"], i["price"], i["qty"] * i["price"]] for i in inv.items]
    rows += [["", "", "Discount", -inv.discount], ["", "", "Tax", inv.tax], ["", "", "Total", inv.total], ["", "", "Paid", inv.paid], ["", "", "Balance", inv.total - inv.paid]]
    story = [p(clinic, "Title"), p(f"Invoice #{inv.number} · {inv.created_at:%d %b %Y} · {status.upper()}"), p(f"Patient: {inv.patient.full_name}"), Spacer(1, 10), _table(rows, [80 * mm, 20 * mm, 35 * mm, 35 * mm]),
             Spacer(1, 8), p("Amounts in PKR.")]
    return _build(story)
