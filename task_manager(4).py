"""
task_manager.py
多任务管理系统模块

功能：
- 维护任务池，支持添加、开始、完成任务
- 同时只能有一个任务在执行
- 完成任务时校验时间规则
- 金币奖励与实际执行时长成正比（每10分钟=1金币）
- 提前结束（10分钟内）返回提示状态，由UI弹窗确认
- **距离任务结束十分钟内的提前结束不可以给奖励**（无论是否强制）

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
# 事件结构（按规范定义）
# ---------------------------------------------------------------------------
# task_completed_event 结构：
# {
#     "task_name": str,
#     "duration": int,       # 实际执行时长（分钟）
#     "success": bool,
#     "coins_reward": int,
#     "early_warning": bool,   # 是否提前结束警告
#     "remaining_minutes": int  # 提前了多少分钟（仅early_warning=True时有效）
# }


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
# 核心函数
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
    结束当前任务，计算实际执行时长并校验时间规则。

    新增逻辑：
    - 如果提前10分钟以内结束，返回 early_warning=True
    - UI 检测到后弹出提示"还有X分钟任务结束"
    - 用户选择"继续任务"或"强制结束"
    - 强制结束时传入 force=True 才能真正结束
    - **强制结束且距离任务结束十分钟内时，不给奖励（success=False, coins_reward=0）**

    Args:
        force: 是否强制结束（用于用户确认提前结束后）

    Returns:
        task_completed_event 字典，如果没有当前任务则返回 None
        如果提前结束且 force=False，返回警告事件（不真正结束任务）
    """
    global current_task

    if current_task is None:
        return None

    # 计算实际执行时长（分钟）
    end_time = time.time()
    actual_duration = int((end_time - current_task["start_time"]) / 60)

    task_name = current_task["task_name"]
    expected_duration = current_task["expected_duration"]

    # 计算还差多少分钟到预计时长
    remaining_minutes = expected_duration - actual_duration

    # 提前结束判断：如果还剩10分钟以内，且用户没点强制结束
    # 返回警告，不真正结束任务
    if not force and 0 < remaining_minutes <= 10:
        return {
            "task_name": task_name,
            "duration": actual_duration,
            "success": False,
            "coins_reward": 0,
            "early_warning": True,
            "remaining_minutes": remaining_minutes
        }

    # --- 修改开始：强制提前结束且剩余时间<=10分钟，不给奖励 ---
    if force and 0 < remaining_minutes <= 10:
        # 强制提前结束，不允许获得奖励
        event = {
            "task_name": task_name,
            "duration": actual_duration,
            "success": False,
            "coins_reward": 0,
            "early_warning": False,          # 用户已确认，不再弹窗
            "remaining_minutes": remaining_minutes
        }
        current_task = None
        return event
    # --- 修改结束 ---

    # 正常结束或强制结束（且剩余时间>10分钟 或 已经超时/已完成）
    # 校验时间规则（-60分钟规则）
    success = actual_duration >= (expected_duration - 60)
    coins_reward = _calculate_coins(actual_duration) if success else 0

    task_completed_event = {
        "task_name": task_name,
        "duration": actual_duration,
        "success": success,
        "coins_reward": coins_reward,
        "early_warning": False,
        "remaining_minutes": 0
    }

    # 重置 current_task
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
    print("多任务管理系统测试 - 提前结束弹窗提示（修改后）")
    print("=" * 60)

    # 场景1：正常完成任务
    print("\n[场景1] 正常完成任务（90分钟任务，执行80分钟）")
    task1 = add_task("写代码", 90)
    start_task(task1)
    # 模拟执行80分钟（实际测试用1秒代替）
    time.sleep(1)
    event = finish_task()
    print(f"  结果: {event}")

    # 场景2：提前8分钟结束 → 弹出警告
    print("\n[场景2] 提前8分钟结束（90分钟任务，执行82分钟）")
    task2 = add_task("背单词", 90)
    start_task(task2)
    time.sleep(1)
    event = finish_task()
    print(f"  结果: {event}")
    print(f"  >>> UI应弹出提示: 还有 {event['remaining_minutes']} 分钟任务结束")
    print(f"  >>> 用户选择'继续'或'强制结束'")

    # 场景3：用户选择强制结束（此时剩余时间仍≤10分钟 → 不给奖励）
    print("\n[场景3] 用户确认强制结束（剩余时间≤10分钟，不给奖励）")
    event = finish_task(force=True)
    print(f"  结果: {event}")   # 应显示 success=False, coins_reward=0

    # 场景4：提前20分钟结束（剩余>10分钟，但提前超过60分钟则失败）
    print("\n[场景4] 提前20分钟结束（90分钟任务，执行70分钟）")
    task3 = add_task("健身", 90)
    start_task(task3)
    time.sleep(1)
    event = finish_task()
    print(f"  结果: {event}")

    # 场景5：强制提前20分钟（剩余>10分钟，但未超过60分钟限制，则可能成功）
    print("\n[场景5] 强制提前20分钟（90分钟任务，执行70分钟）但原规则允许提前60分钟，所以成功给奖励")
    task4 = add_task("学习", 90)
    start_task(task4)
    time.sleep(1)
    event = finish_task(force=True)   # 剩余>10分钟，按原成功条件判断
    print(f"  结果: {event}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)