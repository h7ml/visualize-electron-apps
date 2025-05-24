#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找 macOS 和 Windows 上的 Electron 应用程序

此脚本扫描系统上的应用程序目录，识别基于 Electron 框架构建的应用程序。
它使用多种检测方法来确保高准确度，并提供有关找到的 Electron 应用程序的详细信息，
包括内存使用、CPU 使用率和能耗情况。

命令行使用示例：
--------------

1. 基本扫描（仅识别Electron应用）：
   python find_electron_apps.py
   
2. 分析内存使用情况：
   python find_electron_apps.py --memory
   
3. 分析性能（CPU使用率等）：
   python find_electron_apps.py --performance
   
4. 分析内存、性能和内存/大小比例：
   python find_electron_apps.py --memory --performance --ratio
   
5. 按特定方式排序结果：
   python find_electron_apps.py --sort memory  # 按内存使用排序
   python find_electron_apps.py --sort size    # 按应用大小排序
   python find_electron_apps.py --sort cpu     # 按CPU使用率排序
   python find_electron_apps.py --sort name    # 按名称排序
   
6. 只显示资源使用最多的前N个应用：
   python find_electron_apps.py --memory --performance --top 10
   
7. 指定要扫描的目录：
   python find_electron_apps.py --directories "/Applications" "~/Applications"
   
8. 导出结果到JSON文件：
   python find_electron_apps.py --json-file electron_apps.json
   
9. 设置多线程处理：
   python find_electron_apps.py --workers 16

常用参数说明：
--------------
--memory       : 分析内存使用情况
--performance  : 分析CPU使用率和能耗
--ratio        : 显示内存/大小比例
--sort         : 结果排序方式（name, size, version, memory, cpu）
--top          : 只显示前N个应用
--directories  : 要扫描的目录，默认为系统应用目录
--json-file    : 导出结果到指定的JSON文件
--workers      : 同时处理的最大线程数量

更多详细参数请使用 --help 参数查看。
"""

import os
import sys
import argparse
import platform
import plistlib
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time
import re
import json
import shutil

# 平台检测
IS_WINDOWS = platform.system() == 'Windows'
IS_MACOS = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'

# 尝试导入 psutil，如果没有安装则捕获异常
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("提示: 未安装 psutil 库，某些性能分析功能将受限。")
    print("      可以通过运行以下命令安装它: pip install psutil")
    print("      如果使用 conda 环境，可以运行: conda install psutil")
    print("-" * 80)

# 默认扫描目录
if IS_WINDOWS:
    DEFAULT_SEARCH_DIRS = [
        os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files')),
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
        os.path.join(os.environ.get('APPDATA', ''), 'Programs'),
    ]
elif IS_MACOS:
    DEFAULT_SEARCH_DIRS = [
        '/Applications',
        os.path.expanduser('~/Applications'),
        '/System/Applications',
    ]
else:  # Linux或其他系统
    DEFAULT_SEARCH_DIRS = [
        '/usr/share/applications',
        '/usr/local/share/applications',
        os.path.expanduser('~/.local/share/applications'),
    ]

# Electron 应用的特征标记
ELECTRON_MARKERS_MACOS = [
    'Electron Framework.framework',
    'electron.icns',
    'app.asar',
    'libnode.dylib',
]

ELECTRON_MARKERS_WINDOWS = [
    'electron.exe',
    'resources\\app.asar',
    'resources\\electron.asar',
    'resources\\default_app.asar',
    'locales\\en-US.pak',
]

# 根据平台选择标记
ELECTRON_MARKERS = ELECTRON_MARKERS_MACOS if IS_MACOS else ELECTRON_MARKERS_WINDOWS

# 存储结果的全局变量
electron_apps = []
apps_count = 0
processed_count = 0

def is_electron_app_windows(app_path):
    """
    检测Windows上的应用是否是基于Electron的应用
    
    参数:
        app_path: 应用程序目录的路径
        
    返回:
        bool: 如果是Electron应用则返回True，否则返回False
    """
    try:
        # 检查应用是否是目录
        if not os.path.isdir(app_path):
            # 如果是.exe文件，检查同名目录
            if app_path.lower().endswith('.exe'):
                app_dir = os.path.dirname(app_path)
                app_name = os.path.splitext(os.path.basename(app_path))[0]
                # 有些Electron应用将资源文件放在与EXE同名的目录中
                resources_dir = os.path.join(app_dir, app_name, 'resources')
                if os.path.isdir(resources_dir):
                    app_path = os.path.join(app_dir, app_name)
                else:
                    # 资源文件直接放在应用目录中
                    resources_dir = os.path.join(app_dir, 'resources')
                    if os.path.isdir(resources_dir):
                        app_path = app_dir
                    else:
                        return False
            else:
                return False
        
        # 特殊情况处理：已知的Electron应用
        app_name = os.path.basename(app_path).lower()
        known_electron_apps = [
            'visual studio code', 'vscode', 'code',  # VSCode
            'slack',                                  # Slack
            'discord',                                # Discord
            'figma',                                  # Figma
            'microsoft teams',                        # Microsoft Teams
            'postman',                                # Postman
            'notion',                                 # Notion
            'obsidian',                               # Obsidian
            'spotify',                                # Spotify
            'whatsapp',                               # WhatsApp
            'zoom',                                   # Zoom
            'cursor',                                 # Cursor Editor
            'vscodium',                               # VSCodium
        ]
        
        # 如果应用名称在已知Electron应用列表中，直接返回True
        if app_name in known_electron_apps:
            return True
        
        # 检查是否包含Electron特征标记
        for marker in ELECTRON_MARKERS_WINDOWS:
            marker_path = os.path.join(app_path, marker)
            if os.path.exists(marker_path):
                return True
        
        # 检查资源目录
        resources_dir = os.path.join(app_path, 'resources')
        if os.path.isdir(resources_dir):
            # 检查asar文件
            if os.path.exists(os.path.join(resources_dir, 'app.asar')) or \
               os.path.exists(os.path.join(resources_dir, 'electron.asar')):
                return True
        
        # 检查locales目录
        locales_dir = os.path.join(app_path, 'locales')
        if os.path.isdir(locales_dir):
            if os.path.exists(os.path.join(locales_dir, 'en-US.pak')):
                return True
        
        # 检查可执行文件是否包含Electron字符串
        exe_files = [f for f in os.listdir(app_path) if f.endswith('.exe')]
        for exe_file in exe_files:
            try:
                exe_path = os.path.join(app_path, exe_file)
                with open(exe_path, 'rb') as f:
                    content = f.read()
                    if b'Electron' in content or b'electron.asar' in content or b'app.asar' in content:
                        return True
            except (IOError, PermissionError):
                pass
        
        return False
    except Exception as e:
        print(f"检查应用 {app_path} 时出错: {str(e)}")
        return False

def is_electron_app(app_path):
    """
    检测一个应用是否是基于 Electron 的应用
    
    参数:
        app_path: 应用程序包的路径
        
    返回:
        bool: 如果是 Electron 应用则返回 True，否则返回 False
    """
    # 根据平台选择相应的实现
    if IS_WINDOWS:
        return is_electron_app_windows(app_path)
    
    # macOS实现
    try:
        # 检查应用是否是有效的 .app 包
        if not app_path.endswith('.app') or not os.path.isdir(app_path):
            return False
        
        # 特殊情况处理：已知的 Electron 应用
        app_name = os.path.basename(app_path).lower()
        known_electron_apps = [
            'visual studio code.app', 'vscode.app', 'code.app',  # VSCode
            'slack.app',                                          # Slack
            'discord.app',                                        # Discord
            'figma.app',                                          # Figma
            'microsoft teams.app',                                # Microsoft Teams
            'postman.app',                                        # Postman
            'notion.app',                                         # Notion
            'obsidian.app',                                       # Obsidian
            'spotify.app',                                        # Spotify
            'whatsapp.app',                                       # WhatsApp
            'zoom.app',                                           # Zoom
            'cursor.app',                                         # Cursor Editor
            'vscodium.app',                                       # VSCodium
        ]
        
        # 如果应用名称在已知 Electron 应用列表中，直接返回 True
        if app_name in known_electron_apps:
            return True
        
        # 检查是否包含 Electron 特征标记
        for marker in ELECTRON_MARKERS_MACOS:
            # 在 Contents 目录中搜索特征文件
            contents_dir = os.path.join(app_path, 'Contents')
            if not os.path.isdir(contents_dir):
                continue
                
            # 检查 Resources 目录
            resources_dir = os.path.join(contents_dir, 'Resources')
            if os.path.exists(resources_dir):
                if marker == 'app.asar' and os.path.exists(os.path.join(resources_dir, 'app.asar')):
                    return True
                if marker == 'electron.icns' and os.path.exists(os.path.join(resources_dir, 'electron.icns')):
                    return True
            
            # 检查 Frameworks 目录
            frameworks_dir = os.path.join(contents_dir, 'Frameworks')
            if os.path.exists(frameworks_dir):
                if marker == 'Electron Framework.framework' and os.path.exists(os.path.join(frameworks_dir, 'Electron Framework.framework')):
                    return True
                if marker == 'libnode.dylib':
                    for root, _, files in os.walk(frameworks_dir):
                        if 'libnode.dylib' in files:
                            return True
        
        # 检查应用是否包含 Electron Helper 进程（特别是针对 VSCode 等应用）
        helper_patterns = ['Code Helper', 'Electron Helper', 'Helper (Renderer)', 'Helper (GPU)', 'Helper (Plugin)']
        frameworks_dir = os.path.join(app_path, 'Contents', 'Frameworks')
        if os.path.exists(frameworks_dir):
            for item in os.listdir(frameworks_dir):
                if any(pattern in item for pattern in helper_patterns):
                    return True
            
        # 检查 Info.plist 中是否包含 Electron 相关信息
        plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
        if os.path.exists(plist_path):
            try:
                with open(plist_path, 'rb') as fp:
                    plist_data = plistlib.load(fp)
                    
                    # 检查 CFBundleExecutable 是否为 Electron
                    executable = plist_data.get('CFBundleExecutable', '')
                    if executable and ('electron' in executable.lower() or 'nwjs' in executable.lower() or 'code' in executable.lower()):
                        return True
                    
                    # 检查 NSPrincipalClass 是否包含 "AtomApplication"
                    principal_class = plist_data.get('NSPrincipalClass', '')
                    if principal_class and ('AtomApplication' in principal_class or 'ElectronApplication' in principal_class):
                        return True
                        
                    # 检查 CFBundleDocumentTypes 是否包含 Electron 相关信息
                    doc_types = plist_data.get('CFBundleDocumentTypes', [])
                    for doc_type in doc_types:
                        if 'CFBundleTypeName' in doc_type and 'electron' in str(doc_type['CFBundleTypeName']).lower():
                            return True
                        
            except Exception:
                pass
                
        return False
    except Exception as e:
        print(f"检查应用 {app_path} 时出错: {str(e)}")
        return False

def get_electron_version_windows(app_path):
    """
    尝试获取Windows上Electron应用的版本
    
    参数:
        app_path: 应用程序目录的路径
        
    返回:
        str: 应用的Electron版本，如果无法确定则返回"未知"
    """
    try:
        # 方法1：从package.json获取版本信息
        # 检查可能的package.json位置
        package_json_paths = [
            os.path.join(app_path, 'resources', 'app', 'package.json'),
            os.path.join(app_path, 'resources', 'app.asar.unpacked', 'package.json')
        ]
        
        for package_path in package_json_paths:
            if os.path.exists(package_path):
                try:
                    with open(package_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                        if 'devDependencies' in package_data and 'electron' in package_data['devDependencies']:
                            return package_data['devDependencies']['electron']
                        if 'dependencies' in package_data and 'electron' in package_data['dependencies']:
                            return package_data['dependencies']['electron']
                except Exception:
                    pass
        
        # 方法2：检查可执行文件的版本信息
        # 在Windows上，可以通过检查electron.exe的版本资源获取版本
        if HAS_PSUTIL:
            try:
                exe_files = [f for f in os.listdir(app_path) if f.endswith('.exe')]
                for exe_file in exe_files:
                    exe_path = os.path.join(app_path, exe_file)
                    if os.path.exists(exe_path):
                        # 使用subprocess执行WMIC命令获取文件版本
                        cmd = ['wmic', 'datafile', 'where', f'name="{exe_path.replace("\\", "\\\\")}"', 'get', 'Version', '/value']
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                            if result.returncode == 0:
                                output = result.stdout
                                version_match = re.search(r'Version=(.+)', output)
                                if version_match:
                                    version = version_match.group(1).strip()
                                    if version:
                                        return version
                        except Exception:
                            pass
            except Exception:
                pass
                
        # 方法3：检查about.html或类似文件
        about_paths = [
            os.path.join(app_path, 'resources', 'app', 'about.html'),
            os.path.join(app_path, 'resources', 'about.html')
        ]
        
        for about_path in about_paths:
            if os.path.exists(about_path):
                try:
                    with open(about_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        version_match = re.search(r'Electron\s+v?(\d+\.\d+\.\d+)', content)
                        if version_match:
                            return version_match.group(1)
                except Exception:
                    pass
        
        return "未知"
    except Exception as e:
        print(f"获取 {app_path} 的版本时出错: {str(e)}")
        return "未知"

def get_electron_version(app_path):
    """
    尝试获取 Electron 应用的版本
    
    参数:
        app_path: 应用程序包的路径
        
    返回:
        str: 应用的 Electron 版本，如果无法确定则返回 "未知"
    """
    # 根据平台选择相应的实现
    if IS_WINDOWS:
        return get_electron_version_windows(app_path)
    
    # macOS实现
    try:
        # 方法1：从 Electron Framework 的版本信息中获取
        framework_path = os.path.join(app_path, 'Contents', 'Frameworks', 'Electron Framework.framework')
        if os.path.exists(framework_path):
            version_path = os.path.join(framework_path, 'Versions')
            if os.path.exists(version_path):
                versions = [v for v in os.listdir(version_path) if v != 'Current' and os.path.isdir(os.path.join(version_path, v))]
                if versions:
                    return versions[0]
        
        # 方法2：从 package.json 中获取
        resources_dir = os.path.join(app_path, 'Contents', 'Resources')
        package_json_paths = [
            os.path.join(resources_dir, 'app', 'package.json'),
            os.path.join(resources_dir, 'app.asar.unpacked', 'package.json')
        ]
        
        for package_path in package_json_paths:
            if os.path.exists(package_path):
                try:
                    with open(package_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                        if 'devDependencies' in package_data and 'electron' in package_data['devDependencies']:
                            return package_data['devDependencies']['electron']
                        if 'dependencies' in package_data and 'electron' in package_data['dependencies']:
                            return package_data['dependencies']['electron']
                except Exception:
                    pass
        
        # 方法3：使用 strings 命令在二进制文件中查找版本信息
        try:
            executable_path = os.path.join(app_path, 'Contents', 'MacOS')
            if os.path.exists(executable_path):
                executable_files = os.listdir(executable_path)
                if executable_files:
                    main_executable = os.path.join(executable_path, executable_files[0])
                    result = subprocess.run(['strings', main_executable], capture_output=True, text=True)
                    output = result.stdout
                    
                    # 使用正则表达式查找版本模式
                    version_pattern = r'Electron/(\d+\.\d+\.\d+)'
                    match = re.search(version_pattern, output)
                    if match:
                        return match.group(1)
                    
                    # 尝试另一种格式
                    chrome_pattern = r'Chrome/(\d+\.\d+\.\d+\.\d+)'
                    match = re.search(chrome_pattern, output)
                    if match:
                        return f"基于 Chrome {match.group(1)}"
        except Exception:
            pass
            
        return "未知"
    except Exception as e:
        print(f"获取 {app_path} 的版本时出错: {str(e)}")
        return "未知"

def get_memory_usage_windows(app_path):
    """
    获取Windows上应用程序的内存使用情况
    
    参数:
        app_path: 应用程序目录的路径
        
    返回:
        dict: 包含内存使用信息的字典，包括总内存、是否运行中等
    """
    try:
        app_name = os.path.basename(app_path)
        # 如果是.exe文件，提取基本名称
        if app_name.lower().endswith('.exe'):
            app_name = os.path.splitext(app_name)[0]
            
        # 存储结果
        memory_info = {
            'running': False,
            'memory_mb': 0,
            'processes': 0,
            'status': '未运行',
            'process_details': None
        }
        
        # 如果没有psutil库，无法获取详细的内存信息
        if not HAS_PSUTIL:
            # 尝试使用tasklist命令获取进程信息
            try:
                cmd = ['tasklist', '/fo', 'csv', '/nh']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    processes = []
                    total_memory = 0
                    
                    for line in lines:
                        # 格式: "Image Name","PID","Session Name","Session#","Mem Usage"
                        if not line.strip():
                            continue
                            
                        parts = line.split(',')
                        if len(parts) >= 5:
                            process_name = parts[0].strip('"')
                            # 检查进程名是否与应用名匹配
                            if app_name.lower() in process_name.lower():
                                try:
                                    pid = int(parts[1].strip('"'))
                                    mem_str = parts[4].strip('"').replace(',', '').replace(' K', '')
                                    mem_kb = int(mem_str)
                                    mem_mb = mem_kb / 1024  # 转换为MB
                                    
                                    total_memory += mem_mb
                                    processes.append({
                                        'pid': pid,
                                        'memory_mb': mem_mb,
                                        'command': process_name
                                    })
                                except (ValueError, IndexError):
                                    continue
                    
                    if processes:
                        memory_info['running'] = True
                        memory_info['memory_mb'] = total_memory
                        memory_info['processes'] = len(processes)
                        memory_info['status'] = f"运行中 ({len(processes)} 进程)"
                        memory_info['process_details'] = processes
            except Exception as e:
                print(f"使用tasklist获取内存信息时出错: {str(e)}")
                
            return memory_info
        
        # 使用psutil获取进程信息
        processes = []
        total_memory = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'exe']):
            try:
                # 检查进程的可执行文件路径或名称是否与应用相关
                proc_info = proc.info
                
                # 检查可执行文件路径是否以应用路径开头
                if proc_info.get('exe') and app_path.lower() in proc_info['exe'].lower():
                    mem = proc.memory_info().rss / (1024 * 1024)  # 转换为MB
                    total_memory += mem
                    processes.append({
                        'pid': proc.pid,
                        'memory_mb': mem,
                        'command': proc_info.get('exe', '')
                    })
                # 检查进程名称是否包含应用名
                elif app_name.lower() in proc_info.get('name', '').lower():
                    mem = proc.memory_info().rss / (1024 * 1024)  # 转换为MB
                    total_memory += mem
                    processes.append({
                        'pid': proc.pid,
                        'memory_mb': mem,
                        'command': proc_info.get('name', '')
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        memory_info = {
            'running': len(processes) > 0,
            'memory_mb': total_memory,
            'processes': len(processes),
            'status': f"运行中 ({len(processes)} 进程)" if len(processes) > 0 else "未运行",
            'process_details': processes if len(processes) > 0 else None
        }
        
        return memory_info
    except Exception as e:
        print(f"获取应用 {app_path} 内存使用情况时出错: {str(e)}")
        return {
            'running': False,
            'memory_mb': 0,
            'processes': 0,
            'status': '未知'
        }

def get_memory_usage(app_path):
    """
    获取应用程序的内存使用情况
    
    参数:
        app_path: 应用程序包的路径
        
    返回:
        dict: 包含内存使用信息的字典，包括总内存、是否运行中等
    """
    # 根据平台选择相应的实现
    if IS_WINDOWS:
        return get_memory_usage_windows(app_path)
    
    # macOS实现
    try:
        app_name = os.path.basename(app_path).replace('.app', '')
        
        # 获取应用的进程信息
        # 使用 ps 命令获取包含应用名称的所有进程
        cmd = ['ps', '-eo', 'pid,rss,command']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {
                'running': False,
                'memory_mb': 0,
                'processes': 0,
                'status': '未运行'
            }
        
        # 分析输出以找到匹配的进程
        lines = result.stdout.strip().split('\n')
        total_memory = 0
        processes = []
        
        # 查找可能的进程名模式
        # 1. 直接匹配应用名称
        # 2. 匹配应用路径
        # 3. 匹配 Electron Helper 进程
        app_path_pattern = re.escape(app_path)
        app_name_pattern = re.escape(app_name)
        
        for line in lines[1:]:  # 跳过标题行
            parts = line.strip().split(None, 2)
            if len(parts) < 3:
                continue
                
            pid, rss, command = parts
            
            # 检查是否是目标应用的进程
            is_target = False
            
            # 检查命令行是否包含应用路径
            if re.search(app_path_pattern, command, re.IGNORECASE):
                is_target = True
            # 检查命令行是否包含应用名称（更宽松的匹配）
            elif re.search(app_name_pattern, command, re.IGNORECASE):
                # 排除可能的误匹配（例如，如果应用名是常见词）
                if not re.search(r'\/Library\/', command) and not re.search(r'\/System\/', command):
                    is_target = True
            # 检查是否是 Electron Helper 进程
            elif 'Electron Helper' in command and app_name_pattern in command:
                is_target = True
                
            if is_target:
                try:
                    mem = int(rss) / 1024  # 转换为 MB
                    total_memory += mem
                    processes.append({
                        'pid': pid,
                        'memory_mb': mem,
                        'command': command
                    })
                except ValueError:
                    pass
        
        return {
            'running': len(processes) > 0,
            'memory_mb': total_memory,
            'processes': len(processes),
            'status': f"运行中 ({len(processes)} 进程)" if len(processes) > 0 else "未运行",
            'process_details': processes if len(processes) > 0 else None
        }
    except Exception as e:
        print(f"获取应用 {app_path} 内存使用情况时出错: {str(e)}")
        return {
            'running': False,
            'memory_mb': 0,
            'processes': 0,
            'status': '未知'
        }

def get_process_performance_windows(app_path):
    """
    获取Windows上应用程序的性能信息，包括CPU使用率
    
    参数:
        app_path: 应用程序目录的路径
        
    返回:
        dict: 包含性能信息的字典，包括CPU使用率等
    """
    try:
        app_name = os.path.basename(app_path)
        # 如果是.exe文件，提取基本名称
        if app_name.lower().endswith('.exe'):
            app_name = os.path.splitext(app_name)[0]
            
        performance_info = {
            'cpu_percent': 0,
            'num_threads': 0,
            'energy_impact': 'N/A',  # Windows不提供能耗信息
            'has_performance_data': False
        }
        
        # 如果没有psutil库，无法获取详细的性能信息
        if not HAS_PSUTIL:
            return performance_info
        
        # 使用psutil获取进程信息
        pids = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                # 检查进程的可执行文件路径或名称是否与应用相关
                proc_info = proc.info
                
                # 检查可执行文件路径是否以应用路径开头
                if proc_info.get('exe') and app_path.lower() in proc_info['exe'].lower():
                    pids.append(proc.pid)
                # 检查进程名称是否包含应用名
                elif app_name.lower() in proc_info.get('name', '').lower():
                    pids.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if not pids:
            return performance_info
        
        # 获取CPU使用率和线程数
        total_cpu_percent = 0
        total_threads = 0
        
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                # 获取CPU使用率
                cpu_percent = proc.cpu_percent(interval=0.1)
                total_cpu_percent += cpu_percent
                
                # 获取线程数
                total_threads += proc.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        performance_info = {
            'cpu_percent': total_cpu_percent,
            'num_threads': total_threads,
            'energy_impact': 'N/A',  # Windows不提供能耗信息
            'has_performance_data': len(pids) > 0
        }
        
        return performance_info
    
    except Exception as e:
        print(f"获取应用 {app_path} 性能信息时出错: {str(e)}")
        return {
            'cpu_percent': 0,
            'num_threads': 0,
            'energy_impact': 'N/A',
            'has_performance_data': False
        }

def get_process_performance(app_path):
    """
    获取应用程序的性能信息，包括 CPU 使用率和能耗情况
    
    参数:
        app_path: 应用程序包的路径
        
    返回:
        dict: 包含性能信息的字典，包括 CPU 使用率、能耗等
    """
    # 根据平台选择相应的实现
    if IS_WINDOWS:
        return get_process_performance_windows(app_path)
    
    # macOS实现
    try:
        app_name = os.path.basename(app_path).replace('.app', '')
        
        performance_info = {
            'cpu_percent': 0,
            'num_threads': 0,
            'energy_impact': 'N/A',
            'has_performance_data': False
        }
        
        # 获取进程信息
        pids = []
        
        # 使用 ps 命令获取包含应用名称的所有进程
        cmd = ['ps', '-eo', 'pid,command']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return performance_info
        
        # 分析输出以找到匹配的进程
        lines = result.stdout.strip().split('\n')
        app_path_pattern = re.escape(app_path)
        app_name_pattern = re.escape(app_name)
        
        for line in lines[1:]:  # 跳过标题行
            parts = line.strip().split(None, 1)
            if len(parts) < 2:
                continue
                
            pid, command = parts
            
            # 检查是否是目标应用的进程
            is_target = False
            
            # 检查命令行是否包含应用路径
            if re.search(app_path_pattern, command, re.IGNORECASE):
                is_target = True
            # 检查命令行是否包含应用名称（更宽松的匹配）
            elif re.search(app_name_pattern, command, re.IGNORECASE):
                # 排除可能的误匹配（例如，如果应用名是常见词）
                if not re.search(r'\/Library\/', command) and not re.search(r'\/System\/', command):
                    is_target = True
            # 检查是否是 Electron Helper 进程
            elif 'Electron Helper' in command and app_name_pattern in command:
                is_target = True
                
            if is_target:
                try:
                    pids.append(int(pid))
                except ValueError:
                    pass
        
        if not pids:
            return performance_info
            
        # 使用 psutil 获取更详细的进程信息（如果可用）
        total_cpu_percent = 0
        total_threads = 0
        
        if HAS_PSUTIL:
            for pid in pids:
                try:
                    proc = psutil.Process(pid)
                    # 获取 CPU 使用率（这是一个相对值，100% 表示一个核心的满负荷）
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    total_cpu_percent += cpu_percent
                    
                    # 获取线程数
                    total_threads += proc.num_threads()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        else:
            # 如果没有 psutil，使用 top 命令获取 CPU 使用率
            for pid in pids:
                cmd = ['top', '-l', '1', '-pid', str(pid), '-stats', 'cpu']
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
                    if result.returncode == 0:
                        output = result.stdout
                        # 解析 top 输出以获取 CPU 使用率
                        for line in output.strip().split('\n'):
                            if str(pid) in line:
                                parts = line.split()
                                if len(parts) >= 3:
                                    try:
                                        cpu_percent = float(parts[2].replace('%', ''))
                                        total_cpu_percent += cpu_percent
                                    except (ValueError, IndexError):
                                        pass
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass
        
        # 获取能耗信息（使用 powermetrics，需要管理员权限）
        energy_impact = 'N/A'
        # 检查是否有 sudo 权限
        has_sudo = False
        
        # 仅当存在 sudo 并且用户希望分析能耗时才尝试获取能耗信息
        if shutil.which('sudo') and os.geteuid() == 0:  # 检查是否为 root 用户
            has_sudo = True
        
        if has_sudo and pids:
            try:
                # 使用 powermetrics 命令获取能耗信息
                # 注意：这需要管理员权限，如果没有权限会失败
                cmd = ['sudo', 'powermetrics', '-n', '1', '-i', '100', '--show-process-energy']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0:
                    output = result.stdout
                    # 解析输出以获取能耗信息
                    for pid in pids:
                        pid_pattern = r"^\s*{}\s+.*".format(pid)
                        for line in output.strip().split('\n'):
                            if re.search(pid_pattern, line):
                                parts = line.split()
                                if len(parts) >= 5:  # 进程信息至少应该有 5 个字段
                                    energy_impact = parts[4]  # 能耗值通常在第 5 列
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
        
        performance_info = {
            'cpu_percent': total_cpu_percent,
            'num_threads': total_threads,
            'energy_impact': energy_impact,
            'has_performance_data': len(pids) > 0
        }
        
        return performance_info
    
    except Exception as e:
        print(f"获取应用 {app_path} 性能信息时出错: {str(e)}")
        return {
            'cpu_percent': 0,
            'num_threads': 0,
            'energy_impact': 'N/A',
            'has_performance_data': False
        }

def get_app_info(app_path, analyze_memory=False, analyze_performance=False):
    """
    获取应用程序的详细信息
    
    参数:
        app_path: 应用程序包的路径
        analyze_memory: 是否分析内存使用情况
        analyze_performance: 是否分析性能信息（CPU、能耗等）
        
    返回:
        dict: 包含应用信息的字典
    """
    try:
        # 获取应用名称
        app_name = os.path.basename(app_path)
        
        # 根据平台处理应用名称
        if IS_MACOS:
            app_name = app_name.replace('.app', '')
        elif IS_WINDOWS:
            if app_name.lower().endswith('.exe'):
                app_name = os.path.splitext(app_name)[0]
        
        # 获取应用版本
        app_version = "未知"
        if IS_MACOS:
            plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
            if os.path.exists(plist_path):
                try:
                    with open(plist_path, 'rb') as fp:
                        plist_data = plistlib.load(fp)
                        app_version = plist_data.get('CFBundleShortVersionString', "未知")
                except Exception:
                    pass
        elif IS_WINDOWS:
            # 对于Windows，尝试从可执行文件获取版本信息
            if HAS_PSUTIL:
                try:
                    # 查找主可执行文件
                    exe_files = []
                    if os.path.isdir(app_path):
                        exe_files = [f for f in os.listdir(app_path) if f.lower().endswith('.exe')]
                    elif app_path.lower().endswith('.exe'):
                        exe_files = [os.path.basename(app_path)]
                        app_path = os.path.dirname(app_path)
                    
                    if exe_files:
                        exe_path = os.path.join(app_path, exe_files[0])
                        # 使用wmic获取版本信息
                        cmd = ['wmic', 'datafile', 'where', f'name="{exe_path.replace("\\", "\\\\")}"', 'get', 'Version', '/value']
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                            if result.returncode == 0:
                                output = result.stdout
                                version_match = re.search(r'Version=(.+)', output)
                                if version_match:
                                    app_version = version_match.group(1).strip()
                        except Exception:
                            pass
                except Exception:
                    pass
        
        # 获取 Electron 版本
        electron_version = get_electron_version(app_path)
        
        # 获取应用大小
        app_size = get_dir_size(app_path)
        
        # 创建基本信息字典
        app_info = {
            'name': app_name,
            'path': app_path,
            'version': app_version,
            'electron_version': electron_version,
            'size': app_size
        }
        
        # 如果需要分析内存，则获取内存使用情况
        if analyze_memory:
            memory_info = get_memory_usage(app_path)
            app_info.update({
                'memory_mb': memory_info['memory_mb'],
                'running': memory_info['running'],
                'processes': memory_info['processes'],
                'status': memory_info['status'],
                'memory_size_ratio': memory_info['memory_mb'] / app_size if app_size > 0 else 0
            })
        
        # 如果需要分析性能，则获取 CPU 使用率和能耗情况
        if analyze_performance:
            performance_info = get_process_performance(app_path)
            app_info.update({
                'cpu_percent': performance_info['cpu_percent'],
                'num_threads': performance_info['num_threads'],
                'energy_impact': performance_info['energy_impact'],
                'has_performance_data': performance_info['has_performance_data']
            })
        
        return app_info
    except Exception as e:
        print(f"获取应用 {app_path} 信息时出错: {str(e)}")
        base_info = {
            'name': os.path.basename(app_path).replace('.app', '') if IS_MACOS else os.path.splitext(os.path.basename(app_path))[0] if IS_WINDOWS and app_path.lower().endswith('.exe') else os.path.basename(app_path),
            'path': app_path,
            'version': "未知",
            'electron_version': "未知",
            'size': 0
        }
        
        # 如果需要分析内存，添加默认内存信息
        if analyze_memory:
            base_info.update({
                'memory_mb': 0,
                'running': False,
                'processes': 0,
                'status': '未知',
                'memory_size_ratio': 0
            })
            
        # 如果需要分析性能，添加默认性能信息
        if analyze_performance:
            base_info.update({
                'cpu_percent': 0,
                'num_threads': 0,
                'energy_impact': 'N/A',
                'has_performance_data': False
            })
            
        return base_info

def get_dir_size(path):
    """
    获取目录或文件大小
    
    参数:
        path: 目录或文件路径
        
    返回:
        float: 大小（MB）
    """
    try:
        # 检查是否是文件
        if os.path.isfile(path):
            return os.path.getsize(path) / (1024 * 1024)  # 转换为MB
            
        # 如果是目录，累计所有文件大小
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):  # 跳过符号链接
                    try:
                        total_size += os.path.getsize(fp)
                    except (OSError, PermissionError):
                        # 忽略无法访问的文件
                        pass
        return total_size / (1024 * 1024)  # 转换为MB
    except Exception as e:
        print(f"获取 {path} 大小时出错: {str(e)}")
        return 0

def process_app(app_path, analyze_memory=False, analyze_performance=False):
    """
    处理单个应用程序
    
    参数:
        app_path: 应用程序包的路径
        analyze_memory: 是否分析内存使用情况
        analyze_performance: 是否分析性能信息（CPU、能耗等）
        
    返回:
        dict or None: 如果是 Electron 应用，则返回应用信息，否则返回 None
    """
    global processed_count
    
    try:
        if is_electron_app(app_path):
            app_info = get_app_info(app_path, analyze_memory, analyze_performance)
            processed_count += 1
            print_progress()
            return app_info
    except Exception as e:
        print(f"处理应用 {app_path} 时出错: {str(e)}")
    
    processed_count += 1
    print_progress()
    return None

def print_progress():
    """打印进度信息"""
    if apps_count > 0:
        percent = (processed_count / apps_count) * 100
        sys.stdout.write(f"\r正在处理: {processed_count}/{apps_count} 应用 ({percent:.1f}%)")
        sys.stdout.flush()

def scan_directory(directory, max_workers=8):
    """
    扫描目录查找 Electron 应用
    
    参数:
        directory: 要扫描的目录路径
        max_workers: 最大线程数
        
    返回:
        list: 找到的 Electron 应用列表
    """
    global apps_count, processed_count, electron_apps
    
    print(f"正在扫描目录: {directory}")
    
    # 获取所有 .app 文件
    app_paths = []
    for root, dirs, _ in os.walk(directory):
        # 排除系统应用和缓存目录
        if '/Library/Caches' in root or '/System/Library' in root:
            continue
            
        for dir_name in dirs:
            if dir_name.endswith('.app'):
                app_path = os.path.join(root, dir_name)
                app_paths.append(app_path)
    
    apps_count = len(app_paths)
    processed_count = 0
    
    print(f"找到 {apps_count} 个应用，正在分析...")
    
    # 使用线程池并行处理应用
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_app = {executor.submit(process_app, app): app for app in app_paths}
        for future in future_to_app:
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"处理应用时出错: {str(e)}")
    
    # 清除进度条
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    sys.stdout.flush()
    
    return results

def format_size(size_mb):
    """格式化大小显示"""
    if size_mb > 1000:
        return f"{size_mb/1000:.2f} GB"
    else:
        return f"{size_mb:.2f} MB"

def format_ratio(ratio):
    """格式化内存与包大小比例显示"""
    if ratio == 0:
        return "N/A"
    return f"{ratio:.2f}x"

def print_results(results, sort_by='name', export_path=None, show_memory=False, show_performance=False, show_ratio=False, top_n=0):
    """
    打印结果
    
    参数:
        results: 找到的 Electron 应用列表
        sort_by: 排序方式（name, size, version, memory, cpu）
        export_path: 导出 JSON 文件的路径
        show_memory: 是否显示内存使用情况
        show_performance: 是否显示性能信息（CPU、能耗等）
        show_ratio: 是否显示内存使用与应用大小的比例
        top_n: 只显示资源使用最多的前 N 个应用
    """
    if not results:
        print("未找到任何 Electron 应用。")
        return
    
    # 排序结果
    if sort_by == 'size':
        results.sort(key=lambda x: x['size'], reverse=True)
    elif sort_by == 'version':
        results.sort(key=lambda x: x['electron_version'])
    elif sort_by == 'memory' and show_memory:
        results.sort(key=lambda x: x['memory_mb'], reverse=True)
    elif sort_by == 'cpu' and show_performance:
        results.sort(key=lambda x: x['cpu_percent'], reverse=True)
    else:  # 默认按名称排序
        results.sort(key=lambda x: x['name'].lower())
    
    # 如果指定了 top_n，只保留前 N 个结果
    if top_n > 0 and (show_memory or show_performance):
        results = results[:top_n]
    
    # 导出为 JSON 文件
    if export_path:
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"结果已导出到 {export_path}")
        except Exception as e:
            print(f"导出结果时出错: {str(e)}")
    
    # 打印结果
    print(f"\n找到 {len(results)} 个 Electron 应用:")
    
    # 计算表格宽度
    table_width = 80
    if show_memory:
        table_width += 35
    if show_performance:
        table_width += 35
    
    print("-" * table_width)
    
    # 表头
    header = f"{'应用名称':<30} {'应用版本':<15} {'Electron 版本':<20} {'应用大小':<10}"
    if show_memory:
        header += f" {'内存使用':<12} {'状态':<20}"
        if show_ratio:
            header += f" {'内存/大小比':<12}"
    if show_performance:
        header += f" {'CPU使用率':<10} {'线程数':<8} {'能耗':<12}"
    header += " 路径"
    print(header)
    
    print("-" * table_width)
    
    # 打印每个应用的信息
    for app in results:
        name = app['name']
        if len(name) > 28:
            name = name[:25] + "..."
            
        version = app['version']
        if len(version) > 13:
            version = version[:10] + "..."
            
        electron_version = app['electron_version']
        if len(electron_version) > 18:
            electron_version = electron_version[:15] + "..."
            
        size = format_size(app['size'])
        
        line = f"{name:<30} {version:<15} {electron_version:<20} {size:<10}"
        
        if show_memory:
            if 'memory_mb' in app:
                memory = format_size(app['memory_mb'])
                status = app.get('status', '未知')
                if len(status) > 18:
                    status = status[:15] + "..."
                
                line += f" {memory:<12} {status:<20}"
                
                if show_ratio and 'memory_size_ratio' in app:
                    ratio = format_ratio(app['memory_size_ratio'])
                    line += f" {ratio:<12}"
            else:
                memory_placeholder = "N/A"
                line += f" {memory_placeholder:<12} {'未分析':<20}"
                if show_ratio:
                    line += f" {'N/A':<12}"
        
        if show_performance:
            if 'cpu_percent' in app and app.get('has_performance_data', False):
                cpu = f"{app['cpu_percent']:.1f}%"
                threads = str(app['num_threads'])
                energy = app['energy_impact']
                
                line += f" {cpu:<10} {threads:<8} {energy:<12}"
            else:
                line += f" {'N/A':<10} {'N/A':<8} {'N/A':<12}"
        
        line += f" {app['path']}"
        print(line)
    
    print("-" * table_width)
    
    # 统计 Electron 版本分布
    electron_versions = {}
    for app in results:
        version = app['electron_version']
        if version not in electron_versions:
            electron_versions[version] = 0
        electron_versions[version] += 1
    
    print("\nElectron 版本分布:")
    for version, count in electron_versions.items():
        print(f"- {version}: {count} 个应用")
    
    # 如果分析了内存，显示内存使用统计
    if show_memory:
        running_apps = [app for app in results if app.get('running', False)]
        if running_apps:
            total_memory = sum(app.get('memory_mb', 0) for app in running_apps)
            avg_memory = total_memory / len(running_apps)
            max_memory = max(app.get('memory_mb', 0) for app in running_apps)
            min_memory = min(app.get('memory_mb', 0) for app in running_apps if app.get('memory_mb', 0) > 0)
            
            print("\n内存使用统计:")
            print(f"- 运行中的应用: {len(running_apps)} 个")
            print(f"- 总内存使用: {format_size(total_memory)}")
            print(f"- 平均内存使用: {format_size(avg_memory)}")
            print(f"- 最大内存使用: {format_size(max_memory)}")
            print(f"- 最小内存使用: {format_size(min_memory)}")
            
            if show_ratio:
                # 计算内存与包大小比例的统计
                ratios = [app.get('memory_size_ratio', 0) for app in running_apps if app.get('memory_size_ratio', 0) > 0]
                if ratios:
                    avg_ratio = sum(ratios) / len(ratios)
                    max_ratio = max(ratios)
                    min_ratio = min(ratios)
                    
                    print("\n内存/大小比例统计:")
                    print(f"- 平均比例: {format_ratio(avg_ratio)}")
                    print(f"- 最大比例: {format_ratio(max_ratio)}")
                    print(f"- 最小比例: {format_ratio(min_ratio)}")
                    
                    # 找出内存效率最高和最低的应用
                    most_efficient = min(running_apps, key=lambda x: x.get('memory_size_ratio', float('inf')) if x.get('memory_size_ratio', 0) > 0 else float('inf'))
                    least_efficient = max(running_apps, key=lambda x: x.get('memory_size_ratio', 0))
                    
                    print(f"- 内存效率最高的应用: {most_efficient['name']} (比例: {format_ratio(most_efficient.get('memory_size_ratio', 0))})")
                    print(f"- 内存效率最低的应用: {least_efficient['name']} (比例: {format_ratio(least_efficient.get('memory_size_ratio', 0))})")
        else:
            print("\n内存使用统计: 没有运行中的 Electron 应用")
    
    # 如果分析了性能，显示 CPU 使用统计
    if show_performance:
        apps_with_performance = [app for app in results if app.get('has_performance_data', False)]
        if apps_with_performance:
            total_cpu = sum(app.get('cpu_percent', 0) for app in apps_with_performance)
            avg_cpu = total_cpu / len(apps_with_performance)
            max_cpu = max(app.get('cpu_percent', 0) for app in apps_with_performance)
            min_cpu = min(app.get('cpu_percent', 0) for app in apps_with_performance if app.get('cpu_percent', 0) > 0)
            
            print("\nCPU 使用统计:")
            print(f"- 运行中的应用: {len(apps_with_performance)} 个")
            print(f"- 总 CPU 使用率: {total_cpu:.1f}%")
            print(f"- 平均 CPU 使用率: {avg_cpu:.1f}%")
            print(f"- 最大 CPU 使用率: {max_cpu:.1f}%")
            print(f"- 最小 CPU 使用率: {min_cpu:.1f}%")
            
            # 显示 CPU 使用最多和最少的应用
            most_cpu_intensive = max(apps_with_performance, key=lambda x: x.get('cpu_percent', 0))
            least_cpu_intensive = min(apps_with_performance, key=lambda x: x.get('cpu_percent', float('inf')) if x.get('cpu_percent', 0) > 0 else float('inf'))
            
            print(f"- CPU 使用最多的应用: {most_cpu_intensive['name']} ({most_cpu_intensive.get('cpu_percent', 0):.1f}%)")
            print(f"- CPU 使用最少的应用: {least_cpu_intensive['name']} ({least_cpu_intensive.get('cpu_percent', 0):.1f}%)")
        else:
            print("\nCPU 使用统计: 没有运行中的 Electron 应用")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='查找系统上的 Electron 应用程序',
        epilog='''
示例:
  # 基本扫描，只识别 Electron 应用
  python find_electron_apps.py
  
  # 分析内存使用情况，并按内存排序
  python find_electron_apps.py --memory --sort memory
  
  # 全面分析，包括内存、CPU 和内存/大小比例
  python find_electron_apps.py --memory --performance --ratio
  
  # 只显示资源使用最多的前5个应用
  python find_electron_apps.py --memory --performance --top 5
  
  # 导出结果到 JSON 文件
  python find_electron_apps.py --json-file electron_apps.json
  
  # 指定自定义目录扫描
  python find_electron_apps.py --directories "/Applications" "~/Downloads"
  
  # 设置多线程处理
  python find_electron_apps.py --workers 16
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 设置平台特定的帮助文本
    if IS_WINDOWS:
        dirs_help = '要扫描的目录，默认为 C:\\Program Files 和 C:\\Program Files (x86)'
    elif IS_MACOS:
        dirs_help = '要扫描的目录，默认为 /Applications 和 ~/Applications'
    else:  # Linux
        dirs_help = '要扫描的目录，默认为 /usr/share/applications 和 ~/.local/share/applications'
    
    # 目录选项
    parser.add_argument('-d', '--directories', nargs='+', 
                      help=dirs_help)
    
    # 分析选项
    analysis_group = parser.add_argument_group('分析选项')
    analysis_group.add_argument('-m', '--memory', action='store_true',
                              help='分析正在运行的 Electron 应用的内存使用情况')
    
    analysis_group.add_argument('-p', '--performance', action='store_true',
                              help='分析正在运行的 Electron 应用的 CPU 使用率' + ('和能耗情况' if IS_MACOS else ''))
    
    analysis_group.add_argument('--ratio', action='store_true',
                              help='显示内存使用与应用大小的比例分析')
    
    # 显示选项
    display_group = parser.add_argument_group('显示选项')
    display_group.add_argument('-s', '--sort', choices=['name', 'size', 'version', 'memory', 'cpu'], default='name',
                             help='结果排序方式：按名称(name)、大小(size)、版本(version)、内存使用(memory)或CPU使用率(cpu)排序')
    
    display_group.add_argument('--top', type=int, default=0,
                             help='只显示资源使用最多的前 N 个应用')
    
    # 输出选项
    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument('-e', '--json-file', 
                            help='将结果导出为 JSON 文件的路径')
    
    # 性能选项
    perf_group = parser.add_argument_group('性能选项')
    perf_group.add_argument('-w', '--workers', type=int, default=8,
                          help='同时处理的最大线程数量 (默认: 8)')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 确定要扫描的目录
    directories = args.directories if args.directories else DEFAULT_SEARCH_DIRS
    
    # 检查目录是否存在
    valid_directories = []
    for directory in directories:
        if os.path.isdir(directory):
            valid_directories.append(directory)
        else:
            print(f"警告: 目录 '{directory}' 不存在，将被跳过")
    
    if not valid_directories:
        print("错误: 没有有效的目录可供扫描")
        return 1
    
    # 记录开始时间
    start_time = time.time()
    
    # 扫描每个目录
    all_results = []
    
    # 如果需要分析内存，先输出提示
    if args.memory:
        print("将分析 Electron 应用的内存使用情况...")
        print("注意: 只有正在运行的应用才会显示内存使用数据")
    
    # 扫描每个目录
    for directory in valid_directories:
        # 获取所有可能的Electron应用路径
        app_paths = []
        
        # 根据平台使用不同的搜索策略
        if IS_WINDOWS:
            # 在Windows上，递归查找所有.exe文件和目录
            for root, dirs, files in os.walk(directory):
                # 首先检查目录
                for dir_name in dirs:
                    if not dir_name.startswith('.'):  # 跳过隐藏目录
                        app_dir_path = os.path.join(root, dir_name)
                        app_paths.append(app_dir_path)
                
                # 然后检查.exe文件
                for file_name in files:
                    if file_name.lower().endswith('.exe'):
                        app_path = os.path.join(root, file_name)
                        app_paths.append(app_path)
                        
                # 为避免扫描过多文件，限制递归深度
                if len(root.split(os.sep)) - len(directory.split(os.sep)) > 2:
                    # 清空dirs列表以停止递归
                    dirs[:] = []
        elif IS_MACOS:
            # 在macOS上，递归查找所有.app包
            for root, dirs, _ in os.walk(directory):
                # 排除系统应用和缓存目录
                if '/Library/Caches' in root or '/System/Library' in root:
                    continue
                    
                for dir_name in dirs:
                    if dir_name.endswith('.app'):
                        app_path = os.path.join(root, dir_name)
                        app_paths.append(app_path)
        else:  # Linux或其他系统
            # 在Linux上，查找.desktop文件
            for root, _, files in os.walk(directory):
                for file_name in files:
                    if file_name.endswith('.desktop'):
                        app_path = os.path.join(root, file_name)
                        app_paths.append(app_path)
        
        global apps_count, processed_count
        apps_count = len(app_paths)
        processed_count = 0
        
        print(f"正在扫描目录 {directory}，找到 {apps_count} 个应用，正在分析...")
        
        results = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_app = {executor.submit(process_app, app, args.memory, args.performance): app for app in app_paths}
            for future in future_to_app:
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"处理应用时出错: {str(e)}")
        
        # 清除进度条
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()
        
        all_results.extend(results)
    
    # 打印结果
    print_results(all_results, args.sort, args.export, args.memory, args.performance, args.ratio, args.top)
    
    # 打印总用时
    elapsed_time = time.time() - start_time
    print(f"\n扫描完成，用时 {elapsed_time:.2f} 秒")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
