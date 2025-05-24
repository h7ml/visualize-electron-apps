# Electron应用资源分析器

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.6+-blue.svg" alt="Python 3.6+">
  <img src="https://img.shields.io/badge/Flask-2.2.3-green.svg" alt="Flask 2.2.3">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg" alt="Platform: Windows | macOS">
</div>

<p align="center">扫描、分析并可视化展示系统中Electron应用的资源使用情况</p>

![应用预览](https://via.placeholder.com/800x450.png?text=Electron+应用资源分析器)

## 📝 项目简介

Electron应用资源分析器是一个强大的工具，能够扫描您系统中的所有Electron应用程序，并分析它们的资源使用情况。该工具不仅能识别这些应用，还能提供它们的内存使用、CPU占用和应用大小等详细信息，帮助您了解这些应用对系统资源的影响。

Electron是一个流行的跨平台桌面应用开发框架，但其应用往往比传统桌面应用消耗更多资源。本工具旨在帮助开发者和用户了解这些应用的资源使用情况，从而做出更明智的决策。

## ✨ 功能特点

- **自动扫描检测**：自动识别系统中安装的Electron应用
- **详细信息收集**：获取应用的版本、Electron版本、应用大小等基本信息
- **实时资源监控**：分析运行中应用的内存使用和CPU占用率
- **资源效率分析**：计算内存使用与应用大小的比例，评估资源效率
- **交互式可视化**：通过图表和表格直观展示分析结果
- **数据导出与共享**：支持将分析结果导出为JSON格式
- **在线部署支持**：可以部署到Vercel等平台进行在线数据可视化
- **跨平台支持**：支持Windows和macOS操作系统

## 🔧 技术栈

- **后端**：Python、Flask
- **数据分析**：Pandas
- **可视化**：Plotly
- **前端**：HTML、Tailwind CSS、Alpine.js
- **部署**：Vercel Serverless Functions

## 📋 系统要求

- Python 3.6+
- Windows 10+ 或 macOS 10.15+
- 对于扫描功能：需要管理员/超级用户权限（仅首次运行）

## 🚀 快速开始

### 安装

1. 克隆仓库到本地：
   ```bash
   git clone https://github.com/yourusername/electron-apps-analyzer.git
   cd electron-apps-analyzer
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 使用方法

#### 完整分析流程

运行主程序，执行完整的扫描和可视化流程：

```bash
python main.py
```

这将打开一个交互式菜单，您可以选择：
- 执行完整流程（扫描 + 可视化）
- 仅执行扫描，导出JSON数据
- 仅执行可视化，使用现有JSON数据

#### 仅执行扫描

如果只想扫描系统中的Electron应用并导出数据：

```bash
python find_electron_apps.py --memory --performance
```

常用参数：
- `--memory`：分析内存使用情况
- `--performance`：分析CPU使用率
- `--ratio`：计算内存/大小比例
- `--sort [name|size|memory|cpu]`：指定排序方式
- `--top N`：只显示前N个应用

#### 仅执行可视化

如果已有扫描数据，只想可视化展示：

```bash
python visualize_electron_apps.py --json-file electron_apps.json
```

常用参数：
- `--port PORT`：指定Web服务器端口（默认8080）
- `--no-browser`：不自动打开浏览器

### 在线演示版本

在线演示版本仅提供可视化功能，您需要上传由本地扫描工具生成的数据：

1. 访问演示网站：[https://electron-apps-analyzer.vercel.app/](https://electron-apps-analyzer.vercel.app/)
2. 上传您的JSON数据文件（由`find_electron_apps.py`生成）
3. 查看可视化分析结果

## 📂 项目结构

```
electron-apps-analyzer/
├── api/                        # 用于Vercel部署的API目录
│   ├── __init__.py
│   ├── index.py                # Flask API入口点
│   ├── templates/              # API模板目录
│   │   └── index.html
│   └── static/                 # API静态资源目录
├── find_electron_apps.py       # 扫描Electron应用的脚本
├── visualize_electron_apps.py  # 可视化展示结果的脚本
├── main.py                     # 整合扫描和可视化的主程序
├── requirements.txt            # 项目依赖
├── vercel.json                 # Vercel部署配置
├── DEPLOYMENT.md               # 部署指南
└── README.md                   # 项目说明文档
```

## 🌐 部署到Vercel

您可以将项目的Web部分部署到Vercel，详细步骤请参考[部署指南](DEPLOYMENT.md)。

简要步骤：

1. 安装Vercel CLI：
   ```bash
   npm install -g vercel
   ```

2. 登录Vercel：
   ```bash
   vercel login
   ```

3. 在项目根目录下运行：
   ```bash
   vercel --prod
   ```

## 🔍 常见问题

### Q: 为什么有些应用无法检测到？

A: 应用检测基于多种Electron特征标记。某些高度定制的Electron应用可能会删除或修改这些标记，导致无法被识别。

### Q: 为什么应用的内存使用在不同时间会有差异？

A: 内存使用是动态的，取决于应用的当前状态和活动。建议多次测量以获得更准确的平均值。

### Q: 在线部署版本为什么无法扫描我的系统？

A: 由于安全限制，在线部署版本无法访问您的本地文件系统。您需要在本地运行扫描工具，然后将JSON结果上传到在线版本进行可视化。

## 👥 贡献指南

我们欢迎并感谢任何形式的贡献！以下是一些参与项目的方式：

1. **报告Bug**：如果您发现了问题，请[创建issue](https://github.com/yourusername/electron-apps-analyzer/issues)
2. **提出新功能**：有新想法？欢迎通过issue分享
3. **提交代码**：
   - Fork仓库
   - 创建您的特性分支: `git checkout -b feature/amazing-feature`
   - 提交您的更改: `git commit -m 'Add some amazing feature'`
   - 推送到分支: `git push origin feature/amazing-feature`
   - 创建Pull Request

请确保您的代码符合项目的编码风格，并添加必要的测试和文档。

## 📄 许可证

本项目采用MIT许可证 - 详情请参阅[LICENSE](LICENSE)文件。

## 📬 联系方式

项目作者 - [@yourusername](https://github.com/yourusername)

项目链接: [https://github.com/yourusername/electron-apps-analyzer](https://github.com/yourusername/electron-apps-analyzer)

---

如果您觉得这个项目有用，请给它一个⭐️！ 
