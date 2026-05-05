import sys

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
        # 注意：此时没有任何控制台输出
        pass

    # 始终添加文件日志（推荐）
    from pathlib import Path

    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention="7 days",
        level=level,
        backtrace=True,  # 打包后建议开启，方便排查问题
        diagnose=True,
    )
