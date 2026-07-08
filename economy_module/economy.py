# 经济系统模块 (Economy + Shop)
# 3号模块：经济系统 + 商店

import time
import threading
from typing import Dict, List, Optional

# 全局变量（禁止修改命名）
coins: int = 0  # 初始金币

# 商店商品数据结构优化（按素材分类）
shop_categories: Dict[str, Dict[str, Dict]] = {
    "body": {
        "name": "身体装扮",
        "items": {
            "clothes": {
                "name": "衣服",
                "price": 40,
                "description": "漂亮的衣服",
                "image": "装饰-衣服.png"
            }
        }
    },
    "headwear": {
        "name": "头部装饰",
        "items": {
            "casual_hat": {
                "name": "帽子",
                "price": 20,
                "description": "休闲风格帽子",
                "layer": "head",
                "image": "帽子.PNG"
            }
        }
    },
    "eyewear": {
        "name": "眼部装饰",
        "items": {
            "sheep_glasses": {
                "name": "慢羊羊眼镜",
                "price": 25,
                "description": "休闲风格眼镜",
                "layer": "face",
                "image": "装饰-慢羊羊眼镜.PNG"
            },
            "frame_glasses": {
                "name": "眼镜框",
                "price": 35,
                "description": "酷炫风格眼镜",
                "layer": "face",
                "image": "装饰-眼镜框.PNG"
            }
        }
    },
    "neckwear": {
        "name": "颈部装饰",
        "items": {
            "bow_tie": {
                "name": "蝴蝶结",
                "price": 20,
                "description": "优雅蝴蝶结",
                "layer": "neck",
                "image": "装饰-蝴蝶结.png"
            },
            "necktie": {
                "name": "领结",
                "price": 20,
                "description": "正式领结",
                "layer": "neck",
                "image": "装饰-领结.PNG"
            },
            "scarf": {
                "name": "方巾",
                "price": 35,
                "description": "红色方巾",
                "layer": "neck",
                "image": "装饰-围巾.PNG"
            },
            "bell": {
                "name": "铃铛",
                "price": 15,
                "description": "可爱的铃铛",
                "layer": "neck",
                "image": "装饰-铃铛.png"
            },
            "rope": {
                "name": "上吊绳",
                "price": 30,
                "description": "装饰性绳子",
                "layer": "neck",
                "image": "装饰-\"上吊绳\".PNG"
            }
        }
    },
    "face": {
        "name": "面部装饰",
        "items": {
            "pink_blush": {
                "name": "腮红",
                "price": 15,
                "description": "可爱粉色腮红",
                "image": "腮红.PNG"
            },
            "decorative_blush": {
                "name": "装饰腮红",
                "price": 15,
                "description": "装饰性腮红",
                "image": "装饰-腮红.PNG"
            }
        }
    },
    "food": {
        "name": "食品类",
        "items": {
            "canned_food": {
                "name": "猫罐头",
                "price": 20,
                "description": "美味的罐头食品",
                "image": "食品-猫罐头.PNG"
            },
            "fish_dry": {
                "name": "小鱼干",
                "price": 30,
                "description": "高蛋白零食",
                "image": "食品-小鱼干.PNG"
            }
        }
    },
    "toy": {
        "name": "玩具类",
        "items": {
            "mouse": {
                "name": "老鼠",
                "price": 25,
                "description": "仿真老鼠玩具",
                "image": "玩具-老鼠.PNG"
            },
            "orange_yarn": {
                "name": "橙色毛线",
                "price": 20,
                "description": "可爱的橙色毛线玩具",
                "image": "玩具-橙色毛线.PNG"
            },
            "blue_yarn": {
                "name": "蓝色毛线",
                "price": 20,
                "description": "清新的蓝色毛线玩具",
                "image": "玩具-蓝色毛线.PNG"
            },
            "pink_yarn": {
                "name": "粉色毛线",
                "price": 20,
                "description": "温柔的粉色毛线玩具",
                "image": "玩具-粉色毛线.PNG"
            }
        }
    }
}

# 购买记录 - 存储商品ID和数量
inventory: Dict[str, int] = {}  # 商品ID: 数量

# 仓库系统 - 存储已穿戴的物品
warehouse: Dict[str, List[str]] = {  # 部位: 物品ID列表
    "body": [],  # 身体
    "head": [],  # 头部
    "face": [],  # 面部
    "neck": []   # 颈部
}

# 图层叠加顺序（从下到上）
layer_order: List[str] = ["body", "neck", "face", "head"]

# 穿戴部位定义
wear_slots = {
    "body": "身体",
    "head": "头部",
    "face": "面部",
    "neck": "颈部"
}

# 必须实现的函数
def add_coins(amount: int) -> None:
    """添加金币"""
    global coins
    coins += amount
    if coins < 0:
        coins = 0

def spend_coins(amount: int) -> bool:
    """花费金币，返回是否成功"""
    global coins
    if coins >= amount:
        coins -= amount
        return True
    return False

def get_coins() -> int:
    """获取当前金币数量"""
    return coins

def buy_item(item_id: str, quantity: int = 1) -> bool:
    """购买商品，支持数量参数

    Args:
        item_id: 商品ID
        quantity: 购买数量，默认为1

    Returns:
        bool: 购买是否成功
    """
    # 查找商品所属分类
    for category_id, category in shop_categories.items():
        if item_id in category["items"]:
            item = category["items"][item_id]
            total_price = item["price"] * quantity

            # 检查金币是否足够
            if spend_coins(total_price):
                # 更新库存
                if item_id in inventory:
                    inventory[item_id] += quantity
                else:
                    inventory[item_id] = quantity
                return True
            return False
    return False


def get_purchased_items() -> List[str]:
    """获取已购买的商品ID列表（保持兼容性）"""
    return list(inventory.keys())

def get_inventory() -> Dict[str, Dict]:
    """获取详细的库存信息，包含商品详情和数量"""
    detailed_inventory = {}
    for item_id, quantity in inventory.items():
        # 查找商品所属分类
        for category_id, category in shop_categories.items():
            if item_id in category["items"]:
                item = category["items"][item_id]
                detailed_inventory[item_id] = {
                    "name": item["name"],
                    "price": item["price"],
                    "description": item["description"],
                    "quantity": quantity,
                    "category": category["name"]
                }
                break
    return detailed_inventory

def get_shop_items() -> Dict[str, Dict]:
    """获取商店所有商品（返回新的分类结构）"""
    return shop_categories

def get_categories() -> List[str]:
    """获取商品分类列表"""
    return list(shop_categories.keys())

def get_category_items(category_id: str) -> Dict[str, Dict]:
    """获取指定分类的所有商品"""
    if category_id in shop_categories:
        return shop_categories[category_id]["items"]
    return {}

def get_warehouse() -> Dict[str, Dict]:
    """获取仓库当前穿戴状态（每部位返回最后穿戴的物品）"""
    detailed_warehouse = {}
    for slot_id, item_ids in warehouse.items():
        if slot_id in wear_slots and item_ids:
            slot_name = wear_slots[slot_id]
            # 取该部位最后穿戴的物品（最新）
            latest_id = item_ids[-1]

            # 查找物品信息
            item_info = None
            for category in shop_categories.values():
                if latest_id in category["items"]:
                    item_info = category["items"][latest_id]
                    break

            if item_info:
                detailed_warehouse[slot_id] = {
                    "slot_name": slot_name,
                    "item_id": latest_id,
                    "item_name": item_info["name"],
                    "description": item_info["description"],
                    "layer": item_info.get("layer", slot_id),
                    "image": item_info.get("image")
                }
    return detailed_warehouse

def get_wear_slots() -> Dict[str, str]:
    """获取穿戴部位定义"""
    return wear_slots

def wear_item(item_id: str) -> bool:
    """穿戴装饰物品到对应部位。

    Args:
        item_id: 商品ID

    Returns:
        bool: 穿戴是否成功
    """
    # 查找物品信息及所属部位
    target_slot = None
    found_item = None
    for category_id, category in shop_categories.items():
        if item_id in category["items"]:
            found_item = category["items"][item_id]
            # 根据物品的layer属性确定穿戴部位
            if found_item.get("layer") == "head":
                target_slot = "head"
            elif found_item.get("layer") == "face":
                target_slot = "face"
            elif found_item.get("layer") == "neck":
                target_slot = "neck"
            elif category_id == "body":
                target_slot = "body"
            break

    if not target_slot or not found_item:
        print(f"[错误] 未知物品: {item_id}")
        return False

    # 检查是否拥有该物品（必须在库存中）
    if item_id not in inventory or inventory[item_id] <= 0:
        print(f"[错误] 请先在商店购买 {found_item['name']}")
        return False

    # 检查该位置是否还能穿戴（最多3个）
    if len(warehouse[target_slot]) >= 3:
        print(f"[限制] {wear_slots[target_slot]} 最多只能穿戴3个物品")
        return False

    # 实际穿戴：加入到 warehouse 对应部位
    warehouse[target_slot].append(item_id)
    print(f"[穿戴] {found_item['name']} → {wear_slots[target_slot]} "
          f"({len(warehouse[target_slot])}/3)")
    return True


def take_off_item(item_id: str) -> bool:
    """脱卸指定物品。

    Args:
        item_id: 商品ID

    Returns:
        bool: 脱卸是否成功
    """
    for slot_id, item_ids in warehouse.items():
        if item_id in item_ids:
            item_ids.remove(item_id)
            # 查找物品名
            item_name = item_id
            for category in shop_categories.values():
                if item_id in category["items"]:
                    item_name = category["items"][item_id]["name"]
                    break
            print(f"[脱卸] {item_name} 已从 {wear_slots[slot_id]} 取下")
            return True
    print(f"[错误] 未找到已穿戴的物品: {item_id}")
    return False

def get_equipped_items() -> Dict[str, List[Dict]]:
    """获取当前穿戴的所有物品"""
    equipped = {}
    for slot_id, item_ids in warehouse.items():
        if slot_id in wear_slots and item_ids:
            equipped[slot_id] = []
            for item_id in item_ids:
                # 查找物品信息
                for category in shop_categories.values():
                    if item_id in category["items"]:
                        item = category["items"][item_id]
                        equipped[slot_id].append({
                            "item_name": item["name"],
                            "description": item["description"]
                        })
                        break
    return equipped

def get_render_order() -> List[Dict]:
    """获取渲染顺序（从下到上）"""
    render_items = []
    for slot in layer_order:
        if slot in warehouse and warehouse[slot]:
            for item_id in warehouse[slot]:
                for category in shop_categories.values():
                    if item_id in category["items"]:
                        item = category["items"][item_id]
                        render_items.append({
                            "slot": slot,
                            "slot_name": wear_slots[slot],
                            "item_id": item_id,
                            "item_name": item["name"],
                            "image": item.get("image"),
                            "layer": item.get("layer", slot)
                        })
                        break
    return render_items

# 任务完成事件处理
def on_task_completed(task_name: str, duration: int, success: bool) -> None:
    """监听任务完成事件，给予金币奖励"""
    if success:
        reward = 10  # 完成任务获得10金币
        add_coins(reward)
        print(f"任务 {task_name} 完成！获得 {reward} 金币")

# 键盘发光事件处理
def on_glow_event(glow_type: str, value: int) -> None:
    """监听发光事件（暂时不需要处理）"""
    pass

# 测试主程序
if __name__ == "__main__":
    print("=== 经济系统模块测试 ===")

    # 测试金币系统
    print(f"初始金币: {get_coins()}")
    add_coins(50)
    print(f"获得50金币后: {get_coins()}")
    print(f"尝试消费30金币: {'成功' if spend_coins(30) else '失败'}")
    print(f"消费后金币: {get_coins()}")

    # 测试商店系统
    print("\n=== 商店 ===")
    for cat_id, cat in shop_categories.items():
        print(f"  [{cat['name']}]")
        for item_id, item in cat["items"].items():
            print(f"    {item['name']} ({item_id}): {item['price']}金币")
    print()

    # 测试购买
    print("\n=== 购买测试 ===")
    print(f"当前金币: {get_coins()}")
    print(f"购买食物: {'成功' if buy_item('food') else '失败'}")
    print(f"购买后金币: {get_coins()}")
    print(f"已购买商品: {get_purchased_items()}")

    # 测试任务完成奖励
    print("\n=== 任务完成奖励 ===")
    on_task_completed("测试任务", 30, True)
    print(f"获得奖励后金币: {get_coins()}")

    print("\n=== 测试完成 ===")