"""月饼装盒：把整数除法摆成一份中秋礼物。

直接运行打开可视化；``python 测试.py --console`` 保留回车开始的文字模式。
T / B 输入总数与每盒容量，方向键微调，N 示例，G 重播装盒，C 三种配色。
"""
import argparse
import math

from 社团展示.舞台 import Paint, Stage, mix, polar


MAX_TOTAL = 999999
MAX_CAPACITY = 99
# 名称、纸面、近景、墨色、礼盒、盒内、烘焙暗色、饼面、高光。
PALETTES = (
    ("桂月鎏金", "#F9F0DA", "#EDE0C0", "#756144", "#756751", "#DDD0AF",
     "#995128", "#DFA454", "#F9DDA0"),
    ("青瓷团圆", "#EDF2E5", "#D4E1D1", "#466B62", "#4A756B", "#C3D5BE",
     "#976341", "#D6AB69", "#F1DDB0"),
    ("胭脂礼盒", "#F8EDE6", "#EDD8CE", "#84595A", "#955C66", "#DDBABE",
     "#A3623D", "#E0AC70", "#FFE1B6"),
)
EXAMPLES = ((26, 6), (18, 6), (5, 8), (0, 6), (128, 8), (999999, 99))


def packing(total, capacity):
    """Return full boxes and remainder, accepting only bounded integers."""
    if type(total) is not int or not 0 <= total <= MAX_TOTAL:
        raise ValueError(f"月饼总数应为 0～{MAX_TOTAL} 的整数")
    if type(capacity) is not int or not 1 <= capacity <= MAX_CAPACITY:
        raise ValueError(f"每盒数量应为 1～{MAX_CAPACITY} 的整数")
    return divmod(total, capacity)


def parse_number(text, field):
    """Use the same strict decimal input rule in the dialog and console."""
    value = text.strip()
    lower, upper = (0, MAX_TOTAL) if field == "total" else (1, MAX_CAPACITY)
    if not value.isascii() or not value.isdecimal():
        raise ValueError(f"请输入 {lower}～{upper} 的整数")
    # Compare decimal length first so even enormous pasted strings never reach
    # Python's integer-conversion limit or consume unnecessary arithmetic work.
    value = value.lstrip("0") or "0"
    if len(value) > len(str(upper)) or not lower <= int(value) <= upper:
        raise ValueError(f"请输入 {lower}～{upper} 的整数")
    return int(value)


def console_main():
    print("欢迎来到月饼计算程序")

    def read_number(prompt, field):
        while True:
            value = input(prompt).strip()
            if value.lower() == "q":
                return None
            try:
                return parse_number(value, field)
            except ValueError as error:
                print(error)

    try:
        while True:
            choice = input("输入q退出程序,按下回车继续\n").strip()
            if choice.lower() == "q":
                break
            if choice:
                print("请按回车开始，或输入 q 退出")
                continue
            total = read_number("输入月饼:", "total")
            if total is None:
                break
            capacity = read_number("输入每盒装的月饼数:", "capacity")
            if capacity is None:
                break
            boxes, remainder = packing(total, capacity)
            print(f"月饼可以装满{boxes}个包装盒,还有{remainder}个")
    except (EOFError, KeyboardInterrupt):
        pass
    return 0


class MooncakePacking:
    DEMO_SECONDS = 4.2
    BOX_LIMIT = 3
    SAMPLE_LIMIT = 6
    INPUTS = {"total": (-194, 232, 89, 167), "capacity": (105, 232, 447, 167)}

    def __init__(self):
        self.stage = Stage("月饼装盒 · 月满成礼", "T 总数    B 每盒数    ↑↓ 总数    ←→ 每盒数    N 示例    G 装盒    C 配色",
                           PALETTES[0][1], "#AC8250", light=True)
        self.paint = Paint(self.stage, "mooncake-packing")
        self.paint.backdrop = Paint(self.stage, "mooncake-paper")
        self.paint.background_signature = self.paint.signature = None
        self.reset()
        for keys, callback in ((('c', 'C'), self.cycle_palette), (('n', 'N'), self.next_example),
                               (('g', 'G'), self.replay), (('t', 'T'), lambda: self.edit('total')),
                               (('b', 'B'), lambda: self.edit('capacity'))):
            for key in keys:
                self.stage.screen.onkey(callback, key)
        for key, field, change in (("Up", "total", 1), ("Down", "total", -1),
                                   ("Right", "capacity", 1), ("Left", "capacity", -1)):
            self.stage.screen.onkey(lambda f=field, d=change: self.adjust(f, d), key)
        self.stage.screen.onclick(self.click)

    def reset(self):
        self.total, self.capacity = EXAMPLES[0]
        self.palette = self.example = 0
        self.progress = 1.0
        self.message = ""

    def set_values(self, total, capacity):
        packing(total, capacity)
        self.total, self.capacity = total, capacity
        self.progress, self.message = 1.0, ""

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def next_example(self):
        if not self.stage.paused:
            self.example = (self.example + 1) % len(EXAMPLES)
            self.set_values(*EXAMPLES[self.example])

    def replay(self):
        if not self.stage.paused:
            self.progress, self.message = 0.0, ""

    def adjust(self, field, amount):
        if self.stage.paused:
            return
        if field == "total":
            self.set_values(max(0, min(MAX_TOTAL, self.total+amount)), self.capacity)
        else:
            self.set_values(self.total, max(1, min(MAX_CAPACITY, self.capacity+amount)))

    def edit(self, field):
        if self.stage.paused:
            return
        title, limits = ("月饼总数", f"0～{MAX_TOTAL}") if field == "total" else ("每盒数量", "1～99")
        try:
            value = self.stage.screen.textinput(title, f"请输入 {limits} 的整数；取消保留原数。")
            if value is None:
                return
            try:
                number = parse_number(value, field)
                self.set_values(number if field == "total" else self.total,
                                number if field == "capacity" else self.capacity)
            except ValueError as error:
                self.message = str(error) + "；已保留原数"
        except (EOFError, KeyboardInterrupt):
            pass
        finally:
            if not self.stage.closed:
                self.stage.screen.listen()

    def click(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if not self.stage.in_scene(x, y):
            return
        for field, (left, top, right, bottom) in self.INPUTS.items():
            if left <= x <= right and bottom <= y <= top:
                self.edit(field)
                break

    def cake(self, p, x, y, radius, colors, detailed=False):
        _, paper, _, ink, _, _, dark, gold, light = colors
        # Twelve fluted lobes and offset layers give the pastry a baked edge.
        contour = tuple((math.cos(t)*(1+.036*math.cos(12*t)),
                         math.sin(t)*(1+.036*math.cos(12*t)))
                        for t in (math.tau*i/96 for i in range(96)))
        p.oval(x+radius*.055, y-radius*.12, radius*1.09, radius*.98, mix(paper, dark, .21))
        for scale, dy, fill in ((1, -.07, dark), (.985, -.015, mix(dark, gold, .58)),
                                 (.94, .045, gold), (.84, .065, mix(gold, light, .36))):
            p.poly([(x+u*radius*scale, y+v*radius*scale+radius*dy) for u, v in contour], fill)
        p.circle(x, y+radius*.065, radius*.73, outline=mix(dark, gold, .35), width=1.1)
        p.circle(x, y+radius*.065, radius*.68, outline=mix(gold, light, .75), width=.8)
        count = 8 if detailed else 5
        for i in range(count):
            angle = math.tau*i/count
            points = [polar(radius*s, angle+a, x, y+radius*.065)
                      for s, a in ((.27, -.16), (.53, -.29), (.64, 0), (.53, .29), (.27, .16))]
            p.poly(points, mix(gold, light, .22), mix(dark, gold, .42), .75, smooth=True)
        p.circle(x, y+radius*.065, radius*.23, mix(gold, light, .39), mix(dark, gold, .42), .8)
        if detailed:
            for i in range(24):
                angle = math.tau*i/24
                p.line([polar(radius*.78, angle, x, y+radius*.065),
                        polar(radius*.85, angle, x, y+radius*.065)], mix(dark, gold, .47), 1.1)
            p.text(x, y+radius*.067, "月", mix(dark, ink, .18), 22, bold=True)
            p.line([polar(radius*.65, .7+i*.045, x, y+radius*.065) for i in range(29)],
                   mix(light, paper, .30), 2)
        else:
            p.circle(x-radius*.055, y+radius*.12, radius*.07, light)

    def backdrop(self, colors):
        signature = self.palette, self.stage.scale, self.stage.view
        if signature == self.paint.background_signature:
            return
        self.paint.background_signature = signature
        _, paper, ground, ink, box, lining, dark, gold, light = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(paper, ground)
        for row in range(11):
            y = -255+row*45
            for column in range(9):
                x = -475+column*114
                p.line([(x, y), (x+6, y+.5)], mix(paper, ink, .055), .65)
        for radius in range(76, 49, -3):
            p.circle(-350, 72, radius, mix(paper, light, .16+(76-radius)*.012))
        p.circle(-350, 72, 49, mix(paper, light, .67))
        p.poly([(-505, -135), (-449, -106), (-386, -134), (-322, -91), (-256, -136),
                (-177, -114), (-78, -160), (65, -131), (193, -155), (358, -105),
                (505, -142), (505, -287), (-505, -287)], mix(ground, ink, .09), smooth=True)
        p.poly([(-505, -207), (-374, -170), (-235, -204), (-108, -190), (77, -216),
                (268, -179), (505, -221), (505, -287), (-505, -287)],
               mix(ground, ink, .06), smooth=True)
        p.text(-447, 214, "月满成礼", ink, 25, "w")
        p.text(-445, 181, "MOONCAKE ATELIER", mix(ink, paper, .26), 9, "w")
        p.line([(-445, 161), (-392, 161)], mix(ink, gold, .5), 1.7)
        # The large cake is a labelled detail study, separate from counted boxes.
        p.oval(-349, -30, 108, 72, mix(ground, ink, .14))
        p.oval(-353, -23, 108, 71, mix(box, ground, .59), mix(ink, ground, .59))
        p.oval(-353, -20, 96, 62, mix(lining, light, .42))
        self.cake(p, -353, 6, 69, colors, detailed=True)
        p.text(-353, -112, "花模纹样 · 放大示意", ink, 10)
        p.text(-353, -143, "一枚月饼，一份团圆。", mix(ink, ground, .20), 10)
        # Low stems of osmanthus frame the illustration without covering counts.
        for x, direction in ((-445, .68), (-282, 2.12)):
            base = (x, -239)
            tip = polar(69, direction, *base)
            p.line([base, tip], mix(ink, gold, .4), 1)
            for i in range(1, 5):
                cx, cy = polar(i*12, direction, *base)
                side = 1 if i % 2 else -1
                end = polar(15, direction+side*.7, cx, cy)
                p.poly([(cx, cy), (end[0]-4, end[1]-2), end, (end[0]+3, end[1]+4)],
                       mix(box, ground, .25), smooth=True)
                for k in range(3):
                    px, py = polar(3, k*math.tau/3, cx+side*6, cy+4)
                    p.circle(px, py, 2.1, mix(gold, light, .55))
        p.text(-445, -267, "有限图形示意 · 计算结果按实际数量", mix(ink, paper, .21), 9, "w")
        p.end()

    def draw_box(self, p, x, y, number, capacity, shown, colors):
        _, paper, _, ink, box, lining, _, gold, light = colors
        p.rect(x-81+3, y+75-4, x+81+3, y-80-4, mix(paper, ink, .18))
        p.rect(x-81, y+75, x+81, y-80, box)
        p.rect(x-75, y+68, x+75, y-74, lining)
        p.rect(x-71, y+64, x+71, y-70, "", mix(box, light, .44))
        p.text(x, y+56, f"礼盒 {number:02}", ink, 9)
        count = min(capacity, self.SAMPLE_LIMIT)
        columns = 1 if count == 1 else (2 if count in (2, 4) else 3)
        rows = math.ceil(count/columns)
        for i in range(count):
            xx = x + (i % columns-(columns-1)/2)*43
            yy = y+4 + ((rows-1)/2-i//columns)*44
            p.rect(xx-20, yy+20, xx+20, yy-20, mix(lining, paper, .17), mix(lining, box, .26), .7)
            if i < shown:
                self.cake(p, xx, yy, 15.7, colors)
        label = f"每盒 {capacity} 枚" if capacity <= self.SAMPLE_LIMIT else f"{capacity} 枚 / 绘 {count} 枚示意"
        p.text(x, y-57, label, ink, 8)

    def draw(self, colors):
        boxes, remainder = packing(self.total, self.capacity)
        box_count = min(self.BOX_LIMIT, boxes)
        per_box = min(self.SAMPLE_LIMIT, self.capacity)
        loose = min(self.SAMPLE_LIMIT, remainder)
        sample_count = box_count*per_box+loose
        revealed = min(sample_count, math.floor(self.progress*sample_count+1e-8))
        signature = (self.total, self.capacity, self.palette, revealed,
                     self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            return
        self.paint.signature = signature
        _, paper, ground, ink, box, lining, dark, gold, light = colors
        p = self.paint
        p.begin()
        for field, bounds in self.INPUTS.items():
            left, top, right, bottom = bounds
            p.rect(left+3, top-3, right+3, bottom-3, mix(ground, ink, .1))
            p.rect(left, top, right, bottom, mix(paper, light, .12), mix(ground, gold, .35))
            value = self.total if field == "total" else self.capacity
            label = "月饼总数 · T" if field == "total" else "每盒数量 · B"
            p.text(left+16, top-18, label, ink, 9, "w")
            p.text(left+16, bottom+20, f"{value:,}", mix(ink, dark, .35), 22, "w", True)
            p.text(right-13, bottom+17, "点击编辑", mix(ink, paper, .25), 8, "e")
        p.text(-192, 134, "装盒结果", ink, 10, "w")
        p.text(446, 134, f"{self.total:,} ÷ {self.capacity} = {boxes:,} 余 {remainder}", ink, 11, "e")
        p.line([(-192, 113), (447, 113)], mix(ink, ground, .55), .8)
        p.text(124, 88, f"{boxes:,} 盒完整装满  +  {remainder} 枚待装", ink, 17)
        positions = (-101, 117, 335)
        for index in range(box_count):
            self.draw_box(p, positions[index], -14, index+1, self.capacity,
                          max(0, revealed-index*per_box), colors)
        if not box_count:
            p.rect(-183, 45, 434, -92, mix(ground, paper, .38), mix(ground, box, .25))
            p.text(125, -11, "还没有装满一盒", mix(ink, paper, .14), 19)
            p.text(125, -44, "余下月饼见下方托盘" if remainder else "输入月饼数量，开始准备礼物", ink, 10)
        omitted = max(0, boxes-box_count)
        p.text(125, -115, f"整盒示意 {box_count} / {boxes:,} 盒 · 另 {omitted:,} 盒未绘", ink, 9)
        p.rect(-192, -138, 447, -235, mix(lining, paper, .55), mix(ground, box, .32))
        p.text(-177, -156, f"余数托盘 · {remainder} 枚", ink, 10, "w")
        p.text(431, -156, f"示意 {loose} 枚 · 另 {max(0, remainder-loose)} 枚未绘", ink, 8, "e")
        for i in range(loose):
            x = -123+i*99
            p.oval(x, -204, 28, 15, mix(lining, box, .13))
            if box_count*per_box+i < revealed:
                self.cake(p, x, -201, 18, colors)
        if not remainder:
            p.text(126, -202, "恰好装完，一枚不余。" if self.total else "托盘暂时是空的。", ink, 12)
        p.text(445, -264, "INTEGER DIVISION / DIVMOD", mix(ink, paper, .24), 8, "e")
        p.end()

    def frame(self, dt):
        if dt > 0:
            self.progress = min(1, self.progress+dt/self.DEMO_SECONDS)
        colors = PALETTES[self.palette]
        self.backdrop(colors)
        self.stage.canvas.tag_raise(self.paint.backdrop.tag)
        self.draw(colors)
        self.stage.canvas.tag_raise(self.paint.tag)
        mode = "装盒示意完成" if self.progress >= 1 else f"装盒演示 {round(self.progress*100)}%"
        self.stage.hud(self.message or f"{colors[0]} · {mode}    /    点击数字可输入，方向键微调")


def main(argv=None):
    parser = argparse.ArgumentParser(description="月饼装盒：可视化与文字计算")
    parser.add_argument("--console", action="store_true", help="使用原有文字输入模式")
    args = parser.parse_args(argv)
    if args.console:
        return console_main()
    app = MooncakePacking()
    app.stage.run(app.frame, app.reset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
