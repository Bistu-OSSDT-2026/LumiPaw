# 经济系统模块主程序
# 测试所有功能并演示与其他模块的对接

import time
from economy import (
    add_coins, spend_coins, get_coins, buy_item,
    get_shop_items, get_purchased_items, on_task_completed
)
from shop_ui import shop_interaction
from event_listener import (
    trigger_task_completed, trigger_purchase_event,
    listen_task_events, listen_purchase_events
)

def demo_integration():
    """演示与其他模块的对接"""
    print("\n=== 与其他模块对接演示 ===")

    # 注册任务完成事件监听
    def on_task_reward(event):
        # 当任务完成时，经济系统给予奖励
        if event["success"]:
            reward = 10
            add_coins(reward)
            print(f"[庆祝] 任务完成奖励: +{reward} 金币")

    listen_task_events(on_task_reward)

    # 模拟任务完成
    print("\n模拟用户完成任务...")
    time.sleep(1)
    trigger_task_completed("完成作业", 60, True)
    print(f"当前金币: {get_coins()}")

    # 模拟购买商品
    print("\n模拟用户购买商品...")
    if buy_item("food"):
        trigger_purchase_event("food", 10)
        print("🛒 购买食物成功！")

def run_full_test():
    """运行完整测试"""
    print("=== 经济系统完整测试 ===")

    # 测试金币系统
    print("\n1. 测试金币系统:")
    print(f"初始金币: {get_coins()}")
    add_coins(100)
    print(f"获得100金币: {get_coins()}")
    success = spend_coins(50)
    print(f"花费50金币: {'成功' if success else '失败'}")
    print(f"剩余金币: {get_coins()}")

    # 测试商店系统
    print("\n2. 测试商店系统:")
    print("可用商品:")
    for item_id, item in get_shop_items().items():
        owned = "[已拥有]" if item_id in get_purchased_items() else ""
        print(f"  - {item['name']}: {item['price']}金币 {owned}")

    # 测试购买
    print("\n3. 测试购买功能:")
    print(f"当前金币: {get_coins()}")
    print("尝试购买食物...")
    if buy_item("food"):
        print("[成功] 购买成功！")
        print(f"剩余金币: {get_coins()}")
        print("背包:", get_purchased_items())
    else:
        print("[失败] 购买失败（金币不足）")

    # 测试任务奖励
    print("\n4. 测试任务奖励:")
    on_task_completed("测试任务", 30, True)
    print(f"任务奖励后金币: {get_coins()}")

def main():
    """主函数"""
    print("=== 经济系统模块 ===")
    print("=" * 30)

    while True:
        print("\n请选择:")
        print("1. 运行完整测试")
        print("2. 进入商店")
        print("3. 进入仓库")
        print("4. 查看对接演示")
        print("5. 退出")

        choice = input("\n请输入选项 (1-5): ").strip()

        if choice == "1":
            run_full_test()
        elif choice == "2":
            shop_interaction()
        elif choice == "3":
            from warehouse_ui import warehouse_interaction
            warehouse_interaction()
        elif choice == "4":
            demo_integration()
        elif choice == "5":
            break
        else:
            print("无效选项，请重试")

        input("\n按回车键继续...")

if __name__ == "__main__":
    main()