"""
LumiPaw 4号主程序入口

职责：
1. 初始化 1号 pet_system、2号 task_manager、3号 economy_module
2. 连接事件流：任务完成 -> 经济奖励 -> 桌宠 reward 发光
3. 接入新版分类商店：展示商品、购买物品、展示玩具、刷新金币和背包
4. 提供一个简单验收面板，方便点击演示完整闭环

注意：
- 不直接修改 glow_level/current_task/coins 全局变量
- 不重写各模块业务逻辑，只通过公开函数和事件通信
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True


PROJECT_ROOT = Path(__file__).resolve().parent

DEFAULT_TASK_FILE = PROJECT_ROOT / "task_manager.py"
DEFAULT_ECONOMY_DIR = PROJECT_ROOT / "economy_module"
DEFAULT_PET_PARENT = PROJECT_ROOT
DEFAULT_PET_ASSET_DIR = PROJECT_ROOT / "图片素材"
FALLBACK_PET_FRAME_FILES = ["第一帧.PNG", "第二帧.PNG", "第三帧.PNG", "第四帧.PNG", "第五帧.PNG"]


def _prepend_sys_path(path: Path) -> None:
    path_text = str(path.resolve())
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def _load_module_from_file(module_name: str, file_path: Path) -> Any:
    if not file_path.exists():
        raise FileNotFoundError(f"找不到模块文件: {file_path}")

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _unload_modules(*roots: str) -> None:
    for module_name in list(sys.modules):
        if any(module_name == root or module_name.startswith(root + ".") for root in roots):
            del sys.modules[module_name]


@dataclass
class CoreModules:
    task_manager: Any
    economy: Any
    event_listener: Any


def load_core_modules(
    task_file: Path = DEFAULT_TASK_FILE,
    economy_dir: Path = DEFAULT_ECONOMY_DIR,
) -> CoreModules:
    """加载 2号任务模块和 3号经济模块。"""
    if not economy_dir.exists():
        raise FileNotFoundError(f"找不到经济系统目录: {economy_dir}")

    _unload_modules("economy", "event_listener", "economy_module")
    _prepend_sys_path(economy_dir.parent)
    task_manager = _load_module_from_file("lumipaw_task_manager", task_file)

    package_name = economy_dir.name
    economy = importlib.import_module(f"{package_name}.economy")
    event_listener = importlib.import_module(f"{package_name}.event_listener")
    return CoreModules(task_manager, economy, event_listener)


def load_pet_window(pet_parent: Path = DEFAULT_PET_PARENT) -> type:
    """加载 1号桌宠模块。"""
    pet_dir = pet_parent / "pet_system"
    if not pet_dir.exists():
        raise FileNotFoundError(f"找不到桌宠系统目录: {pet_dir}")

    _unload_modules("pet_system")
    _prepend_sys_path(pet_parent)
    from pet_system import PetWindow

    return PetWindow


def create_pet_window(PetWindow: type, asset_dir: Path = DEFAULT_PET_ASSET_DIR) -> Any:
    """创建桌宠窗口；若新版渲染器支持 image_dir，则启动时直接使用指定素材目录。"""
    pet_module = sys.modules.get(PetWindow.__module__)
    renderer_class = getattr(pet_module, "CatRenderer", None) if pet_module is not None else None
    original_init = getattr(renderer_class, "__init__", None)

    if renderer_class is None or original_init is None:
        return PetWindow()

    def patched_init(self, width: int = 450, height: int = 450, image_dir: str | None = None):
        return original_init(self, width, height, image_dir or str(asset_dir))

    renderer_class.__init__ = patched_init
    try:
        return PetWindow()
    finally:
        renderer_class.__init__ = original_init


def configure_pet_assets(
    pet_window: Any,
    asset_dir: Path = DEFAULT_PET_ASSET_DIR,
    logger: Callable[[str], None] = print,
) -> None:
    """确认新版 pet_system 的 PNG 帧素材可用，必要时才重载。"""
    renderer = getattr(pet_window, "renderer", None)
    if renderer is None or not hasattr(renderer, "load_frames"):
        logger("[桌宠] 当前 PetWindow 未暴露 renderer.load_frames，跳过素材重载")
        return

    frame_files = list(getattr(renderer, "FRAME_FILES", FALLBACK_PET_FRAME_FILES))
    missing = [filename for filename in frame_files if not (asset_dir / filename).exists()]
    if missing:
        logger(f"[桌宠] 素材目录缺少 PNG 帧: {asset_dir}，缺失: {', '.join(missing)}")
        return

    already_loaded = bool(getattr(renderer, "is_loaded", False))
    frame_count = int(getattr(renderer, "frame_count", 0) or 0)
    loaded_dir = Path(str(getattr(renderer, "_image_dir", ""))).resolve()
    desired_dir = asset_dir.resolve()
    if already_loaded and frame_count >= len(frame_files) and loaded_dir == desired_dir:
        logger(f"[桌宠] 新版 pet_system 已自动加载 PNG 帧素材: {asset_dir}")
        return

    renderer.load_frames(str(asset_dir))
    logger(f"[桌宠] 已加载新版 PNG 帧素材: {asset_dir}")


class LumiPawOrchestrator:
    """4号主程序：只负责模块连接和事件分发。"""

    def __init__(
        self,
        modules: CoreModules,
        pet_window: Any | None = None,
        on_change: Callable[[], None] | None = None,
        logger: Callable[[str], None] = print,
    ) -> None:
        self.task_manager = modules.task_manager
        self.economy = modules.economy
        self.event_listener = modules.event_listener
        self.pet_window = pet_window
        self.on_change = on_change
        self.logger = logger
        self.active_task_id: str | None = None
        self._bind_events()

    def _bind_events(self) -> None:
        self.event_listener.listen_task_events(self._handle_task_completed)
        if hasattr(self.event_listener, "listen_purchase_events"):
            self.event_listener.listen_purchase_events(self._handle_purchase_event)
        if hasattr(self.event_listener, "event_listener"):
            self.event_listener.event_listener.start()
        self.logger("[主程序] 事件流已连接：任务完成 -> 金币奖励 -> 桌宠发光；商店购买事件已接入")

    def _notify_change(self) -> None:
        if self.on_change is not None:
            self.on_change()

    def _handle_task_completed(self, event: dict[str, Any]) -> None:
        before = self.economy.get_coins()

        # 新版 task_manager 会在事件里直接给出 coins_reward；旧版仍交给经济模块处理。
        if "coins_reward" in event:
            reward = int(event.get("coins_reward") or 0)
            if reward > 0:
                self.economy.add_coins(reward)
            self.logger(f"[主程序] 使用任务模块金币奖励: +{reward}")
        elif hasattr(self.economy, "on_task_completed"):
            self.economy.on_task_completed(
                event["task_name"],
                event["duration"],
                event["success"],
            )
        elif event["success"]:
            self.economy.add_coins(10)

        after = self.economy.get_coins()

        reward_delta = after - before
        if event["success"] and reward_delta > 0 and self.pet_window is not None:
            self.pet_window.trigger_reward_glow()
            self.logger("[主程序] 桌宠 reward 发光已触发")
        elif self.pet_window is not None:
            self.pet_window.update_state("idle")
            if event["success"]:
                self.logger("[主程序] 本次无金币奖励，未触发 reward 发光")

        self.logger(
            f"[主程序] 任务事件: {event['task_name']} "
            f"success={event['success']} duration={event['duration']} coins {before}->{after}"
        )
        self._notify_change()

    def _handle_purchase_event(self, event: dict[str, Any]) -> None:
        self.logger(f"[商店] 购买事件: {event['item_id']} price={event['price']}")
        self._notify_change()

    def add_task(self, name: str, duration: int) -> str:
        task_id = self.task_manager.add_task(name, duration)
        self.logger(f"[任务] 已添加: {name} ({duration}分钟), id={task_id}")
        self._notify_change()
        return task_id

    def start_task(self, task_id: str) -> bool:
        ok = self.task_manager.start_task(task_id)
        if ok:
            self.active_task_id = task_id
            if self.pet_window is not None:
                self.pet_window.update_state("keyboard")
            self.logger(f"[任务] 已开始: {task_id}")
        else:
            self.logger(f"[任务] 开始失败: {task_id}")
        self._notify_change()
        return ok

    def simulate_active_task_elapsed(self, minutes: int) -> None:
        """仅供自测和一键验收演示使用，让新版任务奖励规则可被立即演示。"""
        current_task = self.task_manager.get_current_task()
        if isinstance(current_task, dict) and "start_time" in current_task:
            current_task["start_time"] -= max(0, minutes) * 60

    def finish_task(self, force: bool = False) -> dict[str, Any] | None:
        try:
            event = self.task_manager.finish_task(force=force)
        except TypeError:
            event = self.task_manager.finish_task()
        if event is None:
            self.logger("[任务] 当前没有正在执行的任务")
            self._notify_change()
            return None

        if event.get("early_warning"):
            remaining = event.get("remaining_minutes", 0)
            message = event.get("message") or f"还有 {remaining} 分钟才会结束"
            self.logger(f"[任务] {message}")
            self._notify_change()
            return event

        self.active_task_id = None
        if "coins_reward" in event:
            self._handle_task_completed(event)
        else:
            self.event_listener.trigger_task_completed(
                event["task_name"],
                event["duration"],
                event["success"],
            )
        return event

    def get_current_task(self) -> dict[str, Any] | None:
        return self.task_manager.get_current_task()

    def get_coins(self) -> int:
        return self.economy.get_coins()

    def get_shop_items(self) -> dict[str, dict[str, Any]]:
        return self.economy.get_shop_items()

    def get_flat_shop_items(self) -> dict[str, dict[str, Any]]:
        """把新版分类商店结构压平成 item_id -> 商品信息，兼容旧版结构。"""
        shop_data = self.economy.get_shop_items()
        flat_items: dict[str, dict[str, Any]] = {}

        for key, value in shop_data.items():
            if isinstance(value, dict) and isinstance(value.get("items"), dict):
                category_name = value.get("name", key)
                for item_id, item in value["items"].items():
                    flat_items[item_id] = {
                        **item,
                        "category_id": key,
                        "category_name": category_name,
                    }
            elif isinstance(value, dict):
                flat_items[key] = {
                    **value,
                    "category_id": "",
                    "category_name": "商店",
                }

        return flat_items

    def get_purchased_items(self) -> list[str]:
        return self.economy.get_purchased_items()

    def get_inventory(self) -> dict[str, Any]:
        if hasattr(self.economy, "get_inventory"):
            return self.economy.get_inventory()

        flat_items = self.get_flat_shop_items()
        inventory: dict[str, Any] = {}
        for item_id in self.economy.get_purchased_items():
            item = flat_items.get(item_id, {})
            inventory[item_id] = {
                "name": item.get("name", item_id),
                "description": item.get("description", ""),
                "quantity": 1,
                "category": item.get("category_name", "商店"),
            }
        return inventory

    def wear_item(self, item_id: str) -> bool:
        flat_items = self.get_flat_shop_items()
        item_name = flat_items.get(item_id, {}).get("name", item_id)

        if self.pet_window is not None and hasattr(self.pet_window, "wear_item"):
            ok = self.pet_window.wear_item(item_id)
        elif hasattr(self.economy, "wear_item"):
            ok = self.economy.wear_item(item_id)
            if ok and self.pet_window is not None and hasattr(self.pet_window, "refresh_decorations"):
                self.pet_window.refresh_decorations()
        else:
            self.logger("[仓库] 当前模块未提供 wear_item 接口")
            self._notify_change()
            return False

        if ok:
            self.logger(f"[仓库] 已穿戴装饰: {item_name}")
        else:
            self.logger(f"[仓库] 无法穿戴装饰: {item_name}")
        self._notify_change()
        return ok

    def take_off_item(self, item_id: str) -> bool:
        flat_items = self.get_flat_shop_items()
        item_name = flat_items.get(item_id, {}).get("name", item_id)

        if self.pet_window is not None and hasattr(self.pet_window, "take_off_item"):
            ok = self.pet_window.take_off_item(item_id)
        elif hasattr(self.economy, "take_off_item"):
            ok = self.economy.take_off_item(item_id)
            if ok and self.pet_window is not None and hasattr(self.pet_window, "refresh_decorations"):
                self.pet_window.refresh_decorations()
        else:
            self.logger("[仓库] 当前模块未提供 take_off_item 接口")
            self._notify_change()
            return False

        if ok:
            self.logger(f"[仓库] 已脱卸装饰: {item_name}")
        else:
            self.logger(f"[仓库] 无法脱卸装饰: {item_name}")
        self._notify_change()
        return ok

    def show_toy(self, item_id: str) -> bool:
        flat_items = self.get_flat_shop_items()
        item = flat_items.get(item_id, {})
        item_name = item.get("name", item_id)

        if item.get("category_id") != "toy":
            self.logger(f"[玩具] 请选择玩具类商品: {item_name}")
            self._notify_change()
            return False
        if item_id not in self.get_purchased_items():
            self.logger(f"[玩具] 请先购买玩具: {item_name}")
            self._notify_change()
            return False
        if self.pet_window is None or not hasattr(self.pet_window, "show_toy"):
            self.logger("[玩具] 当前桌宠模块未提供 show_toy 接口")
            self._notify_change()
            return False

        ok = self.pet_window.show_toy(item_id)
        if ok:
            self.logger(f"[玩具] 已展示玩具: {item_name}")
        else:
            self.logger(f"[玩具] 无法展示玩具: {item_name}")
        self._notify_change()
        return ok

    def hide_toy(self, item_id: str) -> bool:
        flat_items = self.get_flat_shop_items()
        item_name = flat_items.get(item_id, {}).get("name", item_id)

        if self.pet_window is None or not hasattr(self.pet_window, "hide_toy"):
            self.logger("[玩具] 当前桌宠模块未提供 hide_toy 接口")
            self._notify_change()
            return False

        ok = self.pet_window.hide_toy(item_id)
        if ok:
            self.logger(f"[玩具] 已隐藏玩具: {item_name}")
        else:
            self.logger(f"[玩具] 当前未展示该玩具: {item_name}")
        self._notify_change()
        return ok

    def buy_item(self, item_id: str) -> bool:
        shop_items = self.get_flat_shop_items()
        if item_id not in shop_items:
            self.logger(f"[商店] 商品不存在: {item_id}")
            self._notify_change()
            return False

        before = self.economy.get_coins()
        ok = self.economy.buy_item(item_id)
        after = self.economy.get_coins()
        item = shop_items[item_id]

        if ok:
            self.event_listener.trigger_purchase_event(item_id, item["price"])
            self.logger(f"[商店] 已购买 {item['name']}，金币 {before}->{after}")
        else:
            self.logger(f"[商店] 金币不足，无法购买 {item['name']}，当前金币 {before}")

        self._notify_change()
        return ok


def run_self_test(
    task_file: Path = DEFAULT_TASK_FILE,
    economy_dir: Path = DEFAULT_ECONOMY_DIR,
) -> int:
    """非 GUI 自测：验证 4号事件流闭环。"""

    class FakePet:
        def __init__(self) -> None:
            self.reward_count = 0
            self.state = "idle"

        def trigger_reward_glow(self) -> None:
            self.reward_count += 1
            self.state = "reward"

        def update_state(self, state: str) -> None:
            self.state = state

    modules = load_core_modules(task_file, economy_dir)
    fake_pet = FakePet()
    orchestrator = LumiPawOrchestrator(modules, fake_pet)

    def finish_demo_task(name: str) -> dict[str, Any]:
        task_id = orchestrator.add_task(name, 30)
        assert orchestrator.start_task(task_id), "任务应能正常开始"
        orchestrator.simulate_active_task_elapsed(90)
        event = orchestrator.finish_task()
        assert event is not None, "完成任务应返回 task_completed_event"
        assert event["success"] is True, "模拟90分钟任务应符合时间规则"
        return event

    before = orchestrator.get_coins()
    first_event = finish_demo_task("4号集成验收任务 A")
    first_reward = int(first_event.get("coins_reward", 10))
    after_first = orchestrator.get_coins()
    assert after_first == before + first_reward, "任务成功后金币应按任务事件奖励增加"
    assert fake_pet.reward_count == 1, "任务成功后应触发桌宠 reward 发光"

    second_event = finish_demo_task("4号集成验收任务 B")
    second_reward = int(second_event.get("coins_reward", 10))
    after_second = orchestrator.get_coins()
    assert after_second == before + first_reward + second_reward, "两次成功任务后金币应累计增加"
    assert fake_pet.reward_count == 2, "每次成功任务后都应触发桌宠 reward 发光"

    flat_items = orchestrator.get_flat_shop_items()
    wearable_items = [
        (item_id, item)
        for item_id, item in flat_items.items()
        if item.get("price", 10**9) <= after_second
        and (item.get("layer") in {"head", "face", "neck"} or item.get("category_id") == "body")
    ]
    cheapest_id, cheapest_item = min(
        wearable_items or list(flat_items.items()),
        key=lambda row: row[1].get("price", 10**9),
    )
    cheapest_price = cheapest_item["price"]
    assert orchestrator.buy_item(cheapest_id), "两次任务奖励后应能购买最低价商品"
    assert orchestrator.get_coins() == after_second - cheapest_price, "购买后金币应按商品价格扣除"
    assert cheapest_id in orchestrator.get_inventory(), "购买后背包应包含对应商品"

    if hasattr(orchestrator.economy, "wear_item"):
        assert orchestrator.wear_item(cheapest_id), "购买后应能穿戴可穿戴商品"
        render_order = getattr(orchestrator.economy, "get_render_order", lambda: [])()
        assert any(item.get("item_id") == cheapest_id for item in render_order), "穿戴后渲染顺序应包含该装饰"

    if hasattr(orchestrator.economy, "take_off_item"):
        assert orchestrator.take_off_item(cheapest_id), "新版经济模块应能脱卸已穿戴商品"
        render_order = getattr(orchestrator.economy, "get_render_order", lambda: [])()
        assert not any(item.get("item_id") == cheapest_id for item in render_order), "脱卸后渲染顺序不应再包含该装饰"

    print("[自测通过] 任务完成 -> 金币奖励 -> 桌宠 reward 发光；新版分类商店购买/穿戴/脱卸 -> 状态更新")
    return 0


def run_gui(
    task_file: Path = DEFAULT_TASK_FILE,
    economy_dir: Path = DEFAULT_ECONOMY_DIR,
    pet_parent: Path = DEFAULT_PET_PARENT,
    pet_assets: Path = DEFAULT_PET_ASSET_DIR,
) -> int:
    try:
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import (
            QApplication,
            QAbstractItemView,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
            QMessageBox,
            QPushButton,
            QSpinBox,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError("运行图形界面需要安装 PyQt5，请使用能运行 pet_system 的 Python。") from exc

    class ControlPanel(QWidget):
        def __init__(self, orchestrator: LumiPawOrchestrator) -> None:
            super().__init__()
            self.orchestrator = orchestrator
            self.task_rows: dict[str, QListWidgetItem] = {}

            self.setWindowTitle("LumiPaw 主程序 - 4号集成入口")
            self.setMinimumWidth(460)

            self.coin_label = QLabel()
            self.current_label = QLabel()
            self.name_input = QLineEdit("课堂演示任务")

            self.duration_input = QSpinBox()
            self.duration_input.setRange(1, 240)
            self.duration_input.setValue(30)
            self.duration_input.setSuffix(" 分钟")

            self.task_list = QListWidget()
            self.task_list.setSelectionMode(QAbstractItemView.SingleSelection)

            self.shop_label = QLabel("商店")
            self.shop_list = QListWidget()
            self.shop_list.setSelectionMode(QAbstractItemView.SingleSelection)
            self.shop_list.setMinimumHeight(110)
            self.inventory_label = QLabel()
            self.warehouse_label = QLabel()

            self.log_box = QTextEdit()
            self.log_box.setReadOnly(True)
            self.log_box.setMinimumHeight(150)

            add_button = QPushButton("添加任务")
            start_button = QPushButton("开始选中任务")
            finish_button = QPushButton("完成当前任务")
            demo_button = QPushButton("一键验收演示")
            buy_button = QPushButton("购买选中商品")
            wear_button = QPushButton("穿戴选中装饰")
            take_off_button = QPushButton("脱卸选中装饰")
            show_toy_button = QPushButton("展示选中玩具")
            hide_toy_button = QPushButton("隐藏选中玩具")

            add_button.clicked.connect(self.add_task)
            start_button.clicked.connect(self.start_selected_task)
            finish_button.clicked.connect(self.finish_current_task)
            demo_button.clicked.connect(self.run_acceptance_demo)
            buy_button.clicked.connect(self.buy_selected_item)
            wear_button.clicked.connect(self.wear_selected_item)
            take_off_button.clicked.connect(self.take_off_selected_item)
            show_toy_button.clicked.connect(self.show_selected_toy)
            hide_toy_button.clicked.connect(self.hide_selected_toy)

            form_layout = QHBoxLayout()
            form_layout.addWidget(self.name_input, 2)
            form_layout.addWidget(self.duration_input, 1)
            form_layout.addWidget(add_button)

            action_layout = QHBoxLayout()
            action_layout.addWidget(start_button)
            action_layout.addWidget(finish_button)
            action_layout.addWidget(demo_button)

            layout = QVBoxLayout(self)
            layout.addWidget(self.coin_label)
            layout.addWidget(self.current_label)
            layout.addLayout(form_layout)
            layout.addWidget(self.task_list)
            layout.addLayout(action_layout)
            layout.addWidget(self.shop_label)
            layout.addWidget(self.shop_list)
            layout.addWidget(buy_button)
            layout.addWidget(wear_button)
            layout.addWidget(take_off_button)
            layout.addWidget(show_toy_button)
            layout.addWidget(hide_toy_button)
            layout.addWidget(self.inventory_label)
            layout.addWidget(self.warehouse_label)
            layout.addWidget(self.log_box)

            self.refresh()

        def log(self, message: str) -> None:
            self.log_box.append(message)

        def refresh(self) -> None:
            self.coin_label.setText(f"金币: {self.orchestrator.get_coins()}")
            current_task = self.orchestrator.get_current_task()
            if current_task is None:
                self.current_label.setText("当前任务: 无")
            else:
                name = current_task["task_name"]
                duration = current_task["expected_duration"]
                self.current_label.setText(f"当前任务: {name} ({duration}分钟)")
            self.refresh_shop()

        def refresh_shop(self) -> None:
            selected_item = self.shop_list.currentItem()
            selected_id = selected_item.data(Qt.UserRole) if selected_item else None
            self.shop_list.clear()

            flat_items = self.orchestrator.get_flat_shop_items()
            inventory = self.orchestrator.get_inventory()
            for item_id, item in flat_items.items():
                inventory_value = inventory.get(item_id)
                if isinstance(inventory_value, dict):
                    quantity = inventory_value.get("quantity", 0)
                elif isinstance(inventory_value, int):
                    quantity = inventory_value
                else:
                    quantity = 0

                owned = f"已有 x{quantity}" if quantity else "可购买"
                category_name = item.get("category_name", "商店")
                row = QListWidgetItem(
                    f"[{owned}] {category_name} / {item['name']} / "
                    f"{item['price']}金币 / {item.get('description', '')}"
                )
                row.setData(Qt.UserRole, item_id)
                self.shop_list.addItem(row)
                if item_id == selected_id:
                    self.shop_list.setCurrentItem(row)

            inventory_names = []
            for item_id, value in inventory.items():
                if isinstance(value, dict):
                    name = value.get("name", item_id)
                    quantity = value.get("quantity", 1)
                else:
                    name = flat_items.get(item_id, {}).get("name", item_id)
                    quantity = value
                inventory_names.append(f"{name} x{quantity}")
            inventory_text = "、".join(inventory_names) if inventory_names else "空"
            self.inventory_label.setText(f"背包: {inventory_text}")

            render_text = "无"
            get_render_order = getattr(self.orchestrator.economy, "get_render_order", None)
            if callable(get_render_order):
                render_items = get_render_order()
                if render_items:
                    render_text = " -> ".join(
                        f"{item.get('slot_name', item.get('slot', '装饰'))}:{item.get('item_name', item.get('item_id', ''))}"
                        for item in render_items
                    )
            self.warehouse_label.setText(f"装饰顺序: {render_text}")

        def add_task(self) -> str:
            name = self.name_input.text().strip() or "未命名任务"
            duration = self.duration_input.value()
            task_id = self.orchestrator.add_task(name, duration)

            item = QListWidgetItem(f"[待开始] {name} / {duration}分钟 / {task_id}")
            item.setData(Qt.UserRole, task_id)
            item.setData(Qt.UserRole + 1, name)
            item.setData(Qt.UserRole + 2, duration)
            self.task_list.addItem(item)
            self.task_list.setCurrentItem(item)
            self.task_rows[task_id] = item
            self.refresh()
            return task_id

        def start_selected_task(self) -> None:
            item = self.task_list.currentItem()
            if item is None:
                self.log("[提示] 请先选择一个任务")
                return

            task_id = item.data(Qt.UserRole)
            name = item.data(Qt.UserRole + 1)
            duration = item.data(Qt.UserRole + 2)
            if self.orchestrator.start_task(task_id):
                item.setText(f"[进行中] {name} / {duration}分钟 / {task_id}")
            self.refresh()

        def get_finished_status(self, event: dict[str, Any]) -> str:
            if not event["success"] and int(event.get("remaining_minutes") or 0) > 0:
                return "提前结束(无奖励)"
            if not event["success"]:
                return "完成但未达标"

            if "coins_reward" in event:
                reward = int(event.get("coins_reward") or 0)
                actual_duration = int(event.get("duration") or 0)
                if actual_duration == 0 and reward == 0:
                    return "已结束(无奖励)"
                if reward == 0:
                    return "已完成(无奖励)"

            return "已完成"

        def finish_current_task(self) -> None:
            finished_task_id = self.orchestrator.active_task_id
            event = self.orchestrator.finish_task()
            if event is None:
                self.refresh()
                return
            if event.get("early_warning"):
                remaining = event.get("remaining_minutes", 0)
                message = event.get("message") or f"还有 {remaining} 分钟才会结束，确定要提前结束？"
                if event.get("warning_type") == "too_early":
                    detail = "是否仍然提前结束？"
                else:
                    detail = "是否提前结束当前任务？"
                choice = QMessageBox.question(
                    self,
                    "提前结束任务",
                    f"{message}\n{detail}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if choice != QMessageBox.Yes:
                    self.refresh()
                    return
                event = self.orchestrator.finish_task(force=True)
                if event is None:
                    self.refresh()
                    return

            finished_item = self.task_rows.get(finished_task_id or "")
            if finished_item is not None:
                task_id = finished_item.data(Qt.UserRole)
                name = finished_item.data(Qt.UserRole + 1)
                duration = finished_item.data(Qt.UserRole + 2)
                status = self.get_finished_status(event)
                finished_item.setText(f"[{status}] {name} / {duration}分钟 / {task_id}")

            self.refresh()

        def run_acceptance_demo(self) -> None:
            self.duration_input.setValue(30)

            for suffix in ("A", "B"):
                task_name = f"一键验收任务 {suffix}"
                self.name_input.setText(task_name)
                task_id = self.add_task()
                item = self.task_rows[task_id]
                if not self.orchestrator.start_task(task_id):
                    self.log("[验收] 无法开始演示任务，请先完成当前任务")
                    return
                self.orchestrator.simulate_active_task_elapsed(90)
                item.setText(f"[进行中] {task_name} / 30分钟 / {task_id}")
                self.task_list.setCurrentItem(item)
                self.finish_current_task()

            affordable_items = [
                (item_id, item)
                for item_id, item in self.orchestrator.get_flat_shop_items().items()
                if item.get("price", 10**9) <= self.orchestrator.get_coins()
            ]
            if not affordable_items:
                self.log("[验收] 金币仍不足以购买商品")
                self.refresh()
                return

            item_id, item = min(affordable_items, key=lambda row: row[1].get("price", 10**9))
            self.log(f"[验收] 自动购买最低价商品: {item['name']}")
            self.orchestrator.buy_item(item_id)
            self.refresh()

        def buy_selected_item(self) -> None:
            item = self.shop_list.currentItem()
            if item is None:
                self.log("[商店] 请先选择一个商品")
                return

            item_id = item.data(Qt.UserRole)
            self.orchestrator.buy_item(item_id)
            self.refresh()

        def wear_selected_item(self) -> None:
            item = self.shop_list.currentItem()
            if item is None:
                self.log("[仓库] 请先选择一个已购买的装饰商品")
                return

            item_id = item.data(Qt.UserRole)
            self.orchestrator.wear_item(item_id)
            self.refresh()

        def take_off_selected_item(self) -> None:
            item = self.shop_list.currentItem()
            if item is None:
                self.log("[仓库] 请先选择一个已穿戴的装饰商品")
                return

            item_id = item.data(Qt.UserRole)
            self.orchestrator.take_off_item(item_id)
            self.refresh()

        def show_selected_toy(self) -> None:
            item = self.shop_list.currentItem()
            if item is None:
                self.log("[玩具] 请先选择一个已购买的玩具商品")
                return

            item_id = item.data(Qt.UserRole)
            self.orchestrator.show_toy(item_id)
            self.refresh()

        def hide_selected_toy(self) -> None:
            item = self.shop_list.currentItem()
            if item is None:
                self.log("[玩具] 请先选择一个正在展示的玩具商品")
                return

            item_id = item.data(Qt.UserRole)
            self.orchestrator.hide_toy(item_id)
            self.refresh()

    app = QApplication(sys.argv[:1])
    modules = load_core_modules(task_file, economy_dir)
    PetWindow = load_pet_window(pet_parent)

    panel_ref: dict[str, ControlPanel | None] = {"panel": None}
    pending_logs: list[str] = []

    def log_to_panel(message: str) -> None:
        panel = panel_ref["panel"]
        if panel is None:
            pending_logs.append(message)
        else:
            panel.log(message)

    pet_window = create_pet_window(PetWindow, pet_assets)
    if getattr(pet_window, "_keyboard_listener", None) is None:
        log_to_panel("[桌宠] 全局键盘监听未启动；如需按键变亮，请安装 pynput")
    configure_pet_assets(pet_window, pet_assets, logger=log_to_panel)
    pet_window.show()
    pet_window.center_on_screen()

    orchestrator = LumiPawOrchestrator(modules, pet_window, logger=log_to_panel)
    panel = ControlPanel(orchestrator)
    panel_ref["panel"] = panel
    for message in pending_logs:
        panel.log(message)
    orchestrator.on_change = panel.refresh
    panel.show()

    def stop_listener() -> None:
        if hasattr(modules.event_listener, "event_listener"):
            modules.event_listener.event_listener.stop()

    app.aboutToQuit.connect(stop_listener)
    return app.exec_()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LumiPaw 4号主程序入口")
    parser.add_argument("--self-test", action="store_true", help="运行非 GUI 集成自测")
    parser.add_argument("--task-file", type=Path, default=DEFAULT_TASK_FILE)
    parser.add_argument("--economy-dir", type=Path, default=DEFAULT_ECONOMY_DIR)
    parser.add_argument("--pet-parent", type=Path, default=DEFAULT_PET_PARENT)
    parser.add_argument("--pet-assets", type=Path, default=DEFAULT_PET_ASSET_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test(args.task_file, args.economy_dir)
    return run_gui(args.task_file, args.economy_dir, args.pet_parent, args.pet_assets)


if __name__ == "__main__":
    raise SystemExit(main())







