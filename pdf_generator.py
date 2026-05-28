"""
DDS Activity — Daily Management Report
Page 1: Executive Summary (Today's Changes + Brand Completion)
Page 2: Channel Distribution
"""
import io
import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
pt = 1
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Palette ──────────────────────────────────────────────────────────────────
C_INK    = colors.HexColor("#0f172a")
C_MUTED  = colors.HexColor("#64748b")
C_LITE   = colors.HexColor("#94a3b8")
C_BORD   = colors.HexColor("#e2e8f0")
C_SURF   = colors.HexColor("#f8fafc")
C_WHITE  = colors.white
C_NAVY   = colors.HexColor("#1e3a5f")
C_NAVY2  = colors.HexColor("#2d4f7c")   # lighter navy for accent

C_GREEN  = colors.HexColor("#16a34a");  C_GLIT = colors.HexColor("#dcfce7");  C_GDIM = colors.HexColor("#bbf7d0")
C_AMBER  = colors.HexColor("#d97706");  C_ALIT = colors.HexColor("#fef9c3");  C_ADIM = colors.HexColor("#fde68a")
C_BLUE   = colors.HexColor("#2563eb");  C_BLIT = colors.HexColor("#dbeafe");  C_BDIM = colors.HexColor("#bfdbfe")
C_RED    = colors.HexColor("#dc2626");  C_RLIT = colors.HexColor("#fee2e2")


def S(name, **kw):
    return ParagraphStyle(name, **kw)

def load_data():
    from data_fetcher import CACHE_FILE
    with open(CACHE_FILE) as f:
        return json.load(f)


# ── Charts ────────────────────────────────────────────────────────────────────
def make_donut(done, pending, ns, total):
    fig, ax = plt.subplots(figsize=(2.8, 2.8), facecolor="white")
    vals  = [done, pending, ns] if any([done, pending, ns]) else [1, 0, 0]
    clrs  = ["#16a34a", "#d97706", "#cbd5e1"]
    ws, _ = ax.pie(vals, colors=clrs, startangle=90,
                   wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2.5))
    pct = round((done / total) * 100) if total else 0
    ax.text(0,  0.06, f"{pct}%",    ha="center", fontsize=20, fontweight="bold", color="#0f172a")
    ax.text(0, -0.18, "complete",   ha="center", fontsize=8,  color="#64748b")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150, facecolor="white")
    plt.close(fig); buf.seek(0)
    return Image(buf, width=44*mm, height=44*mm)


def make_bar(mp_totals, all_mp):
    labs  = [mp for mp in all_mp if mp != "Amazon"]
    base  = mp_totals.get("Amazon", 1)
    vals  = [round((mp_totals.get(mp, 0) / base) * 100, 1) for mp in labs]
    bclrs = ["#16a34a" if v >= 50 else "#2563eb" if v >= 20 else "#d97706" if v >= 10 else "#ef4444"
             for v in vals]
    fig, ax = plt.subplots(figsize=(8.5, 2.6), facecolor="white")
    ax.set_facecolor("#f8fafc")
    bars = ax.bar(labs, vals, color=bclrs, width=0.55, zorder=3)
    for bar, val in zip(bars, vals):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                    f"{val}%", ha="center", va="bottom", fontsize=7, color="#0f172a", fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.38 if vals else 10)
    ax.set_ylabel("% of Amazon", color="#64748b", fontsize=8)
    ax.tick_params(colors="#64748b", labelsize=8)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.spines["bottom"].set_color("#e2e8f0")
    ax.yaxis.grid(True, color="#e2e8f0", zorder=0)
    ax.set_axisbelow(True)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150, facecolor="white")
    plt.close(fig); buf.seek(0)
    return Image(buf, width=170*mm, height=52*mm)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _no_pad():
    return TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ])


def progress_bar(pct, width, height=7):
    """Returns a full-width progress bar Flowable."""
    done_w = width * max(pct, 1) / 100
    rest_w = width - done_w
    return Table(
        [["", ""]],
        colWidths=[done_w, rest_w],
        style=TableStyle([
            ("BACKGROUND",    (0,0),(0,0), C_GREEN),
            ("BACKGROUND",    (1,0),(1,0), C_BORD),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), height),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ])
    )


def mini_bar(pct, col_w=22*mm, height=5):
    """Tiny inline progress bar for brand rows."""
    done_w = col_w * max(pct, 1) / 100
    rest_w = col_w - done_w
    clr = C_GREEN if pct >= 70 else (C_AMBER if pct >= 30 else C_RED)
    return Table(
        [["", ""]],
        colWidths=[done_w, rest_w],
        style=TableStyle([
            ("BACKGROUND",    (0,0),(0,0), clr),
            ("BACKGROUND",    (1,0),(1,0), colors.HexColor("#e2e8f0")),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), height),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ])
    )


# ── PDF Builder ───────────────────────────────────────────────────────────────
def build_pdf(output_path="management_summary.pdf"):
    data    = load_data()
    changes = data.get("changes")
    W       = A4[0] - 36*mm   # 174 mm usable

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=0,  bottomMargin=14*mm,
        title="DDS Tracker",
    )

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — Executive Summary
    # ══════════════════════════════════════════════════════════════════════════

    # ── Full-width header bar ─────────────────────────────────────────────────
    date_str = data.get("last_updated", "")[:10]
    try:
        date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        date_fmt = date_str

    hdr = Table(
        [[Paragraph("DDS Tracker",
                    S("hL", fontSize=16, textColor=C_WHITE, fontName="Helvetica-Bold", leading=20)),
          Paragraph(f"Ergode International  ·  {date_fmt}",
                    S("hR", fontSize=9, textColor=colors.HexColor("#93c5fd"),
                      fontName="Helvetica", leading=12, alignment=TA_RIGHT))]],
        colWidths=[W*0.6, W*0.4],
        style=TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_NAVY),
            ("TOPPADDING",    (0,0),(-1,-1), 14),
            ("BOTTOMPADDING", (0,0),(-1,-1), 14),
            ("LEFTPADDING",   (0,0),(-1,-1), 18),
            ("RIGHTPADDING",  (0,0),(-1,-1), 18),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ])
    )
    # Extend header to full page width (bleed to margins)
    hdr_wrap = Table([[hdr]], colWidths=[W],
        style=TableStyle([
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("TOPPADDING",   (0,0),(-1,-1), 0),
            ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ]))
    story.append(hdr_wrap)
    story.append(Spacer(1, 8*mm))

    # ── Overall KPI band ──────────────────────────────────────────────────────
    total    = data["total_skus"]
    done     = data["total_completed"]
    pending  = data["total_pending"]
    ns       = data["total_not_started"]
    pct_done = round((done / total) * 100, 1) if total else 0

    s_kpi_lbl = S("kl", fontSize=7,  textColor=C_MUTED,  fontName="Helvetica",      leading=9,  alignment=TA_CENTER)
    s_kpi_num = S("kn", fontSize=26, textColor=C_INK,    fontName="Helvetica-Bold", leading=30, alignment=TA_CENTER)
    s_kpi_sub = S("ks", fontSize=7.5,textColor=C_MUTED,  fontName="Helvetica",      leading=10, alignment=TA_CENTER)

    def tile(lbl, val, sub, clr, bg):
        return [Paragraph(lbl, s_kpi_lbl),
                Paragraph(f'<font color="{clr.hexval()}">{val}</font>', s_kpi_num),
                Paragraph(sub, s_kpi_sub)]

    since = (changes or {}).get("since", "today")
    ch_total = (changes or {}).get("total_mp_gained", 0) + (changes or {}).get("total_dds_completed", 0)

    kpi_row = Table(
        [[tile("TOTAL SKUs",   f"{total:,}",    f"{len(data['brands'])} brands",        C_NAVY,  C_BLIT),
          tile("COMPLETED",    f"{done:,}",     f"{pct_done}% of total",                C_GREEN, C_GLIT),
          tile("PENDING",      f"{pending:,}",  f"{round((pending/total)*100,1) if total else 0}% of total", C_AMBER, C_ALIT),
          tile("TODAY'S GAINS",f"+{ch_total}",  f"since {since}",                       C_BLUE,  C_BLIT)]],
        colWidths=[W/4]*4,
        style=TableStyle([
            ("BACKGROUND",    (0,0),(0,-1), C_BLIT),
            ("BACKGROUND",    (1,0),(1,-1), C_GLIT),
            ("BACKGROUND",    (2,0),(2,-1), C_ALIT),
            ("BACKGROUND",    (3,0),(3,-1), C_BLIT),
            ("BOX",           (0,0),(-1,-1), 1,   C_BORD),
            ("INNERGRID",     (0,0),(-1,-1), 0.5, C_BORD),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ])
    )
    story.append(kpi_row)
    story.append(Spacer(1, 5*mm))

    # ── Progress bar ──────────────────────────────────────────────────────────
    s_prog_lbl = S("pl", fontSize=8.5, textColor=C_MUTED, fontName="Helvetica", leading=11)
    s_prog_pct = S("pp", fontSize=11, textColor=C_GREEN, fontName="Helvetica-Bold", leading=13)

    prog_label = Table(
        [[Paragraph("Overall Completion", s_prog_lbl),
          Paragraph(f"{pct_done}% complete  ·  {done:,} done  ·  {pending:,} pending", s_prog_pct)]],
        colWidths=[W*0.35, W*0.65],
        style=TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("ALIGN",(1,0),(1,0),"RIGHT"),
        ])
    )
    story.append(prog_label)
    story.append(progress_bar(pct_done, W, height=8))
    story.append(Spacer(1, 6*mm))

    # ── Two-column body: Brand Scorecard (left) | Changes Today (right) ───────
    LEFT_W  = W * 0.57
    RIGHT_W = W * 0.43
    GAP     = 4*mm

    # LEFT — Brand scorecard
    s_sh = S("sh", fontSize=10, textColor=C_NAVY, fontName="Helvetica-Bold", leading=13)
    s_bc = S("bc", fontSize=7.5, textColor=C_INK,  fontName="Helvetica",      leading=10)
    s_bh = S("bh", fontSize=7.5, textColor=C_WHITE, fontName="Helvetica-Bold", leading=10)
    s_bg = S("bg", fontSize=7.5, textColor=C_GREEN, fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)
    s_ba = S("ba", fontSize=7.5, textColor=C_AMBER, fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)
    s_br = S("br2",fontSize=7.5, textColor=C_RED,   fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)

    BRAND_W = LEFT_W - 2*mm
    BAR_W   = 22*mm
    cols    = [BRAND_W - 14*mm - 13*mm - 13*mm - BAR_W - 14*mm,
               14*mm, 13*mm, 13*mm, BAR_W, 14*mm]

    b_hdr = [Paragraph(h, s_bh) for h in ["Brand","Total","Done","Pend","Progress","%"]]
    b_rows = [b_hdr]

    for b in data["brands"]:
        pc  = b["pct_complete"]
        ns_ = b["not_started"]
        if pc >= 70:
            row_bg = C_GLIT; pct_s = s_bg
        elif pc >= 30:
            row_bg = C_ALIT; pct_s = s_ba
        else:
            row_bg = C_RLIT; pct_s = s_br
        pct_str = f'<font color="{"#16a34a" if pc>=70 else "#d97706" if pc>=30 else "#dc2626"}">{pc}%</font>'
        b_rows.append([
            Paragraph(b["name"],          s_bc),
            Paragraph(str(b["total"]),    S(f"bt{b['name']}", fontSize=7.5, textColor=C_INK,  fontName="Helvetica", leading=10, alignment=TA_CENTER)),
            Paragraph(str(b["completed"]),S(f"bd{b['name']}", fontSize=7.5, textColor=C_GREEN, fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)),
            Paragraph(str(b["pending"]),  S(f"bp{b['name']}", fontSize=7.5, textColor=C_AMBER, fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)),
            mini_bar(pc, BAR_W, 5),
            Paragraph(pct_str,            S(f"bpc{b['name']}", fontSize=7.5, textColor=C_INK, fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)),
        ])

    n_b = len(b_rows)
    brand_tbl = Table(b_rows, colWidths=cols,
        style=TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),  C_NAVY),
            ("FONTSIZE",       (0,0),(-1,-1), 7.5),
            ("GRID",           (0,0),(-1,-1), 0.3, C_BORD),
            ("TOPPADDING",     (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
            ("LEFTPADDING",    (0,0),(-1,-1), 4),
            ("RIGHTPADDING",   (0,0),(-1,-1), 4),
            ("ALIGN",          (1,0),(-1,-1), "CENTER"),
            ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ] + [
            ("BACKGROUND", (0,i),(-1,i),
             C_GLIT if data["brands"][i-1]["pct_complete"] >= 70
             else C_ALIT if data["brands"][i-1]["pct_complete"] >= 30
             else C_RLIT)
            for i in range(1, n_b)
        ])
    )

    left_col = Table(
        [[Paragraph("Brand Scorecard", s_sh)],
         [Spacer(1, 3*mm)],
         [brand_tbl]],
        colWidths=[BRAND_W],
        style=TableStyle([
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("TOPPADDING",   (0,0),(-1,-1), 0),
            ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ])
    )

    # RIGHT — Changes + Donut
    R_W   = RIGHT_W - GAP
    P     = 4*mm
    CNT_W = 13*mm
    BRD_W = R_W - 2*P - CNT_W

    s_ct  = S("rct", fontSize=9,  textColor=C_INK,   fontName="Helvetica-Bold", leading=12)
    s_cbd = S("rbd", fontSize=7.5,textColor=C_MUTED, fontName="Helvetica",      leading=10)
    s_brn = S("rbn", fontSize=9,  textColor=C_INK,   fontName="Helvetica-Bold", leading=12)
    s_cg  = S("rcg", fontSize=10, textColor=C_GREEN,  fontName="Helvetica-Bold", leading=13, alignment=TA_RIGHT)
    s_ca  = S("rca", fontSize=10, textColor=C_AMBER,  fontName="Helvetica-Bold", leading=13, alignment=TA_RIGHT)
    s_cb  = S("rcb", fontSize=10, textColor=C_BLUE,   fontName="Helvetica-Bold", leading=13, alignment=TA_RIGHT)
    s_nil = S("rnil",fontSize=9,  textColor=C_LITE,   fontName="Helvetica",      leading=12)

    def _row2(lp, rp):
        return Table([[lp, rp]], colWidths=[BRD_W, CNT_W], style=_no_pad())

    def change_box(title, badge, badge_clr, desc, brand_rows, bg, border):
        rows = [[_row2(Paragraph(title, s_ct), Paragraph(badge, S(f"b{title}", fontSize=9,
                   textColor=badge_clr, fontName="Helvetica-Bold", leading=12, alignment=TA_RIGHT)))],
                [Paragraph(desc, s_cbd)]] + \
               [[_row2(l, r)] for l, r in brand_rows]
        n = len(rows)
        ts = TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("BOX",           (0,0),(-1,-1), 1.2, border),
            ("LINEBELOW",     (0,0),(-1,0),  0.5, border),
            ("LEFTPADDING",   (0,0),(-1,-1), P),
            ("RIGHTPADDING",  (0,0),(-1,-1), P),
            ("TOPPADDING",    (0,0),(-1,0),  7),
            ("BOTTOMPADDING", (0,0),(-1,0),  3),
            ("TOPPADDING",    (0,1),(-1,1),  2),
            ("BOTTOMPADDING", (0,1),(-1,1),  5),
        ])
        if n > 2:
            ts.add("TOPPADDING",    (0,2),(-1,-1), 4)
            ts.add("BOTTOMPADDING", (0,2),(-1,-1), 4)
        return Table(rows, colWidths=[R_W], style=ts)

    MAX_BRAND_ROWS = 6   # cap per change box to prevent overflow

    def _cap_rows(rows, nil_row):
        """Trim to MAX_BRAND_ROWS and append a '+N more' row if truncated."""
        if not rows:
            return [nil_row]
        extra = len(rows) - MAX_BRAND_ROWS
        if extra > 0:
            rows = rows[:MAX_BRAND_ROWS]
            rows.append((Paragraph(f"+ {extra} more brands…", s_nil), Paragraph("", s_nil)))
        return rows

    right_parts = [Paragraph("Today's Changes", s_sh), Spacer(1, 2*mm)]

    if changes:
        # DDS box
        dds_by = changes.get("dds_completed_by_brand", {})
        dds_brs = _cap_rows(
            [(Paragraph(b, s_brn), Paragraph(f"+{len(v)}", s_cg))
             for b, v in sorted(dds_by.items())],
            (Paragraph("NIL", s_nil), Paragraph("", s_nil)))
        right_parts.append(change_box(
            "DDS UPDATES",
            f"+{changes['total_dds_completed']}" if changes['total_dds_completed'] else "—",
            C_GREEN, "SKUs completed today", dds_brs, C_GLIT, C_GREEN))
        right_parts.append(Spacer(1, 2*mm))

        # MP box
        mp_by = changes.get("mp_gained_by_brand", {})
        mp_brs_raw = []
        for b, items in sorted(mp_by.items()):
            mps = sorted(set(mp for i in items for mp in i["gained"]))
            cnt = sum(len(i["gained"]) for i in items)
            mp_brs_raw.append((
                Paragraph(f'<b>{b}</b> <font size="7.5" color="{C_AMBER.hexval()}">{" · ".join(mps[:3])}{"…" if len(mps)>3 else ""}</font>',
                          S(f"mpb{b}", fontSize=9, textColor=C_INK, fontName="Helvetica", leading=13)),
                Paragraph(f"+{cnt}", s_ca)
            ))
        mp_brs = _cap_rows(mp_brs_raw, (Paragraph("NIL", s_nil), Paragraph("", s_nil)))
        right_parts.append(change_box(
            "MARKETPLACE",
            f"+{changes['total_mp_gained']}" if changes['total_mp_gained'] else "—",
            C_AMBER, "new channel links added", mp_brs, C_ALIT, C_AMBER))
        right_parts.append(Spacer(1, 2*mm))

        # SKU box
        sku_by = changes.get("new_skus_by_brand", {})
        sku_brs = _cap_rows(
            [(Paragraph(b, s_brn), Paragraph(f"+{len(v)}", s_cb))
             for b, v in sorted(sku_by.items())],
            (Paragraph("NIL", s_nil), Paragraph("", s_nil)))
        right_parts.append(change_box(
            "NEW SKUs",
            f"+{changes['total_new_skus']}" if changes['total_new_skus'] else "—",
            C_BLUE, "new products added", sku_brs, C_BLIT, C_BLUE))
        right_parts.append(Spacer(1, 2*mm))

    # Donut below changes
    right_parts.append(Table(
        [[make_donut(done, pending, ns, total)]],
        colWidths=[R_W],
        style=TableStyle([
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ])
    ))

    right_col = Table(
        [[p] for p in right_parts],
        colWidths=[R_W],
        style=TableStyle([
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("TOPPADDING",   (0,0),(-1,-1), 0),
            ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ])
    )

    body = Table(
        [[left_col, right_col]],
        colWidths=[LEFT_W, RIGHT_W],
        style=TableStyle([
            ("VALIGN",       (0,0),(-1,-1), "TOP"),
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("TOPPADDING",   (0,0),(-1,-1), 0),
            ("BOTTOMPADDING",(0,0),(-1,-1), 0),
            ("LEFTPADDING",  (1,0),(1,-1),  GAP),
        ])
    )
    story.append(body)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — Channel Distribution
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # Header bar (same style)
    hdr2 = Table(
        [[Paragraph("DDS Tracker — Channel Distribution",
                    S("hL2", fontSize=16, textColor=C_WHITE, fontName="Helvetica-Bold", leading=20)),
          Paragraph(f"SKUs live per marketplace  ·  {date_fmt}",
                    S("hR2", fontSize=9, textColor=colors.HexColor("#93c5fd"),
                      fontName="Helvetica", leading=12, alignment=TA_RIGHT))]],
        colWidths=[W*0.6, W*0.4],
        style=TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_NAVY),
            ("TOPPADDING",    (0,0),(-1,-1), 14),
            ("BOTTOMPADDING", (0,0),(-1,-1), 14),
            ("LEFTPADDING",   (0,0),(-1,-1), 18),
            ("RIGHTPADDING",  (0,0),(-1,-1), 18),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ])
    )
    story.append(Table([[hdr2]], colWidths=[W],
        style=TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                          ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)])))
    story.append(Spacer(1, 8*mm))

    all_mp       = data["all_marketplaces"]
    amazon_total = data["mp_totals"].get("Amazon", 1)
    s_mh = lambda mp: S(f"mh{mp}", fontSize=6.5, textColor=C_WHITE,
                         fontName="Helvetica-Bold", leading=8, alignment=TA_CENTER)
    s_cell = S("cell", fontSize=7.5, textColor=C_INK, fontName="Helvetica", leading=10)

    mp_hdr = ([Paragraph("Brand", S("mbh", fontSize=8, textColor=C_WHITE,
                                     fontName="Helvetica-Bold", leading=10))] +
               [Paragraph(mp.replace(" ","\n"), s_mh(mp)) for mp in all_mp] +
               [Paragraph("Live\nMPs", S("mh2", fontSize=6.5, textColor=C_WHITE,
                                          fontName="Helvetica-Bold", leading=8, alignment=TA_CENTER))])

    mp_rows = [mp_hdr]
    for b in data["brands"]:
        row = [Paragraph(b["name"], S(f"bn{b['name'][:4]}", fontSize=7.5, textColor=C_INK,
                                       fontName="Helvetica-Bold", leading=9))]
        for mp in all_mp:
            cnt = b["mp_sku_counts"].get(mp, 0)
            row.append(Paragraph(str(cnt) if cnt else "—",
                                 S(f"cv{mp[:3]}{b['name'][:3]}", fontSize=8,
                                   textColor=C_GREEN if cnt else C_LITE,
                                   fontName="Helvetica-Bold" if cnt else "Helvetica",
                                   leading=10, alignment=TA_CENTER)))
        row.append(Paragraph(str(b["marketplace_count"]),
                             S(f"mc{b['name'][:3]}", fontSize=8, textColor=C_BLUE,
                               fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)))
        mp_rows.append(row)

    totals = [Paragraph("TOTAL", S("tt", fontSize=7.5, textColor=C_MUTED,
                                    fontName="Helvetica-Bold", leading=9))]
    for mp in all_mp:
        cnt = data["mp_totals"].get(mp, 0)
        totals.append(Paragraph(str(cnt) if cnt else "—",
                                S(f"tr{mp[:4]}", fontSize=8, textColor=C_INK,
                                  fontName="Helvetica-Bold", leading=10, alignment=TA_CENTER)))
    totals.append(Paragraph("", s_cell))
    mp_rows.append(totals)

    pct_r = [Paragraph("% of Amazon", S("pa", fontSize=6.5, textColor=C_MUTED,
                                         fontName="Helvetica", leading=8))]
    for mp in all_mp:
        cnt = data["mp_totals"].get(mp, 0)
        if mp == "Amazon":
            pct_r.append(Paragraph("100%", S("par", fontSize=7.5, textColor=C_BLUE,
                                              fontName="Helvetica-Bold", leading=9, alignment=TA_CENTER)))
        elif cnt:
            pv  = round((cnt / amazon_total) * 100, 1)
            col = "#16a34a" if pv >= 50 else "#2563eb" if pv >= 20 else "#d97706" if pv >= 10 else "#dc2626"
            pct_r.append(Paragraph(f'<font color="{col}">{pv}%</font>',
                                   S(f"p2{mp[:4]}", fontSize=7.5, textColor=C_INK,
                                     fontName="Helvetica-Bold", leading=9, alignment=TA_CENTER)))
        else:
            pct_r.append(Paragraph("—", S(f"p3{mp[:4]}", fontSize=7.5, textColor=C_LITE,
                                           fontName="Helvetica", leading=9, alignment=TA_CENTER)))
    pct_r.append(Paragraph("", s_cell))
    mp_rows.append(pct_r)

    bcw  = 32*mm
    mpcw = (W - bcw - 10*mm) / len(all_mp)
    n    = len(mp_rows)

    story.append(Table(mp_rows, colWidths=[bcw] + [mpcw]*len(all_mp) + [10*mm],
        style=TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),   C_NAVY),
            ("ROWBACKGROUNDS",(0,1),(-1,n-3), [C_WHITE, C_SURF]),
            ("BACKGROUND",    (0,n-2),(-1,n-2), C_SURF),
            ("BACKGROUND",    (0,n-1),(-1,n-1), colors.HexColor("#eff6ff")),
            ("GRID",          (0,0),(-1,-1),  0.3, C_BORD),
            ("TOPPADDING",    (0,0),(-1,-1),  4),
            ("BOTTOMPADDING", (0,0),(-1,-1),  4),
            ("VALIGN",        (0,0),(-1,-1),  "MIDDLE"),
            ("LINEABOVE",     (0,n-2),(-1,n-2), 1, C_BLUE),
        ])))

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Marketplace Reach vs Amazon (% of Amazon SKU count)",
                            S("h2b", fontSize=11, textColor=C_INK,
                               fontName="Helvetica-Bold", leading=15)))
    story.append(Spacer(1, 3*mm))
    story.append(make_bar(data["mp_totals"], all_mp))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    print(f"PDF saved: {build_pdf()}")
