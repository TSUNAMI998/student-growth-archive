#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大学生成长档案库 - Flask 后端服务
运行方式: python app.py
访问地址: http://localhost:5000
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app, origins=['*'])

# === Configuration ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# Ensure directories exist
def ensure_dirs():
    for d in [DATA_DIR, OUTPUT_DIR]:
        os.makedirs(d, exist_ok=True)

ensure_dirs()

# === Data Helpers ===

def load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load {filename}: {e}")
    return default if default is not None else {}

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save {filename}: {e}")
        return False
    return True

def generate_id():
    return f"exp_{uuid.uuid4().hex[:12]}"

# === Initialization ===

def init_data():
    # Rules: load from data/rules.json or generate default
    rules = load_json('rules.json')
    if not rules:
        # Default empty rules
        rules = {
            "schema_version": "2.0",
            "college_name": "",
            "academic_year": "",
            "categories": [],
            "global_constraints": [],
            "total_structure": {}
        }
        save_json('rules.json', rules)
    
    # Experiences
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    save_json('experiences.json', experiences)
    
    # Tags
    tags = load_json('tags.json', {
        "skill_tags": [],
        "achievement_tags": [],
        "role_tags": []
    })
    save_json('tags.json', tags)
    
    return rules, experiences, tags

# === API Routes ===

# --- Rules API ---

@app.route('/api/rules', methods=['GET'])
def get_rules():
    rules = load_json('rules.json')
    return jsonify(rules)

@app.route('/api/rules', methods=['POST'])
def update_rules():
    data = request.get_json()
    if save_json('rules.json', data):
        return jsonify({"success": True})
    return jsonify({"error": "Failed to save"}), 500

# --- Experiences API ---

@app.route('/api/experiences', methods=['GET'])
def get_experiences():
    data = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    return jsonify(data)

@app.route('/api/experiences', methods=['POST'])
def add_experience():
    data = request.get_json()
    exp = data.get('experience', {})
    
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    
    if 'id' not in exp or not exp['id']:
        exp['id'] = generate_id()
    
    exp['created_at'] = exp.get('created_at') or datetime.now().isoformat()
    exp['updated_at'] = datetime.now().isoformat()
    
    # Check if exists (update) or new
    existing = [e for e in experiences.get('experiences', []) if e.get('id') == exp['id']]
    if existing:
        # Update
        for i, e in enumerate(experiences['experiences']):
            if e.get('id') == exp['id']:
                experiences['experiences'][i] = exp
                break
    else:
        experiences['experiences'].append(exp)
    
    experiences['metadata'] = experiences.get('metadata', {})
    experiences['metadata']['total_experiences'] = len(experiences['experiences'])
    experiences['metadata']['last_updated'] = datetime.now().isoformat()
    
    save_json('experiences.json', experiences)
    return jsonify({"success": True, "experience": exp})

@app.route('/api/experiences/<exp_id>', methods=['DELETE'])
def delete_experience(exp_id):
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    
    experiences['experiences'] = [e for e in experiences.get('experiences', []) if e.get('id') != exp_id]
    experiences['metadata'] = experiences.get('metadata', {})
    experiences['metadata']['total_experiences'] = len(experiences['experiences'])
    experiences['metadata']['last_updated'] = datetime.now().isoformat()
    
    save_json('experiences.json', experiences)
    return jsonify({"success": True})

@app.route('/api/experiences/<exp_id>', methods=['GET'])
def get_experience(exp_id):
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    for e in experiences.get('experiences', []):
        if e.get('id') == exp_id:
            return jsonify(e)
    return jsonify({"error": "Not found"}), 404

# --- Student Info API ---

@app.route('/api/student', methods=['GET'])
def get_student():
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    return jsonify(experiences.get('student_info', {}))

@app.route('/api/student', methods=['POST'])
def update_student():
    data = request.get_json()
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    experiences['student_info'] = data
    save_json('experiences.json', experiences)
    return jsonify({"success": True})

# --- Tags API ---

@app.route('/api/tags', methods=['GET'])
def get_tags():
    tags = load_json('tags.json', {
        "skill_tags": [],
        "achievement_tags": [],
        "role_tags": []
    })
    return jsonify(tags)

@app.route('/api/tags', methods=['POST'])
def update_tags():
    data = request.get_json()
    save_json('tags.json', data)
    return jsonify({"success": True})

# --- Score Calculation API ---

@app.route('/api/score', methods=['GET'])
def calculate_score():
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    rules = load_json('rules.json', {})
    
    student_info = experiences.get('student_info', {})
    gpa = student_info.get('gpa', 0)
    student_type = student_info.get('student_type', 'undergrad')  # undergrad, master, phd
    
    exps = experiences.get('experiences', [])
    
    # Initialize score structure
    scores = {
        "basic_quality": {"score": 10.0, "max": 10.0, "items": []},
        "academic_score": {"score": 0.0, "max": 60.0, "items": []},
        "academic_research": {"score": 10.0, "base": 10.0, "bonus": 0.0, "max_bonus": 10.0, "items": []},
        "practice": {"score": 10.0, "base": 10.0, "bonus": 0.0, "max_bonus": 10.0, "items": []},
    }
    
    # Calculate academic score based on GPA
    if student_type == 'phd':
        academic_score = 60.0
    elif student_type == 'master':
        academic_score = gpa * 25 * 0.6
    else:
        academic_score = gpa * 25 * 0.6  # undergrad same formula
    
    academic_score = min(academic_score, 60.0)
    scores['academic_score']['score'] = round(academic_score, 2)
    scores['academic_score']['items'].append({
        "name": "学业成绩",
        "score": round(academic_score, 2),
        "gpa": gpa,
        "type": student_type
    })
    
    # Calculate other categories from experiences
    # Group experiences by category
    cat_exps = {}
    for exp in exps:
        cat = exp.get('category', 'other')
        if cat not in cat_exps:
            cat_exps[cat] = []
        cat_exps[cat].append(exp)
    
    # Process experiences and calculate scores
    for exp in exps:
        rule_id = exp.get('rule_id', '')
        quantity = exp.get('quantity', 1)
        
        if not rule_id:
            continue
        
        # Find rule
        rule_score = 0
        rule_max = 0
        rule_cat = ''
        
        for cat in rules.get('categories', []):
            for sub in cat.get('subcategories', []):
                if sub.get('id') == rule_id:
                    rule_score = sub.get('score', 0)
                    rule_max = sub.get('max_score', rule_score)
                    rule_cat = cat.get('id', '')
                    break
        
        if not rule_cat:
            continue
        
        item_score = rule_score * quantity
        
        if rule_cat == 'basic_quality':
            scores['basic_quality']['score'] += item_score
            scores['basic_quality']['items'].append({
                "name": exp.get('name', ''),
                "score": item_score,
                "rule_id": rule_id,
                "quantity": quantity
            })
        elif rule_cat == 'academic_research':
            scores['academic_research']['bonus'] += item_score
            scores['academic_research']['items'].append({
                "name": exp.get('name', ''),
                "score": item_score,
                "rule_id": rule_id,
                "quantity": quantity
            })
        elif rule_cat == 'practice':
            scores['practice']['bonus'] += item_score
            scores['practice']['items'].append({
                "name": exp.get('name', ''),
                "score": item_score,
                "rule_id": rule_id,
                "quantity": quantity
            })
    
    # Apply caps
    scores['basic_quality']['score'] = max(0, min(scores['basic_quality']['score'], scores['basic_quality']['max']))
    scores['academic_research']['bonus'] = min(scores['academic_research']['bonus'], scores['academic_research']['max_bonus'])
    scores['academic_research']['score'] = scores['academic_research']['base'] + scores['academic_research']['bonus']
    scores['practice']['bonus'] = min(scores['practice']['bonus'], scores['practice']['max_bonus'])
    scores['practice']['score'] = scores['practice']['base'] + scores['practice']['bonus']
    
    # Apply global constraint: academic_research bonus + practice bonus <= 10
    total_bonus = scores['academic_research']['bonus'] + scores['practice']['bonus']
    if total_bonus > 10:
        # Scale down proportionally
        scale = 10 / total_bonus
        scores['academic_research']['bonus'] = round(scores['academic_research']['bonus'] * scale, 2)
        scores['practice']['bonus'] = round(scores['practice']['bonus'] * scale, 2)
        scores['academic_research']['score'] = scores['academic_research']['base'] + scores['academic_research']['bonus']
        scores['practice']['score'] = scores['practice']['base'] + scores['practice']['bonus']
    
    # Calculate total
    total = (
        scores['basic_quality']['score'] +
        scores['academic_score']['score'] +
        scores['academic_research']['score'] +
        scores['practice']['score']
    )
    
    scores['total_score'] = round(total, 2)
    scores['total_max'] = 100
    
    return jsonify(scores)

# --- Check Missing API ---

@app.route('/api/check', methods=['GET'])
def check_missing():
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    
    exps = experiences.get('experiences', [])
    issues = []
    
    for exp in exps:
        exp_issues = {
            "id": exp.get('id'),
            "name": exp.get('name', ''),
            "missing_materials": [],
            "missing_fields": [],
            "warnings": []
        }
        
        # Check required fields
        if not exp.get('name'):
            exp_issues['missing_fields'].append('名称')
        if not exp.get('category'):
            exp_issues['missing_fields'].append('分类')
        if not exp.get('start_date'):
            exp_issues['missing_fields'].append('开始日期')
        
        # Check materials
        materials = exp.get('materials', [])
        if not materials:
            exp_issues['warnings'].append('未关联任何材料')
        else:
            for mat in materials:
                mat_path = mat
                if mat_path.startswith('materials/'):
                    full_path = os.path.join(BASE_DIR, mat_path)
                else:
                    full_path = mat_path
                
                if not os.path.exists(full_path):
                    exp_issues['missing_materials'].append(mat)
        
        # Check rule mapping
        if not exp.get('rule_id'):
            exp_issues['warnings'].append('未关联综测规则')
        
        if exp_issues['missing_fields'] or exp_issues['missing_materials'] or exp_issues['warnings']:
            issues.append(exp_issues)
    
    return jsonify({
        "issues": issues,
        "total_experiences": len(exps),
        "total_issues": len(issues)
    })

# --- Export API ---

@app.route('/api/export', methods=['POST'])
def export_data():
    """Export all data as JSON"""
    data = {
        "rules": load_json('rules.json'),
        "experiences": load_json('experiences.json'),
        "tags": load_json('tags.json')
    }
    return jsonify(data)

@app.route('/api/import', methods=['POST'])
def import_data():
    """Import data from JSON"""
    data = request.get_json()
    
    if 'rules' in data:
        save_json('rules.json', data['rules'])
    if 'experiences' in data:
        save_json('experiences.json', data['experiences'])
    if 'tags' in data:
        save_json('tags.json', data['tags'])
    
    return jsonify({"success": True})

# --- GPA Update API ---

@app.route('/api/gpa', methods=['POST'])
def update_gpa():
    data = request.get_json()
    gpa = data.get('gpa', 0)
    student_type = data.get('student_type', 'undergrad')
    
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    
    experiences['student_info'] = experiences.get('student_info', {})
    experiences['student_info']['gpa'] = gpa
    experiences['student_info']['student_type'] = student_type
    
    save_json('experiences.json', experiences)
    return jsonify({"success": True})

# --- Generate Report API ---

@app.route('/api/generate/zongce', methods=['GET'])
def generate_zongce():
    """Generate zongce report data"""
    experiences = load_json('experiences.json', {
        "schema_version": "1.0",
        "student_info": {},
        "experiences": [],
        "metadata": {}
    })
    rules = load_json('rules.json', {})
    scores = calculate_score().get_json()
    
    student = experiences.get('student_info', {})
    exps = experiences.get('experiences', [])
    
    # Group by category
    categories = {}
    for exp in exps:
        cat = exp.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(exp)
    
    report = {
        "student_info": student,
        "academic_year": rules.get('academic_year', ''),
        "college_name": rules.get('college_name', ''),
        "scores": scores,
        "categories": categories,
        "experiences": exps
    }
    
    return jsonify(report)

# === Serve frontend for all non-API routes ===

@app.route('/<path:path>')
def catch_all(path):
    # Serve index.html for SPA routes
    if path.startswith('api/'):
        return jsonify({"error": "API endpoint not found"}), 404
    
    # Check if it's a static file
    file_path = os.path.join(BASE_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path)
    
    # Default to index.html
    return send_file(os.path.join(BASE_DIR, 'index.html'))

# === Main ===

if __name__ == '__main__':
    init_data()
    print("="*60)
    print("  大学生成长档案库")
    print("="*60)
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  访问地址: http://localhost:5000")
    print(f"  数据目录: {DATA_DIR}")
    print("="*60)
    print()
    print("  提示: 请确保已安装依赖:")
    print("  pip install flask flask-cors")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
