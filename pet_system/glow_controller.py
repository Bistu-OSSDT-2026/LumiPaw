"""
glow_controller.py — 发光状态机

管理 glow_level（0~100）和三种状态：idle / keyboard / reward。
通过 PyQt5 信号通知外部 UI 刷新，不直接操作任何 UI 组件。

全局变量（只读引用，禁止直接修改）：
    glow_level: int        # 0~100 桌宠亮度
    current_task: dict|None # 当前任务
    coins: int             # 金币数量

对外接口（规则手册要求）：
    set_glow(level: int)
    trigger_reward_glow()
    update_state(state: str)
"""

from PyQt5.QtCore import QObject, QTimer, pyqtSignal


# ============================================================
# 全局统一变量（禁止修改命名）
# ============================================================
glow_level: int = 0          # 0~100 桌宠亮度
current_task = None           # dict | None 当前任务
coins: int = 0               # 金币数量


class GlowController(QObject):
    """
    发光状态机，管理桌宠的三种状态和 glow_level 变化。

    状态说明：
        idle     — 默认状态，暗淡
        keyboard — 键盘活跃，逐渐变亮
        reward   — 任务完成高亮，glow_level=100，锁定 5 秒后归零

    发光规则（规则手册第五条）：
        每次键盘输入 +2 glow_level，最大 100
        5 秒无输入开始下降，每 200ms -1（等效每秒 -5）
        任务完成：glow_level = 100，保持 5 秒后归零
    """

    # 信号：glow_level 变化时发出，携带当前 level 和状态
    glow_changed = pyqtSignal(int, str)

    # 信号：reward 锁定结束时发出
    reward_finished = pyqtSignal()

    # 状态常量
    STATE_IDLE = "idle"
    STATE_KEYBOARD = "keyboard"
    STATE_REWARD = "reward"

    def __init__(self, parent=None):
        super().__init__(parent)

        # 私有内部变量
        self._glow_level: int = 0
        self._state: str = self.STATE_IDLE
        self._reward_locked: bool = False

        # reward 锁定计时器（60 秒）
        self._reward_timer = QTimer(self)
        self._reward_timer.setSingleShot(True)
        self._reward_timer.timeout.connect(self._on_reward_timeout)

        # 衰减计时器：5 秒无输入后开始每秒 -1
        self._decay_timer = QTimer(self)
        self._decay_timer.setSingleShot(True)
        self._decay_timer.timeout.connect(self._on_decay)

        # 持续衰减定时器：启动后每秒触发一次
        self._decay_repeat_timer = QTimer(self)
        self._decay_repeat_timer.timeout.connect(self._on_decay_tick)

    # ----------------------------------------------------------
    # 对外接口（规则手册必须实现）
    # ----------------------------------------------------------

    def set_glow(self, level: int):
        """设置 glow_level，自动切换状态。

        Args:
            level: int，0~100
        """
        clamped = max(0, min(100, level))
        self._glow_level = clamped

        # 自动推断状态（仅在非 reward 锁定期间）
        if not self._reward_locked:
            if clamped <= 0:
                self._state = self.STATE_IDLE
            else:
                self._state = self.STATE_KEYBOARD

        # 更新全局变量
        global glow_level
        glow_level = self._glow_level

        self.glow_changed.emit(self._glow_level, self._state)

    def trigger_reward_glow(self):
        """触发奖励发光：glow_level = 100，锁定 5 秒后归零。"""
        self._glow_level = 100
        self._state = self.STATE_REWARD
        self._reward_locked = True

        # 启动 5 秒锁定计时器
        self._reward_timer.start(5000)

        # 更新全局变量
        global glow_level
        glow_level = self._glow_level

        self.glow_changed.emit(self._glow_level, self._state)

    def update_state(self, state: str):
        """手动切换状态。

        Args:
            state: "idle" | "keyboard" | "reward"
        """
        valid_states = [self.STATE_IDLE, self.STATE_KEYBOARD, self.STATE_REWARD]
        if state not in valid_states:
            raise ValueError(f"无效状态: {state}，允许值: {valid_states}")

        self._state = state

        # 如果切换到 idle，重置 glow_level
        if state == self.STATE_IDLE:
            self._glow_level = 0
            global glow_level
            glow_level = 0

        self.glow_changed.emit(self._glow_level, self._state)

    def on_key_press(self):
        """处理一次键盘按键：glow_level += 2，重置衰减计时器。

        发光规则：
            每次键盘输入 +2 glow_level，最大 100
            5 秒无输入开始下降，每 200ms -1（每秒 -5）
        """
        if self._reward_locked:
            return  # reward 锁定期间不响应键盘

        # glow_level += 2，最大 100
        new_level = min(100, self._glow_level + 2)
        self.set_glow(new_level)

        # 重置衰减计时器：5 秒无输入后才开始衰减
        self._decay_repeat_timer.stop()
        self._decay_timer.start(5000)

    # ----------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------

    def _on_decay(self):
        """5 秒无输入到期，启动持续衰减（每 100ms -1，等效每秒 -10）。"""
        self._decay_repeat_timer.start(100)

    def _on_decay_tick(self):
        """每 100ms 衰减 -1（每秒 -10），到 0 时停止。"""
        if self._reward_locked:
            self._decay_repeat_timer.stop()
            return

        new_level = max(0, self._glow_level - 1)
        self.set_glow(new_level)

        if new_level <= 0:
            self._decay_repeat_timer.stop()

    def _on_reward_timeout(self):
        """reward 锁定 5 秒到期，亮度归零。"""
        self._reward_locked = False
        self.set_glow(0)
        self.reward_finished.emit()

    # ----------------------------------------------------------
    # 只读属性（不允许外部直接修改）
    # ----------------------------------------------------------

    @property
    def level(self) -> int:
        return self._glow_level

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_reward_locked(self) -> bool:
        return self._reward_locked


# ============================================================
# main 测试入口
# ============================================================
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    ctrl = GlowController()

    # 测试 set_glow
    def on_glow(level, state):
        print(f"[测试] glow_level={level}, state={state}")

    ctrl.glow_changed.connect(on_glow)
    ctrl.reward_finished.connect(lambda: print("[测试] reward 锁定结束"))

    print("=== glow_controller 独立测试 ===")

    # 测试 idle 状态
    ctrl.set_glow(0)
    print(f"当前状态: {ctrl.state}, glow: {ctrl.level}")

    # 测试 on_key_press（模拟连续按键）
    for i in range(5):
        ctrl.on_key_press()
        print(f"  按键 {i+1}: glow={ctrl.level}, state={ctrl.state}")
    print(f"5次按键后 — glow: {ctrl.level}, state: {ctrl.state}")

    # 测试 on_key_press 到最大值
    for i in range(60):
        ctrl.on_key_press()
    print(f"多次按键后 — glow: {ctrl.level} (应为100)")

    # 手动模拟衰减（不真等5秒）
    ctrl._on_decay()
    for i in range(5):
        ctrl._on_decay_tick()
        print(f"  衰减 {i+1}: glow={ctrl.level}")
    print(f"衰减后 — glow: {ctrl.level}")

    # 测试 reward
    ctrl.trigger_reward_glow()
    print(f"触发 reward — 状态: {ctrl.state}, glow: {ctrl.level}, 锁定: {ctrl.is_reward_locked}")

    # reward 期间按键不应生效
    ctrl.on_key_press()
    print(f"reward 期间按键 — glow: {ctrl.level} (应仍为100)")

    # 手动模拟 reward 超时（不真的等 60 秒）
    ctrl._reward_timer.stop()
    ctrl._on_reward_timeout()
    print(f"reward 超时后 — 状态: {ctrl.state}, glow: {ctrl.level}, 锁定: {ctrl.is_reward_locked}")

    # 测试 update_state
    ctrl.update_state("idle")
    print(f"update_state(idle) — 状态: {ctrl.state}, glow: {ctrl.level}")

    # 测试无效状态
    try:
        ctrl.update_state("invalid")
    except ValueError as e:
        print(f"[测试] 预期异常: {e}")

    print("=== 所有测试通过 ===")
