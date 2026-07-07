"""
task_manager.py
多任务管理系统模块

功能：
- 维护任务池，支持添加、开始、完成任务
- 同时只能有一个任务在执行
- 完成任务时校验时间规则并计算金币奖励

约束：
- 不依赖其他模块的内部实现
- 只通过函数参数和返回值进行交互
- 禁止直接修改 glow_level 或 coins（属于其他模块）
- 禁止在模块内写UI代码或混合业务逻辑
"""

import time
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 内部任务池数据结构
# ---------------------------------------------------------------------------
_task_pool: Dict[str, dict] = {}  # task_id -> 任务字典
_task_counter: int = 0  # 用于生成唯一 task_id

# ---------------------------------------------------------------------------
# 全局变量（按规范命名，禁止修改）
# ---------------------------------------------------------------------------
current_task: Optional[dict] = None  # 当前正在执行的任务

# ---------------------------------------------------------------------------
# 事件结构（按规范定义）
# ---------------------------------------------------------------------------
# task_completed_event 结构：
# {
#     "task_name": str,
#     "duration": int,      # 实际执行时长（分钟）
#     "success": bool,
#     "coins_reward": int   # 完成任务获得的金币数量
# }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _generate_task_id() -> str:
    """生成唯一的任务ID。"""
    global _task_counter
    _task_counter += 1
    return f"task_{_task_counter}"


def _calculate_coins_reward(expected_duration: int) -> int:
    """
    根据预计时长计算金币奖励。

    规则：
    - < 30分钟    → 5 金币
    - 30~59分钟   → 10 金币
    - 60~119分钟  → 20 金币
    - 120~179分钟 → 35 金币
    - >= 180分钟  → 50 金币

    Args:
        expected_duration: 预计时长（分钟）

    Returns:
        金币奖励数值
    """
    if expected_duration < 30:
        return 5
    elif expected_duration < 60:
        return 10
    elif expected_duration < 120:
        return 20
    elif expected_duration < 180:
        return 35
    else:
        return 50


def _check_time_rule(actual_duration: int, expected_duration: int) -> bool:
    """
    校验时间规则（-60分钟规则）。

    如果 实际时长 < (预计时长 - 60分钟)，则视为未完成。

    Args:
        actual_duration: 实际执行时长（分钟）
        expected_duration: 预计时长（分钟）

    Returns:
        True 表示完成，False 表示未完成
    """
    return actual_duration >= (expected_duration - 60)


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

    如果已有任务在执行，返回 False。
    设置 start_time 为当前时间（time.time() 时间戳）。

    Args:
        task_id: 要开始的任务ID

    Returns:
        True 表示成功开始，False 表示已有任务在执行或任务不存在
    """
    global current_task

    # 检查是否已有任务在执行
    if current_task is not None:
        return False

    # 检查任务是否存在
    if task_id not in _task_pool:
        return False

    task = _task_pool[task_id]

    # 设置当前任务
    current_task = {
        "task_name": task["task_name"],
        "start_time": time.time(),
        "expected_duration": task["expected_duration"]
    }

    # 更新任务状态
    task["status"] = "active"

    return True


def finish_task() -> Optional[dict]:
    """
    结束当前任务，计算实际执行时长并校验时间规则。

    如果 success=True，根据预计时长计算金币奖励。
    返回 task_completed_event 事件字典，并重置 current_task 为 None。

    Returns:
        task_completed_event 字典，如果没有当前任务则返回 None
    """
    global current_task

    if current_task is None:
        return None

    # 计算实际执行时长（分钟）
    end_time = time.time()
    actual_duration_seconds = end_time - current_task["start_time"]
    actual_duration = int(actual_duration_seconds / 60)

    task_name = current_task["task_name"]
    expected_duration = current_task["expected_duration"]

    # 校验时间规则
    success = _check_time_rule(actual_duration, expected_duration)

    # 计算金币奖励
    coins_reward = _calculate_coins_reward(expected_duration) if success else 0

    # 构建事件字典
    task_completed_event = {
        "task_name": task_name,
        "duration": actual_duration,
        "success": success,
        "coins_reward": coins_reward
    }

    # 重置 current_task
    current_task = None

    return task_completed_event


def get_current_task() -> Optional[dict]:
    """
    返回当前正在执行的任务信息。

    Returns:
        当前任务字典（包含 task_name, start_time, expected_duration），
        如果没有正在执行的任务则返回 None
    """
    return current_task


# ---------------------------------------------------------------------------
# 测试入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("多任务管理系统测试")
    print("=" * 60)

    # 1. 添加3个不同名称和时长的任务
    print("\n[步骤1] 添加任务到任务池...")
    task1_id = add_task("写代码", 90)
    task2_id = add_task("背单词", 30)
    task3_id = add_task("健身", 120)
    print(f"  任务1: {task1_id} - 写代码 (90分钟)")
    print(f"  任务2: {task2_id} - 背单词 (30分钟)")
    print(f"  任务3: {task3_id} - 健身 (120分钟)")

    # 2. 开始第1个任务
    print("\n[步骤2] 开始第1个任务（写代码）...")
    result = start_task(task1_id)
    print(f"  开始结果: {result}")
    print(f"  当前任务: {get_current_task()}")

    # 3. 尝试开始第2个任务（应失败）
    print("\n[步骤3] 尝试开始第2个任务（背单词）...")
    result = start_task(task2_id)
    print(f"  开始结果: {result} (应返回 False，因为已有任务在执行)")

    # 4. 模拟等待几秒后完成第1个任务
    print("\n[步骤4] 模拟等待3秒后完成第1个任务...")
    time.sleep(3)
    event = finish_task()
    print(f"  task_completed_event: {event}")
    print(f"  当前任务: {get_current_task()}")

    # 5. 再开始第2个任务并完成
    print("\n[步骤5] 开始并完成第2个任务（背单词）...")
    start_task(task2_id)
    time.sleep(2)
    event = finish_task()
    print(f"  task_completed_event: {event}")

    # 6. 演示一个时长不足的任务被判定为未完成
    print("\n[步骤6] 演示时长不足判定为未完成...")
    task4_id = add_task("长时间阅读", 120)  # 预计120分钟
    start_task(task4_id)
    time.sleep(1)  # 只执行1秒，远不足120-60=60分钟
    event = finish_task()
    print(f"  task_completed_event: {event}")
    print(f"  success=False, coins_reward=0 (时长不足)")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
