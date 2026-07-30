import textwrap
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from core.language import normalize, text
from models.db_models import Analysis
from services.export.serializers import aspect_label, status_label

SEVERITY_COLORS = {
    "critical": (0.91, 0.30, 0.24),
    "high": (0.91, 0.30, 0.24),
    "medium": (0.91, 0.64, 0.24),
    "low": (0.56, 0.56, 0.56),
}

GREY = (0.4, 0.4, 0.4)
BLACK = (0, 0, 0)
MARGIN = 20 * mm


class _Report:
    def __init__(self, footer: str):
        self.footer = footer
        self.buffer = BytesIO()
        self.canvas = canvas.Canvas(self.buffer, pagesize=A4)
        self.width, self.height = A4
        self.y = self.height - MARGIN

    def ensure_space(self, needed: float = 30) -> None:
        if self.y < MARGIN + needed:
            self._draw_footer()
            self.canvas.showPage()
            self.y = self.height - MARGIN

    def text(
        self,
        content: str,
        font: str = "Helvetica",
        size: int = 10,
        indent: float = 0,
        color: tuple = BLACK,
        leading: float = 5 * mm,
        wrap_at: int | None = None,
    ) -> None:
        lines = textwrap.wrap(content, wrap_at) if wrap_at else [content]

        self.canvas.setFont(font, size)
        self.canvas.setFillColorRGB(*color)
        for line in lines or [""]:
            self.ensure_space()
            self.canvas.drawString(MARGIN + indent, self.y, line)
            self.y -= leading
        self.canvas.setFillColorRGB(*BLACK)

    def space(self, amount: float) -> None:
        self.y -= amount

    def _draw_footer(self) -> None:
        self.canvas.setFont("Helvetica", 8)
        self.canvas.setFillColorRGB(0.5, 0.5, 0.5)
        self.canvas.drawString(MARGIN, 10 * mm, self.footer)
        self.canvas.setFillColorRGB(*BLACK)

    def build(self) -> bytes:
        self._draw_footer()
        self.canvas.save()
        return self.buffer.getvalue()


def generate_pdf(analysis: Analysis) -> bytes:
    language = normalize(getattr(analysis, "language", None))
    report = _Report(text("pdf.footer", language))

    report.text(text("pdf.title", language), font="Helvetica-Bold", size=18, leading=10 * mm)
    report.text(
        text("pdf.repository", language, value=analysis.repo_name), size=11, leading=6 * mm,
    )
    report.text(
        text("pdf.date", language, value=analysis.created_at.strftime('%d/%m/%Y %H:%M')),
        size=11,
        leading=6 * mm,
    )
    if analysis.repo_sha:
        report.text(
            text("pdf.sha", language, value=analysis.repo_sha[:12]), size=11, leading=6 * mm,
        )
    report.space(8 * mm)

    for result in analysis.results:
        report.ensure_space(40)

        report.text(
            aspect_label(result.aspect, language),
            font="Helvetica-Bold",
            size=13,
            leading=6 * mm,
        )
        report.text(
            text("pdf.status", language, value=status_label(result.status, language)),
            indent=5 * mm,
            leading=6 * mm,
        )

        for issue in result.issues or []:
            _draw_issue(report, issue, language)

        recommendations = result.recommendations or []
        if recommendations:
            report.ensure_space(15)
            report.text(
                text("pdf.recommendations", language),
                font="Helvetica-Bold",
                leading=5 * mm,
                indent=5 * mm,
            )
            for rec in recommendations:
                message = rec.get("message", rec.get("description", str(rec)))
                report.text(
                    f"- {message}",
                    size=9,
                    indent=10 * mm,
                    leading=4.5 * mm,
                    wrap_at=95,
                )

        report.space(8 * mm)

    return report.build()


def _draw_issue(report: _Report, issue: dict, language: str) -> None:
    report.ensure_space(25)

    title = issue.get("title", issue.get("message", issue.get("description", str(issue))))
    severity = issue.get("severity", "low")

    report.text(
        f"[{severity.upper()}] {title}",
        font="Helvetica-Bold",
        indent=5 * mm,
        color=SEVERITY_COLORS.get(severity, (0.5, 0.5, 0.5)),
        leading=5 * mm,
        wrap_at=88,
    )

    if issue.get("file_path"):
        report.text(
            text("pdf.file", language, value=issue['file_path']),
            size=9,
            indent=10 * mm,
            color=GREY,
            leading=4.5 * mm,
            wrap_at=100,
        )

    code_hint = issue.get("code_hint")
    if code_hint:
        hint = code_hint[:100] + ("..." if len(code_hint) > 100 else "")
        report.text(hint, font="Courier", size=8, indent=10 * mm, color=(0.3, 0.3, 0.3), leading=4.5 * mm)

    report.space(2 * mm)
