import json
import re
from typing import Any, Dict

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_json_safely(model_text: str) -> Dict[str, Any]:
    """
    Handles common LLM formatting issues:
    - JSON wrapped in ```json ... ```
    - Preamble text before JSON
    - Trailing commentary after JSON
    """
    if not model_text or not isinstance(model_text, str):
        raise json.JSONDecodeError("Empty response", "", 0)

    text = model_text.strip()

    # 1) Extract from code fences if present
    m = _CODE_FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()

    # 2) If still not pure JSON, try best-effort brace slicing
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first:last + 1]

    return json.loads(text)

