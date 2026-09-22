#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大学生成长档案库 - 奖学金答辩幻灯片生成器
功能：从档案数据生成奖学金答辩HTML幻灯片（可在浏览器中演示）
输出：单文件HTML，包含完整的幻灯片导航和排版
无需外部依赖
"""

import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output" / "奖学金PPT"

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

CATEGORY_COLORS = {
    "academic": "#2563EB",
    "competition": "#EA580C",
    "research": "#7C3AED",
    "social_practice": "#16A34A",
    "leadership": "#0891B2",
    "talent": "#DB2777",
    "honor": "#CA8A04",
    "certificate": "#475569"
}

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_ppt_html():
    """生成奖学金答辩HTML幻灯片"""
    experiences = load_json(EXPERIENCES_FILE)
    
    if not experiences.get("experiences"):
        print("⚠ 暂无经历记录，无法生成幻灯片")
        return None
    
    student = experiences.get("student_info", {})
    exps = experiences.get("experiences", [])
    
    # 按类型分组
    categorized = {}
    for exp in exps:
        cat = exp.get("category", "other")
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(exp)
    
    # 筛选高光经历
    highlight_exps = sorted(
        [e for e in exps if e.get("achievement")],
        key=lambda x: x.get("start_date", ""),
        reverse=True
    )
    
    # 统计能力
    all_skills = {}
    for exp in exps:
        for skill in exp.get("skills_gained", []):
            all_skills[skill] = all_skills.get(skill, 0) + 1
    sorted_skills = sorted(all_skills.items(), key=lambda x: -x[1])[:15]
    
    # 构建幻灯片内容
    slides = []
    
    # Slide 1: 封面
    slides.append({
        "type": "title",
        "title": f"{student.get('name', '同学')} 奖学金答辩",
        "subtitle": f"{student.get('college', '')} · {student.get('major', '')} · {student.get('grade', '')}",
        "content": ""
    })
    
    # Slide 2: 个人简介
    intro_content = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:20px;">
      <div class="info-card">
        <h3>基本信息</h3>
        <p><strong>姓名：</strong>{student.get('name', '未填写')}</p>
        <p><strong>学号：</strong>{student.get('student_id', '未填写')}</p>
        <p><strong>学院：</strong>{student.get('college', '未填写')}</p>
        <p><strong>专业：</strong>{student.get('major', '未填写')}</p>
      </div>
      <div class="info-card">
        <h3>成长概览</h3>
        <p>共记录 <strong>{len(exps)}</strong> 段经历</p>
        <p>涵盖 <strong>{len(categorized)}</strong> 个类别</p>
        <p>积累 <strong>{len(all_skills)}</strong> 项能力</p>
      </div>
    </div>
    """
    category_stats = ""
    for cat, items in sorted(categorized.items(), key=lambda x: -len(x[1])):
        cat_name = CATEGORY_NAMES.get(cat, cat)
        achievements = [i.get("achievement", "") for i in items if i.get("achievement")]
        ach_text = f"（{achievements[0]}等）" if achievements else ""
        category_stats += f'<div class="stat-item"><span class="stat-dot" style="background:{CATEGORY_COLORS.get(cat, '#2563EB')}"></span>{cat_name}：{len(items)}项 {ach_text}</div>'
    
    intro_content += f'<div class="category-stats">{category_stats}</div>'
    
    slides.append({
        "type": "content",
        "title": "个人简介与成长概览",
        "content": intro_content
    })
    
    # Slide 3: 核心亮点
    if highlight_exps:
        highlights = '<div class="highlight-list">'
        for i, exp in enumerate(highlight_exps[:5], 1):
            cat = CATEGORY_NAMES.get(exp.get("category", ""), exp.get("category", ""))
            color = CATEGORY_COLORS.get(exp.get("category", ""), "#2563EB")
            highlights += f'''
            <div class="highlight-item" style="border-left-color:{color}">
              <div class="highlight-number">{i}</div>
              <div class="highlight-content">
                <div class="highlight-tag" style="background:{color}20;color:{color}">{cat}</div>
                <h4>{exp.get('name', '')}</h4>
                <p>{exp.get('achievement', '')} {f"（{exp.get('role', '')}）" if exp.get('role') else ""}</p>
              </div>
            </div>
            '''
        highlights += '</div>'
        
        slides.append({
            "type": "content",
            "title": "核心亮点",
            "content": f'<p class="slide-desc">以下是我大学期间最具代表性的成长经历：</p>{highlights}'
        })
    
    # Category slides
    for cat_id, cat_exps in sorted(categorized.items(), key=lambda x: -len(x[1])):
        cat_name = CATEGORY_NAMES.get(cat_id, cat_id)
        color = CATEGORY_COLORS.get(cat_id, "#2563EB")
        
        # Category overview
        overview = f'<div class="category-header" style="background:{color}15;border-color:{color}30;">'
        overview += f'<h3 style="color:{color}">{cat_name}</h3>'
        overview += f'<p>共 {len(cat_exps)} 项经历</p></div>'
        
        exp_list = '<div class="exp-grid">'
        for exp in sorted(cat_exps, key=lambda x: x.get("start_date", ""), reverse=True):
            exp_list += f'''
            <div class="exp-card">
              <h4>{exp.get('name', '')}</h4>
              <p class="exp-date">{exp.get('start_date', '')} ~ {exp.get('end_date', '至今')}</p>
              {f'<p class="exp-achievement">🏆 {exp.get("achievement", "")}</p>' if exp.get('achievement') else ''}
              {f'<p class="exp-role">👤 {exp.get("role", "")}</p>' if exp.get('role') else ''}
              {f'<p class="exp-desc">{exp.get("description", "")}</p>' if exp.get('description') else ''}
            </div>
            '''
        exp_list += '</div>'
        
        slides.append({
            "type": "content",
            "title": f"{cat_name} ({len(cat_exps)}项)",
            "content": overview + exp_list
        })
        
        # Detail slides for top experiences
        top_exps = sorted(
            [e for e in cat_exps if e.get("achievement") or e.get("description")],
            key=lambda x: x.get("start_date", ""),
            reverse=True
        )[:2]
        
        for exp in top_exps:
            detail = f'''
            <div class="detail-card" style="border-color:{color}40;">
              <div class="detail-header">
                <span class="detail-tag" style="background:{color};color:white">{cat_name}</span>
                <h3>{exp.get('name', '')}</h3>
              </div>
              <div class="detail-body">
                {f'<div class="detail-row"><strong>角色：</strong>{exp.get("role", "")}</div>' if exp.get('role') else ''}
                {f'<div class="detail-row"><strong>成果：</strong>{exp.get("achievement", "")}</div>' if exp.get('achievement') else ''}
                {f'<div class="detail-row"><strong>时间：</strong>{exp.get("start_date", "")} ~ {exp.get("end_date", "至今")}</div>' if exp.get('start_date') else ''}
                {f'<div class="detail-section"><h4>具体工作</h4><p>{exp.get("description", "")}</p></div>' if exp.get('description') else ''}
                {f'<div class="detail-section"><h4>能力提升</h4><div class="skill-tags">{"".join([f"<span class=\"skill-tag\">{s}</span>" for s in exp.get("skills_gained", [])])}</div></div>' if exp.get('skills_gained') else ''}
              </div>
            </div>
            '''
            
            slides.append({
                "type": "content",
                "title": exp.get('name', '经历详情'),
                "content": detail
            })
    
    # Skills slide
    if sorted_skills:
        max_count = sorted_skills[0][1]
        skills_html = '<div class="skills-chart">'
        for skill, count in sorted_skills:
            pct = (count / max_count) * 100
            skills_html += f'''
            <div class="skill-bar">
              <span class="skill-name">{skill}</span>
              <div class="skill-track">
                <div class="skill-fill" style="width:{pct}%"><span class="skill-count">{count}次</span></div>
              </div>
            </div>
            '''
        skills_html += '</div>'
        
        slides.append({
            "type": "content",
            "title": "能力成长图谱",
            "content": f'<p class="slide-desc">通过各类实践经历，积累了以下核心能力：</p>{skills_html}'
        })
    
    # Future outlook
    slides.append({
        "type": "content",
        "title": "未来展望",
        "content": '''
        <div class="future-grid">
          <div class="future-item"><div class="future-icon">📚</div><h4>深化学习</h4><p>持续深化专业学习，提升学术素养</p></div>
          <div class="future-item"><div class="future-icon">🔬</div><h4>科研创新</h4><p>积极参与科研项目，培养创新能力</p></div>
          <div class="future-item"><div class="future-icon">🤝</div><h4>社会实践</h4><p>投身社会实践，服务社会发展</p></div>
          <div class="future-item"><div class="future-icon">🌟</div><h4>全面发展</h4><p>全面发展个人素质，成长为复合型人才</p></div>
        </div>
        <p class="thanks">感谢评审老师的聆听！</p>
        '''
    })
    
    # End slide
    slides.append({
        "type": "title",
        "title": "感谢聆听",
        "subtitle": "敬请批评指正",
        "content": ""
    })
    
    # Generate HTML
    html = generate_html_template(slides, student)
    
    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"奖学金答辩_{student.get('name', '未命名')}_{timestamp}.html"
    output_path = OUTPUT_DIR / filename
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✓ 奖学金答辩幻灯片已生成: {output_path}")
    print(f"  共 {len(slides)} 页幻灯片")
    print(f"  涵盖 {len(categorized)} 个类别")
    print(f"  可直接用浏览器打开进行演示")
    
    return output_path

def generate_html_template(slides: list, student: dict) -> str:
    """生成完整的HTML幻灯片模板"""
    
    slides_html = ""
    for i, slide in enumerate(slides):
        if slide["type"] == "title":
            slides_html += f'''
            <div class="slide title-slide" id="slide-{i}">
              <div class="title-content">
                <h1>{slide["title"]}</h1>
                <p class="subtitle">{slide["subtitle"]}</p>
              </div>
            </div>
            '''
        else:
            slides_html += f'''
            <div class="slide content-slide" id="slide-{i}">
              <div class="slide-header">
                <h2>{slide["title"]}</h2>
              </div>
              <div class="slide-body">
                {slide["content"]}
              </div>
            </div>
            '''
    
    # Navigation dots
    nav_dots = "".join([f'<div class="nav-dot{" active" if i == 0 else ""}" data-slide="{i}"></div>' for i in range(len(slides))])
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{student.get('name', '同学')} - 奖学金答辩</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #1a1a2e;
    color: #1e293b;
    overflow: hidden;
  }}
  .presentation {{
    width: 100vw;
    height: 100vh;
    position: relative;
  }}
  .slide {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: 40px 60px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.4s ease;
    overflow-y: auto;
  }}
  .slide.active {{
    opacity: 1;
    pointer-events: auto;
  }}
  
  /* Title Slide */
  .title-slide {{
    background: linear-gradient(135deg, #2563EB 0%, #1d4ed8 50%, #1e40af 100%);
    justify-content: center;
    align-items: center;
    text-align: center;
    color: white;
  }}
  .title-content h1 {{
    font-size: 48px;
    font-weight: 700;
    margin-bottom: 20px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
  }}
  .title-content .subtitle {{
    font-size: 24px;
    opacity: 0.9;
  }}
  
  /* Content Slide */
  .content-slide {{
    background: #f8fafc;
  }}
  .slide-header {{
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 3px solid #2563EB;
  }}
  .slide-header h2 {{
    font-size: 32px;
    color: #1e293b;
    font-weight: 700;
  }}
  .slide-desc {{
    font-size: 16px;
    color: #64748b;
    margin-bottom: 20px;
  }}
  
  /* Info Cards */
  .info-card {{
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }}
  .info-card h3 {{
    font-size: 18px;
    margin-bottom: 12px;
    color: #2563EB;
  }}
  .info-card p {{
    font-size: 15px;
    margin: 6px 0;
    color: #475569;
  }}
  
  /* Category Stats */
  .category-stats {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 20px;
  }}
  .stat-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: white;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  }}
  .stat-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  
  /* Highlights */
  .highlight-list {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  .highlight-item {{
    display: flex;
    align-items: flex-start;
    gap: 16px;
    background: white;
    padding: 16px 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid;
  }}
  .highlight-number {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #2563EB;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 16px;
    flex-shrink: 0;
  }}
  .highlight-content h4 {{
    font-size: 18px;
    margin-bottom: 4px;
  }}
  .highlight-content p {{
    font-size: 14px;
    color: #64748b;
  }}
  .highlight-tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 6px;
  }}
  
  /* Exp Grid */
  .exp-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    margin-top: 16px;
  }}
  .exp-card {{
    background: white;
    padding: 16px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }}
  .exp-card h4 {{
    font-size: 16px;
    margin-bottom: 8px;
  }}
  .exp-card p {{
    font-size: 13px;
    color: #64748b;
    margin: 4px 0;
  }}
  .exp-achievement {{
    color: #16A34A !important;
    font-weight: 600;
  }}
  .exp-role {{
    color: #2563EB !important;
  }}
  
  /* Detail Card */
  .detail-card {{
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    overflow: hidden;
    border-top: 4px solid;
  }}
  .detail-header {{
    padding: 20px 24px;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
  }}
  .detail-tag {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 8px;
  }}
  .detail-header h3 {{
    font-size: 24px;
  }}
  .detail-body {{
    padding: 20px 24px;
  }}
  .detail-row {{
    font-size: 15px;
    padding: 8px 0;
    border-bottom: 1px solid #f1f5f9;
  }}
  .detail-section {{
    margin-top: 16px;
  }}
  .detail-section h4 {{
    font-size: 16px;
    color: #2563EB;
    margin-bottom: 8px;
  }}
  .detail-section p {{
    font-size: 14px;
    line-height: 1.7;
    color: #475569;
  }}
  .skill-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .skill-tag {{
    background: #dbeafe;
    color: #2563EB;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
  }}
  
  /* Skills Chart */
  .skills-chart {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-width: 800px;
  }}
  .skill-bar {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  .skill-name {{
    width: 100px;
    font-size: 14px;
    text-align: right;
    font-weight: 500;
    flex-shrink: 0;
  }}
  .skill-track {{
    flex: 1;
    height: 28px;
    background: #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
  }}
  .skill-fill {{
    height: 100%;
    background: linear-gradient(90deg, #2563EB, #3b82f6);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 12px;
    transition: width 0.5s ease;
    min-width: 40px;
  }}
  .skill-count {{
    color: white;
    font-size: 12px;
    font-weight: 600;
  }}
  
  /* Future Grid */
  .future-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
    margin-top: 20px;
  }}
  .future-item {{
    background: white;
    padding: 24px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }}
  .future-icon {{
    font-size: 36px;
    margin-bottom: 12px;
  }}
  .future-item h4 {{
    font-size: 18px;
    margin-bottom: 8px;
    color: #2563EB;
  }}
  .future-item p {{
    font-size: 14px;
    color: #64748b;
  }}
  .thanks {{
    text-align: center;
    font-size: 20px;
    color: #2563EB;
    margin-top: 40px;
    font-weight: 600;
  }}
  
  /* Navigation */
  .slide-nav {{
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(255,255,255,0.95);
    padding: 8px 16px;
    border-radius: 30px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 100;
  }}
  .nav-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #cbd5e1;
    cursor: pointer;
    transition: all 0.3s;
  }}
  .nav-dot.active {{
    background: #2563EB;
    width: 24px;
    border-radius: 5px;
  }}
  .nav-btn {{
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    padding: 4px 8px;
    color: #475569;
    transition: color 0.2s;
  }}
  .nav-btn:hover {{ color: #2563EB; }}
  .slide-counter {{
    font-size: 13px;
    color: #64748b;
    min-width: 50px;
    text-align: center;
  }}
  
  /* Category Header */
  .category-header {{
    padding: 16px 20px;
    border-radius: 12px;
    border: 2px solid;
    margin-bottom: 16px;
  }}
  .category-header h3 {{
    font-size: 20px;
    margin-bottom: 4px;
  }}
  .category-header p {{
    font-size: 14px;
    color: #64748b;
  }}
  
  /* Print */
  @media print {{
    .slide {{
      position: relative;
      opacity: 1;
      page-break-after: always;
      height: auto;
      min-height: 100vh;
    }}
    .slide-nav {{ display: none; }}
  }}
  
  /* Responsive */
  @media (max-width: 768px) {{
    .slide {{ padding: 20px; }}
    .title-content h1 {{ font-size: 28px; }}
    .slide-header h2 {{ font-size: 24px; }}
    .exp-grid {{ grid-template-columns: 1fr; }}
    .future-grid {{ grid-template-columns: 1fr; }}
    .skills-chart {{ max-width: 100%; }}
    .skill-name {{ width: 70px; font-size: 12px; }}
  }}
</style>
</head>
<body>
<div class="presentation" id="presentation">
  {slides_html}
  
  <div class="slide-nav">
    <button class="nav-btn" onclick="prevSlide()">&#9664;</button>
    <span class="slide-counter"><span id="current">1</span> / {len(slides)}</span>
    <button class="nav-btn" onclick="nextSlide()">&#9654;</button>
    <div style="display:flex;gap:6px;margin-left:8px;">
      {nav_dots}
    </div>
  </div>
</div>

<script>
  let currentSlide = 0;
  const totalSlides = {len(slides)};
  
  function showSlide(n) {{
    if (n < 0) n = 0;
    if (n >= totalSlides) n = totalSlides - 1;
    
    document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
    document.getElementById('slide-' + n).classList.add('active');
    
    document.querySelectorAll('.nav-dot').forEach((d, i) => {{
      d.classList.toggle('active', i === n);
    }});
    
    document.getElementById('current').textContent = n + 1;
    currentSlide = n;
  }}
  
  function nextSlide() {{
    showSlide(currentSlide + 1);
  }}
  
  function prevSlide() {{
    showSlide(currentSlide - 1);
  }}
  
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
    if (e.key === 'ArrowLeft') prevSlide();
  }});
  
  document.querySelectorAll('.nav-dot').forEach(dot => {{
    dot.addEventListener('click', () => {{
      showSlide(parseInt(dot.dataset.slide));
    }});
  }});
  
  showSlide(0);
</script>
</body>
</html>
'''
    return html

def main():
    print("=== 奖学金答辩幻灯片生成器 ===\n")
    generate_ppt_html()

if __name__ == "__main__":
    main()
