#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大学生成长档案库 - 核心数据处理引擎
功能：材料扫描、综测分计算、缺失检测、数据管理、规则自动提取、智能识别
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# ========== 配置 ==========
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MATERIALS_DIR = BASE_DIR / "materials"
OUTPUT_DIR = BASE_DIR / "output"

EXPERIENCES_FILE = DATA_DIR / "experiences.json"
RULES_FILE = DATA_DIR / "rules.json"
TAGS_FILE = DATA_DIR / "tags.json"

# ========== 数据加载与保存 ==========

def load_json(path: Path) -> dict:
    """加载JSON文件"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict) -> None:
    """保存JSON文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_experiences() -> dict:
    return load_json(EXPERIENCES_FILE)

def save_experiences(data: dict) -> None:
    save_json(EXPERIENCES_FILE, data)

def load_rules() -> dict:
    return load_json(RULES_FILE)

def save_rules(data: dict) -> None:
    save_json(RULES_FILE, data)

def load_tags() -> dict:
    return load_json(TAGS_FILE)

# ========== 综测细则自动提取 ==========

def extract_rules_from_text(text: str) -> dict:
    """
    从综测细则文本中自动提取加分项目、分值、上限和证明要求
    返回完整的 rules.json 结构
    """
    # 预定义8大分类
    categories = {
        "学业成绩": {"id": "academic", "keywords": ["学业", "成绩", "GPA", "绩点", "课程", "学习", "奖学金", "学业奖"]},
        "学科竞赛": {"id": "competition", "keywords": ["竞赛", "比赛", "大赛", "学科", "数学建模", "程序设计", "创新创业", "挑战杯", "互联网+"]},
        "科研创新": {"id": "research", "keywords": ["科研", "论文", "专利", "软著", "项目", "课题", "研究", "发明", "创新"]},
        "社会实践": {"id": "social_practice", "keywords": ["实践", "志愿", "服务", "支教", "调研", "实习", "社会", "公益"]},
        "学生工作": {"id": "leadership", "keywords": ["学生工作", "干部", "班委", "学生会", "社团", "助理", "负责人", "组织"]},
        "文体活动": {"id": "talent", "keywords": ["文体", "文艺", "体育", "艺术", "表演", "赛事", "书法", "绘画", "歌唱", "舞蹈"]},
        "荣誉称号": {"id": "honor", "keywords": ["荣誉", "称号", "三好", "优秀", "先进", "标兵", "模范"]},
        "技能证书": {"id": "certificate", "keywords": ["证书", "资格", "等级", "英语", "计算机", "普通话", "驾照", "技能证"]},
    }
    
    result = {
        "schema_version": "1.0",
        "college_name": "",
        "academic_year": "",
        "categories": []
    }
    
    # 尝试提取学院名称和学年
    college_match = re.search(r'([\u4e00-\u9fa5]+(?:学院|大学|系部))', text)
    if college_match:
        result["college_name"] = college_match.group(1)
    
    year_match = re.search(r'(20\d{2}-20\d{2})\s*学年', text)
    if year_match:
        result["academic_year"] = year_match.group(1)
    
    # 为每个分类初始化
    cat_map = {}
    for cat_name, cat_info in categories.items():
        cat_id = cat_info["id"]
        cat_map[cat_id] = {
            "id": cat_id,
            "name": cat_name,
            "description": "",
            "max_score": 0,
            "subcategories": []
        }
    
    # 分块处理文本
    lines = text.split('\n')
    current_category = None
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        # 识别分类标题（通常包含分类名 + "分" 或 "加分"）
        for cat_name, cat_info in categories.items():
            if cat_name in line and any(kw in line for kw in ["分", "加分", "标准", "项目"]):
                current_category = cat_info["id"]
                # 尝试提取上限
                max_match = re.search(r'上限\s*(\d+(?:\.\d+)?)|最高\s*(\d+(?:\.\d+)?)|不超过\s*(\d+(?:\.\d+)?)', line)
                if max_match:
                    cat_map[current_category]["max_score"] = float(max_match.group(1) or max_match.group(2) or max_match.group(3))
                break
        
        # 提取具体加分项
        # 跳过分类标题行（如"二、学科竞赛（上限20分）"）
        if re.match(r'^[一二三四五六七八九十]+、', line) and '上限' in line:
            continue
        
        # 优先用"名称+冒号+分值"模式，只取第一个匹配，避免重复
        line_rule = None
        
        # 模式1（最可靠）：项目名称 + 冒号 + 分值 + 分
        m1 = re.search(r'([^\d：:][^：:]*)[：:]\s*(\d+(?:\.\d+)?)\s*分', line)
        if m1:
            name = m1.group(1).strip()
            score_str = m1.group(2)
        else:
            # 模式2：名称 + 空格 + 分值 + 分（无冒号）
            m2 = re.search(r'([^\d\s][^\d]*?)\s*(\d+(?:\.\d+)?)\s*分', line)
            if m2:
                name = m2.group(1).strip()
                score_str = m2.group(2)
            else:
                name = None
                score_str = None
        
        if name and score_str:
            try:
                score = float(score_str)
            except ValueError:
                score = 0
            
            # 清理名称：去掉前缀序号、多余空格、尾冒号
            name = re.sub(r'^[一二三四五六七八九十\d]+[、\.\s]*', '', name)  # 去掉 "1. " "二、" 前缀
            name = re.sub(r'^[\.\s]+', '', name)  # 去掉残留的 ". " 前缀
            name = name.strip('：: \t')  # 去掉尾冒号和空格
            name = name.strip()
            
            # 跳过分类标题（如"学业成绩（上限20分）"被误匹配）
            if '上限' in name and ('分）' in name or '分)' in name):
                continue
            
            if len(name) >= 2 and score > 0:
                # 确定分类
                if current_category:
                    cat_id = current_category
                else:
                    cat_id = _guess_category(name + " " + line, categories)
                
                # 去重：检查该分类下是否已有同名规则
                existing_names = [r["name"] for r in cat_map[cat_id]["subcategories"]]
                if name in existing_names:
                    continue
                
                # 提取证明要求
                evidence = []
                evidence_keywords = ["证书", "证明", "奖状", "截图", "通知", "文件", "照片", "材料", "复印件", "原件", "聘书", "成绩单"]
                for kw in evidence_keywords:
                    if kw in line:
                        evidence.append(kw)
                
                # 提取上限（如"上限3分"）
                limit_match = re.search(r'上限\s*(\d+(?:\.\d+)?)', line)
                max_s = float(limit_match.group(1)) if limit_match else score
                
                # 标记待确认项
                status = "待确认" if not evidence else "已提取"
                
                rule_id = f"{cat_id}_auto_{len(cat_map[cat_id]['subcategories'])}"
                
                cat_map[cat_id]["subcategories"].append({
                    "id": rule_id,
                    "name": name,
                    "score": score,
                    "max_score": max_s,
                    "evidence_required": evidence if evidence else ["待确认"],
                    "status": status,
                    "source_text": line[:100]
                })
    
    # 构建结果
    for cat_id in ["academic", "competition", "research", "social_practice", 
                   "leadership", "talent", "honor", "certificate"]:
        if cat_map[cat_id]["subcategories"]:
            result["categories"].append(cat_map[cat_id])
    
    # 如果没有提取到任何规则，使用默认模板
    if not result["categories"]:
        result = _get_default_rules_template()
    
    return result

def _guess_category(text: str, categories: dict) -> str:
    """根据文本内容猜测分类"""
    text = text.lower()
    scores = {}
    for cat_name, cat_info in categories.items():
        cat_id = cat_info["id"]
        score = 0
        for kw in cat_info["keywords"]:
            if kw in text:
                score += 1
        scores[cat_id] = score
    
    if scores:
        # Filter out zero scores and None values
        valid_scores = {k: v for k, v in scores.items() if v is not None and v > 0}
        if valid_scores:
            best = max(valid_scores, key=lambda k: valid_scores[k])
            return best
    
    return "competition"  # 默认分类

def _get_default_rules_template() -> dict:
    """获取默认规则模板"""
    return {
        "schema_version": "1.0",
        "college_name": "",
        "academic_year": "",
        "categories": [
            {
                "id": "academic",
                "name": "学业成绩",
                "description": "课程成绩、学术竞赛、论文发表等",
                "max_score": 20,
                "subcategories": [
                    {"id": "academic_gpa_top10", "name": "学业成绩前10%", "score": 10, "max_score": 10, "evidence_required": ["成绩单"], "status": "待确认"},
                    {"id": "academic_gpa_top30", "name": "学业成绩前30%", "score": 5, "max_score": 5, "evidence_required": ["成绩单"], "status": "待确认"},
                ]
            },
            {
                "id": "competition",
                "name": "学科竞赛",
                "description": "数学建模、程序设计、创新创业等各类竞赛",
                "max_score": 20,
                "subcategories": [
                    {"id": "competition_national_1st", "name": "全国竞赛一等奖", "score": 8, "max_score": 8, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "competition_national_2nd", "name": "全国竞赛二等奖", "score": 6, "max_score": 6, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "competition_national_3rd", "name": "全国竞赛三等奖", "score": 4, "max_score": 4, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "competition_provincial_1st", "name": "省级竞赛一等奖", "score": 5, "max_score": 5, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "competition_provincial_2nd", "name": "省级竞赛二等奖", "score": 3, "max_score": 3, "evidence_required": ["证书"], "status": "待确认"},
                ]
            },
            {
                "id": "research",
                "name": "科研创新",
                "description": "科研项目、专利、论文、软著等",
                "max_score": 15,
                "subcategories": [
                    {"id": "research_paper_sci", "name": "SCI论文", "score": 10, "max_score": 10, "evidence_required": ["录用通知/见刊证明"], "status": "待确认"},
                    {"id": "research_paper_core", "name": "核心期刊论文", "score": 6, "max_score": 6, "evidence_required": ["录用通知/见刊证明"], "status": "待确认"},
                    {"id": "research_patent", "name": "发明专利", "score": 8, "max_score": 8, "evidence_required": ["专利证书"], "status": "待确认"},
                ]
            },
            {
                "id": "social_practice",
                "name": "社会实践",
                "description": "志愿服务、社会调研、支教、实习等",
                "max_score": 10,
                "subcategories": [
                    {"id": "social_practice_outstanding", "name": "社会实践优秀个人/团队", "score": 5, "max_score": 5, "evidence_required": ["证明/证书"], "status": "待确认"},
                    {"id": "social_practice_volunteer", "name": "志愿服务时长", "score": 0.1, "max_score": 3, "evidence_required": ["志愿时长证明"], "status": "待确认"},
                ]
            },
            {
                "id": "leadership",
                "name": "学生工作",
                "description": "班委、学生会、社团、助理等学生干部经历",
                "max_score": 10,
                "subcategories": [
                    {"id": "leadership_student_union", "name": "学生会/社团主要负责人", "score": 5, "max_score": 5, "evidence_required": ["聘书/证明"], "status": "待确认"},
                    {"id": "leadership_class", "name": "班委成员", "score": 3, "max_score": 3, "evidence_required": ["聘书/证明"], "status": "待确认"},
                ]
            },
            {
                "id": "talent",
                "name": "文体活动",
                "description": "文艺表演、体育赛事、书法绘画等",
                "max_score": 10,
                "subcategories": [
                    {"id": "talent_national", "name": "国家级文体活动获奖", "score": 5, "max_score": 5, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "talent_provincial", "name": "省级文体活动获奖", "score": 3, "max_score": 3, "evidence_required": ["证书"], "status": "待确认"},
                ]
            },
            {
                "id": "honor",
                "name": "荣誉称号",
                "description": "三好学生、优秀学生干部、优秀团员等",
                "max_score": 10,
                "subcategories": [
                    {"id": "honor_sanhao", "name": "三好学生", "score": 5, "max_score": 5, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "honor_excellent_student", "name": "优秀学生干部", "score": 5, "max_score": 5, "evidence_required": ["证书"], "status": "待确认"},
                ]
            },
            {
                "id": "certificate",
                "name": "技能证书",
                "description": "英语等级、计算机等级、职业资格证书等",
                "max_score": 10,
                "subcategories": [
                    {"id": "certificate_cet6", "name": "英语六级", "score": 3, "max_score": 3, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "certificate_cet4", "name": "英语四级", "score": 1, "max_score": 1, "evidence_required": ["证书"], "status": "待确认"},
                    {"id": "certificate_computer", "name": "计算机等级证书", "score": 2, "max_score": 2, "evidence_required": ["证书"], "status": "待确认"},
                ]
            }
        ]
    }

# ========== 材料文件名解析 ==========

def parse_material_filename(filename: str) -> dict:
    """
    解析材料文件名，提取日期、活动名、材料类型
    支持格式：
    - 2024-03-15_数学建模竞赛_证书.jpg
    - 数学建模_2024.3.15_截图.png
    - 竞赛证书-数学建模-20240315.pdf
    """
    result = {
        "original_name": filename,
        "date": None,
        "event_name": None,
        "material_type": None,
        "category_guess": None
    }
    
    # 移除扩展名
    name_without_ext = Path(filename).stem
    
    # 提取日期
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{4}\.\d{1,2}\.\d{1,2})',
        r'(\d{4}\d{2}\d{2})',
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, name_without_ext)
        if match:
            try:
                if len(match.groups()) == 3:
                    result["date"] = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                elif len(match.group(1)) == 8:
                    result["date"] = f"{match.group(1)[:4]}-{match.group(1)[4:6]}-{match.group(1)[6:8]}"
                else:
                    result["date"] = match.group(1).replace('.', '-')
                break
            except:
                pass
    
    # 提取材料类型
    material_types = {
        "证书": ["证书", "奖状", "证明", "聘书"],
        "截图": ["截图", "截屏", "照片", "图片"],
        "作品": ["作品", "报告", "论文", "代码", "设计", "PPT", "演示"],
        "通知": ["通知", "公告", "公示", "文件"],
    }
    
    for mat_type, keywords in material_types.items():
        for kw in keywords:
            if kw in name_without_ext:
                result["material_type"] = mat_type
                break
        if result["material_type"]:
            break
    
    # 提取活动名（移除日期和材料类型后的剩余部分）
    event_name = name_without_ext
    if result["date"]:
        event_name = event_name.replace(result["date"], "")
    if result["material_type"]:
        for kw in material_types.get(result["material_type"], []):
            event_name = event_name.replace(kw, "")
    
    # 清理分隔符
    event_name = re.sub(r'[_\-\s]+', ' ', event_name).strip()
    if event_name and len(event_name) > 1:
        result["event_name"] = event_name
    
    # 猜测分类
    result["category_guess"] = _guess_material_category(name_without_ext)
    
    return result

def _guess_material_category(text: str) -> str:
    """根据文件名猜测材料分类（兼容 v1.0 八分类和 v2.0 四分类）"""
    categories = {
        "academic_score": ["学业", "成绩", "GPA", "绩点", "课程", "奖学金", "学业奖", "学习", "学业成绩"],
        "academic_research": ["科研", "论文", "专利", "软著", "项目", "课题", "研究", "发明", "学术", "出版", "期刊", "会议"],
        "practice": ["竞赛", "比赛", "大赛", "数学建模", "程序设计", "创新创业", "挑战杯", "互联网+",
                      "实践", "志愿", "服务", "支教", "调研", "实习", "社会", "公益",
                      "学生工作", "干部", "班委", "学生会", "社团", "助理", "负责人",
                      "文体", "文艺", "体育", "艺术", "表演", "书法", "绘画", "歌唱", "舞蹈",
                      "荣誉", "称号", "三好", "优秀", "先进", "标兵", "模范",
                      "证书", "资格", "等级", "英语", "计算机", "普通话", "驾照", "六级", "四级"],
        # v1.0 兼容
        "academic": ["学业", "成绩", "GPA", "绩点", "课程", "奖学金", "学业奖", "学习"],
        "competition": ["竞赛", "比赛", "大赛", "数学建模", "程序设计", "创新创业", "挑战杯", "互联网+", "ACM", "数学竞赛"],
        "research": ["科研", "论文", "专利", "软著", "项目", "课题", "研究", "发明"],
        "social_practice": ["实践", "志愿", "服务", "支教", "调研", "实习", "社会", "公益"],
        "leadership": ["学生工作", "干部", "班委", "学生会", "社团", "助理", "负责人"],
        "talent": ["文体", "文艺", "体育", "艺术", "表演", "书法", "绘画", "歌唱", "舞蹈", "运动会"],
        "honor": ["荣誉", "称号", "三好", "优秀", "先进", "标兵", "模范"],
        "certificate": ["证书", "资格", "等级", "英语", "计算机", "普通话", "驾照", "六级", "四级"],
    }
    
    text = text.lower()
    best_cat = "practice"  # 默认分类
    best_score = 0
    
    for cat_id, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_cat = cat_id
    
    return best_cat

# ========== 材料扫描与智能识别 ==========

def scan_materials() -> Dict[str, List[str]]:
    """
    扫描materials目录，返回各分类下的文件列表
    """
    materials = {}
    if not MATERIALS_DIR.exists():
        return materials
    
    for category_dir in MATERIALS_DIR.iterdir():
        if category_dir.is_dir():
            category = category_dir.name
            files = []
            for file_path in category_dir.iterdir():
                if file_path.is_file() and not file_path.name.startswith("."):
                    rel_path = str(file_path.relative_to(BASE_DIR)).replace("\\", "/")
                    files.append(rel_path)
            if files:
                materials[category] = sorted(files)
    return materials

def analyze_materials(materials: Dict[str, List[str]]) -> List[dict]:
    """
    分析所有材料文件，生成经历草稿
    """
    drafts = []
    event_groups = {}  # 按活动名分组
    
    for category, files in materials.items():
        for file_path in files:
            filename = Path(file_path).name
            parsed = parse_material_filename(filename)
            
            event_name = parsed.get("event_name") or filename
            
            if event_name not in event_groups:
                event_groups[event_name] = {
                    "event_name": event_name,
                    "date": parsed.get("date"),
                    "category": parsed.get("category_guess") or category,
                    "files": [],
                    "material_types": set()
                }
            
            event_groups[event_name]["files"].append(file_path)
            if parsed.get("material_type"):
                event_groups[event_name]["material_types"].add(parsed["material_type"])
    
    # 生成经历草稿
    for event_name, group in event_groups.items():
        drafts.append({
            "name": event_name,
            "category": group["category"],
            "date": group["date"] or "",
            "files": group["files"],
            "material_types": list(group["material_types"]),
            "status": "草稿",
            "needs_confirm": True,
            "suggested_rules": []
        })
    
    return drafts

# ========== 综测分计算 ==========

def get_rule_by_id(rules: dict, rule_id: str) -> Optional[dict]:
    """根据ID查找综测细则条目"""
    for cat in rules.get("categories", []):
        for sub in cat.get("subcategories", []):
            if sub.get("id") == rule_id:
                return sub
    return None

def get_category_by_rule_id(rules: dict, rule_id: str) -> Optional[dict]:
    """根据规则ID查找所属分类"""
    for cat in rules.get("categories", []):
        for sub in cat.get("subcategories", []):
            if sub.get("id") == rule_id:
                return cat
    return None

def estimate_score(experience: dict, rules: dict) -> dict:
    """
    根据综测细则预估单个经历的加分。
    支持 v2.0 schema：区间分、扣分制、基础分+加分、全局约束。
    """
    rule_id = experience.get("rule_id", "")
    if not rule_id:
        return {"score": 0, "rule_matched": None, "category": None, "notes": "未匹配综测细则", "scoring_type": "unknown"}

    rule = get_rule_by_id(rules, rule_id)
    if not rule:
        return {"score": 0, "rule_matched": None, "category": None, "notes": f"未找到规则: {rule_id}", "scoring_type": "unknown"}

    category = get_category_by_rule_id(rules, rule_id)
    cat_id = category.get("id") if category else None

    total_structure = rules.get("total_structure", {})
    cat_struct = total_structure.get(cat_id, {})
    scoring_type = cat_struct.get("type", "加分")

    base_score = rule.get("score", 0)
    rule_max = rule.get("max_score", None)
    quantity = experience.get("quantity", 1)
    total_score = base_score * quantity

    # 区间分：如果规则自身有 max_score 且与 score 不同，说明是区间分
    if rule_max is not None and rule_max != base_score and base_score > 0:
        # score 是参考最高分，max_score 是上限
        total_score = min(total_score, rule_max * quantity)

    notes_parts = [f"匹配规则: {rule.get('name', '')}"]
    if rule.get("notes"):
        notes_parts.append(rule["notes"])

    # 扣分制：score 为负数
    is_deduction = base_score < 0

    return {
        "score": total_score,
        "rule_matched": rule_id,
        "category": cat_id,
        "category_name": category.get("name") if category else None,
        "scoring_type": scoring_type,
        "is_deduction": is_deduction,
        "rule_max_score": rule_max,
        "notes": " | ".join(notes_parts)
    }

def calculate_all_scores(experiences: dict, rules: dict) -> dict:
    """
    计算所有经历的综测分，返回汇总结果。
    支持 v2.0 schema：扣分制、计算制、基础分+加分、全局约束。
    """
    total_structure = rules.get("total_structure", {})
    global_constraints = rules.get("global_constraints", [])

    results = {
        "total_score": 0,
        "category_scores": {},
        "global_constraints": [],
        "experiences": []
    }

    # 初始化各分类
    for cat in rules.get("categories", []):
        cat_id = cat["id"]
        cat_struct = total_structure.get(cat_id, {})
        scoring_type = cat_struct.get("type", "加分")

        if scoring_type == "扣分制":
            # 基准分 = max_score，扣分从基准中减去
            base = cat_struct.get("max", cat.get("max_score", 0))
            current = base  # 从满分开始扣
        elif scoring_type == "基础分+加分":
            base = cat_struct.get("base", 0)
            current = base  # 从基础分开始加
        elif scoring_type == "计算制":
            base = 0
            current = 0  # GPA 制，需手动输入
        else:
            base = 0
            current = 0

        results["category_scores"][cat_id] = {
            "name": cat["name"],
            "max_score": cat.get("max_score", 0),
            "current_score": current,
            "base_score": base,
            "scoring_type": scoring_type,
            "bonus_max": cat_struct.get("bonus_max", None),
            "items": []
        }

    # 逐条计算
    for exp in experiences.get("experiences", []):
        score_info = estimate_score(exp, rules)
        exp_result = {
            "id": exp.get("id"),
            "name": exp.get("name"),
            "score": score_info["score"],
            "category": score_info["category"],
            "category_name": score_info.get("category_name"),
            "scoring_type": score_info.get("scoring_type"),
            "is_deduction": score_info.get("is_deduction", False),
            "notes": score_info["notes"]
        }
        results["experiences"].append(exp_result)

        cat_id = score_info["category"]
        if cat_id and cat_id in results["category_scores"]:
            cat_data = results["category_scores"][cat_id]
            cat_data["items"].append(exp_result)

            if cat_data["scoring_type"] == "扣分制":
                # 扣分制：从基准分中减去（score 为负数，加上负数 = 减）
                cat_data["current_score"] += score_info["score"]
                # 不能低于 0
                if cat_data["current_score"] < 0:
                    cat_data["current_score"] = 0
            elif cat_data["scoring_type"] == "基础分+加分":
                # 基础分+加分：加分为正数，累加后不超过 bonus_max
                bonus = score_info["score"]
                bonus_max = cat_data.get("bonus_max")
                cat_data["current_score"] += bonus
                if bonus_max is not None:
                    bonus_total = cat_data["current_score"] - cat_data["base_score"]
                    if bonus_total > bonus_max:
                        cat_data["current_score"] = cat_data["base_score"] + bonus_max
            else:
                # 普通加分或计算制
                cat_data["current_score"] += score_info["score"]
                cat_max = cat_data["max_score"]
                if cat_max and cat_data["current_score"] > cat_max:
                    cat_data["current_score"] = cat_max

    # 应用全局约束
    for constraint in global_constraints:
        name = constraint.get("name", "")
        rule_text = constraint.get("rule", "") or ""
        desc = constraint.get("description", "")
        cat_ids = constraint.get("category_ids", [])
        max_total = constraint.get("max_total")
        max_items = constraint.get("max_items")

        if max_total is not None and len(cat_ids) >= 2:
            # 学术科研 + 实践能力 加分之和 ≤ max_total
            bonus_total = 0
            for cid in cat_ids:
                cd = results["category_scores"].get(cid)
                if cd and cd["scoring_type"] == "基础分+加分":
                    bonus_total += cd["current_score"] - cd["base_score"]

            if bonus_total > max_total:
                results["global_constraints"].append({
                    "name": name,
                    "description": desc,
                    "actual": bonus_total,
                    "limit": max_total,
                    "status": "超标"
                })
            else:
                results["global_constraints"].append({
                    "name": name,
                    "description": desc,
                    "actual": bonus_total,
                    "limit": max_total,
                    "status": "正常"
                })
        elif max_items is not None:
            # 实践活动最多申报 max_items 项
            # 统计 practice 分类下的经历数
            practice_items = 0
            for cid in cat_ids:
                cd = results["category_scores"].get(cid)
                if cd:
                    practice_items = len(cd["items"])
            if practice_items > max_items:
                results["global_constraints"].append({
                    "name": name,
                    "description": desc,
                    "actual": practice_items,
                    "limit": max_items,
                    "status": "超标"
                })
            else:
                results["global_constraints"].append({
                    "name": name,
                    "description": desc,
                    "actual": practice_items,
                    "limit": max_items,
                    "status": "正常"
                })
        elif "去重" in rule_text or "同一成果" in desc or "同一成果" in name:
            results["global_constraints"].append({
                "name": name,
                "description": desc,
                "status": "提醒",
                "note": "同一成果不可重复加分，系统按首次匹配计"
            })
        elif "最高" in rule_text or "取最高" in rule_text:
            results["global_constraints"].append({
                "name": name,
                "description": desc,
                "status": "提醒",
                "note": "该分类需手动选择最高分单项，系统已列出所有项供确认"
            })
        elif "导师" in rule_text:
            results["global_constraints"].append({
                "name": name,
                "description": desc,
                "status": "提醒",
                "note": "与导师合作时不含导师人数，请在经历中标注"
            })
        elif "用稿" in name or "正式发表" in rule_text:
            results["global_constraints"].append({
                "name": name,
                "description": desc,
                "status": "提醒",
                "note": "用稿通知不加分（毕业年级除外）"
            })
        else:
            results["global_constraints"].append({
                "name": name,
                "description": desc,
                "status": "提醒"
            })

    # 计算总分
    results["total_score"] = sum(
        cat["current_score"] for cat in results["category_scores"].values()
    )

    return results

# ========== 缺失检测 ==========

def check_missing(experiences: dict, materials: Dict[str, List[str]]) -> List[dict]:
    """
    检测哪些经历缺少材料或需要人工确认。
    基于匹配规则的 evidence_required 检查证明材料是否齐全。
    """
    issues = []
    all_materials = set()
    for files in materials.values():
        all_materials.update(files)
    
    rules = load_rules()
    
    for exp in experiences.get("experiences", []):
        exp_issues = {
            "id": exp.get("id"),
            "name": exp.get("name"),
            "missing_materials": [],
            "needs_confirm": [],
            "rule_id": exp.get("rule_id", "")
        }
        
        linked_materials = exp.get("materials", [])
        for mat in linked_materials:
            if mat not in all_materials:
                exp_issues["missing_materials"].append(f"文件不存在: {mat}")
        
        if not linked_materials:
            exp_issues["missing_materials"].append("未关联任何证明材料")
        
        if not exp.get("rule_id"):
            exp_issues["needs_confirm"].append("未匹配综测细则，需人工确认加分项")
        else:
            # 检查规则要求的证明材料
            rule = get_rule_by_id(rules, exp.get("rule_id", ""))
            if rule:
                evidence_required = rule.get("evidence_required", [])
                for ev in evidence_required:
                    # 检查是否有关联材料包含相关关键词
                    has_evidence = False
                    for mat in linked_materials:
                        mat_name = mat.lower()
                        ev_lower = ev.lower()
                        if any(kw in mat_name for kw in ev_lower.split()):
                            has_evidence = True
                            break
                    if not has_evidence and not linked_materials:
                        exp_issues["missing_materials"].append(f"缺少证明: {ev}")
                    elif not has_evidence:
                        exp_issues["needs_confirm"].append(f"请确认是否已提供: {ev}")
        
        if not exp.get("achievement"):
            exp_issues["needs_confirm"].append("未填写具体成果/奖项")
        
        if not exp.get("skills_gained"):
            exp_issues["needs_confirm"].append("未记录能力提升")
        
        if not exp.get("role"):
            exp_issues["needs_confirm"].append("未填写个人角色")
        
        start = exp.get("start_date", "")
        end = exp.get("end_date", "")
        if start and end:
            try:
                s = datetime.strptime(start, "%Y-%m-%d")
                e = datetime.strptime(end, "%Y-%m-%d")
                if e < s:
                    exp_issues["needs_confirm"].append("结束时间早于开始时间")
            except:
                pass
        
        if exp_issues["missing_materials"] or exp_issues["needs_confirm"]:
            issues.append(exp_issues)
    
    return issues

def find_unlinked_materials(experiences: dict, materials: Dict[str, List[str]]) -> List[str]:
    """找出未与任何经历关联的证明材料"""
    linked = set()
    for exp in experiences.get("experiences", []):
        for mat in exp.get("materials", []):
            linked.add(mat)
    
    all_materials = []
    for cat_files in materials.values():
        all_materials.extend(cat_files)
    
    return [m for m in all_materials if m not in linked]

# ========== 经历管理 ==========

def generate_exp_id() -> str:
    """生成唯一经历ID"""
    import uuid
    return f"exp_{uuid.uuid4().hex[:8]}"

def add_experience(
    name: str,
    category: str,
    start_date: str,
    end_date: str,
    role: str = "",
    achievement: str = "",
    description: str = "",
    skills_gained: Optional[List[str]] = None,
    materials: Optional[List[str]] = None,
    rule_id: str = "",
    quantity: int = 1,
    notes: str = "",
    tags: Optional[List[str]] = None
) -> dict:
    """添加一条新经历，返回经历字典"""
    exp = {
        "id": generate_exp_id(),
        "name": name,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "role": role,
        "achievement": achievement,
        "description": description,
        "skills_gained": skills_gained or [],
        "materials": materials or [],
        "rule_id": rule_id,
        "quantity": quantity,
        "notes": notes,
        "tags": tags or [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    data = load_experiences()
    if "experiences" not in data:
        data["experiences"] = []
    
    data["experiences"].append(exp)
    data["metadata"] = data.get("metadata", {})
    data["metadata"]["total_experiences"] = len(data["experiences"])
    data["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    save_experiences(data)
    return exp

def update_experience(exp_id: str, **kwargs) -> Optional[dict]:
    """更新指定ID的经历"""
    data = load_experiences()
    for exp in data.get("experiences", []):
        if exp.get("id") == exp_id:
            for key, value in kwargs.items():
                if key in exp:
                    exp[key] = value
            exp["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_experiences(data)
            return exp
    return None

def delete_experience(exp_id: str) -> bool:
    """删除指定ID的经历"""
    data = load_experiences()
    original_len = len(data.get("experiences", []))
    data["experiences"] = [e for e in data.get("experiences", []) if e.get("id") != exp_id]
    
    if len(data["experiences"]) < original_len:
        data["metadata"] = data.get("metadata", {})
        data["metadata"]["total_experiences"] = len(data["experiences"])
        data["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_experiences(data)
        return True
    return False

# ========== 智能匹配与建议 ==========

def suggest_rule(experience: dict, rules: dict) -> List[dict]:
    """
    根据经历信息，智能建议可能匹配的综测规则
    """
    suggestions = []
    exp_name = experience.get("name", "").lower()
    exp_category = experience.get("category", "").lower()
    achievement = experience.get("achievement", "").lower()
    
    for cat in rules.get("categories", []):
        for sub in cat.get("subcategories", []):
            score = 0
            rule_name = sub.get("name", "").lower()
            
            if any(word in exp_name for word in rule_name.split()):
                score += 3
            
            if cat.get("id", "").lower() in exp_category or cat.get("name", "").lower() in exp_category:
                score += 2
            
            for level in ["一等", "二等", "三等", "特等奖", "国家级", "省级", "校级", "市级", "院级"]:
                if level in achievement and level in rule_name:
                    score += 3
            
            if score > 0:
                suggestions.append({
                    "rule_id": sub["id"],
                    "rule_name": sub["name"],
                    "category": cat["name"],
                    "score": sub.get("score", 0),
                    "confidence": score,
                    "match_reason": f"名称/类别/奖项匹配度: {score}"
                })
    
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    return suggestions[:5]

def suggest_skills(experience: dict, tags: dict) -> List[str]:
    """根据经历描述智能建议能力标签"""
    suggested = []
    text = f"{experience.get('name', '')} {experience.get('description', '')} {experience.get('role', '')}"
    text = text.lower()
    
    for skill in tags.get("skill_tags", []):
        if skill.lower() in text:
            suggested.append(skill)
    
    return list(set(suggested))

# ========== 统计与报告 ==========

def get_dashboard_data() -> dict:
    """获取仪表盘所需的所有数据"""
    experiences = load_experiences()
    rules = load_rules()
    materials = scan_materials()
    
    scores = calculate_all_scores(experiences, rules)
    missing = check_missing(experiences, materials)
    unlinked = find_unlinked_materials(experiences, materials)
    
    timeline = {}
    for exp in experiences.get("experiences", []):
        year = exp.get("start_date", "")[:4]
        if year:
            timeline[year] = timeline.get(year, 0) + 1
    
    skill_count = {}
    for exp in experiences.get("experiences", []):
        for skill in exp.get("skills_gained", []):
            skill_count[skill] = skill_count.get(skill, 0) + 1
    
    return {
        "total_experiences": len(experiences.get("experiences", [])),
        "total_score": scores["total_score"],
        "category_scores": scores["category_scores"],
        "missing_count": len(missing),
        "unlinked_materials": len(unlinked),
        "timeline": timeline,
        "skill_distribution": skill_count,
        "recent_experiences": experiences.get("experiences", [])[-5:][::-1]
    }

def export_summary() -> dict:
    """导出完整汇总报告"""
    experiences = load_experiences()
    rules = load_rules()
    
    scores = calculate_all_scores(experiences, rules)
    materials = scan_materials()
    missing = check_missing(experiences, materials)
    
    return {
        "student_info": experiences.get("student_info", {}),
        "score_summary": scores,
        "missing_issues": missing,
        "material_inventory": materials,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ========== 命令行接口 ==========

def print_help():
    print("""
大学生成长档案库 - 核心引擎

用法: python core.py <命令> [参数]

命令:
  init              初始化数据文件（如果不存在）
  add               交互式添加经历
  list              列出所有经历
  delete <ID>       删除指定经历
  score             计算并显示综测分预估
  missing           检查缺失材料和待确认项
  scan              扫描materials目录
  analyze           分析材料文件，生成经历草稿
  extract-rules     从文本文件提取综测细则
  dashboard         显示仪表盘数据（JSON格式）
  suggest <ID>      为经历推荐匹配的综测规则
  summary           导出完整汇总报告
  export            导出汇总报告到 output/summary.json

示例:
  python core.py init
  python core.py add
  python core.py score
  python core.py missing
  python core.py extract-rules 细则.txt
    """)

def cmd_init():
    """初始化数据文件"""
    if not EXPERIENCES_FILE.exists():
        save_experiences({
            "schema_version": "1.0",
            "student_info": {},
            "experiences": [],
            "metadata": {
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "total_experiences": 0,
                "total_score_estimate": 0
            }
        })
        print(f"已创建 {EXPERIENCES_FILE}")
    else:
        print(f"{EXPERIENCES_FILE} 已存在")
    
    if not RULES_FILE.exists():
        default_rules = _get_default_rules_template()
        save_rules(default_rules)
        print(f"已创建默认综测细则模板 {RULES_FILE}")
        print("请编辑该文件，填入你们学院的具体分值")
    else:
        # 检查是否已有法学院规则
        existing_rules = load_rules()
        sv = existing_rules.get("schema_version", "1.0")
        if sv == "2.0":
            print(f"{RULES_FILE} 已存在 (v{sv}, {existing_rules.get('college_name', '?')})，跳过初始化")
        else:
            print(f"{RULES_FILE} 已存在 (v{sv})")
    
    # 从 rules.json 读取分类，创建对应材料目录
    rules = load_rules()
    cat_ids = []
    for cat in rules.get("categories", []):
        cat_ids.append(cat.get("id", "other"))
    if not cat_ids:
        cat_ids = ["academic", "competition", "research", "social_practice", "leadership", "talent", "honor", "certificate"]
    for cid in cat_ids:
        d = MATERIALS_DIR / cid
        d.mkdir(parents=True, exist_ok=True)
        print(f"已创建目录 {d}")

def cmd_add():
    """交互式添加经历"""
    print("=== 添加新经历 ===")
    name = input("经历名称: ").strip()
    if not name:
        print("名称不能为空")
        return
    
    category = input("类型 (academic/competition/research/social_practice/leadership/talent/honor/certificate): ").strip()
    start_date = input("开始日期 (YYYY-MM-DD): ").strip()
    end_date = input("结束日期 (YYYY-MM-DD): ").strip()
    role = input("你的角色: ").strip()
    achievement = input("获得成果/奖项: ").strip()
    description = input("具体做了什么: ").strip()
    
    skills_input = input("提升的能力（逗号分隔）: ").strip()
    skills = [s.strip() for s in skills_input.split(",") if s.strip()]
    
    materials_input = input("关联材料路径（逗号分隔）: ").strip()
    materials = [m.strip() for m in materials_input.split(",") if m.strip()]
    
    rule_id = input("综测规则ID（可选，留空稍后匹配）: ").strip()
    quantity = input("数量（默认1）: ").strip()
    quantity = int(quantity) if quantity.isdigit() else 1
    
    exp = add_experience(
        name=name, category=category, start_date=start_date, end_date=end_date,
        role=role, achievement=achievement, description=description,
        skills_gained=skills, materials=materials, rule_id=rule_id, quantity=quantity
    )
    
    print(f"\n已添加经历: {name}")
    print(f"  ID: {exp['id']}")
    
    if not rule_id:
        rules = load_rules()
        suggestions = suggest_rule(exp, rules)
        if suggestions:
            print("\n  建议匹配的综测规则:")
            for i, s in enumerate(suggestions[:3], 1):
                print(f"    {i}. {s['rule_name']} (+{s['score']}分) [ID: {s['rule_id']}]")

def cmd_list():
    """列出所有经历"""
    data = load_experiences()
    experiences = data.get("experiences", [])
    
    if not experiences:
        print("暂无经历记录")
        return
    
    # 加载规则以显示分类名称
    rules = load_rules()
    cat_names = {}
    for cat in rules.get("categories", []):
        cat_names[cat.get("id", "")] = cat.get("name", cat.get("id", ""))
    
    print(f"\n共 {len(experiences)} 条经历:\n")
    print(f"{'ID':<15} {'名称':<25} {'分类':<15} {'时间':<22} {'角色':<10}")
    print("-" * 95)
    
    for exp in experiences:
        eid = exp.get("id", "")[:12]
        name = exp.get("name", "")[:23]
        cat = exp.get("category", "")
        # 尝试显示分类中文名
        cat_display = cat_names.get(cat, cat)[:13]
        date = f"{exp.get('start_date','')} ~ {exp.get('end_date','')}"[:20]
        role = exp.get("role", "")[:8]
        print(f"{eid:<15} {name:<25} {cat_display:<15} {date:<22} {role:<10}")

def cmd_score():
    """计算综测分"""
    experiences = load_experiences()
    rules = load_rules()
    
    if not rules or not rules.get("categories"):
        print("未找到综测细则，请先配置 data/rules.json")
        return
    
    scores = calculate_all_scores(experiences, rules)
    
    print(f"\n=== 综测分预估汇总 ===")
    print(f"学院: {rules.get('college_name', '未设置')}  学年: {rules.get('academic_year', '未设置')}")
    print(f"预估总分: {scores['total_score']:.1f} 分 (满分 {rules.get('total_structure', {}).get('total_max', 100)})\n")
    
    print("分类明细:")
    for cat_id, cat_info in scores["category_scores"].items():
        st = cat_info.get("scoring_type", "加分")
        cur = cat_info["current_score"]
        mx = cat_info["max_score"]
        base = cat_info.get("base_score", 0)
        bonus_max = cat_info.get("bonus_max")

        if st == "扣分制":
            print(f"  [{st}] {cat_info['name']}: {cur:.1f} / {base} 分 (基准{base}，扣除{base - cur:.1f})")
        elif st == "基础分+加分":
            bonus = cur - base
            total_max = base + (bonus_max or 0)
            cap_str = f" (加分上限{bonus_max})" if bonus_max else ""
            print(f"  [{st}] {cat_info['name']}: {cur:.1f} / {total_max} 分 (基础{base} + 加分{bonus:.1f}){cap_str}")
        elif st == "计算制":
            print(f"  [{st}] {cat_info['name']}: {cur:.1f} / {mx} 分 (需手动输入GPA对应分)")
        else:
            print(f"  [{st}] {cat_info['name']}: {cur:.1f} / {mx} 分")

        for item in cat_info["items"]:
            sc = item["score"]
            if item.get("is_deduction"):
                print(f"      - {item['name']}: {sc:.1f} 分 (扣分)")
            else:
                print(f"      - {item['name']}: +{sc:.1f} 分")
    
    # 显示全局约束
    if scores.get("global_constraints"):
        print(f"\n全局约束检查:")
        for gc in scores["global_constraints"]:
            status = gc.get("status", "")
            if status == "超标":
                print(f"  [!!] {gc['name']}: {gc.get('actual', '?')} > {gc.get('limit', '?')} ({gc.get('description', gc.get('rule', ''))})")
            else:
                note = gc.get("note", gc.get("description", gc.get("rule", "")))
                print(f"  [{status}] {gc['name']}: {note}")

def cmd_missing():
    """检查缺失"""
    experiences = load_experiences()
    materials = scan_materials()
    
    issues = check_missing(experiences, materials)
    unlinked = find_unlinked_materials(experiences, materials)
    
    print(f"\n=== 缺失检查报告 ===")
    
    if issues:
        print(f"\n发现 {len(issues)} 条经历存在问题:\n")
        for issue in issues:
            print(f"  [{issue['id']}] {issue['name']}")
            for m in issue["missing_materials"]:
                print(f"    [缺失] {m}")
            for c in issue["needs_confirm"]:
                print(f"    [需确认] {c}")
    else:
        print("\n所有经历材料完整，无需处理")
    
    if unlinked:
        print(f"\n发现 {len(unlinked)} 个未关联的证明材料:")
        for u in unlinked[:10]:
            print(f"    - {u}")
        if len(unlinked) > 10:
            print(f"    ... 还有 {len(unlinked)-10} 个")
    else:
        print("\n所有材料已关联")

def cmd_scan():
    """扫描材料"""
    materials = scan_materials()
    
    print("\n=== 材料目录扫描结果 ===")
    total = 0
    for category, files in sorted(materials.items()):
        print(f"\n[{category}] {len(files)} 个文件")
        for f in files[:5]:
            print(f"  - {Path(f).name}")
        if len(files) > 5:
            print(f"  ... 还有 {len(files)-5} 个")
        total += len(files)
    
    print(f"\n总计: {total} 个证明材料文件")

def cmd_analyze():
    """分析材料文件"""
    materials = scan_materials()
    if not materials:
        print("未找到材料文件，请将文件放入 materials/ 各分类目录")
        return
    
    drafts = analyze_materials(materials)
    
    print(f"\n=== 材料分析结果 ===")
    print(f"发现 {len(drafts)} 个活动/经历:\n")
    
    for i, draft in enumerate(drafts, 1):
        print(f"{i}. {draft['name']}")
        print(f"   日期: {draft['date'] or '未识别'}")
        print(f"   分类: {draft['category']}")
        print(f"   材料类型: {', '.join(draft['material_types']) or '未识别'}")
        print(f"   文件数: {len(draft['files'])}")
        print(f"   状态: {draft['status']}")
        print()
    
    # 保存草稿到临时文件
    drafts_file = DATA_DIR / "material_drafts.json"
    save_json(drafts_file, {"drafts": drafts, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    print(f"草稿已保存到 {drafts_file}，可在页面中导入确认")

def cmd_extract_rules(filepath: str = ""):
    """从文本提取综测细则"""
    if not filepath:
        print("请提供细则文件路径: python core.py extract-rules 细则.txt")
        return
    
    path = Path(filepath)
    if not path.exists():
        print(f"文件不存在: {filepath}")
        return
    
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    rules = extract_rules_from_text(text)
    
    # 保存
    save_rules(rules)
    print(f"\n=== 综测细则提取结果 ===")
    print(f"学院: {rules['college_name'] or '未识别'}")
    print(f"学年: {rules['academic_year'] or '未识别'}")
    print(f"共 {len(rules['categories'])} 个分类，{sum(len(c['subcategories']) for c in rules['categories'])} 条规则\n")
    
    for cat in rules["categories"]:
        print(f"[{cat['name']}] 上限: {cat['max_score']}分")
        for sub in cat["subcategories"][:5]:
            status = "[待确认]" if sub.get("status") == "待确认" else "[已提取]"
            sc = sub['score']
            score_str = f"{sc}分" if sc < 0 else f"+{sc}分"
            print(f"  {status} {sub['name']}: {score_str} (需: {', '.join(sub.get('evidence_required', []))})")
        if len(cat["subcategories"]) > 5:
            print(f"  ... 还有 {len(cat['subcategories'])-5} 条")
        print()
    
    print(f"细则已保存到 {RULES_FILE}")
    print("请打开 index.html 在'导入导出'页查看并确认提取的规则")

def cmd_dashboard():
    """仪表盘数据"""
    data = get_dashboard_data()
    print(json.dumps(data, ensure_ascii=False, indent=2))

def cmd_suggest(exp_id: str):
    """建议规则"""
    experiences = load_experiences()
    rules = load_rules()
    
    exp = None
    for e in experiences.get("experiences", []):
        if e.get("id") == exp_id:
            exp = e
            break
    
    if not exp:
        print(f"未找到经历: {exp_id}")
        return
    
    suggestions = suggest_rule(exp, rules)
    
    print(f"\n为经历 '{exp.get('title', exp.get('name', ''))}' 推荐的综测规则:\n")
    for i, s in enumerate(suggestions, 1):
        print(f"{i}. {s['rule_name']} ({s['category']})")
        print(f"   加分: +{s['score']} 分")
        print(f"   匹配度: {s['confidence']}/5")
        print(f"   规则ID: {s['rule_id']}")
        print()

def cmd_summary():
    """汇总报告"""
    report = export_summary()
    print(json.dumps(report, ensure_ascii=False, indent=2))

def cmd_export():
    """导出到文件"""
    report = export_summary()
    output_path = OUTPUT_DIR / "summary.json"
    save_json(output_path, report)
    print(f"汇总报告已导出到: {output_path}")

def main():
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    
    if command == "init":
        cmd_init()
    elif command == "add":
        cmd_add()
    elif command == "list":
        cmd_list()
    elif command == "delete":
        if len(sys.argv) < 3:
            print("请提供经历ID: python core.py delete <ID>")
            return
        if delete_experience(sys.argv[2]):
            print(f"已删除经历: {sys.argv[2]}")
        else:
            print(f"未找到经历: {sys.argv[2]}")
    elif command == "score":
        cmd_score()
    elif command == "missing":
        cmd_missing()
    elif command == "scan":
        cmd_scan()
    elif command == "analyze":
        cmd_analyze()
    elif command == "extract-rules":
        filepath = sys.argv[2] if len(sys.argv) > 2 else ""
        cmd_extract_rules(filepath)
    elif command == "dashboard":
        cmd_dashboard()
    elif command == "suggest":
        if len(sys.argv) < 3:
            print("请提供经历ID: python core.py suggest <ID>")
            return
        cmd_suggest(sys.argv[2])
    elif command == "summary":
        cmd_summary()
    elif command == "export":
        cmd_export()
    else:
        print(f"未知命令: {command}")
        print_help()

if __name__ == "__main__":
    main()
