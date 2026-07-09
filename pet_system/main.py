"""
pet_system/main.py — 1号模块独立测试入口

启动桌宠窗口，功能：
    - 全局键盘监听 → glow_level 变化 + PNG 帧切换
    - 鼠标拖动桌宠
    - 右键菜单退出

不依赖其他模块，可独立运行。
"""

import sys
import os

from PyQt5.QtWidgets import QApplication

# 支持直接运行本文件和作为包导入两种方式
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pet_system.pet_window import PetWindow


def main():
    app = QApplication(sys.argv)
    window = PetWindow()
    window.show()
    window.center_on_screen()

    print("=== LumiPaw 桌宠系统 ===")
    print("操作说明：")
    print("  - 敲击键盘 → 猫变亮 + 切换动画帧")
    print("  - 停止敲击 5 秒后 → 猫逐渐变暗")
    print("  - 鼠标左键拖动 → 移动桌宠位置")
    print("  - 鼠标右键 → 退出")
    print()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
