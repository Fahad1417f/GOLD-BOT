from __future__ import annotations

import json

PROVIDER_KEYS = ("__GOLDBOT_KFOO__", "__KFOO__")
DATA_SELECTOR = "[data-goldbot-kfoo], [data-kfoo-analysis], [data-kfoo]"


def inspect_page(page) -> dict:
    """Inspect the live TradingView page for explicit KFOO publishers only.

    This tool never OCRs or infers KFOO from chart pixels. It only reports
    explicitly published JSON/script/data attributes so the missing upstream
    bridge can be diagnosed without introducing synthetic trading inputs.
    """
    result = page.evaluate(
        r"""(selectors) => {
          const out = {window_keys:{}, dom_nodes:[]};
          for (const key of selectors.keys) {
            try { out.window_keys[key] = window[key] ?? null; } catch (_) { out.window_keys[key] = null; }
          }
          for (const n of document.querySelectorAll(selectors.selector)) {
            const raw = n.getAttribute('data-goldbot-kfoo') || n.getAttribute('data-kfoo-analysis') || n.getAttribute('data-kfoo') || n.textContent || '';
            out.dom_nodes.push({tag:n.tagName, id:n.id||'', className:typeof n.className==='string'?n.className:'', raw:raw.slice(0,20000)});
          }
          return out;
        }""",
        {"keys": list(PROVIDER_KEYS), "selector": DATA_SELECTOR},
    )
    for key, value in list(result.get("window_keys", {}).items()):
        if value is not None:
            return {"source": "window." + key, "payload": value}
    for node in result.get("dom_nodes", []):
        raw = (node.get("raw") or "").strip()
        if not raw:
            continue
        try:
            return {"source": "dom", "node": node, "payload": json.loads(raw)}
        except Exception:
            continue
    return {"source": "none", "payload": None}
