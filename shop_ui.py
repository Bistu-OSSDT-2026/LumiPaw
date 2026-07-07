# 商店UI模块
# 展示商店界面和用户物品

from economy import (
    get_coins, get_shop_items, get_purchased_items, get_inventory,
    buy_item, shop_categories, get_category_items
)
from typing import Dict, List

def display_shop() -> None:
    """显示商店界面"""
    print("\n" + "="*60)
    print("[购物车] 商 店")
    print("="*60)
    print(f"[金币] 你的金币: {get_coins()}")
    print("\n商品分类:")

    # 显示所有分类
    for category_id, category in shop_categories.items():
        print(f"\n[分类] {category['name']}")
        print("-" * 40)

        # 显示该分类下的商品
        for item_id, item in category["items"].items():
            # 检查是否已拥有及数量
            inventory = get_inventory()
            if item_id in inventory:
                quantity = inventory[item_id]
                owned = f"[已有 x{quantity}]"
            else:
                owned = "      "

            print(f"{owned} {item['name']} - {item['price']}金币")

def display_inventory() -> None:
    """显示用户背包"""
    inventory = get_inventory()
    if not inventory:
        print("\n[背包] 你的背包是空的")
    else:
        print("\n[背包] 你的背包:")
        print("=" * 40)
        for item_id, item_info in inventory.items():
            print(f"- {item_info['name']} x{item_info['quantity']}")
            print(f"  {item_info['description']}")
            print(f"  分类: {item_info['category']}")
            print()

def display_category(category_id: str) -> None:
    """显示特定分类的商品"""
    category_items = get_category_items(category_id)

    if not category_items:
        print("无效的分类ID")
        return

    category_info = get_shop_items()[category_id]
    print(f"\n[分类] {category_info['name']} 商品")
    print("=" * 50)
    print(f"[金币] 你的金币: {get_coins()}")
    print("\n商品列表:")

    for item_id, item in category_items.items():
        # 检查库存
        inventory = get_inventory()
        quantity = inventory.get(item_id, 0)

        if quantity > 0:
            print(f"[已有 x{quantity}] {item['name']} - {item['price']}金币")
            print(f"         {item['description']}")
        else:
            print(f"        {item['name']} - {item['price']}金币")
            print(f"         {item['description']}")

def shop_interaction() -> None:
    """增强的商店交互逻辑"""
    while True:
        print("\n" + "="*60)
        print("[购物车] 商 庖")
        print("="*60)
        print(f"[金币] 你的金币: {get_coins()}")
        print("\n选择操作:")
        print("1. 查看所有商品")
        print("2. 按分类浏览")
        print("3. 查看背包")
        print("4. 退出商店")

        main_choice = input("\n请选择 (1-4): ").strip()

        if main_choice == "4" or main_choice == "退出":
            break
        elif main_choice == "1":
            # 显示所有商品
            display_shop()
            buy_items()
        elif main_choice == "2":
            # 按分类浏览
            browse_categories()
        elif main_choice == "3":
            # 查看背包
            display_inventory()
        else:
            print("[失败] 无效的指令")

def browse_categories() -> None:
    """浏览商品分类"""
    categories = get_categories()

    while True:
        print("\n" + "="*50)
        print("商品分类列表")
        print("="*50)

        # 显示所有分类
        for i, category_id in enumerate(categories, 1):
            category = shop_categories[category_id]
            print(f"{i}. {category['name']}")

        print(f"{len(categories) + 1}. 返回主菜单")

        choice = input("\n请选择分类 (返回输入0): ").strip()

        if choice == "0":
            break
        elif choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(categories):
                selected_category = categories[choice_num - 1]
                display_category(selected_category)
                buy_items()
            else:
                print("[失败] 无效的选择")
        else:
            print("[失败] 请输入数字")

def buy_items():
    """购买商品操作"""
    print("\n" + "="*40)
    print("购买商品")
    print("="*40)

    # 让用户输入要购买的商品
    print("输入格式: 商品名称 数量 (例如: 普通猫粮 3)")
    print("直接按回车返回商店")

    item_input = input("\n请输入要购买的商品: ").strip()

    if not item_input:
        return

    try:
        # 解析输入
        parts = item_input.split()
        if len(parts) < 1:
            print("[失败] 输入格式错误")
            return

        item_name = parts[0]
        quantity = int(parts[1]) if len(parts) > 1 else 1

        if quantity < 1:
            print("[失败] 数量必须大于0")
            return

        # 查找商品ID
        item_id = None
        for category_id, category in shop_categories.items():
            for item_id_key, item in category["items"].items():
                if item['name'] == item_name:
                    item_id = item_id_key
                    break
            if item_id:
                break

        if not item_id:
            print("[失败] 未找到该商品")
            return

        # 尝试购买
        if buy_item(item_id, quantity):
            item_info = shop_categories[category_id]["items"][item_id]
            total_price = item_info["price"] * quantity
            print(f"\n[成功] 成功购买 {quantity}个 {item_name}!")
            print(f"花费: {total_price} 金币")
        else:
            item_info = shop_categories[category_id]["items"][item_id]
            print(f"\n[失败] 金币不足，无法购买 {quantity}个 {item_name}")
            print(f"需要: {item_info['price'] * quantity} 金币")
            print(f"你有: {get_coins()} 金币")

    except ValueError:
        print("[失败] 数量必须是数字")
    except Exception as e:
        print(f"[失败] {e}")

def shop_interaction() -> None:
    """商店交互逻辑"""
    while True:
        print("\n" + "="*60)
        print("[购物车] 商 店")
        print("="*60)
        print(f"[金币] 你的金币: {get_coins()}")
        print("\n选择操作:")
        print("1. 查看所有商品")
        print("2. 按分类浏览")
        print("3. 查看背包")
        print("4. 进入仓库")
        print("5. 退出商店")

        main_choice = input("\n请选择 (1-5): ").strip()

        if main_choice == "5" or main_choice == "退出":
            break
        elif main_choice == "1":
            # 显示所有商品
            display_shop()
            buy_items()
        elif main_choice == "2":
            # 按分类浏览
            browse_categories()
        elif main_choice == "3":
            # 查看背包
            display_inventory()
        elif main_choice == "4":
            # 进入仓库
            from warehouse_ui import warehouse_interaction
            warehouse_interaction()
        else:
            print("[失败] 无效的指令")

        input("\n按回车键继续...")

if __name__ == "__main__":
    shop_interaction()