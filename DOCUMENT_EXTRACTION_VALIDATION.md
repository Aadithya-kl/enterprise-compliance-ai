# Universal Document Extraction Validation Report

## Overview
The platform has been upgraded from a PDF-only restriction to support a wide array of document formats. Ingestion handles text files, office documents, spreadsheets, presentations, configuration files, and image-based scans.

---

## Supported Formats & Extraction Methods

| File Extension | Content Type | Processing Library | Extraction Logic |
| :--- | :--- | :--- | :--- |
| `.pdf` | Adobe PDF | `pdfplumber` | Extracts structured text page-by-page. Fallback to OCR if no text is found. |
| `.docx`, `.doc` | Microsoft Word | `python-docx` | Extracts paragraph runs and tabular text. |
| `.txt`, `.rtf`, `.odt` | Plain Text | Built-in | Reads raw text with UTF-8 decoding and replacement fallbacks. |
| `.xlsx`, `.xls` | Microsoft Excel | `openpyxl` | Formats each sheet with headers, extracting cell values delimited by ` | `. |
| `.csv` | Comma Separated | Python `csv` | Reads and forms lines using standard delimiters. |
| `.pptx`, `.ppt` | Slideshow | `python-pptx` | Extracts text frames and tables slide-by-slide. |
| `.json` | JSON Data | Python `json` | Formats data structure using pretty-printed JSON. |
| `.xml` | XML Data | `xml.etree` | Parses elements recursively, combining inner tags and tails. |
| `.yaml`, `.yml` | YAML config | `PyYAML` | Parses and formats YAML key-value trees. |
| `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif` | Images | `pytesseract` + `Pillow` | Uses optical character recognition (OCR) to read text. |

---

## Tesseract OCR & Fallback Design

### Resilience checks:
1. **Library Availability**: The OCR engine is wrapped in import checks. If `pytesseract` or `Pillow` are not installed, the system will not crash, but it raises a clean error informing the user that OCR libraries are required.
2. **Binary Availability**: If the Tesseract command-line binary is missing or configured incorrectly on the system, the execution captures the error, returning a detailed validation warning instead of a raw backend failure.
