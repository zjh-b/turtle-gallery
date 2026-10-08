"""温柔便签：把原来的 26 句问候，收进一扇窗口里的六张纸笺。

C 换配色，N 换一组；点纸卡换一句，也可用 ←→ 选择、Enter 翻换。
直接运行 ``python 弹窗.py``。只有一个主窗口，关闭窗口即可退出。
"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


MESSAGES = (
    "今天天气怎么样",
    "今天的你也很辛苦",
    "期待我们下次见面",
    "在干吗",
    "别熬夜",
    "很高兴和你在一起",
    "愿所有梦想成真",
    "好好吃饭",
    "旦逢良辰，顺颂时宜",
    "见到你就很开心",
    "你笑起来真好看",
    "告诉你，我在想你",
    "时间都很珍贵",
    "你是今天的小幸运",
    "有好多事想对你说",
    "有你在就很安心",
    "你的努力很有用",
    "一切都会变好",
    "慢慢来",
    "今天也为你加油",
    "你已经很棒了",
    "小挫折而已",
    "累了就停下来",
    "你的坚持，终有所得",
    "每天进步一点点",
    "你值得温柔对待",
)
# 保留原文件的消息变量名，方便从原来的示例继续修改文字。
messages = MESSAGES
TURN_SECONDS = .64
CARD_CENTERS = ((-300, 112), (0, 112), (300, 112),
                (-300, -103), (0, -103), (300, -103))
CARD_WIDTH, CARD_HEIGHT = 250, 166
DEFAULT_CARDS = (1, 4, 7, 17, 19, 25)
# 名称、桌面、纸白、墨色、重点色、植物色、六张卡片底色。
PALETTES = (
    ("奶油花笺", "#E9E1D2", "#FFFAEE", "#625649", "#BA8A64", "#7A9074",
     ("#F8E9D7", "#FAF3E6", "#E7EDDA", "#F2DFDA", "#E3EAF0", "#E8E1ED")),
    ("薄荷清晨", "#DDE8DF", "#FAFBEF", "#3E6259", "#7A9D80", "#618C76",
     ("#E2EFDF", "#EFF4E6", "#D9E8E2", "#EDE8D7", "#DEEAF1", "#E6E8DE")),
    ("暮色莓果", "#E5DFE8", "#FBF4EF", "#65516B", "#AD8A9C", "#879285",
     ("#EADDE8", "#F5E7E6", "#E2E8DE", "#E8DBDE", "#E0E3ED", "#E9DFEF")),
)


def note_lines(text):
    """最多两行，优先在逗号后换行，保留原句的每一个字。"""
    if len(text) <= 7:
        return (text,)
    if "，" in text:
        first, second = text.split("，", 1)
        return first + "，", second
    middle = (len(text) + 1) // 2
    return text[:middle], text[middle:]


class KindNotes:
    def __init__(self):
        self.stage = Stage("温柔便签", "C 纸笺配色    N 下一组    点击 换一句    ←→ 选择    Enter 翻换",
                           PALETTES[0][1], PALETTES[0][4], light=True)
        self.paint = Paint(self.stage, "kind-notes-paper")
        self.paint.cards = [Paint(self.stage, f"kind-note-{i}") for i in range(6)]
        self.paint.signature = None
        self.paint.card_signatures = [None] * 6
        rng = random.Random(626)
        self.fibers = tuple((rng.uniform(-480, 480), rng.uniform(-270, 256),
                             rng.uniform(1, 5)) for _ in range(64))
        self.reset()
        for keys, action in ((('c', 'C'), self.cycle_palette), (('n', 'N'), self.next_group)):
            for key in keys:
                self.stage.screen.onkey(action, key)
        self.stage.screen.onkey(lambda: self.move_selection(-1), "Left")
        self.stage.screen.onkey(lambda: self.move_selection(1), "Right")
        self.stage.screen.onkey(self.change_selected, "Return")
        self.stage.screen.onclick(self.click)

    def reset(self):
        self.palette = self.selected = self.cursor = 0
        self.cards = list(DEFAULT_CARDS)
        self.ages = [None] * 6
        self.pending = [None] * 6

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def move_selection(self, direction):
        if not self.stage.paused:
            self.selected = (self.selected + direction) % 6

    def change_selected(self):
        index = self.selected
        if self.stage.paused or self.ages[index] is not None:
            return
        # 六张卡片之间不重复；正在抬起的卡也为自己的下一句话留位置。
        occupied = set(self.cards) | {value for value in self.pending if value is not None}
        while self.cursor in occupied:
            self.cursor = (self.cursor + 1) % len(MESSAGES)
        self.pending[index] = self.cursor
        self.cursor = (self.cursor + 1) % len(MESSAGES)
        self.ages[index] = 0

    def next_group(self):
        if self.stage.paused or any(age is not None for age in self.ages):
            return
        self.pending = [(self.cursor + i) % len(MESSAGES) for i in range(6)]
        self.cursor = (self.cursor + 6) % len(MESSAGES)
        self.ages = [0] * 6

    def card_lift(self, index):
        age = self.ages[index]
        return 0 if age is None else 11 * math.sin(math.pi * min(1, age / TURN_SECONDS))

    def click(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if not self.stage.in_scene(x, y):
            return
        for index, (cx, cy) in enumerate(CARD_CENTERS):
            cy += self.card_lift(index)
            if abs(x - cx) < CARD_WIDTH / 2 and abs(y - cy) < CARD_HEIGHT / 2:
                self.selected = index
                self.change_selected()
                return

    def draw_desk(self, colors):
        signature = self.palette, self.stage.scale, self.stage.view
        if signature == self.paint.signature:
            return
        self.paint.signature = signature
        _, ground, paper, ink, accent, leaf, _ = colors
        p = self.paint
        p.begin()
        p.gradient(mix(ground, paper, .35), ground)
        for x, y, length in self.fibers:
            p.line([(x, y), (x + length, y + .6)], mix(ground, ink, .035))
        p.line([(-456, 218), (456, 218)], mix(ground, accent, .27), .8)
        p.text(-451, 242, "把好心情，寄给你。", ink, 18, "w")
        p.text(450, 243, "KIND NOTES  /  26", mix(ground, ink, .72), 9, "e")
        p.text(-451, -237, "一张小纸笺，一份被惦记的温柔。", mix(ground, ink, .75), 10, "w")
        p.text(448, -235, "轻点纸卡 · 收到下一句问候", mix(ground, ink, .72), 9, "e")
        # 桌沿两枚散落的小叶片，低对比度纹理不穿过卡片文字。
        for x, y, turn in ((-81, -245, .32), (-42, -250, -.42)):
            p.line([polar(17, turn + math.pi, x, y), polar(17, turn, x, y)],
                   mix(ground, leaf, .52), 1)
            p.poly([polar(18, turn, x, y), polar(10, turn + 1.2, x, y),
                    polar(18, turn + math.pi, x, y), polar(10, turn - 1.2, x, y)],
                   mix(ground, leaf, .28), smooth=True)
        p.end()

    def sprig(self, p, x, y, color, paper, angle=0):
        """卡片下角的迷你植物；只作为绘制细节，不额外创建状态。"""
        def at(u, v):
            return x + u * math.cos(angle) - v * math.sin(angle), \
                y + u * math.sin(angle) + v * math.cos(angle)
        p.line([at(0, -14), at(-2, 5), at(3, 24)], color, 1.1, smooth=True)
        for side, along in ((-1, -3), (1, 2), (-1, 9), (1, 15)):
            p.poly([at(0, along), at(side * 13, along + 5), at(side * 14, along + 15),
                    at(side * 3, along + 11)], mix(paper, color, .62), smooth=True)
            p.line([at(0, along), at(side * 10, along + 11)], mix(paper, color, .79), .7)

    def flower(self, p, x, y, size, petal, center):
        for i in range(5):
            px, py = polar(size * .56, math.tau * i / 5 + .2, x, y)
            p.circle(px, py, size * .43, petal)
        p.circle(x, y, size * .22, center)
        p.circle(x - size * .055, y + size * .06, size * .07, mix(center, "#FFFFFF", .55))

    def draw_card(self, index, colors):
        lift = round(self.card_lift(index), 3)
        signature = (self.palette, self.cards[index], index == self.selected, lift,
                     self.stage.scale, self.stage.view)
        if signature == self.paint.card_signatures[index]:
            return
        self.paint.card_signatures[index] = signature
        _, ground, paper, ink, accent, leaf, faces = colors
        face = faces[index]
        cx, cy = CARD_CENTERS[index]
        p = self.paint.cards[index]
        p.begin()
        p.transform(x=cx, y=cy + lift)
        # 三道相近阴影形成纸张厚度，卡片抬起时阴影略偏下。
        for offset, amount in ((7, .025), (4, .055), (2, .09)):
            p.rect(-125 + offset, 83 - offset - lift * .25, 125 + offset,
                   -83 - offset - lift * .25, mix(ground, ink, amount))
        p.rect(-125, 83, 125, -83, face, mix(face, ink, .08))
        p.line([(-123, 81), (123, 81)], mix(face, paper, .80), 1)
        p.line([(-123, -82), (101, -82)], mix(face, ink, .11), 1)
        # 胶带的毛边与压纹；每张卡的位置略有变化，但文字区域始终留白。
        tx = (-25, 48, -49, 46, -43, 23)[index]
        tape = [(-30, 7), (28, 8), (26, 3), (30, -2), (27, -8), (-29, -7), (-27, -3)]
        p.poly([(x + tx, y + 81) for x, y in tape], mix(face, accent, .23))
        for i in range(8):
            p.line([(tx - 25 + i * 7, 87), (tx - 22 + i * 7, 75)], mix(face, paper, .37), .65)
        p.text(-104, 58, f"FOR YOU   {index + 1:02d}", mix(face, ink, .57), 8, "w")
        p.line([(-104, 45), (-75, 45)], mix(face, accent, .65), 1)
        # 卡片下部的装饰各有变化，上部和中部留给问候文字。
        if index in (0, 2):
            self.sprig(p, 91, -53, leaf, face, -.33 if index == 0 else .25)
            p.line([(-102, -59), (-57, -59)], mix(face, accent, .36), .8)
            p.line([(-102, -64), (-69, -64)], mix(face, accent, .25), .8)
        elif index == 1:
            p.poly([(69, -39), (105, -36), (106, -62), (70, -65)], mix(face, accent, .18))
            p.line([(69, -39), (87, -53), (105, -36)], mix(face, accent, .57), .8)
            p.line([(70, -65), (87, -51), (106, -62)], mix(face, accent, .31), .8)
            p.circle(87, -53, 4.5, mix(face, accent, .60))
            p.circle(86.2, -52.2, 2.8, mix(face, accent, .37))
        elif index == 3:
            p.circle(90, -53, 18, mix(face, accent, .18))
            p.circle(90, -53, 14, "", mix(face, accent, .58), .8)
            self.flower(p, 90, -53, 10, mix(face, paper, .69), mix(face, accent, .77))
            p.line([(-103, -62), (-66, -62)], mix(face, accent, .32), .8)
        elif index == 4:
            p.line([(68, -54), (80, -56), (93, -48), (107, -51)], mix(face, ink, .24), .8, smooth=True)
            p.poly([(85, -49), (105, -34), (94, -56), (92, -46)], mix(face, paper, .91),
                   mix(face, ink, .15), .7)
            p.line([(85, -49), (105, -34), (92, -46)], mix(face, accent, .65), .8)
        else:
            p.line([(72, -67), (83, -46), (97, -44)], mix(face, leaf, .69), 1, smooth=True)
            self.flower(p, 84, -46, 11, mix(face, paper, .78), mix(face, accent, .83))
            self.flower(p, 103, -55, 7, mix(face, paper, .63), mix(face, accent, .66))
            p.poly([(76, -62), (65, -59), (64, -49), (74, -52)], mix(face, leaf, .49), smooth=True)
        # 折角和卡片编号保持在阅读区之外。
        p.poly([(104, -83), (125, -62), (125, -83)], mix(face, ink, .06))
        p.poly([(104, -83), (104, -63), (125, -62)], mix(face, paper, .70))
        lines = note_lines(MESSAGES[self.cards[index]])
        text_y = 7 if len(lines) == 1 else 18
        for row, line in enumerate(lines):
            p.text(0, text_y - row * 28, line, ink, 20)
        p.text(-104, -39, "WITH A LITTLE KINDNESS", mix(face, ink, .42), 7, "w")
        if index == self.selected:
            # 选择标记是纸外四角短线，避免按钮边框抢走纸张质感。
            for x, y, sx, sy in ((-132, 91, 1, -1), (132, 91, -1, -1),
                                  (-132, -91, 1, 1), (132, -91, -1, 1)):
                p.line([(x + sx * 10, y), (x, y), (x, y + sy * 10)],
                       mix(ground, accent, .65), 1.2)
        p.end()

    def frame(self, dt):
        if dt > 0:
            for index, age in enumerate(self.ages):
                if age is None:
                    continue
                elapsed = age + dt
                if elapsed >= TURN_SECONDS / 2 and self.pending[index] is not None:
                    self.cards[index] = self.pending[index]
                    self.pending[index] = None
                self.ages[index] = None if elapsed >= TURN_SECONDS else elapsed
        colors = PALETTES[self.palette]
        self.draw_desk(colors)
        self.stage.canvas.tag_raise(self.paint.tag)
        for index in range(6):
            self.draw_card(index, colors)
            self.stage.canvas.tag_raise(self.paint.cards[index].tag)
        self.stage.hud(f"{colors[0]} · 26 句原作问候    /    选中第 {self.selected + 1} 张 · 轻点换一句")


if __name__ == "__main__":
    app = KindNotes()
    app.stage.run(app.frame, app.reset)
