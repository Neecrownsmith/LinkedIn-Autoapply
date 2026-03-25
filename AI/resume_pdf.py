from __future__ import annotations

import html
import importlib
import re
from pathlib import Path
from typing import Any


def _to_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_to_lines(item))
        return out
    text = str(value).strip()
    return [text] if text else []


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _pick_first(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _escape_html(value: Any) -> str:
    return html.escape(_text(value), quote=True)


def _escape_html_with_soft_breaks(value: Any) -> str:
    escaped = _escape_html(value)
    # Allow long URLs/identifiers to wrap in xhtml2pdf instead of clipping.
    return (
        escaped.replace("/", "/&#8203;")
        .replace(".", ".&#8203;")
        .replace("-", "-&#8203;")
        .replace("_", "_&#8203;")
    )


def _escape_pdf_text(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _write_minimal_pdf(lines: list[str], out_path: Path) -> str:
    """Write a simple one-page PDF without external dependencies."""
    # A4 portrait in PDF points (72 dpi): 595 x 842.
    page_width = 595
    page_height = 842
    start_x = 54
    start_y = page_height - 64
    line_step = 14

    commands = ["BT", "/F1 10 Tf", f"{start_x} {start_y} Td", f"{line_step} TL"]
    for line in lines[:120]:
        commands.append(f"({_escape_pdf_text(line)}) Tj")
        commands.append("T*")
    commands.append("ET")

    stream_text = "\n".join(commands) + "\n"
    stream_bytes = stream_text.encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    media_box = f"[0 0 {page_width} {page_height}]".encode("ascii")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox "
        + media_box
        + b" /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
    )
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(
        b"5 0 obj\n<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n"
        + stream_bytes
        + b"endstream\nendobj\n"
    )

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    body = bytearray(header)
    for obj in objects:
        offsets.append(len(body))
        body.extend(obj)

    xref_start = len(body)
    xref = [f"xref\n0 {len(offsets)}\n", "0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n")
    body.extend("".join(xref).encode("ascii"))
    body.extend(
        (
            "trailer\n"
            f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).encode("ascii")
    )

    out_path.write_bytes(bytes(body))
    return str(out_path.resolve())


def _format_date_range(start: str, end: str) -> str:
    start_text = _text(start)
    end_text = _text(end)
    if start_text and end_text:
        return f"{start_text} - {end_text}"
    return start_text or end_text


def _load_personal_fallback() -> dict[str, str]:
    try:
        personal_mod = importlib.import_module("configuration.personal")
    except Exception:
        return {}

    keys = [
        "email_address",
        "phone_number",
        "linkedin_profile_url",
        "portfolio_website",
        "current_city",
        "state",
        "country",
        "languages",
    ]

    out: dict[str, str] = {}
    for key in keys:
        value = getattr(personal_mod, key, "")
        text = _text(value)
        if text:
            out[key] = text
    return out


def _build_contact_items(resume_data: dict[str, Any]) -> list[str]:
    fallback = _load_personal_fallback()
    contact_data = resume_data.get("contact")
    contact_dict = contact_data if isinstance(contact_data, dict) else {}

    email = _pick_first(
        contact_dict.get("email"),
        resume_data.get("email"),
        fallback.get("email_address"),
    )
    phone = _pick_first(
        contact_dict.get("phone"),
        resume_data.get("phone"),
        fallback.get("phone_number"),
    )
    linkedin = _pick_first(
        contact_dict.get("linkedin"),
        resume_data.get("linkedin"),
        fallback.get("linkedin_profile_url"),
    )
    website = _pick_first(
        contact_dict.get("website"),
        resume_data.get("website"),
        fallback.get("portfolio_website"),
    )
    location = _pick_first(
        contact_dict.get("location"),
        resume_data.get("location"),
        " ".join(
            part
            for part in [
                fallback.get("current_city", ""),
                fallback.get("state", ""),
                fallback.get("country", ""),
            ]
            if part
        ),
    )

    items: list[str] = []
    for value in [email, phone, linkedin, website, location]:
        if value:
            items.append(value)
    return items


def _normalize_experience(experience_items: Any) -> list[dict[str, Any]]:
    if not isinstance(experience_items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in experience_items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": _text(item.get("title")),
                "company": _text(item.get("company")),
                "location": _pick_first(item.get("location"), item.get("city"), item.get("place")),
                "start": _text(item.get("start")),
                "end": _text(item.get("end")),
                "bullets": _to_lines(item.get("bullets"))[:8],
            }
        )
    return normalized


def _normalize_education(education_items: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []

    if not isinstance(education_items, list):
        return normalized

    for item in education_items:
        if isinstance(item, dict):
            normalized.append(
                {
                    "school": _text(item.get("school")),
                    "degree": _text(item.get("degree")),
                    "location": _pick_first(item.get("location"), item.get("city"), item.get("place")),
                    "start": _text(item.get("start")),
                    "end": _text(item.get("end")),
                }
            )
            continue

        text_line = _text(item)
        if text_line:
            normalized.append({"school": "", "degree": text_line, "location": "", "start": "", "end": ""})

    return normalized


def _normalize_projects(project_items: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    if not isinstance(project_items, list):
        return normalized

    for item in project_items:
        if isinstance(item, dict):
            normalized.append(
                {
                    "name": _text(item.get("name")),
                    "description_bullets": _to_lines(item.get("description_bullets"))[:6],
                }
            )
            continue

        text_line = _text(item)
        if text_line:
            normalized.append({"name": "", "description_bullets": [text_line]})

    return normalized


def _build_additional_lines(resume_data: dict[str, Any], skills: list[str]) -> list[tuple[str, str]]:
    fallback = _load_personal_fallback()

    def joined(values: Any, limit: int = 20, sep: str = ", ") -> str:
        rows = _to_lines(values)[:limit]
        return sep.join(row for row in rows if row)

    technical_skills = joined(skills[:14], limit=14, sep="; ")
    languages = _pick_first(
        joined(resume_data.get("languages")),
        joined(resume_data.get("language")),
        fallback.get("languages", ""),
    )

    cert_values: list[str] = []
    cert_values.extend(_to_lines(resume_data.get("certifications_and_training")))
    cert_values.extend(_to_lines(resume_data.get("certifications")))
    cert_values.extend(_to_lines(resume_data.get("training")))
    certifications = ", ".join(line for line in cert_values if line)

    awards = joined(resume_data.get("awards"), limit=8)

    lines: list[tuple[str, str]] = []
    if technical_skills:
        lines.append(("Technical Skills", technical_skills))
    if languages:
        lines.append(("Languages", languages))
    if certifications:
        lines.append(("Certifications & Training", certifications))
    if awards:
        lines.append(("Awards", awards))
    return lines


def _tokenize_for_match(text: Any) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", _text(text).lower())
    stop_words = {
        "and",
        "with",
        "for",
        "the",
        "from",
        "into",
        "that",
        "this",
        "your",
        "you",
        "our",
        "using",
        "used",
        "have",
        "has",
        "are",
        "job",
        "role",
        "work",
        "team",
    }
    return {w for w in words if w not in stop_words}


def _score_experience_item(item: dict[str, Any], target_tokens: set[str]) -> int:
    if not target_tokens:
        return 0

    primary_text = " ".join(
        [
            _text(item.get("title")),
            _text(item.get("company")),
            _text(item.get("location")),
        ]
    )
    bullet_text = " ".join(_to_lines(item.get("bullets")))

    primary_tokens = _tokenize_for_match(primary_text)
    bullet_tokens = _tokenize_for_match(bullet_text)

    primary_hits = len(primary_tokens & target_tokens)
    bullet_hits = len(bullet_tokens & target_tokens)

    # Weight title/company matches higher than body bullets.
    return (primary_hits * 4) + bullet_hits


def _pick_relevant_bullets(bullets: list[str], target_tokens: set[str], max_bullets: int = 5) -> list[str]:
    if not bullets:
        return []
    if not target_tokens:
        return bullets[:max_bullets]

    scored: list[tuple[int, int, str]] = []
    for idx, bullet in enumerate(bullets):
        score = len(_tokenize_for_match(bullet) & target_tokens)
        scored.append((score, idx, bullet))

    scored.sort(key=lambda row: (-row[0], row[1]))
    chosen = scored[:max_bullets]
    chosen.sort(key=lambda row: row[1])
    return [row[2] for row in chosen]


def _select_relevant_experience(resume_data: dict[str, Any], experience_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not experience_items:
        return []

    job_context = " ".join(
        [
            _text(resume_data.get("job_description")),
            _text(resume_data.get("headline")),
            _text(resume_data.get("summary")),
            " ".join(_to_lines(resume_data.get("skills"))),
        ]
    )
    target_tokens = _tokenize_for_match(job_context)

    scored_items: list[tuple[int, int, dict[str, Any]]] = []
    for idx, item in enumerate(experience_items):
        score = _score_experience_item(item, target_tokens)
        normalized = dict(item)
        normalized["bullets"] = _pick_relevant_bullets(_to_lines(item.get("bullets")), target_tokens, max_bullets=5)
        scored_items.append((score, idx, normalized))

    relevant = [row for row in scored_items if row[0] > 0]
    if relevant:
        relevant.sort(key=lambda row: (-row[0], row[1]))
        selected = relevant[:4]
    else:
        selected = scored_items[:4]

    # Keep chronology/source order for readability after selecting top matches.
    selected.sort(key=lambda row: row[1])
    return [row[2] for row in selected]


def _render_resume_html(resume_data: dict[str, Any]) -> str:
    full_name = _pick_first(resume_data.get("full_name"), "Candidate Name")
    headline = _text(resume_data.get("headline"))
    summary = _text(resume_data.get("summary"))
    skills = _to_lines(resume_data.get("skills"))[:30]
    education_items_data = _normalize_education(resume_data.get("education"))[:10]
    project_items_data = _normalize_projects(resume_data.get("projects"))[:10]
    contacts = _build_contact_items(resume_data)
    additional_lines = _build_additional_lines(resume_data, skills)
    experience_items = _select_relevant_experience(
        resume_data,
        _normalize_experience(resume_data.get("experience"))[:10],
    )

    def section(title: str, body_html: str) -> str:
        if not body_html.strip():
            return ""
        return (
            "<div class=\"section\">"
            f"<div class=\"section-title\">{_escape_html(title)}</div>"
            f"{body_html}"
            "</div>"
        )

    summary_html = (
        section("Professional Summary", f"<p class=\"summary\">{_escape_html(summary)}</p>")
        if summary
        else ""
    )

    experience_blocks: list[str] = []
    for item in experience_items:
        role = _text(item.get("title"))
        company = _text(item.get("company"))
        date_range = _format_date_range(_text(item.get("start")), _text(item.get("end")))
        location = _pick_first(item.get("location"), "")

        company_or_default = company or "Experience"
        role_or_default = role or "Role"

        bullets = item.get("bullets") if isinstance(item.get("bullets"), list) else []
        bullet_items = "".join(f"<li>- {_escape_html_with_soft_breaks(line)}</li>" for line in bullets)
        bullets_html = f"<ul class=\"bullet-list\">{bullet_items}</ul>" if bullet_items else ""

        experience_blocks.append(
            "<div class=\"exp-item\">"
            "<table class=\"exp-head exp-company-row\" cellpadding=\"0\" cellspacing=\"0\"><tr>"
            f"<td class=\"exp-company\">{_escape_html(company_or_default).upper()}</td>"
            f"<td class=\"exp-right\">{_escape_html(location)}</td>"
            "</tr></table>"
            "<table class=\"exp-head exp-role-row\" cellpadding=\"0\" cellspacing=\"0\"><tr>"
            f"<td class=\"exp-role\">{_escape_html(role_or_default)}</td>"
            f"<td class=\"exp-right\">{_escape_html(date_range)}</td>"
            "</tr></table>"
            f"{bullets_html}"
            "</div>"
        )

    experience_html = section("Professional Experience", "".join(experience_blocks))

    project_blocks: list[str] = []
    for project in project_items_data:
        project_name = _text(project.get("name"))
        desc_bullets = _to_lines(project.get("description_bullets"))
        bullet_items = "".join(
            f"<li>- {_escape_html_with_soft_breaks(line)}</li>" for line in desc_bullets
        )
        bullet_list = f"<ul class=\"bullet-list\">{bullet_items}</ul>" if bullet_items else ""
        name_html = f"<div class=\"project-name\">{_escape_html(project_name)}</div>" if project_name else ""
        project_blocks.append(
            "<div class=\"project-item\">"
            f"{name_html}"
            f"{bullet_list}"
            "</div>"
        )

    projects_html = section(
        "Selected Project Experience",
        "".join(project_blocks),
    )

    education_rows: list[str] = []
    for edu in education_items_data:
        degree = _text(edu.get("degree"))
        school = _text(edu.get("school"))
        location = _text(edu.get("location"))
        date_range = _format_date_range(_text(edu.get("start")), _text(edu.get("end")))

        if not any([degree, school, location, date_range]):
            continue

        school_line = school.upper() if school else ""
        education_rows.append(
            "<div class=\"edu-item\">"
            "<table class=\"edu-head\" cellpadding=\"0\" cellspacing=\"0\"><tr>"
            f"<td class=\"edu-school\">{_escape_html(school_line)}</td>"
            f"<td class=\"edu-location\">{_escape_html(location)}</td>"
            "</tr></table>"
            "<table class=\"edu-head\" cellpadding=\"0\" cellspacing=\"0\"><tr>"
            f"<td class=\"edu-degree\">{_escape_html(degree)}</td>"
            f"<td class=\"edu-date\">{_escape_html(date_range)}</td>"
            "</tr></table>"
            "</div>"
        )

    education_html = section(
        "Education",
        "".join(education_rows),
    )

    contact_items = "".join(f"<li>{_escape_html_with_soft_breaks(line)}</li>" for line in contacts)
    contact_html = section(
        "Contact",
        f"<ul class=\"contact-list\">{contact_items}</ul>" if contact_items else "",
    )

    additional_info_parts = [
        (
            f"<p class=\"additional-line\">"
            f"<span class=\"additional-label\">{_escape_html(label)}:</span> "
            f"{_escape_html(value)}"
            "</p>"
        )
        for label, value in additional_lines
    ]
    additional_info_html = section(
        "Additional",
        "".join(additional_info_parts),
    )

    header_contacts = " | ".join(_escape_html_with_soft_breaks(item) for item in contacts[:4])

    main_sections = [summary_html, experience_html, projects_html, education_html, additional_info_html]
    main_html = "".join(part for part in main_sections if part)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{_escape_html(full_name)} - Resume</title>
  <style>
        @page {{
            size: A4 portrait;
            margin: 14mm 14mm 12mm 14mm;
        }}
        body {{
            margin: 0;
            color: #111111;
            font-family: Times New Roman, Georgia, serif;
            font-size: 11pt;
            line-height: 1.32;
            background: #ffffff;
            word-wrap: break-word;
        }}
        .page {{
            width: 100%;
        }}
        h1 {{
            margin: 0;
            font-size: 15pt;
            font-weight: bold;
            text-align: left;
            line-height: 1.1;
        }}
        .headline {{
            margin-top: 2px;
            text-align: left;
            font-size: 10.9pt;
            font-weight: bold;
            line-height: 1.2;
        }}
        .header-contact {{
            margin-top: 2px;
            text-align: left;
            font-size: 9.8pt;
            line-height: 1.2;
            word-wrap: break-word;
        }}
        .section {{
            margin-top: 14px;
        }}
        .section-title {{
            font-size: 16pt;
            font-weight: bold;
            text-transform: uppercase;
            border-bottom: 2px solid #404040;
            padding-bottom: 2px;
            margin-bottom: 6px;
            line-height: 1.1;
        }}
        .summary {{
            margin: 0;
            text-align: left;
            word-wrap: break-word;
        }}
        .exp-item {{
            margin-bottom: 10px;
        }}
        .exp-head {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            margin: 0;
        }}
        .exp-company {{
            font-size: 13.2pt;
            font-weight: bold;
            width: 62%;
            vertical-align: top;
            padding: 0;
            word-wrap: break-word;
        }}
        .exp-role {{
            font-weight: bold;
            font-size: 11.5pt;
            width: 62%;
            vertical-align: top;
            padding: 0;
            word-wrap: break-word;
        }}
        .exp-right {{
            font-size: 11pt;
            font-weight: bold;
            text-align: right;
            width: 38%;
            vertical-align: top;
            padding: 0;
            word-wrap: break-word;
        }}
        .bullet-list {{
            margin: 2px 0 0 0;
            padding: 0;
            list-style: none;
        }}
        .bullet-list li {{
            margin: 0 0 1px 0;
            padding: 0;
            font-size: 10.8pt;
            line-height: 1.25;
            word-wrap: break-word;
        }}
        .project-item {{
            margin-bottom: 8px;
        }}
        .project-name {{
            font-weight: bold;
            font-size: 11.3pt;
            margin-bottom: 2px;
        }}
        .additional-line {{
            margin: 0 0 2px 0;
            font-size: 10.8pt;
            line-height: 1.2;
            word-wrap: break-word;
        }}
        .additional-label {{
            font-weight: bold;
        }}
        .edu-item {{
            margin-bottom: 6px;
        }}
        .edu-head {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}
        .edu-school {{
            width: 72%;
            vertical-align: top;
            font-weight: bold;
            font-size: 12pt;
            word-wrap: break-word;
        }}
        .edu-location {{
            width: 28%;
            text-align: right;
            vertical-align: top;
            font-size: 10.8pt;
            font-weight: bold;
            word-wrap: break-word;
        }}
        .edu-degree {{
            width: 72%;
            vertical-align: top;
            font-style: italic;
            font-weight: bold;
            font-size: 10.8pt;
            word-wrap: break-word;
        }}
        .edu-date {{
            width: 28%;
            text-align: right;
            vertical-align: top;
            font-size: 10.8pt;
            font-weight: bold;
            word-wrap: break-word;
        }}
        .contact-list {{
            margin: 0;
            padding: 0;
            list-style: none;
        }}
        .contact-list li {{
            margin-bottom: 2px;
            word-wrap: break-word;
        }}
        td {{
            -pdf-keep-in-frame-mode: shrink;
        }}
  </style>
</head>
<body>
  <div class="page">
    <h1>{_escape_html(full_name)}</h1>
    {f'<div class="headline">{_escape_html(headline)}</div>' if headline else ''}
    {f'<div class="header-contact">{header_contacts}</div>' if header_contacts else ''}

        {main_html}
  </div>
</body>
</html>
"""


def _build_fallback_lines(resume_data: dict[str, Any]) -> list[str]:
    full_name = _pick_first(resume_data.get("full_name"), "Candidate Name")
    headline = _text(resume_data.get("headline"))
    summary = _text(resume_data.get("summary"))
    skills = _to_lines(resume_data.get("skills"))[:30]
    education_items_data = _normalize_education(resume_data.get("education"))[:10]
    project_items_data = _normalize_projects(resume_data.get("projects"))[:10]
    additional_lines = _build_additional_lines(resume_data, skills)
    contacts = _build_contact_items(resume_data)
    experience_items = _select_relevant_experience(
        resume_data,
        _normalize_experience(resume_data.get("experience"))[:10],
    )

    lines: list[str] = [full_name]
    if headline:
        lines.append(headline)
    if contacts:
        lines.append(" | ".join(contacts[:4]))

    if summary:
        lines.extend(["", "SUMMARY", summary])
    if skills:
        lines.extend(["", "SKILLS", ", ".join(skills)])

    if experience_items:
        lines.extend(["", "EXPERIENCE"])
        for item in experience_items:
            heading = " | ".join(
                part for part in [_text(item.get("title")), _text(item.get("company"))] if part
            )
            if heading:
                lines.append(heading)
            date_line = _format_date_range(_text(item.get("start")), _text(item.get("end")))
            if date_line:
                lines.append(date_line)
            for bullet in _to_lines(item.get("bullets"))[:8]:
                lines.append(f"- {bullet}")

    if project_items_data:
        lines.extend(["", "PROJECTS"])
        for project in project_items_data:
            name = _text(project.get("name"))
            if name:
                lines.append(name)
            for bullet in _to_lines(project.get("description_bullets"))[:6]:
                lines.append(f"- {bullet}")

    if education_items_data:
        lines.extend(["", "EDUCATION"])
        for edu in education_items_data:
            school = _text(edu.get("school"))
            degree = _text(edu.get("degree"))
            location = _text(edu.get("location"))
            if school:
                lines.append(" | ".join(part for part in [school, location] if part))
            if degree:
                lines.append(degree)
            date_line = _format_date_range(_text(edu.get("start")), _text(edu.get("end")))
            if date_line:
                lines.append(date_line)

    if additional_lines:
        lines.extend(["", "ADDITIONAL"])
        for label, value in additional_lines:
            lines.append(f"{label}: {value}")

    return lines


def _try_render_html_to_pdf(html_content: str, out_path: Path) -> bool:
    try:
        pisa_mod = importlib.import_module("xhtml2pdf.pisa")
        create_pdf = getattr(pisa_mod, "CreatePDF")
        with out_path.open("wb") as pdf_file:
            result = create_pdf(src=html_content, dest=pdf_file, encoding="utf-8")
        # xhtml2pdf may report non-zero `err` for unsupported CSS while still
        # producing a valid styled PDF. Prefer the generated file when present.
        if out_path.exists() and out_path.stat().st_size > 0:
            return True
        return getattr(result, "err", 1) == 0
    except Exception:
        return False



def render_resume_pdf(resume_data: dict[str, Any], output_path: str) -> str:
    """Render structured resume JSON into a professional PDF using HTML/CSS.

    Returns the absolute path to the created PDF.
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = _render_resume_html(resume_data or {})

    # Save an editable HTML copy next to the PDF for quick manual review/customization.
    html_path = out_path.with_suffix(".html")
    try:
        html_path.write_text(html_content, encoding="utf-8")
    except Exception:
        pass

    if _try_render_html_to_pdf(html_content, out_path):
        return str(out_path.resolve())

    # Safety fallback: keep automation functional if the HTML-to-PDF engine is unavailable.
    fallback_lines = _build_fallback_lines(resume_data or {})
    return _write_minimal_pdf(fallback_lines, out_path)
