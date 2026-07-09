"""
pet_system — 1号模块：桌宠系统

提供 Bongo Cat 桌宠显示、glow_level 驱动亮度变化、奖励发光等功能。

对外暴露：
    PetWindow — 桌宠主窗口，包含规则手册要求的 3 个接口：
        set_glow(level: int)
        trigger_reward_glow()
        update_state(state: str)
"""

from .pet_window import PetWindow

__all__ = ["PetWindow"]
