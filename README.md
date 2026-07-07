# 经济系统模块 (Economy + Shop)

## 3号模块：经济系统 + 商店

### 模块概述
本模块实现了完整的金币系统和商店功能，包括：
- 金币积累和消费
- 商店购买系统
- 物品背包管理
- 事件监听和响应
- 与其他模块的对接

### 必须实现的函数（核心接口）

```python
# 金币系统
add_coins(amount: int) -> None      # 添加金币
spend_coins(amount: int) -> bool    # 花费金币，返回是否成功
get_coins() -> int                 # 获取当前金币数量

# 商店系统
buy_item(item_id: str) -> bool     # 购买商品
get_shop_items() -> Dict           # 获取商店所有商品
get_purchased_items() -> List      # 获取已购买的商品列表
```

### 与4号主程序的对接接口

#### 1. 事件监听（4号需要调用）
```python
from event_listener import listen_task_events, listen_purchase_events

# 监听任务完成事件
def on_task_reward(event):
    if event["success"]:
        # 给予金币奖励
        add_coins(10)

listen_task_events(on_task_reward)

# 监听购买事件
def on_purchase(event):
    # 处理购买逻辑
    pass

listen_purchase_events(on_purchase)
```

#### 2. 事件触发（4号需要调用）
```python
from event_listener import trigger_task_completed, trigger_purchase_event

# 任务完成时触发
trigger_task_completed(task_name, duration, success)

# 购买商品后触发
trigger_purchase_event(item_id, price)
```

### 全局变量规范
- `coins`: int - 当前金币数量（0~无上限）
- `shop_items`: Dict - 商店商品数据
- `purchased_items`: List - 已购买商品列表

### 统一事件结构
```python
# 任务完成事件
task_completed_event = {
    "task_name": str,
    "duration": int,
    "success": bool
}

# 购买事件
purchase_event = {
    "item_id": str,
    "price": int
}
```

### 使用方法

#### 基本使用
```python
from economy import add_coins, get_coins, buy_item

# 添加金币
add_coins(50)

# 获取当前金币
current_coins = get_coins()

# 购买商品
if buy_item("food"):
    print("购买成功！")
```

#### 与主程序对接
```python
# 在主程序中导入
from economy_module import event_listener

# 注册事件回调
def handle_task_completion(event):
    if event["success"]:
        # 给予10金币奖励
        add_coins(10)

event_listener.register_task_callback(handle_task_completion)
```

### 商店商品列表
- `food`: 食物 (10金币) - 恢复少量宠物能量
- `toy`: 玩具 (25金币) - 让宠物开心
- `medicine`: 药品 (50金币) - 恢复宠物健康
- `accessory`: 饰品 (100金币) - 给宠物佩戴装饰

### 独立运行测试
```bash
cd economy_module
python main.py
```

### 模块独立性说明
- ✅ 可以独立运行（包含main测试）
- ✅ 不依赖其他模块内部实现
- ✅ 只通过函数参数和返回值进行交互
- ✅ 遵守全局变量命名规范
- ✅ 使用统一事件结构进行通信