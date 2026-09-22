#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大学生成长档案库 - 综测申报表生成器
功能：从档案数据生成综测申报表格
输出格式：Markdown表格（便于阅读和打印）+ CSV（便于导入Excel）
无需外部依赖
"""

import json
import csv
import io
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output" / "综测申报表"

EXPERIENCES_FILE = DATA_DIR / "experiences.json"
RULES_FILE = DATA_DIR / "rules.json"

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

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_rule_by_id(rules: dict, rule_id: str):
    for cat in rules.get("categories", []):
        for sub in cat.get("subcategories", []):
            if sub.get("id") == rule_id:
                return sub, cat
    return None, None

def calculate_scores(experiences: dict, rules: dict) -> dict:
    """计算综测分"""
    exps = experiences.get("experiences", [])
    results = {
        "total_score": 0,
        "category_scores": {},
        "items": [],
        "needs_confirm": []
    }
    
    # 初始化分类
    for cat in rules.get("categories", []):
        results["category_scores"][cat["id"]] = {
            "name": cat["name"],
            "max_score": cat.get("max_score", 0),
            "current_score": 0,
            "items": []
        }
    
    for exp in exps:
        rule_id = exp.get("rule_id", "")
        rule, cat = get_rule_by_id(rules, rule_id)
        
        if rule and cat:
            base_score = rule.get("score", 0)
            quantity = exp.get("quantity", 1)
            score = base_score * quantity
            
            exp_result = {
                "id": exp.get("id", ""),
                "name": exp.get("name", ""),
                "category_id": cat["id"],
                "category_name": cat["name"],
                "rule_name": rule.get("name", ""),
                "score": score,
                "quantity": quantity,
                "role": exp.get("role", ""),
                "achievement": exp.get("achievement", ""),
                "date": f"{exp.get('start_date', '')} ~ {exp.get('end_date', '')}",
                "materials": exp.get("materials", []),
                "needs_confirm": False,
                "confirm_reason": ""
            }
            
            # 检查是否需要人工确认
            if not exp.get("materials"):
                exp_result["needs_confirm"] = True
                exp_result["confirm_reason"] = "缺少证明材料"
            if not exp.get("achievement"):
                exp_result["needs_confirm"] = True
                if exp_result["confirm_reason"]:
                    exp_result["confirm_reason"] += ";未填写成果"
                else:
                    exp_result["confirm_reason"] = "未填写成果"
            if not exp.get("rule_id"):
                exp_result["needs_confirm"] = True
                exp_result["confirm_reason"] = "未匹配综测细则"
            
            results["items"].append(exp_result)
            
            cat_id = cat["id"]
            if cat_id in results["category_scores"]:
                results["category_scores"][cat_id]["items"].append(exp_result)
                results["category_scores"][cat_id]["current_score"] += score
        else:
            # 未匹配规则，但需要记录
            exp_result = {
                "id": exp.get("id", ""),
                "name": exp.get("name", ""),
                "category_id": exp.get("category", ""),
                "category_name": CATEGORY_NAMES.get(exp.get("category", ""), exp.get("category", "")),
                "rule_name": "未匹配",
                "score": 0,
                "quantity": exp.get("quantity", 1),
                "role": exp.get("role", ""),
                "achievement": exp.get("achievement", ""),
                "date": f"{exp.get('start_date', '')} ~ {exp.get('end_date', '')}",
                "materials": exp.get("materials", []),
                "needs_confirm": True,
                "confirm_reason": "未匹配综测细则，需人工确认"
            }
            results["items"].append(exp_result)
    
    # 应用分类上限
    for cat_id, cat_info in results["category_scores"].items():
        if cat_info["current_score"] > cat_info["max_score"]:
            cat_info["current_score"] = cat_info["max_score"]
    
    results["total_score"] = sum(cat["current_score"] for cat in results["category_scores"].values())
    results["needs_confirm"] = [i for i in results["items"] if i["needs_confirm"]]
    
    return results

def generate_markdown_table(scores: dict, student: dict) -> str:
    """生成Markdown格式的综测申报表"""
    lines = []
    
    # 标题
    lines.append("# 大学生综合素质测评申报表")
    lines.append("")
    
    # 学生信息
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"| 项目 | 内容 | 项目 | 内容 |")
    lines.append(f"|------|------|------|------|")
    lines.append(f"| 姓名 | {student.get('name', '未填写')} | 学号 | {student.get('student_id', '未填写')} |")
    lines.append(f"| 学院 | {student.get('college', '未填写')} | 专业 | {student.get('major', '未填写')} |")
    lines.append(f"| 年级 | {student.get('grade', '未填写')} | 班级 | {student.get('class', '未填写')} |")
    lines.append(f"| 申报日期 | {datetime.now().strftime('%Y年%m月%d日')} | | |")
    lines.append("")
    
    # 得分汇总
    lines.append(f"## 得分汇总")
    lines.append("")
    lines.append(f"**预估总分：{scores['total_score']:.1f} 分**")
    lines.append("")
    lines.append(f"| 类别 | 已得分 | 上限 | 状态 |")
    lines.append(f"|------|--------|------|------|")
    for cat_id, cat_info in scores["category_scores"].items():
        if cat_info["max_score"] > 0:
            status = "✅ 正常" if cat_info["current_score"] <= cat_info["max_score"] else "⚠️ 超上限"
            lines.append(f"| {cat_info['name']} | {cat_info['current_score']:.1f} | {cat_info['max_score']} | {status} |")
    lines.append("")
    
    # 加分项目明细
    lines.append(f"## 加分项目明细")
    lines.append("")
    
    idx = 1
    for cat_id, cat_info in scores["category_scores"].items():
        if cat_info["items"]:
            lines.append(f"### {cat_info['name']}（上限 {cat_info['max_score']} 分，已得 {cat_info['current_score']:.1f} 分）")
            lines.append("")
            lines.append(f"| 序号 | 项目名称 | 获奖/成果 | 时间 | 角色 | 匹配规则 | 加分 | 状态 |")
            lines.append(f"|------|----------|-----------|------|------|----------|------|------|")
            
            for item in cat_info["items"]:
                status = "✅ 已确认" if not item["needs_confirm"] else f"⚠️ {item['confirm_reason']}"
                lines.append(f"| {idx} | {item['name']} | {item['achievement'] or '-'} | {item['date']} | {item['role'] or '-'} | {item['rule_name']} | +{item['score']:.1f} | {status} |")
                idx += 1
            
            lines.append("")
    
    # 未匹配项
    unmatched = [i for i in scores["items"] if i["rule_name"] == "未匹配" or i["score"] == 0]
    if unmatched:
        lines.append(f"### 待确认项目（未匹配综测细则）")
        lines.append("")
        lines.append(f"| 序号 | 项目名称 | 类型 | 成果 | 时间 | 状态 |")
        lines.append(f"|------|----------|------|------|------|------|")
        for i, item in enumerate(unmatched, 1):
            lines.append(f"| {i} | {item['name']} | {item['category_name']} | {item['achievement'] or '-'} | {item['date']} | ⚠️ 需人工确认 |")
        lines.append("")
    
    # 材料清单
    lines.append(f"## 证明材料清单")
    lines.append("")
    lines.append(f"| 序号 | 经历名称 | 材料路径 |")
    lines.append(f"|------|----------|----------|")
    
    mat_idx = 1
    for item in scores["items"]:
        if item["materials"]:
            for mat in item["materials"]:
                lines.append(f"| {mat_idx} | {item['name']} | {mat} |")
                mat_idx += 1
    
    if mat_idx == 1:
        lines.append(f"| - | 暂无关联材料 | - |")
    
    lines.append("")
    
    # 需确认事项
    if scores["needs_confirm"]:
        lines.append(f"## ⚠️ 需人工确认事项")
        lines.append("")
        for item in scores["needs_confirm"]:
            lines.append(f"- **{item['name']}**：{item['confirm_reason']}")
        lines.append("")
    
    # 备注
    lines.append(f"---")
    lines.append(f"*本表由大学生成长档案库自动生成，仅供参考。最终得分以学院审核为准。*")
    lines.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return "\n".join(lines)

def generate_csv(scores: dict, student: dict) -> str:
    """生成CSV格式的综测申报表"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    
    # 学生信息
    writer.writerow(["大学生综合素质测评申报表"])
    writer.writerow([])
    writer.writerow(["姓名", student.get("name", ""), "学号", student.get("student_id", "")])
    writer.writerow(["学院", student.get("college", ""), "专业", student.get("major", "")])
    writer.writerow(["年级", student.get("grade", ""), "班级", student.get("class", "")])
    writer.writerow(["申报日期", datetime.now().strftime("%Y-%m-%d"), "", ""])
    writer.writerow([])
    
    # 得分汇总
    writer.writerow(["得分汇总"])
    writer.writerow(["类别", "已得分", "上限", "状态"])
    for cat_id, cat_info in scores["category_scores"].items():
        if cat_info["max_score"] > 0:
            status = "正常" if cat_info["current_score"] <= cat_info["max_score"] else "超上限"
            writer.writerow([cat_info["name"], f"{cat_info['current_score']:.1f}", cat_info["max_score"], status])
    writer.writerow([])
    
    # 加分明细
    writer.writerow(["加分项目明细"])
    writer.writerow(["序号", "类别", "项目名称", "获奖/成果", "时间", "角色", "匹配规则", "加分", "状态"])
    
    idx = 1
    for cat_id, cat_info in scores["category_scores"].items():
        for item in cat_info["items"]:
            status = "已确认" if not item["needs_confirm"] else item["confirm_reason"]
            writer.writerow([
                idx,
                item["category_name"],
                item["name"],
                item["achievement"] or "-",
                item["date"],
                item["role"] or "-",
                item["rule_name"],
                f"{item['score']:.1f}",
                status
            ])
            idx += 1
    
    writer.writerow([])
    writer.writerow(["总分", f"{scores['total_score']:.1f}"])
    
    return buf.getvalue()

def generate_zongce():
    """生成综测申报表"""
    experiences = load_json(EXPERIENCES_FILE)
    rules = load_json(RULES_FILE)
    
    if not experiences.get("experiences"):
        print("⚠ 暂无经历记录，无法生成申报表")
        print("  请先通过 index.html 或 python core.py add 添加经历")
        return None
    
    if not rules.get("categories"):
        print("⚠ 未配置综测细则，无法计算分数")
        print(f"  请编辑 {RULES_FILE} 配置你所在学院的综测细则")
        print(f"  参考模板：templates/rules_template.json")
        return None
    
    scores = calculate_scores(experiences, rules)
    student = experiences.get("student_info", {})
    
    # 生成Markdown
    markdown_content = generate_markdown_table(scores, student)
    
    # 生成CSV
    csv_content = generate_csv(scores, student)
    
    # 保存文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = student.get("name", "未命名")
    
    md_path = OUTPUT_DIR / f"综测申报表_{name}_{timestamp}.md"
    csv_path = OUTPUT_DIR / f"综测申报表_{name}_{timestamp}.csv"
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_content)
    
    print(f"✓ 综测申报表已生成:")
    print(f"  Markdown: {md_path}")
    print(f"  CSV:      {csv_path}")
    print(f"  预估总分: {scores['total_score']:.1f} 分")
    
    # 打印需确认项
    if scores["needs_confirm"]:
        print(f"\n⚠ 发现 {len(scores['needs_confirm'])} 项需要人工确认:")
        for item in scores["needs_confirm"]:
            print(f"  - {item['name']}: {item['confirm_reason']}")
    else:
        print(f"\n✅ 所有项目已确认，无需处理")
    
    return {"md_path": md_path, "csv_path": csv_path, "total_score": scores["total_score"]}

def main():
    print("=== 综测申报表生成器 ===\n")
    result = generate_zongce()
    if result:
        print(f"\n文件已保存到 output/综测申报表/ 目录")

if __name__ == "__main__":
    main()
