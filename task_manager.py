"""
task_manager.py
多任务管理系统模块

功能：
- 维护任务池，支持添加、开始、完成任务
- 同时只能有一个任务在执行
- 严格按预计时长判定完成
- 提前10分钟以内结束：允许完成，按实际时长给奖励
- 提前超过10分钟：提示"没有奖励"，强制结束也不给
- 金币奖励与实际执行时长成正比（每10分钟=1金币）

约束：
- 不依赖其他模块的内部实现
- 只通过函数参数和返回值进行交互
- 禁止直接修改 glow_level 或 coins（属于其他模块）
- 禁止在模块内写UI代码或混合业务逻辑
"""

import time
import math
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# 内部任务池数据结构
# ---------------------------------------------------------------------------
_task_pool: Dict[str, dict] = {}
_task_counter: int = 0

# ---------------------------------------------------------------------------
# 全局变量（按规范命名，禁止修改）
# ---------------------------------------------------------------------------
current_task: Optional[dict] = None


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _generate_task_id() -> str:
    """生成唯一的任务ID。"""
    global _task_counter
    _task_counter += 1
    return f"task_{_task_counter}"


def _calculate_coins(actual_duration: int) -> int:
    """
    根据实际执行时长计算金币奖励，成正比关系。
    每10分钟 = 1金币，不足10分钟按10分钟计（至少1金币）。
    """
    if actual_duration <= 0:
        return 0
    return max(1, math.ceil(actual_duration / 10))


# ---------------------------------------------------------------------------
# 核心函数（接口保持不变）
# ---------------------------------------------------------------------------

def add_task(name: str, duration: int) -> str:
    """
    添加任务到任务池。

    Args:
        name: 任务名称（用户自由输入）
        duration: 预计时长（分钟，用户自由输入）

    Returns:
        新任务的 task_id（字符串）
    """
    task_id = _generate_task_id()
    _task_pool[task_id] = {
        "task_id": task_id,
        "task_name": name,
        "expected_duration": duration,
        "status": "pending"
    }
    return task_id


def start_task(task_id: str) -> bool:
    """
    将指定任务设为 current_task，开始执行。

    Args:
        task_id: 要开始的任务ID

    Returns:
        True 表示成功开始，False 表示已有任务在执行或任务不存在
    """
    global current_task

    if current_task is not None:
        return False

    if task_id not in _task_pool:
        return False

    task = _task_pool[task_id]

    current_task = {
        "task_name": task["task_name"],
        "start_time": time.time(),
        "expected_duration": task["expected_duration"]
    }

    task["status"] = "active"
    return True


def finish_task(force: bool = False) -> Optional[dict]:
    """
    结束当前任务。

    规则：
    - actual_duration >= expected_duration：正常完成，success=True，计算金币
    - 0 < remaining_minutes <= 10（提前10分钟内）：
        用户确认后可完成，success=True，按实际时长计算金币
    - remaining_minutes > 10（提前超过10分钟）：
        提示"提前结束没有奖励"，强制结束也不给奖励

    Args:
        force: 是否强制结束（用户确认后传入 True）

    Returns:
        task_completed_event 或 warning 事件，没有当前任务则返回 None
    """
    global current_task

    if current_task is None:
        return None

    # 计算实际执行时长（分钟）
    end_time = time.time()
    actual_duration = int((end_time - current_task["start_time"]) / 60)

    task_name = current_task["task_name"]
    expected_duration = current_task["expected_duration"]
    remaining_minutes = expected_duration - actual_duration

    # 情况1：已达到或超过预计时长，正常完成
    if actual_duration >= expected_duration:
        success = True
        coins_reward = _calculate_coins(actual_duration)

        task_completed_event = {
            "task_name": task_name,
            "duration": actual_duration,
            "success": success,
            "coins_reward": coins_reward,
            "early_warning": False,
            "remaining_minutes": 0,
            "warning_type": None,
            "message": None
        }

        current_task = None
        return task_completed_event

    # 情况2：提前10分钟以内（0 < remaining <= 10）
    # 用户确认后可以完成，给奖励
    if 0 < remaining_minutes <= 10:
        if not force:
            # 先弹窗让用户确认
            return {
                "task_name": task_name,
                "duration": actual_duration,
                "success": False,
                "coins_reward": 0,
                "early_warning": True,
                "remaining_minutes": remaining_minutes,
                "warning_type": "confirm_early",
                "message": f"还有 {remaining_minutes} 分钟才会结束，确定要提前结束？"
            }
        else:
            # 用户确认，允许完成，按实际时长给奖励
            success = True
            coins_reward = _calculate_coins(actual_duration)

            task_completed_event = {
                "task_name": task_name,
                "duration": actual_duration,
                "success": success,
                "coins_reward": coins_reward,
                "early_warning": False,
                "remaining_minutes": 0,
                "warning_type": None,
                "message": None
            }

            current_task = None
            return task_completed_event

    # 情况3：提前超过10分钟（remaining_minutes > 10）
    if not force:
        # 弹窗提示没有奖励
        return {
            "task_name": task_name,
            "duration": actual_duration,
            "success": False,
            "coins_reward": 0,
            "early_warning": True,
            "remaining_minutes": remaining_minutes,
            "warning_type": "too_early",
            "message": f"还有 {remaining_minutes} 分钟才会结束，提前结束没有奖励哦"
        }
    else:
        # 用户强制结束，但不给奖励
        task_completed_event = {
            "task_name": task_name,
            "duration": actual_duration,
            "success": False,
            "coins_reward": 0,
            "early_warning": False,
            "remaining_minutes": remaining_minutes,
            "warning_type": None,
            "message": None
        }

        current_task = None
        return task_completed_event


def get_current_task() -> Optional[dict]:
    """返回当前正在执行的任务信息。"""
    return current_task


# ---------------------------------------------------------------------------
# 测试入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("多任务管理系统测试 - 提前10分钟内有奖励")
    print("=" * 60)

    # 场景1：正常完成
    print("\n[场景1] 正常完成（90分钟任务，执行90分钟）")
    task1 = add_task("写代码", 90)
    start_task(task1)
    current_task["start_time"] = time.time() - 90 * 60
    event = finish_task()
    print(f"  success={event['success']}, coins={event['coins_reward']}")

    # 场景2：提前5分钟结束 → 弹窗确认 → 确认后给奖励
    print("\n[场景2] 提前5分钟结束（90分钟任务，执行85分钟）")
    task2 = add_task("背单词", 90)
    start_task(task2)
    current_task["start_time"] = time.time() - 85 * 60
    event = finish_task()
    print(f"  弹窗: {event['message']}")
    print(f"  current_task还在: {get_current_task() is not None}")

    print("  用户确认...")
    event = finish_task(force=True)
    print(f"  success={event['success']}, coins={event['coins_reward']}")

    # 场景3：提前15分钟结束 → 弹窗"没有奖励" → 强制结束也不给
    print("\n[场景3] 提前15分钟结束（90分钟任务，执行75分钟）")
    task3 = add_task("健身", 90)
    start_task(task3)
    current_task["start_time"] = time.time() - 75 * 60
    event = finish_task()
    print(f"  弹窗: {event['message']}")

    print("  用户强制结束...")
    event = finish_task(force=True)
    print(f"  success={event['success']}, coins={event['coins_reward']}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
