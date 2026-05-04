# QQListener 开发指南

本文档面向开发者，介绍如何搭建开发环境、理解项目架构以及进行二次开发。

## 环境要求

- **Python**: 3.11+
- **操作系统**: Windows 10 1903+ (Win7/8/8.1 不支持)
- **IDE**: 推荐使用 VS Code 或 PyCharm

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/BSOD-MEMZ/QQListener.git
cd QQListener
```

### 2. 同步环境

```bash
uv sync
```

### 3. 运行程序

```bash
uv run main.py
```

## 项目结构详解

```
QQListener/
├── main.py                    # 程序入口点
├── pyproject.toml             # 项目配置和依赖管理
├── ruff.toml                  # 代码规范配置
├── src/                       # 源代码目录
│   ├── main.py               # src 包入口
│   ├── core/                 # 核心功能模块
│   │   ├── app.py            # QQListenerApp 主应用类
│   │   ├── settings.py       # Settings 配置管理（单例）
│   │   ├── signals.py        # 全局信号定义
│   │   └── worker.py         # NotificationWorker 工作线程
│   ├── ui/                   # 用户界面模块
│   │   ├── settings_window.py # 设置窗口
│   │   ├── notify_window.py   # 通知弹窗
│   │   ├── notify_manager.py  # 通知管理器（单例）
│   │   └── tray_icon.py       # 系统托盘图标
│   └── utils/                # 工具模块
│       ├── message_processor.py # 消息处理逻辑
│       └── tts.py             # TTS 语音合成
├── asset/                     # 静态资源
├── translations/              # 国际化翻译文件
└── setting.json              # 用户配置文件（运行时生成）
```

## 架构设计

### 整体架构

```
主进程 (QApplication)
├── 核心模块
│   ├── Settings (单例模式)      # 配置管理
│   ├── Signals (全局信号)       # 全局信号定义
│   └── NotifyManager (单例模式)  # 通知管理器
│
├── NotificationWorker (QThread)  # 通知监控工作线程
│   ├── 捕获模式
│   │   ├── WinSDK 模式          # 监听系统通知
│   │   └── UIA 模式             # UI自动化获取
│   └── MessageProcessor         # 消息解析/优先级判断
│
└── UI 界面
    ├── SettingsWin              # 设置窗口
    ├── NotifyWindow             # 通知弹窗
    └── TrayIcon                 # 系统托盘
```

### 核心组件交互流程

```
1. 通知捕获流程:
   NotificationWorker → MessageProcessor → NotifyManager → NotifyWindow

2. 设置变更流程:
   SettingsWindow → Settings.save() → Signals.settings_changed → 各组件响应

3. 语音播报流程:
   NotifyWindow → TTSManager → TTSThread → pygame 播放
```

## 核心类详解

### Settings - 配置管理（单例模式）

负责所有配置的加载、保存和访问。采用单例模式确保全局唯一实例。

**主要功能:**
- 从 JSON 文件加载/保存配置
- 提供类型安全的属性访问
- 支持默认值和空值检查

**使用示例:**

```python
from src.core.settings import get_settings

settings = get_settings()

# 读取配置
interval = settings.scan_interval  # float: 扫描间隔
persons = settings.important_persons  # list: 重要人物列表

# 修改配置
settings.set("ScanInterval", 0.5)
settings.update({
    "User_QQ": "123456789",
    "Tencent_Files_Path": "C:/Users/..."
})

# 保存到文件
settings.save()
```

**添加新配置项:**

1. 在 `settings.py` 中添加属性:
```python
@property
def my_new_setting(self) -> str:
    result = self.get("My_New_Setting", "default_value")
    return str(result) if result else "default_value"
```

2. 在 `settings_window.py` 中添加 UI:
```python
self.my_setting = QLineEdit(self.data.get("My_New_Setting", self.settings.my_new_setting))
form.addRow(self.tr("我的新设置"), self.my_setting)
```

3. 在 `save_settings()` 中保存:
```python
"My_New_Setting": self.my_setting.text(),
```

### NotificationWorker - 通知监控工作线程

继承自 `QThread`，在后台持续监控 Windows 通知。

**两种工作模式:**

#### WinSDK 模式（推荐）
通过 Windows SDK 监听系统通知中心，性能最好。

```python
# 使用 winsdk 库
import winsdk.windows.ui.notifications.management as mgmt

listener = mgmt.UserNotificationListener.current
notifs = await listener.get_notifications_async(
    notifications.NotificationKinds.TOAST
)
```

#### UIA 模式（备选）
通过 UI Automation 技术从窗口元素获取通知，兼容性更好但性能较差。

```python
# 使用 uiautomation 库
import uiautomation as auto
desktop = auto.GetRootControl()
# 遍历窗口控件获取通知文本
```

**信号:**
- `notification_ready(dict)`: 当有新通知时发射，携带通知数据

### MessageProcessor - 消息处理器

负责解析通知内容、判断优先级、过滤黑名单。

**处理流程:**
1. 计算消息哈希，检查冷却时间
2. 检查黑名单过滤
3. 判断优先级（普通/重要/呼叫）
4. 提取图片缩略图（如果包含图片）

**优先级判断逻辑:**
```python
# 呼叫消息（最高优先级）
if calling_keyword in message:
    priority = 0  # 紧急
    duration = calling_duration

# 重要人物/关键词
elif sender in important_persons or keyword in message:
    priority = 0  # 重要
    duration = duration_important

# 普通消息
else:
    priority = 1  # 普通
    duration = duration_everyone
```

### NotifyManager - 通知管理器（单例）

管理所有通知窗口的创建和销毁。

```python
from src.ui.notify_manager import get_notify_manager

manager = get_notify_manager()

# 显示通知
window = manager.show_notification({
    "Sender": "发送者",
    "Message": "消息内容",
    "Duration": 5000,
    "Priority": 0,
    "Calling": False
})

# 关闭所有通知
manager.close_all_notifications()
```

### NotifyWindow - 通知弹窗

显示通知的独立窗口，支持动画效果和交互。

**特性:**
- 毛玻璃背景和阴影效果
- 渐入/渐出动画
- 支持显示图片缩略图
- 支持文件附件预览
- 呼叫模式特殊动画

### TTSManager - 语音管理器

管理语音播报功能。

**支持的引擎:**
- **Edge TTS**: 基于神经网络，音质好，需联网
- **系统 TTS**: Windows 自带，离线可用

```python
from src.utils.tts import TTSManager

tts = TTSManager()
tts.speak("您有一条新消息")  # 异步播放
tts.stop()  # 停止播放
```

## 代码规范

项目使用 **Ruff** 进行代码检查和格式化。

### 安装 Ruff

```bash
pip install ruff
```

### 常用命令

```bash
# 检查代码
ruff check src/

# 自动修复问题
ruff check src/ --fix

# 格式化代码
ruff format src/

# 检查特定规则
ruff check src/ --select E,W,F,B
```

### 编码规范

1. **类型注解**: 所有函数参数和返回值都应添加类型注解
2. **空值检查**: 使用 `if x:` 或 `if x is not None:` 进行空值检查
3. **异常处理**: 使用具体的异常类型，避免裸 `except:`
4. **文档字符串**: 类和方法应添加文档字符串说明

**示例:**

```python
def process_data(data: dict[str, Any] | None) -> dict | None:
    """处理数据并返回结果
    
    Args:
        data: 输入数据字典
        
    Returns:
        处理后的数据，如果输入无效则返回 None
    """
    if not data or not isinstance(data, dict):
        return None
    
    try:
        result = {k: v for k, v in data.items() if v}
        return result
    except (OSError, ValueError) as e:
        print(f"处理失败: {e}")
        return None
```

## 扩展开发

### 添加新的通知捕获模式

1. 在 `worker.py` 中添加新方法:

```python
async def _run_custom_mode(self):
    """自定义捕获模式"""
    while self._running:
        try:
            # 实现捕获逻辑
            texts = await self._fetch_notifications()
            
            if texts:
                result = self.processor.process_notification(texts)
                if result:
                    self.notification_ready.emit(result)
                    
        except Exception as e:
            print(f"自定义模式异常: {e}")
            
        await asyncio.sleep(self.settings.scan_interval)
```

2. 在 `run()` 中添加模式选择:

```python
def run(self):
    if self.settings.capture_mode == "custom":
        asyncio.run(self._run_custom_mode())
```

### 添加新的 TTS 引擎

1. 在 `tts.py` 的 `TTSThread` 中添加:

```python
def _run_custom_tts(self):
    """使用自定义 TTS 引擎"""
    try:
        # 初始化引擎
        engine = CustomTTSEngine()
        
        # 合成语音
        audio_data = engine.synthesize(self.text)
        
        # 保存并播放
        output_file = "custom_tts.wav"
        engine.save(audio_data, output_file)
        
        self.finished_signal.emit(output_file)
    except Exception as e:
        print(f"自定义 TTS 失败: {e}")
        self.finished_signal.emit("")
```

2. 在 `run()` 中添加引擎选择:

```python
def run(self):
    if self.settings.tts_engine == "custom":
        self._run_custom_tts()
```

### 自定义通知样式

修改 `notify_window.py` 中的 `PRIORITY_STYLES`:

```python
PRIORITY_STYLES = {
    0: {  # 紧急/重要
        "bg_color": "rgba(255, 0, 0, 255)",      # 红色背景
        "text_color": "white",
        "overlay": "rgba(255, 0, 0, 100)",
    },
    1: {  # 普通
        "bg_color": "rgba(43, 43, 43, 255)",
        "text_color": "white",
        "overlay": "rgba(0, 0, 0, 80)",
    },
    # 添加更多优先级...
}
```

或使用 QSS 覆写功能（在设置中启用）。

## 调试技巧

### 启用调试输出

在代码中添加日志输出:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告")
logger.error("错误")
```

### 调试 WinSDK 模式

```python
# 在 worker.py 中添加调试输出
async def _run_winsdk_mode(self):
    print("WinSDK 模式启动")
    # ...
    notifs = await listener.get_notifications_async(...)
    print(f"获取到 {len(notifs)} 条通知")
```

### 调试 UIA 模式

```python
# 在 _get_uia_toasts 中添加调试
for pane in desktop.GetChildren():
    print(f"找到控件: {pane.ClassName}")
```

## 打包发布

### 使用 PyInstaller

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller --onefile --windowed --icon=icon.ico main.py

# 包含资源文件
pyinstaller --onefile --windowed --icon=icon.ico \
    --add-data "asset;asset" \
    --add-data "translations;translations" \
    main.py
```

## 相关资源

- [PySide6 文档](https://doc.qt.io/qtforpython/)
- [Windows SDK 通知 API](https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/)
- [Edge TTS 文档](https://github.com/rany2/edge-tts)
- [项目主页](https://xxtsoft.top/support/qqlistener)

## 联系方式

- 作者: xxt8582753
- 邮箱: xxt8582753@126.com
- 网站: https://xxtsoft.top

---

**Happy Coding! **
