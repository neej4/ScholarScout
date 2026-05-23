"""
File upload route: /api/upload
Accepts text files (.txt, .md, .pdf text extraction) as additional context for idea generation.
Stores content in session-level memory (not persisted to disk).
"""
import os
from flask import Blueprint, jsonify, request

upload_bp = Blueprint("upload", __name__)

# In-memory storage for uploaded context (per-server session, cleared on restart)
_uploaded_context: str = ""
MAX_CONTEXT_CHARS = 50000  # ~12500 tokens — enough for most papers/docs


@upload_bp.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Upload a text file to use as additional context for idea generation.

    Accepts multipart/form-data with a 'file' field.
    Supported: .txt, .md, .json, .pdf (text extraction).
    
    Returns: {"status": "ok", "chars": int, "preview": str}
    """
    global _uploaded_context

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use form field name 'file'."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Check extension
    allowed_ext = {".txt", ".md", ".json", ".pdf"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({
            "error": f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(allowed_ext))}"
        }), 400

    # Read content
    try:
        raw_bytes = file.read()

        if ext == ".pdf":
            content = _extract_pdf_text(raw_bytes)
            if not content:
                return jsonify({"error": "Could not extract text from PDF. Try a text-based PDF (not scanned image)."}), 400
        else:
            content = raw_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {e}"}), 400

    # Truncate to max
    if len(content) > MAX_CONTEXT_CHARS:
        content = content[:MAX_CONTEXT_CHARS]

    # Reject empty files
    if not content.strip():
        return jsonify({"error": "File is empty. Upload a file with text content."}), 400

    _uploaded_context = content

    return jsonify({
        "status": "ok",
        "filename": file.filename,
        "chars": len(content),
        "preview": content[:200] + ("..." if len(content) > 200 else ""),
    })


def _extract_pdf_text(raw_bytes: bytes) -> str:
    """
    Basic PDF text extraction without external dependencies.
    Handles simple text-based PDFs by extracting text between BT/ET operators.
    For complex PDFs, returns empty string (user should convert to .txt first).
    """
    import re as _re
    import zlib

    text_parts = []
    content = raw_bytes

    # Try to decompress FlateDecode streams and extract text
    # This is a best-effort approach for simple PDFs
    try:
        # Find all stream objects
        streams = _re.findall(rb'stream\r?\n(.*?)\r?\nendstream', content, _re.DOTALL)
        for stream_data in streams:
            # Try to decompress
            try:
                decompressed = zlib.decompress(stream_data)
            except Exception:
                decompressed = stream_data

            # Extract text between BT and ET (text objects)
            text_objects = _re.findall(rb'BT(.*?)ET', decompressed, _re.DOTALL)
            for obj in text_objects:
                # Extract strings in parentheses (Tj operator) or hex strings
                strings = _re.findall(rb'\((.*?)\)', obj)
                for s in strings:
                    try:
                        decoded = s.decode('utf-8', errors='ignore')
                        # Filter out control chars
                        decoded = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', decoded)
                        if decoded.strip():
                            text_parts.append(decoded)
                    except Exception:
                        continue
    except Exception:
        pass

    # Also try simple text extraction (some PDFs have readable text directly)
    try:
        simple_text = _re.findall(rb'\(([\x20-\x7e]{4,})\)', content)
        for t in simple_text[:100]:
            decoded = t.decode('ascii', errors='ignore').strip()
            if len(decoded) > 5 and decoded not in text_parts:
                text_parts.append(decoded)
    except Exception:
        pass

    result = " ".join(text_parts)
    # Clean up excessive whitespace
    result = _re.sub(r'\s+', ' ', result).strip()
    return result


@upload_bp.route("/api/upload", methods=["DELETE"])
def api_upload_clear():
    """Clear uploaded context."""
    global _uploaded_context
    _uploaded_context = ""
    return jsonify({"status": "cleared"})


@upload_bp.route("/api/upload", methods=["GET"])
def api_upload_get():
    """Get current uploaded context info."""
    return jsonify({
        "has_file": bool(_uploaded_context),
        "chars": len(_uploaded_context),
        "preview": _uploaded_context[:200] + ("..." if len(_uploaded_context) > 200 else ""),
    })


def get_uploaded_context() -> str:
    """Get the uploaded context string (called by ideas.py and pipeline)."""
    return _uploaded_context
