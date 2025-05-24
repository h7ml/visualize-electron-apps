#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化展示跨平台的 Electron 应用程序资源使用情况

此脚本从JSON文件读取Electron应用数据，创建一个Web应用来可视化展示这些数据。
使用Flask作为Web框架，Tailwind CSS进行样式美化，Plotly进行图表可视化。
支持在Windows、macOS和Linux上运行。

命令行使用示例：
--------------

1. 使用默认配置启动可视化工具：
   python visualize_electron_apps.py
   
2. 指定JSON数据文件：
   python visualize_electron_apps.py --json-file my_electron_apps.json
   
3. 指定Web服务器端口：
   python visualize_electron_apps.py --port 5000
   
4. 不自动打开浏览器：
   python visualize_electron_apps.py --no-browser
   
5. 组合使用多个参数：
   python visualize_electron_apps.py --json-file my_data.json --port 3000 --no-browser

常用参数说明：
--------------
--json-file   : 指定JSON数据文件路径 (默认: electron_apps.json)
--port        : 指定Web服务器端口 (默认: 8080)
--no-browser  : 启动服务器后不自动打开浏览器
--host        : 指定Web服务器主机 (默认: 127.0.0.1)

更多详细参数请使用 --help 参数查看。
"""

import os
import json
import pandas as pd
import argparse
import webbrowser
import threading
import time
from flask import Flask, render_template, request, jsonify

# 检查必要的依赖包
try:
    import plotly
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    print("请安装Plotly：pip install plotly")
    exit(1)

app = Flask(__name__)

# 读取JSON数据
def load_data(json_file=None):
    if json_file is None:
        # 尝试从命令行参数中获取
        try:
            args = parse_arguments()
            json_file = args.json_file
        except:
            # 如果无法获取命令行参数，使用默认值
            json_file = 'electron_apps.json'
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"错误：未找到文件 {json_file}")
        return []
    except json.JSONDecodeError:
        print(f"错误：JSON格式不正确 {json_file}")
        return []

# 创建HTML模板目录
os.makedirs('templates', exist_ok=True)

# 创建静态资源目录
os.makedirs('static', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# API路由 - 获取所有应用数据
@app.route('/api/apps')
def get_apps():
    data = load_data()
    return jsonify(data)

# API路由 - 获取内存使用图表数据
@app.route('/api/chart/memory')
def memory_chart():
    data = load_data()
    df = pd.DataFrame(data)
    
    # 只保留运行中的应用
    running_apps = df[df['running'] == True].copy()
    
    if running_apps.empty:
        return jsonify({"error": "没有运行中的应用"})
    
    # 按内存使用量排序
    running_apps = running_apps.sort_values('memory_mb', ascending=False)
    
    # 创建图表数据
    chart_data = {
        'app_names': running_apps['name'].tolist(),
        'memory_usage': running_apps['memory_mb'].tolist(),
        'max_memory': running_apps['memory_mb'].max(),
        'total_memory': running_apps['memory_mb'].sum(),
        'avg_memory': running_apps['memory_mb'].mean(),
    }
    
    return jsonify(chart_data)

# API路由 - 获取CPU使用图表数据
@app.route('/api/chart/cpu')
def cpu_chart():
    data = load_data()
    df = pd.DataFrame(data)
    
    # 只保留运行中且有性能数据的应用
    running_apps = df[(df['running'] == True) & (df['has_performance_data'] == True)].copy()
    
    if running_apps.empty:
        return jsonify({"error": "没有运行中的应用"})
    
    # 按CPU使用率排序
    running_apps = running_apps.sort_values('cpu_percent', ascending=False)
    
    # 创建图表数据
    chart_data = {
        'app_names': running_apps['name'].tolist(),
        'cpu_usage': running_apps['cpu_percent'].tolist(),
        'max_cpu': running_apps['cpu_percent'].max(),
        'total_cpu': running_apps['cpu_percent'].sum(),
        'avg_cpu': running_apps['cpu_percent'].mean(),
    }
    
    return jsonify(chart_data)

# API路由 - 获取应用大小图表数据
@app.route('/api/chart/size')
def size_chart():
    data = load_data()
    df = pd.DataFrame(data)
    
    # 按应用大小排序
    df = df.sort_values('size', ascending=False)
    
    # 取前15个最大的应用
    top_apps = df.head(15)
    
    # 创建图表数据
    chart_data = {
        'app_names': top_apps['name'].tolist(),
        'app_sizes': top_apps['size'].tolist(),
        'max_size': df['size'].max(),
        'total_size': df['size'].sum(),
        'avg_size': df['size'].mean(),
    }
    
    return jsonify(chart_data)

# API路由 - 获取内存/大小比例图表数据
@app.route('/api/chart/ratio')
def ratio_chart():
    data = load_data()
    df = pd.DataFrame(data)
    
    # 只保留运行中的应用
    running_apps = df[df['running'] == True].copy()
    
    if running_apps.empty:
        return jsonify({"error": "没有运行中的应用"})
    
    # 按内存/大小比例排序
    running_apps = running_apps.sort_values('memory_size_ratio', ascending=False)
    
    # 创建图表数据
    chart_data = {
        'app_names': running_apps['name'].tolist(),
        'ratios': running_apps['memory_size_ratio'].tolist(),
        'max_ratio': running_apps['memory_size_ratio'].max(),
        'min_ratio': running_apps['memory_size_ratio'][running_apps['memory_size_ratio'] > 0].min() if any(running_apps['memory_size_ratio'] > 0) else 0,
        'avg_ratio': running_apps['memory_size_ratio'].mean(),
    }
    
    return jsonify(chart_data)

# 创建index.html模板
def create_templates():
    index_html = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Electron应用资源使用分析</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <style>
        [x-cloak] { display: none !important; }
    </style>
</head>
<body class="bg-gray-100 text-gray-900" x-data="appData()">
    <header class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white shadow-lg">
        <div class="container mx-auto px-4 py-6">
            <h1 class="text-3xl font-bold">Electron应用资源使用分析</h1>
            <p class="mt-2 text-blue-100">可视化展示跨平台Electron应用的内存、CPU使用情况和应用大小</p>
        </div>
    </header>

    <main class="container mx-auto px-4 py-8">
        <!-- 数据加载指示器 -->
        <div x-show="loading" class="flex justify-center items-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <span class="ml-3 text-lg">加载数据中...</span>
        </div>

        <div x-cloak x-show="!loading" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 摘要卡片 -->
            <div class="col-span-1 lg:col-span-2 bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4 text-gray-800">系统概览</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div class="bg-blue-50 p-4 rounded-lg border border-blue-200">
                        <p class="text-sm text-blue-600 font-medium">检测到的Electron应用</p>
                        <p class="text-2xl font-bold" x-text="summary.totalApps"></p>
                    </div>
                    <div class="bg-green-50 p-4 rounded-lg border border-green-200">
                        <p class="text-sm text-green-600 font-medium">运行中的应用</p>
                        <p class="text-2xl font-bold" x-text="summary.runningApps"></p>
                    </div>
                    <div class="bg-purple-50 p-4 rounded-lg border border-purple-200">
                        <p class="text-sm text-purple-600 font-medium">总内存使用</p>
                        <p class="text-2xl font-bold" x-text="formatMemory(summary.totalMemory)"></p>
                    </div>
                    <div class="bg-amber-50 p-4 rounded-lg border border-amber-200">
                        <p class="text-sm text-amber-600 font-medium">总CPU使用率</p>
                        <p class="text-2xl font-bold" x-text="summary.totalCpu + '%'"></p>
                    </div>
                </div>
            </div>

            <!-- 内存使用图表 -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4 text-gray-800">内存使用情况</h2>
                <div x-show="memoryError" class="text-red-500 py-10 text-center">
                    <p x-text="memoryError"></p>
                </div>
                <div x-show="!memoryError" id="memoryChart" class="w-full h-80"></div>
            </div>

            <!-- CPU使用图表 -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4 text-gray-800">CPU使用情况</h2>
                <div x-show="cpuError" class="text-red-500 py-10 text-center">
                    <p x-text="cpuError"></p>
                </div>
                <div x-show="!cpuError" id="cpuChart" class="w-full h-80"></div>
            </div>

            <!-- 应用大小图表 -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4 text-gray-800">应用大小分布 (Top 15)</h2>
                <div id="sizeChart" class="w-full h-80"></div>
            </div>

            <!-- 内存/大小比例图表 -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4 text-gray-800">内存使用与应用大小比例</h2>
                <div x-show="ratioError" class="text-red-500 py-10 text-center">
                    <p x-text="ratioError"></p>
                </div>
                <div x-show="!ratioError" id="ratioChart" class="w-full h-80"></div>
            </div>

            <!-- 应用详情表格 -->
            <div class="col-span-1 lg:col-span-2 bg-white rounded-lg shadow-md p-6">
                <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-4">
                    <h2 class="text-xl font-semibold text-gray-800">应用详情</h2>
                    <div class="mt-3 md:mt-0 flex flex-wrap gap-2">
                        <select x-model="sortField" class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="name">按名称</option>
                            <option value="memory_mb">按内存使用</option>
                            <option value="cpu_percent">按CPU使用</option>
                            <option value="size">按应用大小</option>
                            <option value="memory_size_ratio">按内存/大小比例</option>
                        </select>
                        <select x-model="sortDirection" class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="asc">升序</option>
                            <option value="desc">降序</option>
                        </select>
                        <label class="inline-flex items-center">
                            <input type="checkbox" x-model="showOnlyRunning" class="rounded text-blue-600 focus:ring-blue-500">
                            <span class="ml-2 text-sm text-gray-700">仅显示运行中</span>
                        </label>
                    </div>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">应用名称</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">版本</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Electron版本</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">内存使用</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CPU使用率</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">应用大小</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">内存/大小比例</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            <template x-for="app in filteredApps" :key="app.path">
                                <tr class="hover:bg-gray-50">
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="flex items-center">
                                            <div class="text-sm font-medium text-gray-900" x-text="app.name"></div>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm text-gray-500" x-text="app.version"></div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm text-gray-500" x-text="app.electron_version"></div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full" 
                                            :class="app.running ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'"
                                            x-text="app.status">
                                        </span>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm text-gray-500" x-text="formatMemory(app.memory_mb)"></div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm text-gray-500" x-text="app.has_performance_data ? app.cpu_percent + '%' : 'N/A'"></div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm text-gray-500" x-text="formatSize(app.size)"></div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm text-gray-500" x-text="formatRatio(app.memory_size_ratio)"></div>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>

    <footer class="bg-gray-800 text-white py-6">
        <div class="container mx-auto px-4 text-center">
            <p>Electron应用资源使用分析工具 | 基于Flask、Tailwind CSS和Plotly</p>
        </div>
    </footer>

    <script>
        function appData() {
            return {
                apps: [],
                loading: true,
                memoryError: null,
                cpuError: null,
                ratioError: null,
                sortField: 'memory_mb',
                sortDirection: 'desc',
                showOnlyRunning: false,
                summary: {
                    totalApps: 0,
                    runningApps: 0,
                    totalMemory: 0,
                    totalCpu: 0
                },
                init() {
                    this.fetchData();
                },
                async fetchData() {
                    try {
                        const response = await fetch('/api/apps');
                        const data = await response.json();
                        this.apps = data;
                        
                        // 计算摘要数据
                        this.summary.totalApps = this.apps.length;
                        this.summary.runningApps = this.apps.filter(app => app.running).length;
                        this.summary.totalMemory = this.apps.reduce((sum, app) => sum + app.memory_mb, 0);
                        this.summary.totalCpu = this.apps.reduce((sum, app) => sum + app.cpu_percent, 0).toFixed(1);
                        
                        this.loading = false;
                        
                        // 加载图表
                        this.loadMemoryChart();
                        this.loadCpuChart();
                        this.loadSizeChart();
                        this.loadRatioChart();
                    } catch (error) {
                        console.error('Error fetching data:', error);
                        this.loading = false;
                    }
                },
                async loadMemoryChart() {
                    try {
                        const response = await fetch('/api/chart/memory');
                        const data = await response.json();
                        
                        if (data.error) {
                            this.memoryError = data.error;
                            return;
                        }
                        
                        const trace = {
                            x: data.app_names,
                            y: data.memory_usage,
                            type: 'bar',
                            marker: {
                                color: 'rgba(54, 162, 235, 0.8)'
                            }
                        };
                        
                        const layout = {
                            margin: { t: 10, l: 70, r: 10, b: 120 },
                            xaxis: {
                                tickangle: -45
                            },
                            yaxis: {
                                title: '内存使用 (MB)'
                            }
                        };
                        
                        Plotly.newPlot('memoryChart', [trace], layout);
                    } catch (error) {
                        console.error('Error loading memory chart:', error);
                        this.memoryError = '加载内存使用图表时出错';
                    }
                },
                async loadCpuChart() {
                    try {
                        const response = await fetch('/api/chart/cpu');
                        const data = await response.json();
                        
                        if (data.error) {
                            this.cpuError = data.error;
                            return;
                        }
                        
                        const trace = {
                            x: data.app_names,
                            y: data.cpu_usage,
                            type: 'bar',
                            marker: {
                                color: 'rgba(255, 99, 132, 0.8)'
                            }
                        };
                        
                        const layout = {
                            margin: { t: 10, l: 50, r: 10, b: 120 },
                            xaxis: {
                                tickangle: -45
                            },
                            yaxis: {
                                title: 'CPU使用率 (%)'
                            }
                        };
                        
                        Plotly.newPlot('cpuChart', [trace], layout);
                    } catch (error) {
                        console.error('Error loading CPU chart:', error);
                        this.cpuError = '加载CPU使用图表时出错';
                    }
                },
                async loadSizeChart() {
                    try {
                        const response = await fetch('/api/chart/size');
                        const data = await response.json();
                        
                        const trace = {
                            x: data.app_names,
                            y: data.app_sizes,
                            type: 'bar',
                            marker: {
                                color: 'rgba(75, 192, 192, 0.8)'
                            }
                        };
                        
                        const layout = {
                            margin: { t: 10, l: 70, r: 10, b: 120 },
                            xaxis: {
                                tickangle: -45
                            },
                            yaxis: {
                                title: '应用大小 (MB)'
                            }
                        };
                        
                        Plotly.newPlot('sizeChart', [trace], layout);
                    } catch (error) {
                        console.error('Error loading size chart:', error);
                    }
                },
                async loadRatioChart() {
                    try {
                        const response = await fetch('/api/chart/ratio');
                        const data = await response.json();
                        
                        if (data.error) {
                            this.ratioError = data.error;
                            return;
                        }
                        
                        const trace = {
                            x: data.app_names,
                            y: data.ratios,
                            type: 'bar',
                            marker: {
                                color: 'rgba(153, 102, 255, 0.8)'
                            }
                        };
                        
                        const layout = {
                            margin: { t: 10, l: 70, r: 10, b: 120 },
                            xaxis: {
                                tickangle: -45
                            },
                            yaxis: {
                                title: '内存/大小比例'
                            }
                        };
                        
                        Plotly.newPlot('ratioChart', [trace], layout);
                    } catch (error) {
                        console.error('Error loading ratio chart:', error);
                        this.ratioError = '加载内存/大小比例图表时出错';
                    }
                },
                get filteredApps() {
                    let filtered = [...this.apps];
                    
                    if (this.showOnlyRunning) {
                        filtered = filtered.filter(app => app.running);
                    }
                    
                    filtered.sort((a, b) => {
                        const aValue = a[this.sortField] || 0;
                        const bValue = b[this.sortField] || 0;
                        
                        if (this.sortDirection === 'asc') {
                            return aValue - bValue;
                        } else {
                            return bValue - aValue;
                        }
                    });
                    
                    return filtered;
                },
                formatMemory(memory) {
                    if (!memory || memory === 0) return 'N/A';
                    if (memory >= 1024) {
                        return (memory / 1024).toFixed(2) + ' GB';
                    } else {
                        return memory.toFixed(2) + ' MB';
                    }
                },
                formatSize(size) {
                    if (!size) return 'N/A';
                    if (size >= 1024) {
                        return (size / 1024).toFixed(2) + ' GB';
                    } else {
                        return size.toFixed(2) + ' MB';
                    }
                },
                formatRatio(ratio) {
                    if (!ratio || ratio === 0) return 'N/A';
                    return ratio.toFixed(2) + 'x';
                }
            }
        }
    </script>
</body>
</html>
    """
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)

# 添加命令行参数解析
def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='可视化展示Electron应用程序资源使用情况')
    
    parser.add_argument('--json-file', default='electron_apps.json',
                      help='指定JSON数据文件路径 (默认: electron_apps.json)')
    parser.add_argument('--port', type=int, default=8080,
                      help='指定Web服务器端口 (默认: 8080)')
    parser.add_argument('--host', default='127.0.0.1',
                      help='指定Web服务器主机 (默认: 127.0.0.1)')
    parser.add_argument('--no-browser', action='store_true',
                      help='启动服务器后不自动打开浏览器')
    
    return parser.parse_args()

# 创建模板文件
create_templates()

# 主函数
if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()
    
    # 检测平台
    import platform
    is_windows = platform.system() == 'Windows'
    is_macos = platform.system() == 'Darwin'
    is_linux = platform.system() == 'Linux'
    
    # 设置平台特定的说明
    platform_name = "Windows" if is_windows else "macOS" if is_macos else "Linux"
    
    print(f"正在启动Electron应用资源使用分析可视化工具...")
    print("=" * 80)
    print(f"数据文件: {args.json_file}")
    print(f"服务地址: http://{args.host}:{args.port}")
    print("=" * 80)
    
    if not os.path.exists(args.json_file):
        print(f"警告: 未找到 {args.json_file} 文件")
        print(f"请先运行 python find_electron_apps.py --memory --performance --json-file {args.json_file} 导出应用数据")
    
    # 自动打开浏览器
    if not args.no_browser:
        def open_browser():
            time.sleep(1)  # 等待服务器启动
            webbrowser.open(f'http://{args.host}:{args.port}')
        
        threading.Thread(target=open_browser).start()
    
    # 启动Flask应用
    app.run(debug=True, host=args.host, port=args.port) 
