# 贡献指南

感谢您考虑为Electron应用资源分析器项目做出贡献！这个文档将指导您如何参与项目开发。

## 行为准则

参与本项目即表示您同意遵守我们的行为准则。请尊重所有的项目贡献者和用户。

## 如何贡献

### 报告Bug

如果您发现了Bug，请通过GitHub Issues报告，并尽可能提供以下信息：

1. 清晰具体的标题和描述
2. 重现步骤（如何触发这个Bug）
3. 预期行为与实际行为
4. 环境信息（操作系统、Python版本等）
5. 如果可能，附上截图或代码示例

### 提出新功能

如果您有新功能的想法，同样欢迎通过GitHub Issues提出：

1. 清晰描述这个功能的作用
2. 说明为什么这个功能对项目有价值
3. 如果可能，描述它的工作方式或提供简单的实现思路

### 提交代码

1. Fork仓库
2. 创建您的特性分支：`git checkout -b feature/amazing-feature`
3. 进行您的更改
4. 遵循编码规范（见下文）
5. 提交您的更改：`git commit -m 'Add some amazing feature'`
6. 推送到分支：`git push origin feature/amazing-feature`
7. 创建Pull Request

## 编码规范

### Python代码规范

- 遵循[PEP 8](https://www.python.org/dev/peps/pep-0008/)代码风格指南
- 使用4个空格进行缩进（不使用Tab）
- 行长度不超过100个字符
- 每个函数、类和模块都应当有恰当的文档字符串
- 变量和函数名使用小写下划线命名法（例如：`calculate_memory_usage`）
- 类名使用驼峰命名法（例如：`ElectronAppAnalyzer`）
- 常量使用大写字母和下划线（例如：`MAX_APPS`）

### 前端代码规范

- HTML/CSS/JavaScript遵循一致的缩进（2个空格）
- JavaScript使用camelCase命名变量和函数
- 尽量使用ES6+语法
- 保持HTML语义化

### 提交信息规范

提交信息应当简洁明了，并遵循以下格式：

```
<类型>: <简短描述>

<详细描述（可选）>
```

类型可以是：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更改
- `style`: 不影响代码运行的风格修改
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

## 开发环境设置

### 本地开发

1. 克隆仓库到本地：
   ```bash
   git clone https://github.com/yourusername/electron-apps-analyzer.git
   cd electron-apps-analyzer
   ```

2. 创建并激活虚拟环境（推荐）：
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. 安装开发依赖：
   ```bash
   pip install -r requirements-dev.txt  # 如果存在
   # 否则
   pip install -r requirements.txt
   ```

### 测试

在提交代码之前，请确保所有测试都能通过：

```bash
python -m pytest
```

或者，运行特定测试：

```bash
python -m pytest tests/test_specific.py
```

## 文档

如果您的更改影响了用户体验或添加了新功能，请同时更新相关文档。

## 发布流程

项目维护者将负责版本发布。如果您是维护者，请遵循以下步骤：

1. 更新版本号（遵循[语义版本控制](https://semver.org/)）
2. 更新CHANGELOG.md
3. 创建新的GitHub发布，附带发布说明

## 许可证

通过贡献代码，您同意您的贡献将在项目的MIT许可证下提供。

---

再次感谢您的贡献！ 
