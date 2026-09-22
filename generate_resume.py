#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大学生成长档案库 - 简历与作品集生成器
功能：
  1. 从档案数据生成 Markdown 格式简历
  2. 生成 HTML 作品集（经历时间线 + 详情页）
  3. 支持按实习/岗位方向筛选经历（基于技能标签匹配）
无需外部依赖
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# --- 配置 ------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

EXPERIENCES_FILE = DATA_DIR / "experiences.json"

CATEGORY_NAMES = {
    "academic": "学业成绩",
    "competition": "学科竞赛",
    "research": "科研创新",
    "social_practice": "社会实践",
    "leadership": "学生工作",
    "talent": "文体活动",
    "honor": "荣誉称号",
    "certificate": "技能证书"
}

CATEGORY_EMOJI = {
    "academic": "📚",
    "competition": "🏆",
    "research": "🔬",
    "social_practice": "🌍",
    "leadership": "🎯",
    "talent": "🎨",
    "honor": "⭐",
    "certificate": "📜"
}

CATEGORY_COLORS = {
    "academic": "#2563EB", "competition": "#EA580C", "research": "#7C3AED",
    "social_practice": "#16A34A", "leadership": "#0891B2", "talent": "#DB2777",
    "honor": "#CA8A04", "certificate": "#475569"
}


# --- 工具函数 --------------------------------------------------------------

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_date(d: str) -> str:
    """YYYY-MM-DD -> YYYY.MM"""
    try:
        return d.replace("-", ".")[:7]
    except Exception:
        return d


# --- 经历筛选 --------------------------------------------------------------

def score_relevance(exp: dict, target_skills: list) -> float:
    if not target_skills:
        return 1.0
    raw_text = f"{exp.get('name', '')} {exp.get('description', '')} " \
               f"{' '.join(exp.get('skills_gained', []))} " \
               f"{exp.get('role', '')} {exp.get('achievement', '')}"
    raw_text = raw_text.lower()
    matched = sum(1 for s in target_skills if s.lower() in raw_text)
    return 0.3 + 0.7 * (matched / max(len(target_skills), 1))


def filter_experiences(exps, target_skills=None, categories=None, min_relevance=0.0):
    result = []
    for e in exps:
        if categories and e.get("category", "") not in categories:
            continue
        rel = score_relevance(e, target_skills or [])
        if rel < min_relevance:
            continue
        result.append({**e, "_relevance": round(rel, 2)})
    result.sort(key=lambda x: (-x["_relevance"], x.get("end_date", ""), x.get("start_date", "")), reverse=False)
    return result


# --- Markdown 简历 ---------------------------------------------------------

def generate_resume(target_skills=None, categories=None, output_name=None):
    experiences = load_json(EXPERIENCES_FILE)
    exps_all = experiences.get("experiences", [])
    if not exps_all:
        print("⚠ 暂无经历记录，无法生成简历。请先通过 index.html 或 core.py add 添加经历。")
        return None

    student = experiences.get("student_info", {})
    name = student.get("name", "XXX")
    exps = filter_experiences(exps_all, target_skills, categories, min_relevance=0.25)
    if not exps:
        exps = exps_all

    md = []
    md.append(f"# {name}")
    md.append("")

    info_lines = []
    if student.get("phone"):
        info_lines.append(f"📞 {student['phone']}")
    if student.get("email"):
        info_lines.append(f"📧 {student['email']}")
    if student.get("github"):
        info_lines.append(f"🔗 GitHub: {student['github']}")
    if student.get("blog"):
        info_lines.append(f"📝 博客: {student['blog']}")
    if student.get("major"):
        info_lines.append(f"🎓 {student.get('college', '')} · {student['major']} · {student.get('grade', '')}")
    if info_lines:
        md.append(" | ".join(info_lines))
        md.append("")
    md.append("---")
    md.append("")

    academic_items = [e for e in exps_all if e.get("category") == "academic" and e.get("achievement")]
    if academic_items or student.get("college"):
        md.append("## 🎓 教育背景")
        md.append("")
        md.append(f"- **{student.get('college', 'XX大学')}** · {student.get('major', 'XX专业')} · {student.get('grade', '20XX级')}")
        for item in academic_items[:3]:
            md.append(f"  - {item['name']}: {item.get('achievement', '')}")
        md.append("")

    skill_counter = {}
    for e in exps_all:
        for s in e.get("skills_gained", []):
            skill_counter[s] = skill_counter.get(s, 0) + 1
    if skill_counter:
        top_skills = sorted(skill_counter.items(), key=lambda kv: -kv[1])[:12]
        md.append("## 💡 核心技能")
        md.append("")
        md.append(", ".join([f"**{s}** ({c}次实践)" for s, c in top_skills]))
        md.append("")

    md.append("## 📂 项目与竞赛经历")
    md.append("")
    if target_skills:
        md.append("以下经历按与目标岗位的相关度排序：")
    else:
        md.append("以下经历按时间倒序排列：")
    md.append("")

    for i, e in enumerate(exps, 1):
        cat_emoji = CATEGORY_EMOJI.get(e.get("category"), "📌")
        date_str = f"{fmt_date(e.get('start_date', ''))} - {fmt_date(e.get('end_date', ''))}"
        if date_str.strip() == "-":
            date_str = ""

        title_line = f"{cat_emoji} **{e['name']}**"
        if e.get("achievement"):
            title_line += f" · {e['achievement']}"
        if date_str:
            title_line += f"  <span style='color:#999;font-size:13px;'>{date_str}</span>"
        md.append(title_line)

        if e.get("role"):
            md.append(f"- **角色**：{e['role']}")
        if e.get("description"):
            for line in e["description"].split("\n"):
                line = line.strip()
                if line:
                    md.append(f"- {line}")
        if e.get("skills_gained"):
            md.append(f"- **技能**：{' · '.join(e['skills_gained'])}")
        if target_skills and e.get("_relevance"):
            md.append(f"- <span style='color:#999;font-size:12px;'>岗位匹配度: {e['_relevance']}</span>")
        md.append("")

    honors = [e for e in exps_all if e.get("category") == "honor" or e.get("achievement")]
    if honors:
        md.append("## 🏅 荣誉与奖项")
        md.append("")
        for h in sorted(honors, key=lambda x: x.get("start_date", ""), reverse=True)[:8]:
            date = fmt_date(h.get("start_date", ""))
            ach = h.get("achievement", "")
            md.append(f"- **{h['name']}** · {ach}  ({date})")
        md.append("")

    md.append("---")
    md.append("")
    md.append(f"*本简历由「大学生成长档案库」自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    if target_skills:
        md.append(f"*面向岗位关键词：{', '.join(target_skills)}*")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = output_name or f"简历_{name}_{timestamp}.md"
    out_path = OUTPUT_DIR / "简历" / fname
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"✓ Markdown 简历已生成: {out_path}")
    print(f"  共筛选 {len(exps)} 条经历")
    if target_skills:
        print(f"  岗位方向: {', '.join(target_skills)}")
    return out_path


# --- HTML 作品集 -----------------------------------------------------------

def generate_portfolio(categories=None):
    experiences = load_json(EXPERIENCES_FILE)
    exps_all = experiences.get("experiences", [])
    if not exps_all:
        print("⚠ 暂无经历记录，无法生成作品集。")
        return None

    student = experiences.get("student_info", {})
    name = student.get("name", "同学")

    if categories:
        exps = [e for e in exps_all if e.get("category") in categories]
    else:
        exps = exps_all

    exps.sort(key=lambda x: x.get("end_date", "") or x.get("start_date", ""), reverse=True)

    skill_counter = {}
    for e in exps_all:
        for s in e.get("skills_gained", []):
            skill_counter[s] = skill_counter.get(s, 0) + 1
    top_skills = sorted(skill_counter.items(), key=lambda kv: -kv[1])[:15]

    # 构建卡片HTML
    cards_html = []
    for e in exps:
        cat = e.get("category", "other")
        cat_name = CATEGORY_NAMES.get(cat, cat)
        emoji = CATEGORY_EMOJI.get(cat, "📌")
        color = CATEGORY_COLORS.get(cat, "#2563EB")

        date_str = ""
        if e.get("start_date"):
            date_str = fmt_date(e["start_date"])
            if e.get("end_date"):
                date_str += f" - {fmt_date(e['end_date'])}"

        skills_tags = ""
        if e.get("skills_gained"):
            skills_tags = "".join(f'<span class="skill-tag">{s}</span>' for s in e["skills_gained"])

        ach = f'<span class="achievement">🏆 {e["achievement"]}</span>' if e.get("achievement") else ""
        role = f'<span class="role">👤 {e["role"]}</span>' if e.get("role") else ""
        desc = e.get("description", "").replace("\n", "<br>")

        mats_html = ""
        if e.get("materials"):
            mats = "<br>".join(e["materials"])
            mats_html = f'<div class="materials"><strong>📎 证明材料：</strong><div class="material-paths">{mats}</div></div>'

        card = f"""<div class="portfolio-card" data-category="{cat}">
  <div class="card-header" style="border-left-color:{color}">
    <span class="card-emoji">{emoji}</span>
    <div class="card-meta">
      <span class="card-category" style="color:{color}">{cat_name}</span>
      <span class="card-date">{date_str}</span>
    </div>
  </div>
  <h3 class="card-title">{e['name']}</h3>
  <div class="card-badges">{ach}{role}</div>
  <div class="card-desc">{desc}</div>
  <div class="card-skills">{skills_tags}</div>
  {mats_html}
</div>"""
        cards_html.append(card)

    # 时间线HTML
    timeline_items = []
    for e in exps[:20]:
        cat = e.get("category", "")
        dot_color = CATEGORY_COLORS.get(cat, "#2563EB")
        cat_name = CATEGORY_NAMES.get(cat, cat)
        ach_html = f'<div style="margin-top:8px;"><span class="achievement">🏆 {e["achievement"]}</span></div>' if e.get("achievement") else ""
        desc_html = f'<div style="margin-top:6px;font-size:13px;color:#64748b;">{e["description"].replace(chr(10), "<br>")}</div>' if e.get("description") else ""

        item = f"""    <div class="timeline-item" data-category="{cat}">
      <div class="timeline-dot" style="background: {dot_color}"></div>
      <div class="timeline-content">
        <div class="timeline-title">{e["name"]}</div>
        <div class="timeline-date">{fmt_date(e.get('start_date',''))} - {fmt_date(e.get('end_date',''))} · {cat_name}</div>
        {ach_html}
        {desc_html}
      </div>
    </div>"""
        timeline_items.append(item)

    # 概览卡片
    skills_overview_html = ""
    for s, c in top_skills:
        skills_overview_html += f'<div class="overview-skill"><span class="overview-skill-name">{s}</span><span class="overview-skill-count">{c}次</span></div>'

    # 分类过滤按钮
    cat_filters_list = ['<button class="filter-btn active" data-cat="all">全部</button>']
    for cid, cname in CATEGORY_NAMES.items():
        has_any = any(e.get("category") == cid for e in exps)
        if has_any:
            cat_filters_list.append(f'<button class="filter-btn" data-cat="{cid}">{CATEGORY_EMOJI[cid]} {cname}</button>')

    # 数据准备完成，构建HTML
    cards_str = "\n".join(cards_html)
    timeline_str = "\n".join(timeline_items)
    cat_filters_str = " ".join(cat_filters_list)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} - 个人作品集</title>
<style>
:root {{ --primary: #2563EB; --bg: #f8fafc; --card: #ffffff; --text: #1e293b; --text2: #64748b; --border: #e2e8f0; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height:1.6; }}
.header {{ background: linear-gradient(135deg, #2563EB 0%, #1e40af 100%); color: white; padding: 60px 40px; text-align: center; }}
.header h1 {{ font-size: 42px; font-weight: 700; margin-bottom: 10px; }}
.header p {{ font-size: 18px; opacity: 0.9; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}

.overview {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 40px; }}
.overview-card {{ background: var(--card); padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.overview-card h3 {{ font-size: 16px; color: var(--text2); margin-bottom: 16px; text-transform: uppercase; letter-spacing: 1px; }}
.overview-stat {{ font-size: 36px; font-weight: 700; color: var(--primary); }}
.overview-stat-label {{ font-size: 14px; color: var(--text2); margin-top: 4px; }}
.overview-skill {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; }}
.overview-skill-name {{ font-weight: 500; }}
.overview-skill-count {{ color: var(--text2); font-size: 13px; }}

.filters {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 30px; justify-content: center; }}
.filter-btn {{ padding: 8px 18px; border-radius: 20px; border: 1px solid var(--border); background: var(--card); cursor: pointer; font-size: 14px; transition: all 0.2s; }}
.filter-btn:hover {{ background: #eff6ff; border-color: var(--primary); }}
.filter-btn.active {{ background: var(--primary); color: white; border-color: var(--primary); }}

.portfolio-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 24px; }}
.portfolio-card {{ background: var(--card); border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; }}
.portfolio-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }}
.card-header {{ display: flex; align-items: center; gap: 12px; padding: 16px 20px; border-left: 4px solid; background: #f8fafc; }}
.card-emoji {{ font-size: 24px; }}
.card-meta {{ display: flex; flex-direction: column; }}
.card-category {{ font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
.card-date {{ font-size: 12px; color: var(--text2); margin-top: 2px; }}
.card-title {{ font-size: 18px; font-weight: 700; padding: 16px 20px 0; }}
.card-badges {{ display: flex; gap: 8px; flex-wrap: wrap; padding: 10px 20px; }}
.achievement {{ background: #dcfce7; color: #16A34A; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
.role {{ background: #dbeafe; color: #2563EB; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
.card-desc {{ padding: 0 20px 16px; font-size: 14px; color: var(--text2); line-height: 1.7; }}
.card-skills {{ padding: 0 20px 16px; display: flex; flex-wrap: wrap; gap: 6px; }}
.skill-tag {{ background: var(--bg); color: var(--text2); padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
.materials {{ padding: 12px 20px 16px; background: #fafafa; border-top: 1px solid var(--border); }}
.materials strong {{ font-size: 13px; color: var(--text2); }}
.material-paths {{ font-size: 12px; color: #94a3b8; margin-top: 6px; word-break: break-all; }}

.timeline {{ position: relative; padding-left: 30px; max-width: 800px; margin: 0 auto; }}
.timeline::before {{ content:''; position:absolute; left:10px; top:0; bottom:0; width:2px; background: var(--border); }}
.timeline-item {{ position: relative; padding-bottom: 30px; }}
.timeline-dot {{ position: absolute; left: -30px; top: 4px; width: 16px; height: 16px; border-radius: 50%; background: var(--primary); border: 3px solid var(--card); box-shadow: 0 0 0 2px var(--border); }}
.timeline-content {{ background: var(--card); padding: 16px 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.timeline-title {{ font-weight: 700; font-size: 16px; }}
.timeline-date {{ font-size: 12px; color: var(--text2); margin-top: 4px; }}

.footer {{ text-align: center; padding: 40px; color: var(--text2); font-size: 13px; }}

@media (max-width: 768px) {{
  .header {{ padding: 40px 20px; }}
  .header h1 {{ font-size: 28px; }}
  .portfolio-grid {{ grid-template-columns: 1fr; }}
  .filters {{ justify-content: flex-start; overflow-x: auto; padding-bottom: 10px; }}
}}
@media print {{
  .filters {{ display: none; }}
  .portfolio-card {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>

<div class="header">
  <h1>{name} 的作品集</h1>
  <p>{student.get('college', '')} · {student.get('major', '')} · 大学生成长档案精选</p>
</div>

<div class="container">
  <div class="overview">
    <div class="overview-card">
      <h3>经历总数</h3>
      <div class="overview-stat">{len(exps_all)}</div>
      <div class="overview-stat-label">累计记录的成长经历</div>
    </div>
    <div class="overview-card">
      <h3>能力标签</h3>
      <div class="overview-stat">{len(skill_counter)}</div>
      <div class="overview-stat-label">已识别的核心技能</div>
    </div>
    <div class="overview-card">
      <h3>能力分布 TOP10</h3>
      {skills_overview_html}
    </div>
  </div>

  <div class="filters">
    {cat_filters_str}
  </div>

  <h2 style="text-align:center; margin-bottom:30px; font-size:24px;">📅 经历时间线</h2>
  <div class="timeline">
{timeline_str}
  </div>

  <h2 style="text-align:center; margin: 50px 0 30px; font-size:24px;">🗂️ 经历详情</h2>
  <div class="portfolio-grid">
{cards_str}
  </div>
</div>

<div class="footer">
  <p>本作品集由「大学生成长档案库」自动生成 · {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
</div>

<script>
  document.querySelectorAll('.filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const cat = btn.dataset.cat;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.portfolio-card, .timeline-item').forEach(el => {{
        if (cat === 'all' || el.dataset.category === cat) {{
          el.style.display = '';
        }} else {{
          el.style.display = 'none';
        }}
      }});
    }});
  }});
</script>

</body>
</html>"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"作品集_{name}_{timestamp}.html"
    out_path = OUTPUT_DIR / "作品集" / fname
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✓ HTML 作品集已生成: {out_path}")
    print(f"  共 {len(exps)} 条经历")
    return out_path


# --- CLI 入口 --------------------------------------------------------------

def print_help():
    print("""
大学生成长档案库 - 简历与作品集生成器

用法：
  python generate_resume.py resume [技能关键词 ...] [--cat 类别1,类别2 ...]
  python generate_resume.py portfolio [--cat 类别1,类别2 ...]

示例：
  python generate_resume.py resume Python 数据分析 机器学习
  python generate_resume.py resume JavaScript React 前端
  python generate_resume.py portfolio --cat competition,research
  python generate_resume.py portfolio
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_help()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]
    categories = None
    target_skills = []

    i = 0
    while i < len(args):
        if args[i] == "--cat" and i + 1 < len(args):
            categories = [c.strip() for c in args[i + 1].split(",") if c.strip()]
            i += 2
        else:
            target_skills.append(args[i])
            i += 1

    if cmd == "resume":
        generate_resume(
            target_skills=target_skills or None,
            categories=categories
        )
    elif cmd == "portfolio":
        generate_portfolio(categories=categories)
    else:
        print(f"未知命令: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
