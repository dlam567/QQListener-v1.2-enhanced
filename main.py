#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from PySide6.QtCore import QSharedMemory, QSystemSemaphore


def setup_working_directory():
    """将工作目录切换到程序所在目录"""
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        os.chdir(exe_dir)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_single_instance():
    """检查单实例，返回 True 表示可以继续，False 表示已有实例"""
    semaphore = QSystemSemaphore("QQListener_Semaphore", 1)
    shared_memory = QSharedMemory("QQListener_SharedMemory")

    semaphore.acquire()
    if shared_memory.attach():
        semaphore.release()
        return False, None, None

    shared_memory.create(1)
    semaphore.release()
    return True, shared_memory, semaphore


def main():
    # 1. 设置工作目录
    setup_working_directory()

    # 2. 单实例检测（不创建 QApplication）
    is_first, shared_memory, semaphore = check_single_instance()

    if not is_first:
        # 已有实例，尝试激活窗口（需要临时创建 QApplication）
        from PySide6.QtWidgets import QApplication, QMessageBox
        temp_app = QApplication(sys.argv)
        QMessageBox.warning(None, "程序已在运行", "QQListener 已经在运行中！")
        sys.exit(0)

    # 3. 运行主程序（app.py 内部会创建 QApplication）
    from src.core.app import run_app

    try:
        run_app()
    finally:
        if shared_memory:
            shared_memory.detach()


if __name__ == "__main__":
    main()