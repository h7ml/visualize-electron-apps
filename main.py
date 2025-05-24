#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Electron应用扫描与可视化工具

这个脚本整合了find_electron_apps.py和visualize_electron_apps.py的功能，
提供一个统一的界面来执行Electron应用扫描和可视化的完整工作流程。

支持以下操作模式：
- 完整流程（扫描 + 可视化）
- 仅扫描（导出JSON数据）
- 仅可视化（使用现有JSON数据）

可以通过命令行参数或交互式菜单来控制执行模式。

命令行使用示例：
--------------

1. 执行完整流程（扫描+可视化）：
   python main.py
   
   或者明确指定：
   python main.py --all

2. 仅执行扫描，导出JSON数据：
   python main.py --scan --memory --performance

3. 仅执行可视化，使用现有JSON数据：
   python main.py --visualize --json-file your_data.json
   
4. 完整流程，带更多选项：
   python main.py --all --memory --performance --ratio --sort memory --top 10 --port 8080

5. 交互式模式（无参数）：
   python main.py
   
   这将显示一个交互式菜单，您可以选择操作并配置选项。

常用参数说明：
--------------
--scan         : 仅执行扫描
--visualize    : 仅执行可视化
--all          : 执行完整流程
--json-file    : 指定JSON数据文件路径
--memory       : 分析内存使用情况
--performance  : 分析CPU使用率
--ratio        : 显示内存/大小比例
--sort         : 结果排序方式
--top          : 只显示前N个应用
--port         : Web服务器端口
--no-browser   : 不自动打开浏览器

更多详细参数请使用 --help 参数查看。
"""

import os
import sys
import json
import time
import platform
import argparse
import subprocess
import webbrowser
import shutil
from pathlib import Path

# 检测当前平台
IS_WINDOWS = platform.system() == 'Windows'
IS_MACOS = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'

# 默认JSON文件路径
DEFAULT_JSON_FILE = 'electron_apps.json'

# 平台特定的Python命令
PYTHON_CMD = 'python' if IS_WINDOWS else 'python3'

# 脚本路径
SCAN_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'find_electron_apps.py')
VISUALIZE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visualize_electron_apps.py') 

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Electron应用扫描与可视化工具',
        epilog='''
示例:
  # 启动交互式菜单
  python main.py
  
  # 执行完整流程（扫描+可视化）
  python main.py --all --memory --performance
  
  # 仅执行扫描，导出JSON数据
  python main.py --scan --memory --performance --json-file electron_apps.json
  
  # 仅执行可视化，使用现有JSON数据
  python main.py --visualize --json-file electron_apps.json
  
  # 完整流程，带更多选项
  python main.py --all --memory --performance --ratio --sort memory --top 10 --port 8080
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 操作模式选项
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--scan', action='store_true',
                           help='仅执行扫描，导出JSON数据')
    mode_group.add_argument('--visualize', action='store_true',
                           help='仅执行可视化，使用现有JSON数据')
    mode_group.add_argument('--all', action='store_true',
                           help='执行完整流程（扫描+可视化，默认）')
    
    # JSON文件路径
    parser.add_argument('--json-file', default=DEFAULT_JSON_FILE,
                        help=f'指定JSON数据文件路径（默认：{DEFAULT_JSON_FILE}）')
    
    # 扫描相关参数
    scan_group = parser.add_argument_group('扫描选项', '传递给find_electron_apps.py的参数')
    scan_group.add_argument('-m', '--memory', action='store_true',
                          help='分析正在运行的Electron应用的内存使用情况')
    scan_group.add_argument('-p', '--performance', action='store_true',
                          help='分析正在运行的Electron应用的CPU使用率' + ('和能耗情况' if IS_MACOS else ''))
    scan_group.add_argument('--ratio', action='store_true',
                          help='显示内存使用与应用大小的比例分析')
    scan_group.add_argument('-d', '--directories', nargs='+',
                          help='要扫描的目录，默认为系统应用目录')
    scan_group.add_argument('-s', '--sort', choices=['name', 'size', 'version', 'memory', 'cpu'],
                          default='name', help='结果排序方式')
    scan_group.add_argument('-w', '--workers', type=int, default=8,
                          help='同时处理的最大线程数量 (默认: 8)')
    scan_group.add_argument('--top', type=int, default=0,
                          help='只显示资源使用最多的前N个应用')
    
    # 可视化相关参数
    vis_group = parser.add_argument_group('可视化选项', '传递给visualize_electron_apps.py的参数')
    vis_group.add_argument('--port', type=int, default=8080,
                         help='Web服务器端口（默认：8080）')
    vis_group.add_argument('--host', default='127.0.0.1',
                         help='Web服务器主机（默认：127.0.0.1）')
    vis_group.add_argument('--no-browser', action='store_true',
                         help='不自动打开浏览器')
    
    args = parser.parse_args()
    
    # 如果没有指定操作模式，默认为完整流程
    if not (args.scan or args.visualize or args.all):
        args.all = True
    
    return args 

def print_header():
    """打印脚本标题"""
    print("\n" + "=" * 80)
    print(f"{'Electron应用扫描与可视化工具':^80}")
    print("=" * 80)

def show_interactive_menu():
    """显示交互式菜单并处理用户输入"""
    args = argparse.Namespace()
    args.json_file = DEFAULT_JSON_FILE
    args.memory = False
    args.performance = False
    args.ratio = False
    args.directories = None
    args.sort = 'name'
    args.workers = 8
    args.top = 0
    args.port = 8080
    args.host = '127.0.0.1'
    args.no_browser = False
    
    while True:
        print_header()
        print("\n请选择要执行的操作：")
        print("1. 执行完整流程（扫描 + 可视化）")
        print("2. 仅执行扫描，导出JSON数据")
        print("3. 仅执行可视化，使用现有JSON数据")
        print("4. 配置扫描选项")
        print("5. 配置可视化选项")
        print("0. 退出程序")
        
        try:
            choice = input("\n请输入选项编号 [0-5]: ")
            
            if choice == '0':
                print("\n感谢使用！再见！")
                sys.exit(0)
            elif choice == '1':
                # 执行完整流程
                args.scan = False
                args.visualize = False
                args.all = True
                return args
            elif choice == '2':
                # 仅执行扫描
                args.scan = True
                args.visualize = False
                args.all = False
                return args
            elif choice == '3':
                # 仅执行可视化
                args.scan = False
                args.visualize = True
                args.all = False
                return args
            elif choice == '4':
                configure_scan_options(args)
            elif choice == '5':
                configure_visualization_options(args)
            else:
                print("\n无效选项，请重试。")
        except KeyboardInterrupt:
            print("\n操作已取消。")
            sys.exit(0)
        except Exception as e:
            print(f"\n发生错误: {str(e)}")

def configure_scan_options(args):
    """配置扫描选项"""
    while True:
        print("\n===== 扫描选项配置 =====")
        print(f"1. 分析内存使用     : {'是' if args.memory else '否'}")
        print(f"2. 分析性能指标     : {'是' if args.performance else '否'}")
        print(f"3. 显示内存/大小比例: {'是' if args.ratio else '否'}")
        print(f"4. 结果排序方式     : {args.sort}")
        print(f"5. 线程数量         : {args.workers}")
        print(f"6. 显示前N个应用    : {args.top if args.top > 0 else '全部'}")
        print(f"7. 指定扫描目录     : {', '.join(args.directories) if args.directories else '默认系统目录'}")
        print(f"8. JSON文件路径     : {args.json_file}")
        print("0. 返回主菜单")
        
        try:
            choice = input("\n请输入选项编号 [0-8]: ")
            
            if choice == '0':
                break
            elif choice == '1':
                args.memory = not args.memory
            elif choice == '2':
                args.performance = not args.performance
            elif choice == '3':
                args.ratio = not args.ratio
            elif choice == '4':
                sort_options = ['name', 'size', 'version', 'memory', 'cpu']
                print(f"\n排序选项: {', '.join(sort_options)}")
                new_sort = input(f"请输入排序方式 [{args.sort}]: ")
                if new_sort in sort_options:
                    args.sort = new_sort
                else:
                    print("无效的排序选项，使用当前值。")
            elif choice == '5':
                try:
                    new_workers = int(input(f"请输入线程数量 [{args.workers}]: "))
                    if new_workers > 0:
                        args.workers = new_workers
                    else:
                        print("线程数量必须大于0。")
                except ValueError:
                    print("请输入有效的数字。")
            elif choice == '6':
                try:
                    new_top = int(input(f"显示前N个应用 (0表示全部) [{args.top}]: "))
                    if new_top >= 0:
                        args.top = new_top
                    else:
                        print("数量必须大于或等于0。")
                except ValueError:
                    print("请输入有效的数字。")
            elif choice == '7':
                print("\n当前扫描目录: ", end="")
                if args.directories:
                    print(", ".join(args.directories))
                else:
                    print("默认系统目录")
                
                new_dirs = input("请输入新的扫描目录，多个目录用空格分隔（留空使用默认）: ")
                if new_dirs.strip():
                    args.directories = new_dirs.strip().split()
                else:
                    args.directories = None
            elif choice == '8':
                new_file = input(f"请输入JSON文件路径 [{args.json_file}]: ")
                if new_file.strip():
                    args.json_file = new_file.strip()
            else:
                print("无效选项，请重试。")
        except KeyboardInterrupt:
            print("\n配置已取消。")
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")

def configure_visualization_options(args):
    """配置可视化选项"""
    while True:
        print("\n===== 可视化选项配置 =====")
        print(f"1. Web服务器端口   : {args.port}")
        print(f"2. Web服务器主机   : {args.host}")
        print(f"3. 自动打开浏览器   : {'否' if args.no_browser else '是'}")
        print(f"4. JSON文件路径     : {args.json_file}")
        print("0. 返回主菜单")
        
        try:
            choice = input("\n请输入选项编号 [0-4]: ")
            
            if choice == '0':
                break
            elif choice == '1':
                try:
                    new_port = int(input(f"请输入Web服务器端口 [{args.port}]: "))
                    if new_port > 0 and new_port < 65536:
                        args.port = new_port
                    else:
                        print("端口号必须在1-65535范围内。")
                except ValueError:
                    print("请输入有效的数字。")
            elif choice == '2':
                new_host = input(f"请输入Web服务器主机 [{args.host}]: ")
                if new_host.strip():
                    args.host = new_host.strip()
            elif choice == '3':
                args.no_browser = not args.no_browser
                print(f"自动打开浏览器: {'否' if args.no_browser else '是'}")
            elif choice == '4':
                new_file = input(f"请输入JSON文件路径 [{args.json_file}]: ")
                if new_file.strip():
                    args.json_file = new_file.strip()
            else:
                print("无效选项，请重试。")
        except KeyboardInterrupt:
            print("\n配置已取消。")
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")

def run_scan(args):
    """
    执行Electron应用扫描
    
    参数:
        args: 命令行参数命名空间
        
    返回:
        bool: 成功返回True，失败返回False
    """
    print("\n" + "=" * 80)
    print("开始扫描Electron应用...")
    print("-" * 80)
    
    # 构建命令行参数
    cmd = [PYTHON_CMD, SCAN_SCRIPT]
    
    # 添加内存分析参数
    if args.memory:
        cmd.append('-m')
    
    # 添加性能分析参数
    if args.performance:
        cmd.append('-p')
    
    # 添加比例分析参数
    if args.ratio:
        cmd.append('--ratio')
    
    # 添加排序参数
    if args.sort:
        cmd.extend(['-s', args.sort])
    
    # 添加线程数参数
    if args.workers != 8:  # 默认值是8
        cmd.extend(['-w', str(args.workers)])
    
    # 添加前N个应用参数
    if args.top > 0:
        cmd.extend(['--top', str(args.top)])
    
    # 添加目录参数
    if args.directories:
        cmd.extend(['-d'] + args.directories)
    
    # 添加JSON导出参数
    cmd.extend(['-e', args.json_file])
    
    try:
        # 运行扫描命令
        print(f"执行命令: {' '.join(cmd)}")
        process = subprocess.run(cmd, check=True)
        
        if process.returncode == 0:
            print(f"\n扫描完成！结果已保存到 {args.json_file}")
            return True
        else:
            print(f"\n扫描失败，返回代码: {process.returncode}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"\n执行扫描时出错: {str(e)}")
        return False
    except Exception as e:
        print(f"\n发生未知错误: {str(e)}")
        return False

def run_visualization(args):
    """
    执行Electron应用可视化
    
    参数:
        args: 命令行参数命名空间
        
    返回:
        bool: 成功返回True，失败返回False
    """
    print("\n" + "=" * 80)
    print("启动Electron应用可视化工具...")
    print("-" * 80)
    
    # 检查JSON文件是否存在
    if not os.path.exists(args.json_file):
        print(f"错误: JSON文件 {args.json_file} 不存在")
        print(f"请先运行扫描命令或指定正确的JSON文件路径")
        return False
    
    # 构建命令行参数
    cmd = [PYTHON_CMD, VISUALIZE_SCRIPT]
    
    # 环境变量设置
    env = os.environ.copy()
    # 设置Flask环境变量
    env['FLASK_RUN_PORT'] = str(args.port)
    env['FLASK_RUN_HOST'] = args.host
    env['FLASK_APP'] = VISUALIZE_SCRIPT
    
    try:
        # 启动可视化服务器（非阻塞模式）
        print(f"执行命令: {' '.join(cmd)}")
        
        # 复制JSON文件到当前目录的electron_apps.json（如果文件名不是默认值）
        if args.json_file != DEFAULT_JSON_FILE and args.json_file != os.path.join(os.getcwd(), DEFAULT_JSON_FILE):
            try:
                shutil.copy2(args.json_file, DEFAULT_JSON_FILE)
                print(f"已复制 {args.json_file} 到 {DEFAULT_JSON_FILE}")
            except Exception as e:
                print(f"警告: 无法复制JSON文件: {str(e)}")
                print("可视化工具可能无法正常加载数据")
        
        # 检查visualize_electron_apps.py是否支持命令行参数
        # 我们通过运行帮助命令来检查
        try:
            help_cmd = [PYTHON_CMD, VISUALIZE_SCRIPT, "--help"]
            help_result = subprocess.run(help_cmd, capture_output=True, text=True)
            
            # 检查是否支持端口参数
            if "--port" in help_result.stdout:
                cmd.extend(['--port', str(args.port)])
            else:
                print(f"注意: 可视化脚本不支持--port参数，将使用默认端口8080")
                if args.port != 8080:
                    print(f"警告: 您指定的端口 {args.port} 可能不会生效")
            
            # 检查是否支持主机参数
            if "--host" in help_result.stdout:
                cmd.extend(['--host', args.host])
            else:
                print(f"注意: 可视化脚本不支持--host参数，将使用默认主机127.0.0.1")
                if args.host != '127.0.0.1':
                    print(f"警告: 您指定的主机 {args.host} 可能不会生效")
            
            # 检查是否支持JSON文件参数
            if "--json-file" in help_result.stdout:
                cmd.extend(['--json-file', args.json_file])
            
            # 检查是否支持no-browser参数
            if "--no-browser" in help_result.stdout and args.no_browser:
                cmd.append('--no-browser')
        except Exception:
            # 无法确定是否支持，尝试添加参数
            cmd.extend(['--port', str(args.port)])
            cmd.extend(['--host', args.host])
            cmd.extend(['--json-file', args.json_file])
            if args.no_browser:
                cmd.append('--no-browser')
        
        # 启动子进程
        process = subprocess.Popen(cmd, env=env)
        
        # 等待服务器启动
        print("\n正在启动Web服务器，请稍候...")
        time.sleep(2)
        
        # 打开浏览器
        if not args.no_browser:
            url = f"http://{args.host}:{args.port}"
            print(f"\n正在打开浏览器: {url}")
            webbrowser.open(url)
        
        print("\n可视化服务已启动！")
        print(f"请访问 http://{args.host}:{args.port} 查看结果")
        print("\n按Ctrl+C终止服务器...")
        
        # 等待用户中断
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n用户中断，正在停止服务器...")
        finally:
            # 确保进程被终止
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            print("可视化服务已停止")
        
        return True
    except Exception as e:
        print(f"\n启动可视化服务时出错: {str(e)}")
        return False

def run_full_workflow(args):
    """
    执行完整的Electron应用分析工作流（扫描+可视化）
    
    参数:
        args: 命令行参数命名空间
        
    返回:
        bool: 成功返回True，失败返回False
    """
    print("\n" + "=" * 80)
    print("执行完整的Electron应用分析工作流")
    print("=" * 80)
    
    # 先执行扫描
    scan_success = run_scan(args)
    
    if not scan_success:
        print("\n警告: 扫描过程未成功完成")
        choice = input("是否继续执行可视化步骤？(y/n) [n]: ")
        if choice.lower() != 'y':
            return False
    
    # 执行可视化
    return run_visualization(args)

def check_scripts_exist():
    """检查必要的脚本文件是否存在"""
    if not os.path.exists(SCAN_SCRIPT):
        print(f"错误: 未找到扫描脚本 {SCAN_SCRIPT}")
        return False
    
    if not os.path.exists(VISUALIZE_SCRIPT):
        print(f"错误: 未找到可视化脚本 {VISUALIZE_SCRIPT}")
        return False
    
    return True

def print_system_info():
    """打印系统信息"""
    print("\n系统信息:")
    print(f"- 操作系统: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"- Python版本: {platform.python_version()}")
    print(f"- 执行路径: {os.path.dirname(os.path.abspath(__file__))}")

def verify_dependencies():
    """验证必要的依赖项是否已安装"""
    missing_packages = []
    
    # 检查扫描工具依赖
    try:
        import psutil
    except ImportError:
        missing_packages.append("psutil")
    
    # 检查可视化工具依赖
    try:
        import flask
    except ImportError:
        missing_packages.append("flask")
    
    try:
        import plotly
    except ImportError:
        missing_packages.append("plotly")
    
    try:
        import pandas
    except ImportError:
        missing_packages.append("pandas")
    
    if missing_packages:
        print("\n警告: 以下依赖包未安装:")
        for pkg in missing_packages:
            print(f"- {pkg}")
        
        print("\n建议安装以下依赖包:")
        print(f"{PYTHON_CMD} -m pip install {' '.join(missing_packages)}")
        
        return False
    
    return True

def main():
    """主函数"""
    # 打印脚本标题
    print_header()
    
    # 检查必要的脚本文件是否存在
    if not check_scripts_exist():
        return 1
    
    # 打印系统信息
    print_system_info()
    
    # 验证依赖项
    verify_dependencies()
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 解析命令行参数
        args = parse_arguments()
    else:
        # 显示交互式菜单
        args = show_interactive_menu()
    
    # 根据参数执行相应的操作
    try:
        if args.scan:
            # 仅执行扫描
            result = run_scan(args)
        elif args.visualize:
            # 仅执行可视化
            result = run_visualization(args)
        elif args.all:
            # 执行完整流程
            result = run_full_workflow(args)
        else:
            print("错误: 未指定操作模式")
            return 1
        
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return 1
    except Exception as e:
        print(f"\n发生未知错误: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
