import sys
import os
from pathlib import Path
from loguru import logger


def setup_logging(level="INFO"):
    # 移除默认处理器
    logger.remove()

    # 检查 stderr 是否可用
    if sys.stderr is not None:
        # 有控制台：输出到 stderr
        logger.add(sys.stderr, level=level, backtrace=False, diagnose=False)
    else:
        # 无控制台模式（PyInstaller --noconsole）：只输出到文件
        pass

    # 获取合适的日志目录
    log_dir = get_log_directory()

    # 确保目录存在
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # 如果还没有权限，使用临时目录作为备用
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / "QQListener_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(f"使用备用日志目录: {log_dir}")

    # 添加文件日志
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention="7 days",
        level=level,
        backtrace=True,
        diagnose=True,
        encoding="utf-8",  # 添加编码设置，避免中文乱码
    )

    logger.info(f"日志系统初始化完成，日志目录: {log_dir}")


def get_log_directory():
    """
    获取合适的日志目录，按优先级：
    1. 程序所在目录下的 logs（对于安装在 ProgramData 的程序）
    2. 用户应用数据目录
    3. 程序所在目录（兜底）
    """
    # 判断是否是打包后的 exe
    if getattr(sys, 'frozen', False):
        # 打包后的 exe，获取 exe 所在目录
        exe_dir = Path(sys.executable).parent
    else:
        # 开发环境，获取项目根目录
        exe_dir = Path(__file__).parent.parent.parent

    # 方案1: 使用程序目录下的 logs（适用于安装在 ProgramData 的情况）
    program_logs = exe_dir / "logs"

    # 方案2: 使用用户 AppData 目录（推荐用于普通程序）
    user_logs = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / "QQListener" / "logs"

    # 方案3: 使用公共 ProgramData 目录（适用于所有用户共享）
    common_logs = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / "QQListener" / "logs"

    # 自动选择策略：
    # 如果程序安装在 Program Files 或 ProgramData，使用用户目录
    # 否则使用程序目录下的 logs

    program_path = str(exe_dir).lower()

    if 'program files' in program_path or 'programdata' in program_path:
        # 安装在受保护目录，使用用户 AppData
        log_dir = user_logs
    else:
        # 安装在普通目录（如 D:\MyApp），使用程序目录
        log_dir = program_logs

    return log_dir