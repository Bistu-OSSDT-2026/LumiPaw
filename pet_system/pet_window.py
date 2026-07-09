"""
pet_window.py — 桌宠主窗口

PyQt5 置顶无边框透明窗口，组合 CatRenderer 和 GlowController，
暴露规则手册要求的 3 个标准接口。

功能：
    - 全局键盘监听：按键 → glow_level += 2，5秒无输入衰减
    - 键盘帧切换：每次按键播放下一帧 PNG
    - 鼠标拖动：按住桌宠窗口可拖动位置
    - 右键菜单：退出桌宠
    - 装饰穿戴：通过 economy_module 穿戴/脱卸装饰物品

对外接口（规则手册要求）：
    set_glow(level: int)
    trigger_reward_glow()
    update_state(state: str)

扩展接口（穿戴系统）：
    wear_item(item_id: str) -> bool
    take_off_item(item_id: str) -> bool
    refresh_decorations()

禁止：
    直接修改 glow_level
    依赖其他模块内部实现
"""

import os
import sys
from PyQt5.QtWidgets import QWidget, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter

from .glow_controller import GlowController
from .cat_renderer import CatRenderer

# 确保项目根目录在 sys.path 中，用于导入 economy_module
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from economy_module.economy import (
        wear_item as _economy_wear_original,
        take_off_item as _economy_take_off,
        get_render_order as _economy_render_order,
        get_coins,
        shop_categories, inventory, warehouse, wear_slots,
    )
    ECONOMY_AVAILABLE = True

    # --- Monkey Patch: 去除 economy.wear_item 的 3 次上限 ---
    def _unlimited_wear(item_id: str) -> bool:
        """去除了每部位最多 3 件限制的 wear_item。"""
        target_slot = None
        found_item = None
        for category_id, category in shop_categories.items():
            if item_id in category["items"]:
                found_item = category["items"][item_id]
                if found_item.get("layer") == "head":
                    target_slot = "head"
                elif found_item.get("layer") == "face":
                    target_slot = "face"
                elif found_item.get("layer") == "neck":
                    target_slot = "neck"
                elif category_id == "body":
                    target_slot = "body"
                elif category_id in ("face", "eyewear"):
                    target_slot = "face"
                elif category_id == "headwear":
                    target_slot = "head"
                elif category_id == "neckwear":
                    target_slot = "neck"
                break

        if not target_slot or not found_item:
            print(f"[错误] 未知物品: {item_id}")
            return False
        if item_id not in inventory or inventory[item_id] <= 0:
            print(f"[错误] 请先在商店购买 {found_item['name']}")
            return False

        # ⇓ 原有限制检查 (len >= 3) 已被移除 ⇓
        warehouse[target_slot].append(item_id)
        print(f"[穿戴] {found_item['name']} → {wear_slots[target_slot]}")
        return True

    _economy_wear = _unlimited_wear  # 替换原函数

except ImportError:
    ECONOMY_AVAILABLE = False
    print("[pet_window] economy_module 未找到，装饰穿戴功能不可用")

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("[警告] pynput 未安装，全局键盘监听不可用。请运行: pip install pynput")


class PetWindow(QWidget):
    """桌宠主窗口，置顶、无边框、透明背景。"""

    # 信号：从 pynput 线程桥接到主线程
    _key_pressed_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 窗口属性：置顶 + 无边框 + 透明
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint  # 置顶
            | Qt.FramelessWindowHint  # 无边框
            | Qt.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景

        # 窗口尺寸（原图 200 的 2.25 倍，不超过 3 倍）
        self._width = 450
        self._height = 450
        self.setFixedSize(self._width, self._height)

        # 核心组件
        self._renderer = CatRenderer(self._width, self._height)
        self._controller = GlowController(self)

        # 连接信号：glow 变化时重绘
        self._controller.glow_changed.connect(self._on_glow_changed)

        # 键盘信号桥接
        self._key_pressed_signal.connect(self._on_global_key_press)

        # 右键菜单：关闭桌宠
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 动画定时器（20 FPS）—— 用于 reward 等状态的动画渲染
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(50)

        # 鼠标拖动状态
        self._drag_pos = None

        # 全局键盘监听器（pynput）
        self._keyboard_listener = None
        self._start_keyboard_listener()

        # 启动时同步当前装饰状态
        self.refresh_decorations()

    # ----------------------------------------------------------
    # 全局键盘监听
    # ----------------------------------------------------------

    def _start_keyboard_listener(self):
        """启动全局键盘监听。"""
        if not PYNPUT_AVAILABLE:
            return

        def on_press(key):
            """pynput 回调：在独立线程中执行。"""
            try:
                self._key_pressed_signal.emit()
            except RuntimeError:
                # 窗口已销毁，忽略
                pass

        self._keyboard_listener = keyboard.Listener(on_press=on_press)
        self._keyboard_listener.daemon = True
        self._keyboard_listener.start()

    def _on_global_key_press(self):
        """主线程回调：处理全局按键。"""
        # glow_level += 2（通过 controller，不直接修改变量）
        self._controller.on_key_press()

        # 切换到下一帧 PNG
        self._renderer.advance_frame()

    # ----------------------------------------------------------
    # 鼠标拖动
    # ----------------------------------------------------------

    def mousePressEvent(self, event):
        """记录鼠标按下位置，用于拖动。"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """拖动窗口。"""
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """清除拖动状态。"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = None
            event.accept()

    # ----------------------------------------------------------
    # 右键菜单
    # ----------------------------------------------------------

    def _show_context_menu(self, pos: QPoint):
        """右键弹出菜单。"""
        menu = QMenu(self)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)
        menu.exec_(self.mapToGlobal(pos))

    # ----------------------------------------------------------
    # 对外接口（规则手册必须实现）
    # ----------------------------------------------------------

    def set_glow(self, level: int):
        """设置 glow_level，驱动亮度变化。

        Args:
            level: int，0~100
        """
        self._controller.set_glow(level)

    def trigger_reward_glow(self):
        """触发奖励发光：glow_level=100，锁定 60 秒。"""
        self._controller.trigger_reward_glow()

    def update_state(self, state: str):
        """切换状态：idle / keyboard / reward。

        Args:
            state: str
        """
        self._controller.update_state(state)

    # ----------------------------------------------------------
    # 扩展接口：装饰穿戴
    # ----------------------------------------------------------

    def wear_item(self, item_id: str) -> bool:
        """穿戴装饰物品（去除了每部位次数限制）。

        Args:
            item_id: 物品 ID（如 "bow_tie", "scarf", "casual_hat"）

        Returns:
            bool: 穿戴是否成功
        """
        if not ECONOMY_AVAILABLE:
            print("[pet_window] economy_module 不可用")
            return False

        result = _economy_wear(item_id)
        if result:
            self.refresh_decorations()
        return result

    def take_off_item(self, item_id: str) -> bool:
        """脱卸装饰物品。

        Args:
            item_id: 物品 ID

        Returns:
            bool: 脱卸是否成功
        """
        if not ECONOMY_AVAILABLE:
            return False

        result = _economy_take_off(item_id)
        if result:
            self.refresh_decorations()
        return result

    def refresh_decorations(self):
        """从 economy_module 同步当前穿戴状态并刷新渲染。"""
        if not ECONOMY_AVAILABLE:
            return

        try:
            render_order = _economy_render_order()
            self._renderer.update_decorations(render_order)
            self.update()
        except Exception as e:
            print(f"[pet_window] 刷新装饰失败: {e}")

    # ----------------------------------------------------------
    # 扩展接口：玩具展示
    # ----------------------------------------------------------

    def show_toy(self, item_id: str) -> bool:
        """在左下角展示一个玩具。

        Args:
            item_id: 玩具物品 ID（如 "mouse", "orange_yarn"）

        Returns:
            bool: 展示是否成功
        """
        if not ECONOMY_AVAILABLE:
            return False

        try:
            # 在 economy 的 shop_categories 中查找该物品
            from economy_module.economy import shop_categories as _cats
            for cat_id, cat in _cats.items():
                if item_id in cat.get("items", {}):
                    item = cat["items"][item_id]
                    img = item.get("image", "")
                    if not img:
                        return False
                    self._renderer._toys.clear()
                    self._renderer.add_toy(item_id, img)
                    self.update()
                    return True
            print(f"[pet_window] 未知物品: {item_id}")
            return False
        except Exception as e:
            print(f"[pet_window] 展示玩具失败: {e}")
            return False

    def hide_toy(self, item_id: str) -> bool:
        """隐藏左下角的玩具。

        Args:
            item_id: 玩具物品 ID

        Returns:
            bool: 隐藏是否成功
        """
        result = self._renderer.remove_toy(item_id)
        if result:
            self.update()
        return result

    # ----------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------

    def _on_glow_changed(self, level: int, state: str):
        """glow 变化回调，触发重绘。"""
        self.update()

    def _tick(self):
        """动画帧推进（仅用于 reward 等需要持续动画的状态）。"""
        self.update()

    def paintEvent(self, event):
        """重绘窗口。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._renderer.render(
            painter,
            self._controller.level,
            self._controller.state,
        )
        painter.end()

    def center_on_screen(self):
        """将窗口定位到屏幕底部居中。"""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self._width) // 2
        y = screen.height() - self._height - 50  # 距底部 50px
        self.move(x, y)

    def closeEvent(self, event):
        """窗口关闭时清理资源。"""
        # 停止全局键盘监听器
        if self._keyboard_listener is not None:
            try:
                self._keyboard_listener.stop()
            except Exception:
                pass
        super().closeEvent(event)

    # ----------------------------------------------------------
    # 只读属性
    # ----------------------------------------------------------

    @property
    def controller(self) -> GlowController:
        return self._controller

    @property
    def renderer(self) -> CatRenderer:
        return self._renderer
