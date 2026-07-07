# 仓库UI模块
# 管理物品穿戴和展示

from economy import (
    get_inventory, get_warehouse, get_wear_slots, wear_item,
    get_equipped_items, get_render_order, shop_categories
)
from typing import Dict, List

def display_warehouse() -> None:
    """显示仓库界面"""
    print("\n" + "="*60)
    print("[仓库] 物品仓库")
    print("="*60)

    # 显示当前装饰指令状态
    print("\n当前装饰指令记录:")
    equipped = get_equipped_items()
    if not equipped:
        print("   未下达任何装饰指令")
    else:
        for slot_id, items in equipped.items():
            slot_name = wear_slots[slot_id]
            print(f"   {slot_name} ({len(items)}/3):")
            for item in items:
                print(f"      {item['item_name']} [指令记录]")
                print(f"         {item['description']}")

    # 显示库存物品
    print("\n库存物品:")
    inventory = get_inventory()
    if not inventory:
        print("   没有可穿戴的物品")
    else:
        # 按部位分类显示
        for category_id, category in shop_categories.items():
            if category_id in ["body", "headwear", "eyewear", "neckwear", "face"]:
                category_items = category["items"]
                has_items = False

                for item_id, quantity in inventory.items():
                    if item_id in category_items:
                        has_items = True
                        item = category_items[item_id]
                        slot_name = ""
                        if category_id == "body":
                            slot_name = "身体"
                        elif category_id == "headwear":
                            slot_name = "头部"
                        elif category_id == "eyewear":
                            slot_name = "面部"
                        elif category_id == "neckwear":
                            slot_name = "颈部"
                        elif category_id == "face":
                            slot_name = "面部"

                        current_equipped = get_warehouse()
                        equipped_name = ""
                        for slot, equipped_id in current_equipped.items():
                            if equipped_id == item_id:
                                equipped_name = f" [已穿戴]"
                                break

                        print(f"   {slot_name}: {item['name']} x{quantity}{equipped_name}")
                        print(f"      {item['description']}")

                if has_items:
                    print()

def display_wear_slots() -> None:
    """显示穿戴部位"""
    print("\n" + "="*50)
    print("[穿戴] 部位说明")
    print("="*50)

    wear_slots = get_wear_slots()
    print("可穿戴部位:")
    for slot_id, slot_name in wear_slots.items():
        print(f"   {slot_name}: 只能穿戴一个物品")

    print("\n图层叠加顺序:")
    print("   1. 身体（最底层）")
    print("   2. 颈部")
    print("   3. 面部")
    print("   4. 头部（最顶层）")

def warehouse_interaction() -> None:
    """仓库交互逻辑"""
    while True:
        print("\n" + "="*60)
        print("[仓库] 装饰指令中心")
        print("="*60)
        print("\n选择操作:")
        print("1. 查看仓库")
        print("2. 下达穿戴装饰指令")
        print("3. 查看装饰顺序")
        print("4. 返回商店")

        choice = input("\n请选择 (1-4): ").strip()

        if choice == "1":
            display_warehouse()
        elif choice == "2":
            wear_items()
        elif choice == "3":
            display_wear_slots()
            display_render_order()
        elif choice == "4":
            break
        else:
            print("[无效] 请输入1-4之间的数字")

        input("\n按回车键继续...")

def wear_items():
    """下达穿戴装饰指令操作"""
    display_warehouse()

    print("\n下达穿戴装饰指令")
    print("-" * 40)
    print("输入格式: 物品名称")
    print("直接按回车返回")
    print("\n注意：这里只下达装饰指令，不会实际穿戴物品")

    item_name = input("\n请输入要下达装饰指令的物品名称: ").strip()

    if not item_name:
        return

    # 查找物品ID
    item_id = None
    for category_id, category in shop_categories.items():
        if category_id in ["body", "headwear", "eyewear", "neckwear", "face"]:
            for item_id_key, item in category["items"].items():
                if item['name'] == item_name:
                    item_id = item_id_key
                    break
            if item_id:
                break

    if not item_id:
        print("[错误] 未找到该物品")
        return

    # 检查库存
    inventory = get_inventory()
    if item_id not in inventory or inventory[item_id] <= 0:
        print("[错误] 没有该物品的库存")
        return

    # 下达装饰指令
    if wear_item(item_id):
        print(f"[成功] 已下达装饰指令：为猫咪穿戴 {item_name}!")
        print("[提示] 指令已记录，等待后续处理")

        # 显示当前的指令记录
        print("\n已下达的装饰指令:")
        print(f"   物品：{item_name}")
        print("   状态：已记录")
        print("   说明：此指令不会消耗物品，仅用于记录装饰意图")
    else:
        print("[错误] 下达指令失败")

def display_render_order():
    """显示渲染顺序"""
    print("\n" + "="*50)
    print("[渲染] 图层叠加顺序")
    print("="*50)

    render_order = get_render_order()
    print("当前渲染顺序（从下到上）:")
    for i, item in enumerate(render_order, 1):
        print(f"   {i}. {item['slot_name']}: {item['item_name']}")
        if item['image']:
            print(f"      图片: {item['image']}")

if __name__ == "__main__":
    warehouse_interaction()