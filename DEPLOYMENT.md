# 将Electron应用分析工具部署到Vercel

本指南详细说明了如何将Electron应用资源使用分析工具的Web部分部署到Vercel。

## 前提条件

- [Node.js](https://nodejs.org/) 安装（用于Vercel CLI）
- [npm](https://www.npmjs.com/) 或 [yarn](https://yarnpkg.com/) 包管理器
- [Vercel](https://vercel.com/) 账号
- [Git](https://git-scm.com/) 安装（推荐）

## 方法一：使用Vercel CLI部署

### 步骤1：安装Vercel CLI

```bash
npm install -g vercel
```

### 步骤2：登录Vercel

```bash
vercel login
```

系统会引导您完成登录过程，可以选择通过浏览器或电子邮件进行验证。

### 步骤3：初始化Git仓库（如果尚未初始化）

```bash
git init
git add .
git commit -m "Initial commit"
```

### 步骤4：部署到Vercel

在项目根目录下运行：

```bash
vercel
```

按照提示配置部署选项：

- **Set up and deploy?** 选择 `Y`
- **Which scope?** 选择您的个人账号或团队
- **Link to existing project?** 如果是首次部署，选择 `N`
- **What's your project's name?** 输入项目名称，例如 `visualize-electron-apps`
- **In which directory is your code located?** 默认为 `.`（当前目录）

部署完成后，Vercel会提供一个预览URL。要部署到生产环境，请运行：

```bash
vercel --prod
```

## 方法二：通过Vercel网站部署

### 步骤1：将代码推送到GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/h7ml/visualize_electron_apps.git
git push -u origin main
```

### 步骤2：导入GitHub仓库

1. 登录 [Vercel 仪表板](https://vercel.com/dashboard)
2. 点击 "Import Project" 或 "New Project"
3. 选择 "Import Git Repository"
4. 选择您的GitHub仓库
5. Vercel会自动检测项目类型，点击 "Deploy" 开始部署

## 自定义域名（可选）

部署成功后，您可以为项目添加自定义域名：

1. 在Vercel仪表板中，选择您的项目
2. 点击 "Settings" > "Domains"
3. 添加您的域名并按照指示配置DNS记录

## 环境变量（可选）

如果您的项目需要特定的环境变量，可以在Vercel仪表板中配置：

1. 在项目设置中，选择 "Environment Variables"
2. 添加所需的键值对

## 部署配置文件

项目中的 `vercel.json` 文件已经配置好了路由规则，将所有请求重定向到Flask应用：

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/api/index" }]
}
```

## 常见问题解答

### Q: 部署时出现"Build Failed"错误怎么办？

A: 检查 `requirements.txt` 文件是否正确列出了所有依赖，并确保依赖版本与Vercel兼容。

### Q: 为什么我在Vercel上部署的应用无法扫描我的电脑上的Electron应用？

A: 由于安全限制，Vercel等云平台无法访问您本地计算机上的文件系统。扫描功能只能在本地运行，Web部署版本仅提供可视化功能，需要上传由本地扫描工具生成的JSON数据。

### Q: 部署后，我的Flask应用返回404错误？

A: 确保 `vercel.json` 文件正确配置，并且 `api/index.py` 文件位于正确的位置。Vercel的Python Serverless Functions需要放在 `api` 目录下。

## 注意事项

- Vercel的免费计划有一定的限制，如果您的应用访问量很大，可能需要升级到付费计划
- Vercel部署的应用是无状态的，如果需要持久化存储用户上传的数据，需要使用外部存储服务 
