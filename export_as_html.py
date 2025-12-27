# export_as_html.py
import html
import re
from pathlib import Path
from typing import Dict, Optional, List


DIARY_HEADER_RE = re.compile(
    r"^===\s*DiaryID:\s*(\d+)\s*\|\s*Date:\s*([^|]+)\|\s*TS:\s*([0-9]+)\s*===$"
)
TITLE_RE = re.compile(r"^Title:\s*(.*)$")
IMG_REF_RE = re.compile(r"\[图(\d+)\]")
TS_LINE_RE = re.compile(r"^\[(\d{1,2}:\d{2}:\d{2})\]$")


def build_image_index(images_dir: Path) -> Dict[int, Path]:
    index: Dict[int, Path] = {}
    if not images_dir.exists():
        return index

    for p in images_dir.iterdir():
        if not p.is_file():
            continue
        m = re.match(r"^image_(\d+)\.[A-Za-z0-9]+$", p.name)
        if not m:
            continue
        img_id = int(m.group(1))
        if img_id not in index:
            index[img_id] = p
        else:
            if index[img_id].suffix.lower() == ".bin" and p.suffix.lower() != ".bin":
                index[img_id] = p
    return index


def _replace_img_refs(escaped_text: str, img_index: Dict[int, Path], images_dir: Path) -> str:
    def repl(m: re.Match) -> str:
        img_id = int(m.group(1))
        p: Optional[Path] = img_index.get(img_id)

        if p is None:
            candidates = list(images_dir.glob(f"image_{img_id}.*"))
            if candidates:
                candidates.sort(key=lambda x: (x.suffix.lower() == ".bin", x.name))
                p = candidates[0]

        if p is None or not p.exists():
            return f'<span class="img-missing">图片已丢失（图{img_id}）</span>'

        rel = p.as_posix()
        return (
            f'<figure class="img-wrap">'
            f'<img src="{html.escape(rel)}" alt="图{img_id}" loading="lazy" />'
            f'<figcaption>图{img_id}</figcaption>'
            f'</figure>'
        )

    return IMG_REF_RE.sub(repl, escaped_text)


def render_content_to_html(raw_text: str, img_index: Dict[int, Path], images_dir: Path) -> str:
    lines = raw_text.splitlines()
    blocks: List[str] = []
    buf: List[str] = []

    def flush_paragraph():
        nonlocal buf
        if not buf:
            return
        text = "\n".join(buf).strip("\n")
        esc = html.escape(text).replace("\n", "<br>")
        esc = _replace_img_refs(esc, img_index, images_dir)
        blocks.append(f'<p class="p">{esc}</p>')
        buf = []

    for ln in lines:
        s = ln.strip()
        if s == "":
            flush_paragraph()
            continue

        mt = TS_LINE_RE.match(s)
        if mt:
            flush_paragraph()
            blocks.append(f'<div class="ts">{html.escape(mt.group(1))}</div>')
            continue

        buf.append(ln)

    flush_paragraph()
    return "\n".join(blocks)


def parse_dairies_txt(dairies_path: Path) -> List[Dict]:
    entries: List[Dict] = []
    current: Optionallne = None  # type: ignore

    current = None
    with dairies_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            mh = DIARY_HEADER_RE.match(line)
            if mh:
                if current is not None:
                    entries.append(current)
                current = {
                    "id": int(mh.group(1)),
                    "date": mh.group(2).strip(),
                    "ts": mh.group(3).strip(),
                    "title": "",
                    "content_lines": [],
                }
                continue

            if current is None:
                continue

            mt = TITLE_RE.match(line)
            if mt:
                current["title"] = mt.group(1).strip()
                continue

            current["content_lines"].append(line)

    if current is not None:
        entries.append(current)

    entries.sort(key=lambda x: x["id"])
    return entries


def export_as_html(
    dairies_txt: str = "dairies.txt",
    images_dir: str = "recovery_images",
    out_html: str = "dairies.html",
) -> None:
    dairies_path = Path(dairies_txt)
    images_path = Path(images_dir)
    out_path = Path(out_html)

    if not dairies_path.exists():
        raise FileNotFoundError(f"Not found: {dairies_path}")

    img_index = build_image_index(images_path)
    entries = parse_dairies_txt(dairies_path)

    date_map: Dict[str, List[int]] = {}
    for e in entries:
        date_map.setdefault(e["date"], []).append(e["id"])

    diary_blocks: List[str] = []
    last_day = None
    for e in entries:
        did = e["id"]
        ymd = e["date"]
        title = e["title"] or ""
        ts = e["ts"]

        day_anchor = ""
        if ymd != last_day:
            day_anchor = f'<div class="day-anchor" id="day-{html.escape(ymd)}"></div>'
            last_day = ymd

        raw_text = "\n".join(e["content_lines"]).strip("\n")
        merged_html = render_content_to_html(raw_text, img_index, images_path)

        diary_blocks.append(
            f"""
            {day_anchor}
            <section class="diary" id="diary-{did}" data-date="{html.escape(ymd)}">
              <div class="title">{html.escape(title) if title else "（无标题）"}</div>
              <div class="meta">DiaryID: {did} · Date: {html.escape(ymd)} · TS: {html.escape(ts)}</div>
              <div class="content">{merged_html}</div>
            </section>
            """
        )

    dates_js_array = "[" + ",".join(f'"{d}"' for d in sorted(date_map.keys())) + "]"

    css = """
    :root { color-scheme: light; }
    body {
      font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang SC","Microsoft YaHei",sans-serif;
      margin: 0;
      background: #fafafa;
      line-height: 1.75;
    }
    .page {
      max-width: 920px;
      margin: 28px auto;
      padding: 0 18px 90px;
    }
    h1 { margin: 0 0 10px; }
    .meta { color: #666; font-size: 13px; margin-top: 4px; }
    .diary {
      border: 1px solid #e8e8e8;
      border-radius: 16px;
      padding: 18px 18px 14px;
      margin: 16px 0;
      background: #fff;
      box-shadow: 0 6px 18px rgba(0,0,0,0.04);
    }
    .title { font-weight: 800; font-size: 20px; margin: 0 0 6px; }
    .content { margin-top: 12px; font-size: 15px; color: #111; }
    .p { margin: 10px 0; }
    .ts {
      display: inline-block;
      font-size: 12px;
      color: #b00020;
      background: #fff0f0;
      border: 1px solid #ffd1d1;
      padding: 2px 8px;
      border-radius: 999px;
      margin: 6px 0 8px;
    }
    .day-anchor { height: 1px; }
    .img-wrap {
      margin: 12px 0;
      padding: 10px;
      border: 1px dashed #ddd;
      border-radius: 14px;
      background: #fafafa;
    }
    .img-wrap img { max-width: 100%; height: auto; display: block; border-radius: 12px; }
    .img-wrap figcaption { color: #666; font-size: 12px; margin-top: 6px; }
    .img-missing {
      color: #b00020;
      font-weight: 700;
      background: #fff0f0;
      padding: 2px 6px;
      border-radius: 8px;
      border: 1px solid #ffd1d1;
    }
    .diary.flash { outline: 3px solid #ff7aa2; box-shadow: 0 0 0 6px rgba(255,122,162,0.15); }

    .calendar-float {
      position: fixed;
      right: 18px;
      bottom: 18px;
      width: 320px;
      border-radius: 16px;
      background: rgba(255,255,255,0.92);
      border: 1px solid #e7e7e7;
      box-shadow: 0 10px 30px rgba(0,0,0,0.12);
      backdrop-filter: blur(10px);
      z-index: 9999;
      overflow: hidden;
      user-select: none;
    }
    .cal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      background: linear-gradient(90deg, rgba(255,180,205,0.55), rgba(180,235,255,0.55));
      cursor: move;
    }
    .cal-title { font-weight: 800; }
    .cal-actions { display: flex; gap: 6px; }
    .cal-btn {
      border: 1px solid rgba(0,0,0,0.08);
      background: rgba(255,255,255,0.8);
      border-radius: 10px;
      padding: 4px 8px;
      cursor: pointer;
      font-size: 12px;
    }
    .cal-body { padding: 10px 12px 12px; }
    .cal-nav { display:flex; align-items:center; justify-content: space-between; margin-bottom: 8px; }
    .cal-nav button {
      border: 1px solid rgba(0,0,0,0.08);
      background: rgba(255,255,255,0.85);
      border-radius: 10px;
      padding: 4px 8px;
      cursor: pointer;
    }
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
    .cal-weekday { text-align: center; font-size: 12px; color: #666; padding: 4px 0; }
    .cal-day {
      text-align: center;
      padding: 10px 0;
      border-radius: 12px;
      border: 1px solid rgba(0,0,0,0.06);
      background: rgba(255,255,255,0.75);
      font-size: 14px;
      cursor: default;
    }
    .cal-day.muted { color: #aaa; background: rgba(255,255,255,0.5); }
    .cal-day.has { color: #d7005d; font-weight: 800; cursor: pointer; }
    .cal-day.has:hover { background: rgba(255,180,205,0.35); }
    .cal-day.today { border-color: rgba(215,0,93,0.35); }
    .cal-collapsed .cal-body { display: none; }
    """

    js = f"""
    const diaryDates = new Set({dates_js_array});
    const WEEKDAYS = ["一","二","三","四","五","六","日"];
    function pad2(n) {{ return String(n).padStart(2, "0"); }}
    function ymdStr(y,m,d) {{ return `${{y}}-${{pad2(m)}}-${{pad2(d)}}`; }}

    function getInitialYM() {{
      const keys = Array.from(diaryDates).sort();
      if (keys.length > 0) {{
        const last = keys[keys.length-1];
        const [y,m] = last.split("-").map(Number);
        return {{y, m}};
      }}
      const now = new Date();
      return {{y: now.getFullYear(), m: now.getMonth()+1}};
    }}

    let view = getInitialYM();

    function renderCalendar() {{
      const y = view.y, m = view.m;
      document.getElementById("calMonth").textContent = `${{y}}年${{m}}月`;
      const grid = document.getElementById("calGrid");
      grid.innerHTML = "";

      for (const w of WEEKDAYS) {{
        const el = document.createElement("div");
        el.className = "cal-weekday";
        el.textContent = "周" + w;
        grid.appendChild(el);
      }}

      const first = new Date(y, m-1, 1);
      let firstWeekday = first.getDay();
      firstWeekday = (firstWeekday + 6) % 7;

      const daysInMonth = new Date(y, m, 0).getDate();
      const prevDays = new Date(y, m-1, 0).getDate();

      const totalCells = 42;
      let dayNum = 1;
      let nextNum = 1;

      const now = new Date();
      const todayY = now.getFullYear(), todayM = now.getMonth()+1, todayD = now.getDate();

      for (let i=0; i<totalCells; i++) {{
        const cell = document.createElement("div");
        cell.className = "cal-day";

        let cy=y, cm=m, cd=0;
        if (i < firstWeekday) {{
          cd = prevDays - (firstWeekday - 1 - i);
          cm = m-1; cy=y;
          if (cm <= 0) {{ cm=12; cy=y-1; }}
          cell.classList.add("muted");
          cell.textContent = cd;
        }} else if (dayNum <= daysInMonth) {{
          cd = dayNum;
          cell.textContent = cd;
          dayNum++;
        }} else {{
          cd = nextNum++;
          cm = m+1; cy=y;
          if (cm >= 13) {{ cm=1; cy=y+1; }}
          cell.classList.add("muted");
          cell.textContent = cd;
        }}

        const key = ymdStr(cy, cm, cd);

        if (diaryDates.has(key)) {{
          cell.classList.add("has");
          cell.title = "有日记";
          cell.addEventListener("click", () => jumpToDate(key));
        }}

        if (cy===todayY && cm===todayM && cd===todayD) {{
          cell.classList.add("today");
        }}

        grid.appendChild(cell);
      }}
    }}

    function jumpToDate(key) {{
      const anchor = document.getElementById("day-" + key);
      if (anchor) {{
        anchor.scrollIntoView({{ behavior: "smooth", block: "start" }});
        setTimeout(() => {{
          const firstDiary = document.querySelector(`.diary[data-date="${{CSS.escape(key)}}"]`);
          if (firstDiary) {{
            firstDiary.classList.add("flash");
            setTimeout(() => firstDiary.classList.remove("flash"), 1200);
          }}
        }}, 350);
      }} else {{
        alert("该日期没有找到对应日记锚点：" + key);
      }}
    }}

    function prevMonth() {{
      view.m--;
      if (view.m <= 0) {{ view.m = 12; view.y--; }}
      renderCalendar();
    }}
    function nextMonth() {{
      view.m++;
      if (view.m >= 13) {{ view.m = 1; view.y++; }}
      renderCalendar();
    }}

    const floatEl = document.getElementById("calendarFloat");
    const headerEl = document.getElementById("calHeader");

    document.getElementById("btnPrev").addEventListener("click", prevMonth);
    document.getElementById("btnNext").addEventListener("click", nextMonth);

    document.getElementById("btnToggle").addEventListener("click", () => {{
      floatEl.classList.toggle("cal-collapsed");
    }});

    document.getElementById("btnJumpToday").addEventListener("click", () => {{
      const now = new Date();
      view = {{ y: now.getFullYear(), m: now.getMonth()+1 }};
      renderCalendar();
    }});

    let dragging = false;
    let startX=0, startY=0, startLeft=0, startTop=0;

    headerEl.addEventListener("mousedown", (e) => {{
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = floatEl.getBoundingClientRect();
      startLeft = rect.left;
      startTop = rect.top;
      floatEl.style.right = "auto";
      floatEl.style.bottom = "auto";
      floatEl.style.left = startLeft + "px";
      floatEl.style.top = startTop + "px";
    }});

    window.addEventListener("mousemove", (e) => {{
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      floatEl.style.left = (startLeft + dx) + "px";
      floatEl.style.top = (startTop + dy) + "px";
    }});

    window.addEventListener("mouseup", () => {{ dragging = false; }});

    renderCalendar();
    """

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>dairies export</title>
<style>{css}</style>
</head>
<body>
  <div class="page">
    <h1>日记导出</h1>
    <div class="meta">来源：{html.escape(str(dairies_path))} · 图片目录：{html.escape(str(images_path))} · 日记数：{len(entries)} · 已索引图片：{len(img_index)}</div>
    {''.join(diary_blocks)}
  </div>

  <div class="calendar-float" id="calendarFloat">
    <div class="cal-header" id="calHeader">
      <div class="cal-title">日历</div>
      <div class="cal-actions">
        <button class="cal-btn" id="btnJumpToday" title="跳到本月">今天</button>
        <button class="cal-btn" id="btnToggle" title="折叠/展开">折叠</button>
      </div>
    </div>
    <div class="cal-body">
      <div class="cal-nav">
        <button id="btnPrev" title="上个月">«</button>
        <div id="calMonth" style="font-weight:800;"></div>
        <button id="btnNext" title="下个月">»</button>
      </div>
      <div class="cal-grid" id="calGrid"></div>
    </div>
  </div>

<script>{js}</script>
</body>
</html>
"""

    out_path.write_text(html_doc, encoding="utf-8")
    print(f"OK: wrote {out_path} (entries={len(entries)}, diary_dates={len(date_map)}, images_indexed={len(img_index)})")
