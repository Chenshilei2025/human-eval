"""Build a server-free HTML containing the blinded tasks."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
template = (HERE / "index.html").read_text(encoding="utf-8")
data = {
    "eil": json.loads((ROOT / "eil_blinded_tasks.json").read_text(encoding="utf-8")),
    "miu": json.loads((ROOT / "miu_blinded_tasks.json").read_text(encoding="utf-8")),
}
marker = "const EMBEDDED_DATA=null;"
if template.count(marker) != 1:
    raise ValueError(f"expected exactly one standalone data marker, found {template.count(marker)}")
html = template.replace(marker, "const EMBEDDED_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
(HERE / "human_eval_standalone.html").write_text(html, encoding="utf-8")
print(f"wrote {HERE / 'human_eval_standalone.html'}")
