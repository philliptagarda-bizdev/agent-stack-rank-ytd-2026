#!/usr/bin/env python3
import re
from pathlib import Path
h = Path("Presales_Weekly_Report_W3_Jun_2026.html").read_text(encoding="utf-8")
# join all <script>...</script> blocks
blocks = re.findall(r'<script\b[^>]*>(.*?)</script>', h, flags=re.DOTALL|re.IGNORECASE)
print(f"script blocks: {len(blocks)}")
Path("/tmp/ck.js").write_text("\n;\n".join(blocks), encoding="utf-8")
print("written /tmp/ck.js")
