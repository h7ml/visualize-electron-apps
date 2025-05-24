#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Electron应用资源使用情况可视化API

这个脚本为Vercel部署创建Flask API，用于可视化Electron应用的资源使用情况。
"""

import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__)

# 默认演示数据文件路径
DEMO_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_data.json')

# 用户上传数据的临时存储
TEMP_DIR = tempfile.gettempdir()
USER_DATA_FILE = os.path.join(TEMP_DIR, 'user_electron_apps.json')

# 确保演示数据存在
def init_demo_data():
    if not os.path.exists(DEMO_DATA_FILE):
        demo_data = [
            {
                "name": "Visual Studio Code",
                "path": "/Applications/Visual Studio Code.app",
                "version": "1.60.0",
                "electron_version": "13.5.1",
                "size": 674.8,
                "running": True,
                "status": "运行中",
                "memory_mb": 423.5,
                "cpu_percent": 2.8,
                "has_performance_data": True,
                "memory_size_ratio": 0.63
            },
            {
                "name": "Slack",
                "path": "/Applications/Slack.app",
                "version": "4.18.0",
                "electron_version": "12.0.0",
                "size": 485.2,
                "running": True,
                "status": "运行中",
                "memory_mb": 512.6,
                "cpu_percent": 3.2,
                "has_performance_data": True,
                "memory_size_ratio": 1.06
            },
            {
                "name": "Discord",
                "path": "/Applications/Discord.app",
                "version": "0.0.264",
                "electron_version": "13.6.6",
                "size": 398.7,
                "running": True,
                "status": "运行中",
                "memory_mb": 628.9,
                "cpu_percent": 4.5,
                "has_performance_data": True,
                "memory_size_ratio": 1.58
            },
            {
                "name": "Notion",
                "path": "/Applications/Notion.app",
                "version": "2.0.18",
                "electron_version": "16.0.5",
                "size": 345.6,
                "running": False,
                "status": "未运行",
                "memory_mb": 0,
                "cpu_percent": 0,
                "has_performance_data": False,
                "memory_size_ratio": 0
            },
            {
                "name": "Microsoft Teams",
                "path": "/Applications/Microsoft Teams.app",
                "version": "1.4.00.26453",
                "electron_version": "10.4.7",
                "size": 512.3,
                "running": True,
                "status": "运行中",
                "memory_mb": 856.2,
                "cpu_percent": 7.2,
                "has_performance_data": True,
                "memory_size_ratio": 1.67
            }
        ]
        with open(DEMO_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(demo_data, f, ensure_ascii=False, indent=2)

# 读取JSON数据
def load_data():
    # 优先使用用户上传的数据，否则使用演示数据
    if os.path.exists(USER_DATA_FILE):
        json_file = USER_DATA_FILE
    else:
        json_file = DEMO_DATA_FILE
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        if json_file != DEMO_DATA_FILE:
            # 如果用户文件有问题，尝试使用演示数据
            try:
                with open(DEMO_DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 静态文件路由
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# API路由 - 获取所有应用数据
@app.route('/api/apps')
def get_apps():
    data = load_data()
    return jsonify(data)

# API路由 - 获取内存使用图表数据
@app.route('/api/chart/memory')
def memory_chart():
    data = load_data()
    
    # 只保留运行中的应用
    running_apps = [app for app in data if app.get('running', False)]
    
    if not running_apps:
        return jsonify({"error": "没有运行中的应用"})
    
    # 按内存使用量排序
    running_apps.sort(key=lambda x: x.get('memory_mb', 0), reverse=True)
    
    # 创建图表数据
    memory_values = [app.get('memory_mb', 0) for app in running_apps]
    
    chart_data = {
        'app_names': [app.get('name', '') for app in running_apps],
        'memory_usage': memory_values,
        'max_memory': max(memory_values) if memory_values else 0,
        'total_memory': sum(memory_values),
        'avg_memory': sum(memory_values) / len(memory_values) if memory_values else 0,
    }
    
    return jsonify(chart_data)

# API路由 - 获取CPU使用图表数据
@app.route('/api/chart/cpu')
def cpu_chart():
    data = load_data()
    
    # 只保留运行中且有性能数据的应用
    running_apps = [app for app in data if app.get('running', False) and app.get('has_performance_data', False)]
    
    if not running_apps:
        return jsonify({"error": "没有运行中的应用"})
    
    # 按CPU使用率排序
    running_apps.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
    
    # 创建图表数据
    cpu_values = [app.get('cpu_percent', 0) for app in running_apps]
    
    chart_data = {
        'app_names': [app.get('name', '') for app in running_apps],
        'cpu_usage': cpu_values,
        'max_cpu': max(cpu_values) if cpu_values else 0,
        'total_cpu': sum(cpu_values),
        'avg_cpu': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
    }
    
    return jsonify(chart_data)

# API路由 - 获取应用大小图表数据
@app.route('/api/chart/size')
def size_chart():
    data = load_data()
    
    # 按应用大小排序
    sorted_apps = sorted(data, key=lambda x: x.get('size', 0), reverse=True)
    
    # 取前15个最大的应用
    top_apps = sorted_apps[:15]
    
    # 创建图表数据
    size_values = [app.get('size', 0) for app in data]
    
    chart_data = {
        'app_names': [app.get('name', '') for app in top_apps],
        'app_sizes': [app.get('size', 0) for app in top_apps],
        'max_size': max(size_values) if size_values else 0,
        'total_size': sum(size_values),
        'avg_size': sum(size_values) / len(size_values) if size_values else 0,
    }
    
    return jsonify(chart_data)

# API路由 - 获取内存/大小比例图表数据
@app.route('/api/chart/ratio')
def ratio_chart():
    data = load_data()
    
    # 只保留运行中的应用
    running_apps = [app for app in data if app.get('running', False)]
    
    if not running_apps:
        return jsonify({"error": "没有运行中的应用"})
    
    # 按内存/大小比例排序
    running_apps.sort(key=lambda x: x.get('memory_size_ratio', 0), reverse=True)
    
    # 创建图表数据
    ratio_values = [app.get('memory_size_ratio', 0) for app in running_apps]
    
    chart_data = {
        'app_names': [app.get('name', '') for app in running_apps],
        'ratios': ratio_values,
        'max_ratio': max(ratio_values) if ratio_values else 0,
        'min_ratio': min([r for r in ratio_values if r > 0]) if any(r > 0 for r in ratio_values) else 0,
        'avg_ratio': sum(ratio_values) / len(ratio_values) if ratio_values else 0,
    }
    
    return jsonify(chart_data)

# API路由 - 文件上传
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "没有文件部分"}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "没有选择文件"}), 400
        
    if file and file.filename.endswith('.json'):
        filename = secure_filename(file.filename)
        file.save(USER_DATA_FILE)
        
        # 验证JSON格式
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                json.load(f)
            return jsonify({"message": "文件上传成功"}), 200
        except json.JSONDecodeError:
            os.remove(USER_DATA_FILE)
            return jsonify({"error": "无效的JSON格式"}), 400
    
    return jsonify({"error": "只允许上传JSON文件"}), 400

# 初始化演示数据
init_demo_data()

# 本地测试用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) 
