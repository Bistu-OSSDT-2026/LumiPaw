# 经济系统模块验证脚本
from economy import add_coins, get_coins, buy_item, get_purchased_items
from event_listener import trigger_task_completed, listen_task_events

print("=== 经济系统模块验证 ===")

# 测试金币系统
print("1. 金币系统测试")
print(f"初始金币: {get_coins()}")
add_coins(100)
print(f"增加100金币后: {get_coins()}")

# 测试购买
print("\n2. 购买功能测试")
buy_item("food")
print(f"购买食物后金币: {get_coins()}")
print(f"背包内容: {get_purchased_items()}")

# 测试任务奖励
print("\n3. 任务奖励测试")
trigger_task_completed("测试任务", 30, True)
print(f"任务完成后金币: {get_coins()}")

print("\n=== 验证完成 ===")
