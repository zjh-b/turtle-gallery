import tkinter as tk
import random

# 提示语列表
messages = [
    "今天天气怎么样",
    "今天的你也很辛苦",
    "期待我们下次见面",
    "在干吗",
    "别熬夜",
    "很高兴和你在一起",
    "愿所有梦想成真",
    "好好吃饭",
    "旦逢良辰，顺颂时宜",  # 这里补全了之前缺少的逗号
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
]

# 背景色列表
bg_colors = ["#FFC0CB", "#ADD8E6", "#FFB6C1", "#B0E0E6"]

# 弹窗计数器和最大数量设置
popup_count = 0
max_popups = 50  # 这里可以设置你想要的最大弹窗数量

def create_popup(root):
    global popup_count
    if popup_count >=max_popups:
        return  # 达到最大数量则不再创建

    # 随机选择内容和样式
    msg = random.choice(messages)
    bg = random.choice(bg_colors)
    font_size = random.randint(12, 16)

    # 创建弹窗
    popup = tk.Toplevel(root)
    popup.title("亲爱的你啊")  # 统一窗口名
    popup.configure(bg=bg)

    # 随机位置
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = random.randint(50, screen_width - 200)
    y = random.randint(50, screen_height - 100)
    popup.geometry(f"200x50+{x}+{y}")  # 窗口大小：宽200，高100

    # 添加文字
    label = tk.Label(
        popup,
        text=msg,
        bg=bg,
        font=("楷体", font_size),
        wraplength=180
    )
    label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    popup_count += 1  # 每创建一个弹窗就增加计数

# 创建弹窗
def create_next_popup(root):
    global popup_count
    if popup_count < max_popups:  # 只有没达到最大数量时才继续创建
        create_popup(root)
        root.after(100, create_next_popup, root)  # 100毫秒后创建下一个

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    create_next_popup(root)
    root.mainloop()
