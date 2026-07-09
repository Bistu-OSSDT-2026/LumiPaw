"""
cat_renderer.py — Bongo Cat 渲染器

加载 PNG 动画帧并显示，根据 glow_level 和状态叠加发光效果。

功能：
    - 从 图片素材/ 目录加载 5 张 PNG 帧图片（2048x2048 -> 缩放到窗口尺寸）
    - advance_frame() 切换到下一帧（0->1->2->3->4->0 循环）
    - render() 绘制当前帧 PNG + 发光叠加层
    - 发光严格限制在图片像素范围内：透明区域不发光
    - 发光叠加约 10% 高斯模糊

此模块只负责绘制，不管理任何状态变量。
"""

import math
import os
import time
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QRadialGradient,
    QPixmap, QImage,
)
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect,
)


class CatRenderer:
    """Bongo Cat PNG 帧动画渲染器。"""

    # PNG 帧文件名（按顺序：1.png ~ 5.png）
    FRAME_FILES = [
        "1.PNG",
        "2.PNG",
        "3.PNG",
        "4.PNG",
        "5.PNG",
    ]

    # 装饰部位锚点：相对于猫帧的 (x_ratio, y_ratio)
    SLOT_ANCHORS = {
        "body": (0.50, 0.58),   # 身体中央偏下
        "neck": (0.50, 0.42),   # 颈部
        "face": (0.50, 0.35),   # 面部/眼部
        "head": (0.50, 0.12),   # 头顶
    }

    # 装饰缩放：与猫帧使用相同缩放系数（均为 2048→窗口尺寸）
    # 饰品 PNG 本身就是与猫帧同尺寸的对位图层，直接叠加即可自然对齐

    def __init__(self, width: int = 450, height: int = 450,
                 image_dir: str = None):
        self._width = width
        self._height = height
        self._frame_index = 0
        self._frames = []       # 缩放后的 QPixmap
        self._glow_masks = []  # 每帧的发光蒙版（alpha 通道 + 10% 高斯模糊）
        self._loaded = False
        self._image_dir = image_dir   # 图片素材目录
        self._decorations = []       # 当前穿戴的装饰列表
        self._toys = []              # 左下角显示的玩具列表

        self.load_frames(image_dir)

    def load_frames(self, image_dir: str = None):
        """加载 PNG 帧图片并缩放到窗口尺寸。

        Args:
            image_dir: PNG 文件所在目录，默认为项目根目录下的 图片素材/
        """
        if image_dir is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            image_dir = os.path.join(project_root, "图片素材")
        self._image_dir = image_dir

        self._frames = []
        self._glow_masks = []
        for filename in self.FRAME_FILES:
            filepath = os.path.join(image_dir, filename)
            pixmap = QPixmap(filepath)
            if pixmap.isNull():
                print("[cat_renderer] [警告] 无法加载: " + filepath)
                pixmap = QPixmap(self._width, self._height)
                pixmap.fill(Qt.transparent)
                self._glow_masks.append(QPixmap())
            else:
                pixmap = pixmap.scaled(
                    self._width, self._height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                glow_mask = self._create_glow_mask(pixmap)
                self._glow_masks.append(glow_mask)

            self._frames.append(pixmap)

        self._loaded = len(self._frames) > 0
        print("[cat_renderer] 已加载 " + str(len(self._frames))
              + " 帧 PNG (来自: " + image_dir + ")")

    def _create_glow_mask(self, pixmap: QPixmap) -> QPixmap:
        """从 PNG 提取 alpha 通道生成发光蒙版，再施加 10% 高斯模糊。

        使用 QImage.bits() 批量读取像素内存，避免逐像素 API 调用。

        Args:
            pixmap: 缩放后的原始 QPixmap

        Returns:
            带模糊的发光蒙版 QPixmap（白=有像素，黑=透明）
        """
        img = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        w, h = img.width(), img.height()

        # 用 bits() 批量读取像素数据（B,G,R,A 每像素 4 字节）
        src_ptr = img.bits()
        src_ptr.setsize(h * img.bytesPerLine())
        src_buf = bytes(src_ptr)  # bytes 不可变，避免 bytearray 引用问题

        # 构造蒙版：把 alpha 值写入 B,G,R，透明像素保持黑色
        mask_buf = bytearray(len(src_buf))
        for i in range(0, len(src_buf), 4):
            a = src_buf[i + 3]
            if a > 0:
                mask_buf[i]     = a   # B
                mask_buf[i + 1] = a   # G
                mask_buf[i + 2] = a   # R
                mask_buf[i + 3] = 255 # A

        # 构造 QImage 后立即 copy()，确保 QImage 持有独立内存副本
        # （否则依赖外部 buffer，一旦回收会段错误）
        mask = QImage(bytes(mask_buf), w, h, img.bytesPerLine(),
                      QImage.Format_ARGB32).copy()

        mask_pixmap = QPixmap.fromImage(mask)

        # 10% 高斯模糊
        blur_radius = max(2, round(min(w, h) * 0.10))
        return self._apply_blur(mask_pixmap, blur_radius)

    def _apply_blur(self, pixmap: QPixmap, radius: int) -> QPixmap:
        """使用 QGraphicsBlurEffect 进行高斯模糊。"""
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pixmap)

        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(radius)
        item.setGraphicsEffect(blur)
        scene.addItem(item)

        result = QPixmap(pixmap.size())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        scene.render(painter)
        painter.end()
        return result

    def advance_frame(self):
        """切换到下一帧（循环）。"""
        if self._loaded:
            self._frame_index = (self._frame_index + 1) % len(self._frames)

    # ----------------------------------------------------------
    # 装饰穿戴
    # ----------------------------------------------------------

    def update_decorations(self, render_order: list):
        """更新当前穿戴的装饰列表，同部位只保留最后穿戴的一个。

        render_order 中 image 以 "玩具-" 开头的会被放入左下角玩具区。
        """
        self._decorations = []
        self._toys = []
        for item in render_order:
            img_path = item.get("image", "")
            if not img_path:
                continue
            # 玩具 → 左下角
            if img_path.startswith("玩具-"):
                pixmap = self._load_toy_image(img_path)
                if pixmap and not pixmap.isNull():
                    self._toys.append({
                        "item_id": item.get("item_id", ""),
                        "pixmap": pixmap,
                    })
            else:
                # 装饰 → 叠加到猫身
                pixmap = self._load_decoration_image(img_path)
                if pixmap and not pixmap.isNull():
                    self._decorations.append({
                        "slot": item.get("slot", ""),
                        "item_id": item.get("item_id", ""),
                        "pixmap": pixmap,
                    })

        # 同部位只保留最后穿戴的一个（后加的覆盖先加的）
        seen_slots = {}
        for d in self._decorations:
            seen_slots[d["slot"]] = d
        self._decorations = list(seen_slots.values())

        # 玩具只保留最后展示的一个
        if len(self._toys) > 1:
            self._toys = self._toys[-1:]

    def _load_decoration_image(self, filename: str) -> QPixmap:
        """加载装饰图片，缩放到合适尺寸。

        自动适配 economy_module 中可能不匹配的文件名（大小写、前缀、引号）。

        Args:
            filename: 装饰图片文件名（来自 economy_module 的 image 字段）

        Returns:
            缩放后的 QPixmap，失败返回 None
        """
        # 1. 精确路径尝试
        filepath = os.path.join(self._image_dir, filename)
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            return self._scale_decoration(pixmap)

        # 2. 构建实际文件索引（首次构建后缓存）
        if not hasattr(self, '_file_index'):
            self._file_index = {}
            for f in os.listdir(self._image_dir):
                # 键1: 原文件名
                self._file_index[f] = f
                # 键2: 小写
                lower = f.lower()
                if lower not in self._file_index:
                    self._file_index[lower] = f
                # 键3: 去除前缀 + 小写
                for prefix in ['装饰-', '玩具-', '食品-']:
                    if lower.startswith(prefix):
                        no_prefix = lower[len(prefix):]
                        if no_prefix not in self._file_index:
                            self._file_index[no_prefix] = f
                # 键4: 去引号版本（处理弯引号 vs 直引号）
                clean = lower.replace('\u201c', '"').replace('\u201d', '"')
                if clean != lower and clean not in self._file_index:
                    self._file_index[clean] = f
                clean2 = lower.replace('"', '\u201c').replace('"', '\u201d')
                if clean2 != lower and clean2 not in self._file_index:
                    self._file_index[clean2] = f

        # 3. 用 filename 在索引中查找
        lookup_key = filename.lower()
        matched = self._file_index.get(lookup_key)

        # 去掉 装饰- 前缀再查一次
        if not matched:
            for prefix in ['装饰-', '玩具-', '食品-']:
                if lookup_key.startswith(prefix):
                    no_prefix = lookup_key[len(prefix):]
                    matched = self._file_index.get(no_prefix)
                    break

        # 去引号再查
        if not matched:
            clean = lookup_key.replace('\u201c', '"').replace('\u201d', '"')
            matched = self._file_index.get(clean)

        if not matched:
            print(f"[cat_renderer] [警告] 找不到装饰图片: {filename}")
            return None

        matched_path = os.path.join(self._image_dir, matched)
        pixmap = QPixmap(matched_path)
        if pixmap.isNull():
            return None

        return self._scale_decoration(pixmap)

    def _scale_decoration(self, pixmap: QPixmap) -> QPixmap:
        """装饰与猫帧使用相同缩放系数（2048 → 窗口尺寸，KeepAspectRatio）。"""
        return pixmap.scaled(
            self._width, self._height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    # ----------------------------------------------------------
    # 玩具（左下角显示）
    # ----------------------------------------------------------

    def _load_toy_image(self, filename: str) -> QPixmap:
        """加载玩具图片，与猫帧同缩放系数后裁剪到内容区域。

        Returns:
            仅包含玩具实物区域的 QPixmap，失败返回 None
        """
        filepath = os.path.join(self._image_dir, filename)
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            if not hasattr(self, '_file_index'):
                self._file_index = {}
            matched = self._file_index.get(filename.lower())
            if matched:
                pixmap = QPixmap(os.path.join(self._image_dir, matched))
        if pixmap.isNull():
            print(f"[cat_renderer] [警告] 找不到玩具图片: {filename}")
            return None

        # 与猫帧同缩放系数（2048 → 窗口尺寸）
        scaled = pixmap.scaled(
            self._width, self._height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        # 裁剪到非透明区域（只保留玩具实物本身）
        return self._crop_to_content(scaled)

    def _crop_to_content(self, pixmap: QPixmap) -> QPixmap:
        """裁剪 QPixmap 到非透明像素的包围盒。"""
        img = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        w, h = img.width(), img.height()
        min_x, min_y = w, h
        max_x, max_y = 0, 0
        ptr = img.bits()
        ptr.setsize(h * img.bytesPerLine())
        buf = bytes(ptr)
        for y in range(h):
            off = y * img.bytesPerLine()
            for x in range(w):
                a = buf[off + x * 4 + 3]
                if a > 0:
                    if x < min_x: min_x = x
                    if y < min_y: min_y = y
                    if x > max_x: max_x = x
                    if y > max_y: max_y = y
        if min_x > max_x or min_y > max_y:
            return pixmap
        margin = 2
        return pixmap.copy(
            max(0, min_x - margin), max(0, min_y - margin),
            min(w, max_x - min_x + margin * 2),
            min(h, max_y - min_y + margin * 2),
        )

    def add_toy(self, item_id: str, image_path: str):
        """添加一个玩具到靠近猫的位置。"""
        pixmap = self._load_toy_image(image_path)
        if pixmap and not pixmap.isNull():
            self._toys = [t for t in self._toys if t["item_id"] != item_id]
            self._toys.append({"item_id": item_id, "pixmap": pixmap})

    def remove_toy(self, item_id: str) -> bool:
        """移除左下角的玩具。

        Args:
            item_id: 物品 ID

        Returns:
            bool: 是否找到并移除
        """
        before = len(self._toys)
        self._toys = [t for t in self._toys if t["item_id"] != item_id]
        return len(self._toys) < before

    # ----------------------------------------------------------
    # 主绘制接口
    # ----------------------------------------------------------

    def render(self, painter: QPainter, glow_level: int, state: str):
        """绘制一帧桌宠。"""
        if not self._loaded or not self._frames:
            return

        w = self._width
        h = self._height
        idx = self._frame_index

        # 1. 绘制当前帧 PNG（居中）
        frame = self._frames[idx]
        x = (w - frame.width()) // 2
        y = (h - frame.height()) // 2
        painter.drawPixmap(x, y, frame)

        # 2. 绘制装饰（按图层顺序叠加）
        self._draw_decorations(painter, w, h, x, y, frame.width(), frame.height())

        # 3. 叠加发光效果（限制在像素范围内）
        if state == "keyboard" and glow_level > 0:
            self._draw_keyboard_glow(painter, w, h, glow_level)
        elif state == "reward":
            self._draw_reward_glow(painter, w, h, time.time())

        # 4. 绘制左下角玩具
        self._draw_toys(painter, w, h)

    # ----------------------------------------------------------
    # 装饰渲染
    # ----------------------------------------------------------

    def _draw_decorations(self, painter: QPainter, win_w: int, win_h: int,
                          frame_x: int, frame_y: int,
                          frame_w: int, frame_h: int):
        """在猫帧同一位置叠加装饰图片（饰品与猫帧同尺寸同位置对齐）。"""
        if not self._decorations:
            return

        painter.save()

        for deco in self._decorations:
            pixmap = deco.get("pixmap")
            if not pixmap or pixmap.isNull():
                continue

            # 饰品与猫帧同缩放、同位置叠加
            painter.drawPixmap(frame_x, frame_y, pixmap)

        painter.restore()

    # ----------------------------------------------------------
    # 玩具（左下角）
    # ----------------------------------------------------------

    def _draw_toys(self, painter: QPainter, win_w: int, win_h: int):
        """在靠近猫的底部区域绘制玩具（与猫帧同缩放系数，不遮挡猫）。"""
        if not self._toys:
            return

        padding = 15
        # 从猫的底部区域开始摆放：靠近底部边缘，略微偏右
        for toy in self._toys:
            pm = toy.get("pixmap")
            if not pm or pm.isNull():
                continue

            # 放置到靠近猫但避开猫身的位置
            # 偏右侧底部，保证不进入猫的中心区域
            x = win_w - pm.width() - padding
            y = win_h - pm.height() - padding
            painter.drawPixmap(x, y, pm)

    def _draw_keyboard_glow(self, painter: QPainter, w: int, h: int,
                            glow_level: int):
        """keyboard 状态：蓝白色光晕，仅在有像素的区域发光。

        通过离屏画布 + CompositionMode_SourceIn 实现像素级裁剪：
            1. 在临时画布上画径向渐变
            2. 用 mask 作为目标的限制层（SourceIn：只保留 mask 不透明处的内容）
        """
        if not self._glow_masks:
            return

        idx = self._frame_index
        mask = self._glow_masks[idx]
        frame = self._frames[idx]
        x = (w - frame.width()) // 2
        y = (h - frame.height()) // 2

        ratio = glow_level / 100.0
        alpha_base = int(50 * ratio)

        cx = x + frame.width() // 2
        cy = y + frame.height() // 2
        radius = int(max(frame.width(), frame.height()) * 0.85)

        gradient = QRadialGradient(cx, cy, radius)
        gradient.setColorAt(0.0, QColor(200, 230, 255, min(255, alpha_base * 4)))
        gradient.setColorAt(0.3, QColor(130, 190, 255, min(255, alpha_base * 3)))
        gradient.setColorAt(0.6, QColor(100, 160, 255, min(255, alpha_base * 2)))
        gradient.setColorAt(1.0, QColor(80, 130, 255, 0))

        # 离屏渲染：渐变 -> SourceIn(mask) -> 结果叠加到主画布
        glow = self._render_masked_glow(mask, gradient, w, h)
        painter.drawPixmap(0, 0, glow)

    def _draw_reward_glow(self, painter: QPainter, w: int, h: int, t: float):
        """reward 状态：金色脉冲光晕，仅在有像素的区域发光。"""
        if not self._glow_masks:
            return

        idx = self._frame_index
        mask = self._glow_masks[idx]
        frame = self._frames[idx]
        x = (w - frame.width()) // 2
        y = (h - frame.height()) // 2

        pulse = 0.5 + 0.5 * math.sin(t * 5.0)
        alpha_base = int(70 + 80 * pulse)

        cx = x + frame.width() // 2
        cy = y + frame.height() // 2
        radius = int(max(frame.width(), frame.height()) * 0.85)

        gradient = QRadialGradient(cx, cy, radius)
        gradient.setColorAt(0.0, QColor(255, 240, 120, min(255, int(alpha_base * 3))))
        gradient.setColorAt(0.3, QColor(255, 215, 0, min(255, int(alpha_base * 2))))
        gradient.setColorAt(0.6, QColor(255, 180, 50, min(255, alpha_base)))
        gradient.setColorAt(1.0, QColor(255, 150, 0, 0))

        glow = self._render_masked_glow(mask, gradient, w, h)
        painter.drawPixmap(0, 0, glow)

    def _render_masked_glow(self, mask: QPixmap, gradient: QRadialGradient,
                            w: int, h: int) -> QPixmap:
        """在离屏画布上渲染渐变并用 mask 限制到像素范围。

        步骤：
            1. 创建透明临时画布
            2. 画径向渐变（覆盖整个画布）
            3. 切换到 SourceIn 模式，绘制 mask —— 只保留 mask 不透明处的渐变
        """
        canvas = QPixmap(w, h)
        canvas.fill(Qt.transparent)

        p = QPainter(canvas)
        p.setRenderHint(QPainter.Antialiasing)

        # 1. 画径向渐变
        p.setBrush(gradient)
        p.setPen(Qt.NoPen)
        p.drawRect(0, 0, w, h)

        # 2. 用 mask 裁剪：SourceIn = 只保留目标(mask)不透明处的源(渐变)
        p.setCompositionMode(QPainter.CompositionMode_SourceIn)
        p.drawPixmap(0, 0, mask)

        p.end()
        return canvas

    # ----------------------------------------------------------
    # 只读属性
    # ----------------------------------------------------------

    @property
    def frame_index(self) -> int:
        return self._frame_index

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def is_loaded(self) -> bool:
        return self._loaded
