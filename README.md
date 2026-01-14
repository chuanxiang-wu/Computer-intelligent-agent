# Computer Agent 项目文档

## 项目概述

Computer Agent 是一个能够将自然语言转换为计算机操作的智能代理系统。该项目基于视觉语言模型（VLM）和大型语言模型（LLM），通过理解屏幕截图和用户指令，自动执行各种 GUI 操作任务。

### 核心特性

- **视觉理解**：使用视觉语言模型（如 Qwen3-VL-30B-A3B-Thinking）理解屏幕截图
- **自然语言交互**：支持中文自然语言指令输入
- **多平台支持**：支持 Windows、Linux、macOS 操作系统
- **双代理架构**：
  - **GUI Agent**：处理点击、输入、导航等图形界面操作
  - **Code Agent**：执行 Python/Bash 代码完成复杂的数据处理和计算任务
- **反思机制**：内置轨迹反思功能，优化任务执行路径
- **OCR 能力**：集成 Tesseract OCR 进行文本识别和定位

### 技术栈

- **编程语言**：Python 3.11
- **核心依赖**：
  - `openai==2.14.0` - LLM API 调用
  - `pyautogui==0.9.54` - GUI 自动化操作
  - `Pillow==12.1.0` - 图像处理
  - `pytesseract==0.3.13` - OCR 文本识别
  - `numpy==2.4.0` - 数值计算
  - `backoff==2.2.1` - API 重试机制

## 项目结构

```
computer_agent/
├── agent/               # 代理核心模块
│   ├── agent.py        # 主代理类（Agent）
│   ├── worker.py       # 工作代理类（Worker）
│   └── code_agent.py   # 代码执行代理
├── core/               # 核心引擎模块
│   ├── engine.py       # LLM 引擎（OpenAI/vLLM）
│   ├── llm.py          # LLM 代理封装
│   └── model.py        # 基础模型类
├── utils/              # 工具模块
│   ├── common_utils.py # 通用工具函数
│   ├── grounding.py    # 视觉定位和坐标生成
│   ├── local_env.py    # 本地环境配置
│   └── formatters.py   # 输出格式化
├── prompt/             # 提示词模块
│   └── sys_prompt.py   # 系统提示词模板
├── logs/               # 日志目录
│   └── agent.log       # 代理运行日志
├── main.py             # 主入口文件
├── requirements.txt    # Python 依赖
├── pyproject.toml      # 项目配置
└── README.md           # 项目说明
```

## 核心模块说明

### 1. Agent 模块（agent/）

#### Agent 类（agent/agent.py）
- **职责**：主代理协调器，管理 Worker 和 Grounding Agent
- **关键方法**：
  - `predict(instruction, observation)`：根据指令和观察生成动作
  - `reset()`：重置代理状态

#### Worker 类（agent/worker.py）
- **职责**：执行具体任务，生成操作计划
- **关键功能**：
  - 生成反思（Reflection）优化执行轨迹
  - 协调 GUI Agent 和 Code Agent
  - 管理消息历史和上下文
- **关键方法**：
  - `generate_next_action(instruction, obs)`：生成下一步动作
  - `_generate_reflection(instruction, obs)`：生成反思
  - `flush_messages()`：管理消息历史长度

#### CodeAgent 类（agent/code_agent.py）
- **职责**：执行 Python/Bash 代码完成复杂任务
- **适用场景**：
  - 电子表格计算和数据处理
  - 批量文件操作
  - 数据筛选、排序、格式化

### 2. Core 模块（core/）

#### LLM 引擎（core/engine.py）
- **LLMEngineOpenAI**：OpenAI API 兼容引擎
  - 支持标准生成和思考模式（Thinking Mode）
  - 自动重试机制（backoff）
- **LMMEnginevLLM**：vLLM 本地部署引擎
  - 支持自定义端点
  - 支持思考模式

#### LLM 代理（core/llm.py）
- **LLMAgent**：LLM 调用封装
  - 消息管理（添加、删除、替换）
  - 图像编码（Base64）
  - 多引擎支持（OpenAI/vLLM）

### 3. Utils 模块（utils/）

#### 视觉定位（utils/grounding.py）
- **OSWorldACI**：操作系统世界抽象计算机接口
- **核心方法**：
  - `click()`：点击操作
  - `type()`：文本输入
  - `drag_and_drop()`：拖拽操作
  - `scroll()`：滚动操作
  - `hotkey()`：快捷键操作
  - `switch_applications()`：切换应用
  - `call_code_agent()`：调用代码代理
  - `generate_coords()`：生成坐标（视觉定位）
  - `generate_text_coords()`：生成文本坐标（OCR）

#### 通用工具（utils/common_utils.py）
- `call_llm_safe()`：安全的 LLM 调用
- `split_thinking_response()`：分离思考内容
- `create_pyautogui_code()`：生成 PyAutoGUI 代码
- `parse_code_from_string()`：从字符串解析代码

### 4. Prompt 模块（prompt/）

#### 系统提示词（prompt/sys_prompt.py）
- **PROCEDURAL_MEMORY**：过程记忆提示词
  - `construct_simple_worker_procedural_memory()`：构建 Worker 提示词
  - `REFLECTION_ON_TRAJECTORY`：轨迹反思提示词
  - `CODE_AGENT_PROMPT`：代码代理提示词
  - `PHRASE_TO_WORD_COORDS_PROMPT`：文本坐标定位提示词

## 构建和运行

### 环境准备

1. **Python 版本要求**：Python 3.11
2. **虚拟环境创建**：
```bash
# 使用 uv（推荐）
uv venv
.venv\Scripts\activate

# 或使用 venv
python -m venv .venv
.venv\Scripts\activate
```

3. **安装依赖**：
```bash
pip install -r requirements.txt
```

### 配置要求

在使用前，需要在 `main.py` 中配置以下参数：

```python
engine_params = {
    "engine_type": "openai",  # 或 "vllm"
    "model": "Qwen/Qwen3-VL-30B-A3B-Thinking",
    "base_url": "your base_url",  # API 端点
    "api_key": "your api key",    # API 密钥
    "temperature": 0
}

# 视觉定位配置
grounding_width = 1000  # 模型输出坐标宽度
grounding_height = 1000  # 模型输出坐标高度
screen_width = 1920     # 屏幕实际宽度
screen_height = 1080    # 屏幕实际高度
```

### 运行方式

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 运行主程序
python main.py
```

### 交互流程

1. 程序启动后，会提示输入命令
2. 输入自然语言指令（例如："打开浏览器中的bilibili网站"）
3. Agent 会：
   - 截取当前屏幕
   - 分析屏幕内容
   - 生成操作计划
   - 执行操作（点击、输入等）
   - 反思执行结果
   - 继续下一步，直到任务完成
4. 输入 `exit` 或 `q` 退出程序

### 日志查看

运行日志保存在 `logs/agent.log` 文件中，包含：
- Agent 决策信息
- 执行的操作代码
- 反思内容
- 错误信息

## 开发约定

### 代码风格

- **命名规范**：
  - 类名：大驼峰（PascalCase），如 `OSWorldACI`
  - 函数/方法名：小写+下划线（snake_case），如 `generate_coords`
  - 常量：全大写+下划线（UPPER_SNAKE_CASE），如 `UBUNTU_APP_SETUP`
- **注释**：
  - 使用中文注释
  - 关键逻辑必须添加注释说明
  - 类和方法使用 docstring 文档字符串
- **日志**：
  - 使用 Python logging 模块
  - 日志级别：DEBUG、INFO、WARNING、ERROR
  - 日志格式：`时间 - 模块名 - 级别 - 消息`

### 架构原则

1. **单一职责**：每个类和方法只负责一个明确的功能
2. **代理分层**：
   - Agent：协调层
   - Worker：执行层
   - Grounding Agent：视觉定位层
   - Code Agent：代码执行层
3. **消息管理**：
   - 长上下文模型：保留所有文本，只保留最新图片
   - 短上下文模型：删除整个轮次消息
4. **错误处理**：
   - 使用 try-except 捕获异常
   - 记录详细的错误日志
   - 提供合理的降级策略

### 测试建议

- **单元测试**：测试核心工具函数（坐标转换、OCR 解析等）
- **集成测试**：测试完整的任务执行流程
- **视觉测试**：验证坐标生成的准确性
- **代码测试**：验证 Code Agent 的代码执行安全性

### 关键注意事项

1. **坐标系统**：
   - 模型输出坐标与实际屏幕坐标需要转换
   - 转换公式：`实际坐标 = 模型坐标 * (屏幕尺寸 / 模型输出尺寸)`

2. **平台兼容性**：
   - 不同操作系统的快捷键不同（Windows: Ctrl, macOS: Cmd）
   - 文件路径分隔符不同
   - 应用切换方式不同

3. **性能优化**：
   - 控制消息历史长度（`max_trajectory_length`）
   - 合理使用缓存
   - 避免不必要的截图和 OCR 操作


## 常见问题

### Q1: 如何更换 LLM 模型？
修改 `main.py` 中的 `engine_params` 配置，更改 `model` 和 `base_url` 参数。

### Q2: 如何调整屏幕分辨率？
修改 `main.py` 中的 `screen_width` 和 `screen_height` 参数，确保与实际屏幕一致。

### Q3: Code Agent 执行失败怎么办？
- 检查任务是否适合用代码完成
- 查看 `logs/agent.log` 中的详细错误信息
- 尝试手动执行代码排查问题

### Q4: 如何添加新的操作？
在 `utils/grounding.py` 的 `OSWorldACI` 类中添加新方法，并使用 `@agent_action` 装饰器。

### Q5: 如何禁用反思功能？
在 `main.py` 中设置 `enable_reflection=False`。

## 扩展开发

### 添加新的 LLM 引擎

1. 在 `core/engine.py` 中创建新的引擎类
2. 实现 `generate()` 和 `generate_with_thinking()` 方法
3. 在 `core/llm.py` 的 `LLMAgent` 中添加对新引擎的支持

### 添加新的平台支持

1. 在 `utils/grounding.py` 的 `OSWorldACI` 中添加平台特定的操作逻辑
2. 更新 `switch_applications()` 和 `open()` 方法
3. 测试所有操作在新平台上的兼容性

### 自定义提示词

1. 在 `prompt/sys_prompt.py` 中修改 `PROCEDURAL_MEMORY` 类
2. 根据需求调整系统提示词模板
3. 测试提示词对任务执行的影响

## 许可证

详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎提交 Issue 和 Pull Request。在提交前请确保：
- 代码符合项目风格规范
- 添加必要的测试
- 更新相关文档
- 通过所有现有测试