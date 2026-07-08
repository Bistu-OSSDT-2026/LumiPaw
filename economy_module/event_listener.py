# 经济系统事件监听器
# 监听其他模块的事件并做出响应

import threading
import time
from typing import Callable, Any

# 事件类型定义
task_completed_event = {
    "task_name": str,
    "duration": int,
    "success": bool
}

glow_event = {
    "type": str,  # "keyboard" | "reward"
    "value": int
}

purchase_event = {
    "item_id": str,
    "price": int
}

class EconomyEventListener:
    """经济系统事件监听器"""

    def __init__(self):
        self.running = False
        self.callbacks = {
            "task_completed": [],
            "glow": [],
            "purchase": []
        }

    def register_task_callback(self, callback: Callable) -> None:
        """注册任务完成事件回调"""
        self.callbacks["task_completed"].append(callback)

    def register_glow_callback(self, callback: Callable) -> None:
        """注册发光事件回调"""
        self.callbacks["glow"].append(callback)

    def register_purchase_callback(self, callback: Callable) -> None:
        """注册购买事件回调"""
        self.callbacks["purchase"].append(callback)

    def emit_task_completed(self, task_name: str, duration: int, success: bool) -> None:
        """触发任务完成事件"""
        event = {
            "task_name": task_name,
            "duration": duration,
            "success": success
        }
        for callback in self.callbacks["task_completed"]:
            callback(event)

    def emit_glow(self, glow_type: str, value: int) -> None:
        """触发发光事件"""
        event = {
            "type": glow_type,
            "value": value
        }
        for callback in self.callbacks["glow"]:
            callback(event)

    def emit_purchase(self, item_id: str, price: int) -> None:
        """触发购买事件"""
        event = {
            "item_id": item_id,
            "price": price
        }
        for callback in self.callbacks["purchase"]:
            callback(event)

    def start(self) -> None:
        """启动监听器"""
        self.running = True
        # 这里可以添加实际的监听逻辑
        print("经济系统事件监听器已启动")

    def stop(self) -> None:
        """停止监听器"""
        self.running = False
        print("经济系统事件监听器已停止")

# 创建全局监听器实例
event_listener = EconomyEventListener()

# 便捷函数
def listen_task_events(callback: Callable) -> None:
    """监听任务完成事件"""
    event_listener.register_task_callback(callback)

def listen_glow_events(callback: Callable) -> None:
    """监听发光事件"""
    event_listener.register_glow_callback(callback)

def listen_purchase_events(callback: Callable) -> None:
    """监听购买事件"""
    event_listener.register_purchase_callback(callback)

def trigger_task_completed(task_name: str, duration: int, success: bool) -> None:
    """触发任务完成事件（供其他模块调用）"""
    event_listener.emit_task_completed(task_name, duration, success)

def trigger_glow_event(glow_type: str, value: int) -> None:
    """触发发光事件（供其他模块调用）"""
    event_listener.emit_glow(glow_type, value)

def trigger_purchase_event(item_id: str, price: int) -> None:
    """触发购买事件（供其他模块调用）"""
    event_listener.emit_purchase(item_id, price)

if __name__ == "__main__":
    # 测试事件监听器
    def on_task(event: dict) -> None:
        print(f"收到任务完成事件: {event}")

    def on_glow(event: dict) -> None:
        print(f"收到发光事件: {event}")

    # 注册事件
    listen_task_events(on_task)
    listen_glow_events(on_glow)

    # 测试触发事件
    print("测试事件触发:")
    trigger_task_completed("测试任务", 30, True)
    trigger_glow_event("keyboard", 2)

    print("\n事件监听器测试完成")