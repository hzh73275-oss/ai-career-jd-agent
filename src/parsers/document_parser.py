import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def clean_text(text: str) -> str:
  return re.sub(r"\s+", " ", text or "").strip()


def read_text_file(path: Path) -> str:
  return path.read_text(encoding="utf-8", errors="ignore")


def read_docx(path: Path) -> str:
  texts: list[str] = []
  with zipfile.ZipFile(path) as archive:
    names = [
      name for name in archive.namelist()
      if name.startswith("word/") and name.endswith(".xml")
      and ("document.xml" in name or "header" in name or "footer" in name)
    ]
    for name in sorted(names):
      root = ElementTree.fromstring(archive.read(name))
      texts.extend(
        node.text for node in root.iter()
        if node.tag.endswith("}t") and node.text
      )
  return clean_text(" ".join(texts))


def read_pdf(path: Path) -> str:
  try:
    from pypdf import PdfReader
  except ImportError as exc:
    raise RuntimeError("读取 PDF 需要安装 pypdf：pip install pypdf") from exc

  reader = PdfReader(str(path))
  texts = [page.extract_text() or "" for page in reader.pages]
  return clean_text("\n".join(texts))


def read_document(path_or_text: str) -> str:
  value = (path_or_text or "").strip()
  path = Path(value)
  if path.exists():
    suffix = path.suffix.lower()
    if suffix == ".docx":
      return read_docx(path)
    if suffix == ".pdf":
      return read_pdf(path)
    return clean_text(read_text_file(path))
  return clean_text(value)
