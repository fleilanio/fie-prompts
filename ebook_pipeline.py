#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


PT_SMALL = {"a", "as", "o", "os", "um", "uma", "uns", "umas", "de", "da", "das", "do", "dos", "e", "em", "no", "na", "nos", "nas", "por", "para", "com", "sem", "sob", "sobre"}
EN_SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "nor", "of", "on", "or", "the", "to", "with"}
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV", 16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX", 21: "XXI", 22: "XXII", 23: "XXIII", 24: "XXIV", 25: "XXV", 26: "XXVI", 27: "XXVII", 28: "XXVIII", 29: "XXIX", 30: "XXX", 40: "XL", 50: "L", 100: "C"}


def parse_args():
    parser = argparse.ArgumentParser(description="TXT -> structured Markdown -> DOCX using Pandoc and optional reference.docx")
    parser.add_argument("input", help="input .txt")
    parser.add_argument("output", nargs="?", help="output .docx")
    parser.add_argument("--reference", help="reference.docx template")
    parser.add_argument("--md", help="markdown intermediary path")
    parser.add_argument("--lang", default="auto", choices=["auto", "pt-br", "en"])
    parser.add_argument("--title")
    parser.add_argument("--author")
    parser.add_argument("--drop-before-first-chapter", action="store_true")
    parser.add_argument("--drop-empty-notes", action="store_true")
    parser.add_argument("--keep-separators", action="store_true")
    parser.add_argument("--reference-styles", default="auto", choices=["auto", "off"])
    parser.add_argument("--no-typography", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    return parser.parse_args()


def detect_lang(lines):
    sample = " ".join(line.strip() for line in lines if len(line.strip()) > 40)[:12000].lower()
    pt_hits = sum(word in sample for word in [" você ", " capítulo ", " então ", " minha ", " não ", " que ", " uma "])
    en_hits = sum(word in sample for word in [" the ", " chapter ", " and ", " that ", " not ", " with ", " from "])
    return "pt-br" if pt_hits >= en_hits else "en"


def title_case(text, lang):
    small = EN_SMALL if lang == "en" else PT_SMALL
    words_seen = 0
    parts = []
    for part in re.split(r"(\s+)", text):
        if not part or part.isspace():
            parts.append(part)
            continue
        lower = part.lower()
        if words_seen > 0 and lower in small:
            parts.append(lower)
        else:
            parts.append(re.sub(r"^([a-záàâãéêíóôõúç])", lambda m: m.group(1).upper(), lower))
        words_seen += 1
    return "".join(parts)


def to_roman(value):
    try:
        return ROMAN.get(int(value), value.upper())
    except ValueError:
        return value.upper()


def structural_match(line, lang):
    trimmed = line.strip()
    md = re.match(r"^#{1,6}\s+(.+)$", trimmed)
    source = md.group(1).strip() if md else trimmed
    if lang == "en":
        patterns = [
            ("volume", r"^(volume)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("book", r"^(book)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("part", r"^(part)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("chapter", r"^(chapter)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("section", r"^(section)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("article", r"^(article)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
        ]
        special = r"^(introduction|preface|prologue|epilogue|foreword|afterword|appendix|bibliography|acknowledgments)$"
    else:
        patterns = [
            ("tomo", r"^(tomo)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("livro", r"^(livro)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("parte", r"^(parte)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("capitulo", r"^(cap[íi]tulo)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("secao", r"^(se[çc][ãa]o)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
            ("artigo", r"^(artigo)\s+([0-9ivxlcdm]+)\s*(?:[—-]\s*(.+))?$"),
        ]
        special = r"^(introdução|prefácio|prólogo|epílogo|posfácio|conclusão|apêndice|bibliografia|agradecimentos)$"

    for kind, pattern in patterns:
        match = re.match(pattern, source, re.I)
        if match:
            return {"type": kind, "label": match.group(1), "number": match.group(2), "title": match.group(3) or ""}
    if re.match(special, source, re.I):
        return {"type": "special", "label": source, "number": "", "title": ""}
    return None


def hierarchy_for(lines, lang):
    order = ["volume", "book", "part", "chapter", "section", "article", "special"] if lang == "en" else ["tomo", "livro", "parte", "capitulo", "secao", "artigo", "special"]
    present = {match["type"] for line in lines if (match := structural_match(line, lang))}
    active = [kind for kind in order if kind in present]
    return {kind: min(index + 1, 6) for index, kind in enumerate(active)}


def make_heading(line, lang, hierarchy):
    match = structural_match(line, lang)
    if not match:
        return None
    level = hierarchy.get(match["type"], 1)
    labels = {
        "volume": "VOLUME", "book": "BOOK", "part": "PART", "chapter": "CHAPTER", "section": "SECTION", "article": "ARTICLE",
        "tomo": "TOMO", "livro": "LIVRO", "parte": "PARTE", "capitulo": "CAPÍTULO", "secao": "SEÇÃO", "artigo": "ARTIGO",
    }
    if match["type"] == "special":
        return f"{'#' * level} {match['label'].upper()}"
    suffix = f" — {title_case(match['title'], lang)}" if match["title"] else ""
    return f"{'#' * level} {labels[match['type']]} {to_roman(match['number'])}{suffix}"


def smart_quotes(text):
    open_quote = True
    out = []
    for char in text:
        if char == '"':
            out.append("“" if open_quote else "”")
            open_quote = not open_quote
        else:
            out.append(char)
    return "".join(out)


def typography(text, lang):
    out = smart_quotes(text)
    out = re.sub(r"\.\.\.+", "…", out)
    out = re.sub(r"\.\.", "…", out)
    out = re.sub(r"\betc\.\.", "etc.", out, flags=re.I)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    out = re.sub(r"(\d)\s*-\s*(\d)", r"\1–\2", out)
    out = re.sub(r"(\d)(km|cm|mm|m|kg|g|l)\b", r"\1 \2", out, flags=re.I)
    if lang == "pt-br":
        out = re.sub(r"^(\s*)-\s+", r"\1— ", out)
        out = re.sub(r"\s-\s", " — ", out)
    else:
        out = re.sub(r"\s+—\s+", "—", out)
    return out


def detect_reference_styles(reference):
    styles = {"title": None, "subtitle": None, "scene": None, "quote": None, "intense_quote": None, "footnote_text": None}
    if not reference:
        return styles
    try:
        with zipfile.ZipFile(reference) as docx:
            xml = docx.read("word/styles.xml").decode("utf-8", errors="ignore")
    except Exception:
        return styles
    mapping = {"title": "Ttulo", "subtitle": "Subttulo", "scene": "LegCena", "quote": "Citao", "intense_quote": "CitaoIntensa", "footnote_text": "Textodenotaderodap"}
    for key, style_id in mapping.items():
        if f'w:styleId="{style_id}"' in xml:
            styles[key] = style_id
    return styles


def custom_style(style, text):
    escaped = text.replace("*", r"\*")
    return [f'::: {{custom-style="{style}"}}', escaped, ':::']


def analyze(lines, lang, hierarchy):
    refs, defs = set(), set()
    headings = notes_sections = separators = 0
    for line in lines:
        if make_heading(line, lang, hierarchy):
            headings += 1
        if re.match(r"^#{0,3}\s*(notas?|notes?|notas de rodap[eé]|footnotes?)\s*$", line.strip(), re.I):
            notes_sections += 1
        if re.match(r"^(---|\* \* \*|\*\*\*)$", line.strip()):
            separators += 1
        refs.update(re.findall(r"\[\^(\d+)\](?!:)", line))
        match = re.match(r"^\[\^(\d+)\]:", line)
        if match:
            defs.add(match.group(1))
    return {"headings": headings, "notes_sections": notes_sections, "separators": separators, "refs": refs, "defs": defs}


def normalize(lines, args, lang, hierarchy, styles):
    out = []
    title_done = author_done = started = False
    if args.title:
        out.extend(custom_style(styles["title"], args.title) if styles.get("title") else [f"# {args.title}"])
        out.append("")
        title_done = True
    if args.author:
        out.extend(custom_style(styles["subtitle"], args.author) if styles.get("subtitle") else [f"## {args.author}"])
        out.append("")
        author_done = True

    for index, raw in enumerate(lines):
        trimmed = raw.strip()
        heading = make_heading(raw, lang, hierarchy)
        if args.title and index < 10 and re.match(r"^#\s+", trimmed):
            continue
        if args.author and index < 10 and re.match(r"^##\s+", trimmed):
            continue
        if args.drop_before_first_chapter and not started and not heading:
            continue
        if heading:
            started = True
        if args.drop_empty_notes and re.match(r"^#{0,3}\s*(notas? de rodap[eé]|footnotes?|notes?)\s*$", trimmed, re.I):
            lookahead = lines[index + 1:index + 3]
            if any(re.match(r"^\*?\(?((não há notas)|(no notes))", item.strip(), re.I) for item in lookahead):
                continue
            continue
        if re.match(r"^(---|\* \* \*|\*\*\*)$", trimmed):
            if args.keep_separators:
                out.extend(custom_style(styles["scene"], "* * *") if styles.get("scene") else ["* * *"])
            continue
        if heading:
            out.append(heading)
            continue
        if re.match(r"^#\s+", trimmed) and not title_done:
            title = re.sub(r"^#\s+", "", trimmed)
            out.extend(custom_style(styles["title"], title) if styles.get("title") else [f"# {title}"])
            title_done = True
            continue
        if re.match(r"^##\s+", trimmed) and title_done and not author_done:
            author = re.sub(r"^##\s+", "", trimmed)
            out.extend(custom_style(styles["subtitle"], author) if styles.get("subtitle") else [f"## {author}"])
            author_done = True
            continue
        if not trimmed:
            if out and out[-1] != "":
                out.append("")
            continue
        out.append(typography(raw, lang) if not args.no_typography else raw)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def validate_docx(docx_path):
    with zipfile.ZipFile(docx_path) as docx:
        bad = docx.testzip()
        if bad:
            raise RuntimeError(f"Invalid DOCX zip member: {bad}")
        required = {"[Content_Types].xml", "word/document.xml", "word/styles.xml"}
        missing = required - set(docx.namelist())
        if missing:
            raise RuntimeError(f"Missing DOCX parts: {', '.join(sorted(missing))}")


def patch_missing_paragraph_styles(docx_path, styles):
    with tempfile.TemporaryDirectory(prefix="ebook-docx-") as tmp:
        with zipfile.ZipFile(docx_path) as docx:
            docx.extractall(tmp)
        styles_path = Path(tmp) / "word" / "styles.xml"
        style_xml = styles_path.read_text(encoding="utf-8")
        style_ids = set(re.findall(r'w:styleId="([^"]+)"', style_xml))
        for xml_path in [Path(tmp) / "word" / "document.xml", Path(tmp) / "word" / "footnotes.xml"]:
            if not xml_path.exists():
                continue
            xml = xml_path.read_text(encoding="utf-8")
            def repl(match):
                style_id = match.group(1)
                if style_id in style_ids:
                    return match.group(0)
                if style_id == "FootnoteText" and styles.get("footnote_text"):
                    return f'<w:pStyle w:val="{styles["footnote_text"]}" />'
                return '<w:pStyle w:val="Normal" />'
            xml_path.write_text(re.sub(r'<w:pStyle\s+w:val="([^"]+)"\s*/>', repl, xml), encoding="utf-8")
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as out:
            content = Path(tmp) / "[Content_Types].xml"
            if content.exists():
                out.write(content, "[Content_Types].xml")
            for root, _, files in os.walk(tmp):
                for name in files:
                    full = Path(root) / name
                    rel = full.relative_to(tmp).as_posix()
                    if rel == "[Content_Types].xml":
                        continue
                    out.write(full, rel)


def main():
    args = parse_args()
    input_path = Path(args.input).resolve()
    if not args.output and not args.analyze_only:
        raise SystemExit("output .docx required unless --analyze-only")
    output_path = Path(args.output).resolve() if args.output else None
    md_path = Path(args.md).resolve() if args.md else (output_path.with_suffix(".md") if output_path else input_path.with_suffix(".md"))
    lines = input_path.read_text(encoding="utf-8").splitlines()
    lang = detect_lang(lines) if args.lang == "auto" else args.lang
    hierarchy = hierarchy_for(lines, lang)
    styles = {} if args.reference_styles == "off" else detect_reference_styles(args.reference)
    stats = analyze(lines, lang, hierarchy)

    print(f"Language: {lang}")
    print(f"Hierarchy: {', '.join(f'{k}=H{v}' for k, v in hierarchy.items()) or 'none'}")
    print(f"Headings: {stats['headings']}")
    print(f"Notes sections: {stats['notes_sections']}")
    print(f"Footnote refs: {len(stats['refs'])}")
    print(f"Footnote defs: {len(stats['defs'])}")
    print(f"Separators: {stats['separators']}")
    if args.reference and args.reference_styles != "off":
        found = ", ".join(f"{k}={v}" for k, v in styles.items() if v)
        print(f"Reference styles: {found or 'none'}")
    missing_defs = sorted(stats["refs"] - stats["defs"])
    missing_refs = sorted(stats["defs"] - stats["refs"])
    if missing_defs or missing_refs:
        raise SystemExit(f"Footnote mismatch. Missing defs: {missing_defs or 'none'}; missing refs: {missing_refs or 'none'}")
    if args.analyze_only:
        return

    md_path.write_text(normalize(lines, args, lang, hierarchy, styles), encoding="utf-8")
    print(f"Markdown: {md_path}")
    cmd = ["pandoc", str(md_path), "--from", "markdown+smart+fenced_divs", "--to", "docx", "--output", str(output_path)]
    if args.reference:
        cmd.insert(-2, f"--reference-doc={Path(args.reference).resolve()}")
    subprocess.run(cmd, check=True)
    if args.reference and args.reference_styles != "off":
        patch_missing_paragraph_styles(output_path, styles)
    validate_docx(output_path)
    print(f"DOCX: {output_path}")
    print("Validation: ok")


if __name__ == "__main__":
    main()
