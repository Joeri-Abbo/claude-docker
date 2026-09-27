# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Schuberg Philis
"""Build the --api egress audit PDF from the session logs run.sh saves.

Usage: python3 egress_report.py <log-dir> <out.pdf>   (run via `run.sh --report`)

Every --api session leaves <id>.log (squid's access log, which is every
connection the container made: its network is --internal) and <id>.meta
(key=value lines) in <log-dir>. The report lists, per session, all model
traffic: requests to the configured endpoint and to the model-provider hosts
the proxy blocks. The verdict is FAIL if a provider request was not refused.

Stdlib only, like update_pins.py: the PDF is hand-written (Courier text).
"""

import datetime
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

# Keep in sync with EGRESS_MODEL_PROVIDERS in run.sh.
PROVIDERS = ("anthropic.com", "claude.ai", "claude.com")


def host_of(url):
    host = url.split("://", 1)[-1].split("/", 1)[0]
    return host.rsplit(":", 1)[0] if ":" in host else host


def is_provider(host):
    return any(host == p or host.endswith("." + p) for p in PROVIDERS)


def parse(log_text):
    """squid's default access-log format:
    time elapsed client result/status bytes method URL user hierarchy/peer type
    """
    rows = []
    for line in log_text.splitlines():
        f = line.split()
        if len(f) < 9 or "/" not in f[3]:
            continue
        rows.append({
            "time": float(f[0]),
            "result": f[3].split("/", 1)[0],
            "method": f[5],
            "host": host_of(f[6]),
            "peer": f[8].split("/", 1)[-1],
        })
    return rows


def ts(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def session(log_path):
    meta = {}
    meta_path = log_path.with_suffix(".meta")
    if meta_path.exists():
        for line in meta_path.read_text().splitlines():
            k, _, v = line.partition("=")
            meta[k] = v
    rows = parse(log_path.read_text(errors="replace"))
    endpoint = meta.get("endpoint", "")
    for r in rows:
        r["model"] = r["host"] == endpoint or is_provider(r["host"])
    model = [r for r in rows if r["model"]]
    leaked = [r for r in model if is_provider(r["host"]) and r["result"] != "TCP_DENIED"]
    return meta, rows, model, leaked


def table(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    out = []
    for k, rs in sorted(groups.items()):
        out.append(f"  {k[0]:<34} {k[1]:<11} {len(rs):>5}  {ts(rs[0]['time'])[:-1]}-{ts(rs[-1]['time'])[11:]}")
        peers = sorted({r["peer"] for r in rs if r["peer"] != "-"})
        if peers:
            out.append(f"  {'':<34} upstream IP: {', '.join(peers)}")
    return out


def report_lines(log_dir):
    logs = sorted(Path(log_dir).glob("*.log"))
    lines = [("H", "Claude Code EU model-traffic report"),
             ("T", f"Generated {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%SZ} from {log_dir}"),
             ("T", f"Sessions: {len(logs)}"),
             ("T", ""),
             ("T", "Scope: model (LLM) traffic of Claude Code in claude-docker --api sessions."),
             ("T", "Each session ran on an --internal network whose only way out is the squid"),
             ("T", "proxy that wrote the log below, so the log lists every connection made."),
             ("T", "The proxy allows the configured endpoint and refuses"),
             ("T", f"{', '.join('*.' + p for p in PROVIDERS)}."),
             ("T", "The endpoint's own upstream region is evidenced by the gateway, not here."),
             ("T", "")]
    failed = 0
    for log in logs:
        meta, rows, model, leaked = session(log)
        failed += bool(leaked)
        lines.append(("H", f"Session {log.stem}"))
        for k in ("start", "end", "user", "host", "workspace", "image", "image_id", "endpoint"):
            lines.append(("T", f"  {k:<10} {meta.get(k, '(missing)')}"))
        lines.append(("T", f"  log sha256 {hashlib.sha256(log.read_bytes()).hexdigest()}"))
        lines.append(("T", ""))
        allowed = [r for r in model if r["result"] != "TCP_DENIED"]
        verdict = "FAIL" if leaked else "PASS"
        lines.append(("B", f"Verdict: {verdict}"))
        lines.append(("T", f"  {len(allowed)} model request(s) reached {', '.join(sorted({r['host'] for r in allowed})) or 'no host'};"))
        lines.append(("T", f"  {len(model) - len(allowed)} request(s) to model providers refused, {len(leaked)} not refused."))
        lines.append(("T", ""))
        lines.append(("B", "Model traffic"))
        lines.append(("T", f"  {'host':<34} {'result':<11} {'count':>5}  first-last (UTC)"))
        lines += [("T", s) for s in table(model, lambda r: (r["host"], r["result"]))] or [("T", "  (none)")]
        lines.append(("T", ""))
        other = [r for r in rows if not r["model"]]
        lines.append(("B", "Other traffic (not model traffic, out of scope)"))
        lines += [("T", s) for s in table(other, lambda r: (r["host"], r["result"]))] or [("T", "  (none)")]
        lines.append(("T", ""))
    lines.insert(3, ("B", f"Overall: {'FAIL' if failed else 'PASS'} ({failed} of {len(logs)} sessions failed)"))
    return lines, failed


def pdf(lines):
    """Minimal PDF 1.4: A4 pages of Courier/Courier-Bold text, 90 columns."""
    fonts = {"H": ("F2", 13, 20), "B": ("F2", 9, 13), "T": ("F1", 9, 11)}
    pages, cur, y = [], [], 800
    for kind, text in lines:
        font, size, lead = fonts[kind]
        for chunk in [text[i:i + 90] for i in range(0, len(text), 90)] or [""]:
            if y < 50:
                pages.append(cur)
                cur, y = [], 800
            esc = chunk.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            cur.append(f"BT /{font} {size} Tf 45 {y} Td ({esc}) Tj ET")
            y -= lead
    pages.append(cur)

    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>"]
    kids = []
    for n, page in enumerate(pages, 1):
        stream = "\n".join(page + [f"BT /F1 8 Tf 500 25 Td (page {n}/{len(pages)}) Tj ET"])
        stream = stream.encode("latin-1", "replace")
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {len(objs)} 0 R "
                    "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>")
        kids.append(f"{len(objs)} 0 R")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"

    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + (o if isinstance(o, bytes) else o.encode()) + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def main(argv):
    if len(argv) != 3:
        sys.exit("usage: egress_report.py <log-dir> <out.pdf>")
    log_dir, out = argv[1], argv[2]
    if not any(Path(log_dir).glob("*.log")):
        sys.exit(f"egress_report: no session logs in {log_dir} (run an --api session first)")
    lines, failed = report_lines(log_dir)
    Path(out).write_bytes(pdf(lines))
    print(f"egress_report: wrote {out} ({'FAIL' if failed else 'PASS'})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
