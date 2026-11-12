"""OCR сканов приказов о границах ОКН через установленный Tesseract.

По умолчанию обрабатываются первые 10 приказов. Исходные PDF не меняются.
"""
import argparse
import csv
import re
import shutil
import subprocess
from pathlib import Path

import fitz

R = Path(__file__).resolve().parents[2]
OUT = R / "tmp/okn-ocr"


def read(name):
    with (R / "data/okn" / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    if not rows:
        return
    path = R / "data/okn" / name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pages(text):
    parts = re.split(r"(?:^|\n)PAGE (\d+)\n", text)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]


def tesseract_path(value):
    path = Path(value) if value else None
    return str(path) if path and path.exists() else shutil.which(value or "tesseract")


def selected_sources(args):
    sources = [r for r in read("evidence_sources.csv") if r["source_id"].startswith("boundary_")]
    if args.source_id:
        wanted = set(args.source_id)
        sources = [r for r in sources if r["source_id"] in wanted]
        missing = wanted - {r["source_id"] for r in sources}
        if missing:
            raise SystemExit("Неизвестные source_id: " + ", ".join(sorted(missing)))
    else:
        sources = sources if args.all else sources[:args.sample]
    assert sources, "Нет приказов для OCR"
    return sources


def run_one(source, exe, lang, dpi, keep_images, dry_run, tessdata_dir, reuse_text):
    pdf = R / source["local_path"]
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    existing = OUT / f"{source['source_id']}.txt"
    if reuse_text and existing.exists() and not dry_run:
        return {"source_id": source["source_id"], "pdf": source["local_path"],
                "pages": len(pages(existing.read_text(encoding="utf-8"))),
                "text_chars": len(existing.read_text(encoding="utf-8")), "status": "готов (повторно использован)", "ошибки": ""}
    with fitz.open(pdf) as document:
        if not len(document):
            raise ValueError(f"Пустой PDF: {pdf}")
        image_dir = OUT / "images" / source["source_id"]
        image_dir.mkdir(parents=True, exist_ok=True)
        text_parts = []
        errors = []
        for number, page in enumerate(document, 1):
            image = image_dir / f"page-{number:03d}.png"
            if not dry_run:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
                pixmap.save(image)
                command = [exe, str(image), "stdout", "-l", lang, "--psm", "6"]
                if tessdata_dir:
                    command.extend(["--tessdata-dir", str(tessdata_dir)])
                result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
                if result.returncode:
                    errors.append(f"страница {number}: {result.stderr.strip()}")
                text_parts.append(f"PAGE {number}\n{result.stdout}")
        if not dry_run:
            (OUT / f"{source['source_id']}.txt").write_text("\n".join(text_parts), encoding="utf-8")
        if not keep_images and image_dir.exists() and not dry_run:
            shutil.rmtree(image_dir)
        return {"source_id": source["source_id"], "pdf": source["local_path"], "pages": len(document),
                "text_chars": sum(len(x) for x in text_parts), "status": "ошибка OCR" if errors else ("готов" if not dry_run else "план"),
                "ошибки": " | ".join(errors)}


def find_hits(sources):
    targets = read("egrokn_altai_unresolved_audit.csv")
    targets = [r for r in targets if "подсказка" not in r["группа_проблемы"]]
    hits = []
    for source in sources:
        text_path = OUT / f"{source['source_id']}.txt"
        if not text_path.exists():
            continue
        for page, text in pages(text_path.read_text(encoding="utf-8")):
            compact = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
            for row in targets:
                reg = row["рег_номер"]
                account = re.sub(r"\D", "", row["учетный_номер_СТП"])
                methods = []
                if re.search(rf"(?<!\d){re.escape(reg)}(?!\d)", text) or re.search(rf"(?<!\d){re.escape(reg)}(?!\d)", compact):
                    methods.append("реестровый номер")
                if account and len(account) >= 6 and account in re.sub(r"\D", "", text):
                    methods.append("учетный номер СТП")
                if methods:
                    hits.append({"рег_номер": reg, "название": row["название"], "source_id": source["source_id"],
                                 "страница": page, "метод": " + ".join(methods)})
    unique = {(r["рег_номер"], r["source_id"], r["страница"], r["метод"]): r for r in hits}
    return list(unique.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sample", type=int, default=10, help="число первых приказов (по умолчанию 10)")
    group.add_argument("--all", action="store_true", help="обработать все приказы")
    group.add_argument("--source-id", action="append", help="обработать конкретный source_id; можно повторять")
    parser.add_argument("--tesseract", help="путь к tesseract.exe; иначе поиск в PATH")
    parser.add_argument("--lang", default="rus+eng", help="языки Tesseract")
    parser.add_argument("--dpi", type=int, default=200, help="разрешение рендера, по умолчанию 200 DPI")
    parser.add_argument("--keep-images", action="store_true", help="сохранить PNG страниц для визуальной проверки")
    parser.add_argument("--tessdata-dir", help="папка с .traineddata, например tmp/tessdata")
    parser.add_argument("--reuse-text", action="store_true", help="не распознавать уже готовые txt")
    parser.add_argument("--dry-run", action="store_true", help="проверить PDF и план, не запускать OCR")
    args = parser.parse_args()
    assert args.dpi >= 150
    sources = selected_sources(args)
    exe = tesseract_path(args.tesseract)
    if not args.dry_run and not exe:
        raise SystemExit("Tesseract не найден. Укажите --tesseract путь к tesseract.exe или добавьте его в PATH.")
    if not args.dry_run:
        list_command = [exe]
        if args.tessdata_dir:
            list_command.extend(["--tessdata-dir", str(R / args.tessdata_dir), "--list-langs"])
        else:
            list_command.append("--list-langs")
        languages = subprocess.run(list_command, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        for language in args.lang.split("+"):
            if language not in languages.split():
                raise SystemExit(f"Языковой пакет Tesseract не найден: {language}")
    OUT.mkdir(parents=True, exist_ok=True)
    inventory = [run_one(s, exe, args.lang, args.dpi, args.keep_images, args.dry_run, args.tessdata_dir, args.reuse_text) for s in sources]
    write("ocr_boundary_inventory.csv", inventory)
    if not args.dry_run:
        hits = find_hits(sources)
        if hits:
            write("ocr_boundary_hits_70.csv", hits)
        else:
            (R / "data/okn/ocr_boundary_hits_70.csv").write_text(
                "рег_номер,название,source_id,страница,метод\n", encoding="utf-8-sig"
            )
    print(f"Приказов: {len(sources)}; страниц: {sum(r['pages'] for r in inventory)}; режим: {'план' if args.dry_run else 'OCR'}")


if __name__ == "__main__":
    main()
