"""Turtle Gallery 的作品资料；导入本模块不会打开窗口或运行作品。"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS = {"all": "全部作品", "interactive": "互动精选", "original": "创意原稿"}
CATEGORIES = ("全部主题", "风景动画", "几何绘画", "趣味挑战", "角色与物件", "文字实验")


def _work(number, title, subtitle, filename, category, controls, description,
          accent="#7FE3CF", motif="orbit", tags=(), console=False, collection="interactive", featured=False,
          entry_class=None, creation=False, autoplay=False, web_play=None):
    original = collection == "original"
    return {
        "id": number, "number": f"{number:02d}", "title": title, "subtitle": subtitle,
        "filename": filename if original else "社团展示/" + filename,
        "collection": collection, "featured": featured,
        "entry_class": entry_class, "creation": creation, "autoplay": autoplay, "web_play": web_play,
        "category": category, "controls": controls, "description": description,
        "accent": accent, "motif": motif, "console": console,
        "preview": (f"docs/assets/originals/{number:02d}.png" if original else
                    f"社团展示/previews/{number:02d}.png"),
        "tags": tuple(tags),
    }


WORKS = [
    _work(1, "把夜空点亮", "烟花齐放 · 四种花型 · 湖面倒影", "01_点击烟花.py", "风景动画",
          "点击发射；A 自动；C 切换花型；F 烟花齐放。", "从升空拖尾，到绽放的爱心与金柳，把城市和湖面一起点亮。",
          "#F7C887", "fireworks", ("烟花", "粒子", "fireworks"), entry_class="Fireworks", web_play="play/fireworks.html"),
    _work(2, "口袋里的宇宙", "星云微尘 · 日冕流光 · 分层星环", "02_旋转星系.py", "风景动画",
          "点击星球查看介绍；↑↓ 调整速度；O 显示/隐藏轨道。", "星云与微尘衬托流动日冕，行星带着云层、表面纹理和分层星环绕行；大小与距离采用艺术化比例。",
          "#A8B8FF", "orbit", ("星系", "宇宙", "solar"), entry_class="Galaxy"),
    _work(3, "一笔生花", "旋转对称 · 镜像手绘 · 三种配色", "03_鼠标万花筒.py", "几何绘画",
          "拖动画画；↑↓ 调整对称份数；P 换色；C 清空；D 自动。", "鼠标的一笔同时出现在多个方向，手绘线条生长成旋转花瓣。",
          "#EDA7D8", "flower", ("万花筒", "对称", "kaleidoscope"), entry_class="Kaleidoscope", web_play="play/kaleidoscope.html"),
    _work(4, "清浅荷塘", "锦鲤摆尾 · 鱼群避让 · 点击投喂", "04_互动鱼塘.py", "风景动画",
          "点击水面投喂；F 添加锦鲤，最多 14 尾。", "荷花、涟漪和锦鲤组成一池小景，鱼群会追逐食物并避开同伴。",
          "#9BD9B7", "fish", ("鱼塘", "锦鲤", "pond"), entry_class="Pond"),
    _work(5, "把星光装进口袋", "键鼠控制 · 接取光效 · 分数挑战", "05_接住星星.py", "趣味挑战",
          "←→ 或 A/D 移动；M 切换鼠标控制；漏接五颗结束。", "在月夜里移动编织篮子，接住星星，比比谁的反应更快。",
          "#F5D18B", "star", ("接星星", "游戏", "stars"), entry_class="StarGame"),
    _work(6, "一树四季", "层叠树冠 · 四季山景 · 点击唤风", "06_四季分形树.py", "风景动画",
          "1～4 选季节；S 下一季；G 逐层生长；↑↓ 调整风力；点击唤起一阵风。", "远山与草地间，同一棵树换上春花、浓荫、金叶与雪枝；点击让花叶随风起舞，按 G 观察递归生长。",
          "#F0ACB2", "tree", ("四季", "递归", "tree"), entry_class="SeasonTree"),
    _work(7, "深海来信", "脉动伞盖 · 发光触手 · 追随光点", "07_深海水母.py", "风景动画",
          "点击留下光点；C 切换配色；↑↓ 调整水流。", "一群水母随水流漂动，柔软的触手和脉动伞盖回应你留下的光点。",
          "#91D9ED", "jelly", ("水母", "海洋", "jellyfish"), entry_class="Jellyfish"),
    _work(8, "山水有回声", "昼夜渐变 · 远山倒影 · 点击行舟", "08_山水画卷.py", "风景动画",
          "D 切换昼夜；点击湖面添舟，最多 5 艘；↑↓ 调整风速。", "远山、亭台、归鸟与小舟铺成画卷，天色和水中的倒影一起渐变。",
          "#BCD4BB", "mountain", ("山水", "风景", "landscape"), entry_class="Landscape"),
    _work(9, "圆在画花", "五层光纹 · 三种配色 · 滚圆原理", "09_几何绘图仪.py", "几何绘画",
          "1～4 选曲线；P 换配色；L 切换单线/叠层；C 重绘；G 圆盘开关；↑↓ 调速。", "默认呈现二十瓣织锦，将同一条内旋轮线缩放、旋转成五层光纹；切换配色或按 G 观察原始曲线的滚圆机构。",
          "#C2B2F1", "flower", ("绘图仪", "内旋轮线", "spirograph"), entry_class="Spirograph"),
    _work(10, "霓虹弹球", "方向反弹 · 砖块粒子 · 自动演示", "10_霓虹弹球.py", "趣味挑战",
          "鼠标或 ←→ 移动；点击/Enter 发球；A 切换自动演示。", "击碎 40 块彩砖，利用球拍的不同位置改变反弹角度，也可以观看自动演示。",
          "#72DED6", "bricks", ("打砖块", "游戏", "breakout"), entry_class="Breakout"),
    _work(11, "递归圆阵", "一个圆 · 四向分支 · 层层缩小", "2.py", "几何绘画",
          "自动绘制；关闭作品窗口返回画廊。", "从半径 100 的红圆出发，每层向上下左右递归画出半径减半的圆。",
          "#F29299", "circles", ("递归", "圆", "fractal"), collection="original"),
    _work(12, "彩色方块螺旋", "八色画笔 · 旋转方块 · 黑底绽放", "import turtle.py", "几何绘画",
          "自动绘制；关闭作品窗口返回画廊。", "画笔每次转过 44 度，位移与方块尺寸逐渐增加，叠出八色几何轨迹。",
          "#B6ACFF", "squares", ("螺旋", "方块", "spiral"), collection="original"),
    _work(13, "一颗红心", "圆弧与直线 · 一笔填色", "xin.py", "角色与物件",
          "自动绘制；关闭作品窗口返回画廊。", "两段圆弧和两条长线围成爱心，再用红色填满，是简单而直接的画笔创意。",
          "#F38EA7", "heart", ("爱心", "heart"), collection="original"),
    _work(14, "圆弧叶影", "玉色叶片 · 细密叶脉 · 露珠微光", "yeizi.py", "几何绘画",
          "C 换配色；V 显示/隐藏叶脉；点击叶面落露；空格暂停，R 重来。", "由原来的四段半圆出发，画出层叠叶面、叶脉与露珠，观察圆弧如何组成植物轮廓。",
          "#9ED8B3", "leaf", ("叶子", "圆弧", "leaf"), collection="original", entry_class="ArcLeaves"),
    _work(15, "圆弧雨伞", "彩色伞面 · 雨丝倒影 · 点击水波", "yusan.py", "角色与物件",
          "C 换配色；↑↓ 调雨量；点击水面添波纹；空格暂停，R 重来。", "保留圆弧伞顶、波浪伞沿与弯钩伞柄，增添织物分片、雨滴与水面倒影。",
          "#8ACBE0", "umbrella", ("雨伞", "umbrella"), collection="original", entry_class="RainUmbrella"),
    _work(16, "彩球碰撞", "20 颗彩球 · 随机颜色 · 边界反弹", "下落的小球.py", "风景动画",
          "自动运动；关闭作品窗口，或在画廊点击“结束作品”。", "20 颗大小和速度各异的小球在黑色舞台运动，碰到窗口边界就反向弹回。",
          "#E7AEDE", "balls", ("小球", "动画", "bounce"), collection="original"),
    _work(17, "随机分形树", "随机分叉 · 递归枝条 · 粉色花点", "分形树.py", "风景动画",
          "自动绘制；重新打开可生成另一棵树；关闭窗口返回。", "左右分枝分别选择随机角度和长度，末梢用粉色小点点出花朵。",
          "#EFACC0", "tree", ("树", "递归", "random"), collection="original"),
    _work(18, "哆啦A梦头像", "蓝白圆脸 · 圆眼红鼻 · 六根胡须", "哆啦A梦.py", "角色与物件",
          "观看逐笔绘制；关闭作品窗口返回画廊。", "用圆、圆弧和直线画出熟悉的蓝色头像，适合讲解坐标定位与填色。",
          "#81C9F0", "face", ("角色", "头像", "doraemon"), collection="original"),
    _work(19, "旋转太极", "黑白双鱼 · 圆弧填色 · 连续旋转", "太极.py", "几何绘画",
          "自动旋转；关闭作品窗口，或在画廊点击“结束作品”。", "使用方向角重新绘制黑白双鱼，让静态的太极图在画布中央缓缓转动。",
          "#D9DEE8", "yin", ("太极", "旋转", "yin yang"), collection="original"),
    _work(20, "温柔便签", "随机短句 · 四种底色 · 桌面小实验", "弹窗.py", "文字实验",
          "主动点击“开始作品”后，会连续打开最多 50 张便签；画廊的“结束作品”可一起关闭。",
          "把一句句问候写成散落的彩色小窗口。这个原稿会创建多个窗口，请在详情页主动开始。",
          "#F0BDC9", "notes", ("弹窗", "文字", "notes"), collection="original"),
    _work(21, "指针时钟", "实时走针 · 十二刻度 · 彩色指针", "时钟.py", "风景动画",
          "自动显示本机时间；关闭作品窗口，或在画廊点击“结束作品”。", "用当前系统时间计算时针、分针和秒针的角度，每隔 0.1 秒刷新表盘。",
          "#A5C5EB", "clock", ("时间", "clock"), collection="original"),
    _work(22, "月饼装盒计算", "整数除法 · 余数 · 交互问答", "测试.py", "文字实验",
          "在文字窗口按回车继续，再输入月饼数与每盒数量；输入 q 退出。",
          "一段命令行小程序：输入月饼数量和每盒容量，算出能装满几盒以及剩下多少个。",
          "#E8C48B", "mooncake", ("计算器", "月饼", "console"), console=True, collection="original"),
    _work(23, "见缝插针", "点击发针 · 旋转针盘 · 时机挑战", "见缝插针.py", "趣味挑战",
          "点击画布插入新针；与已有针角度过近即结束；关闭窗口后可重新打开。",
          "针盘不停转动，找准空隙插入下一根针，在越来越密的针阵中挑战反应。",
          "#C4A5F1", "needles", ("游戏", "点击", "needle"), collection="original"),
    _work(24, "旋转风车", "折纸明暗 · 四叶旋转 · 点击送风", "风车.py", "风景动画",
          "C 换配色；↑↓ 调速；D 反转；点击送风；空格暂停，R 重来。", "四片折纸叶面随风转动，折痕、轴心与木杆构成完整风车；定时动画支持暂停和调速。",
          "#83DCD9", "pinwheel", ("风车", "旋转", "windmill"), collection="original", entry_class="PaperPinwheel"),
    _work(25, "星空彼岸花", "星河流光 · 卷曲花瓣 · 花丝绽放", "25_星空彼岸花.py", "风景动画",
          "点击落下流星；C 切换花色；G 重播绽放；↑↓ 调整速度；E 打开创作工坊。", "细长的卷曲花瓣与舒展花丝在星空下盛放；在创作工坊中调整参数与种子，保存自己的花朵配方。",
          "#FF809F", "flower", ("浪漫光影", "短视频", "抖音", "tiktok", "彼岸花", "starry lily"), featured=True,
          entry_class="StarryLily", creation=True, autoplay=True),
    _work(26, "怦然心动", "粒子爱心 · 呼吸光晕 · 星点聚合", "26_怦然心动.py", "几何绘画",
          "点击让爱心散成星尘再相聚；C 切换色彩；↑↓ 调整心跳；E 打开创作工坊。", "光点聚成有层次的爱心，随着双拍节奏轻轻跳动；在创作工坊中调整参数与种子，保存自己的粒子配方。",
          "#FFA7C3", "heart", ("浪漫光影", "短视频", "抖音", "tiktok", "爱心", "粒子", "particle heart"), featured=True,
          entry_class="ParticleHeart", creation=True, autoplay=True, web_play="play/heart.html"),
    _work(27, "星河玫瑰", "层叠花瓣 · 星空微光 · 逐瓣盛开", "27_星河玫瑰.py", "风景动画",
          "点击洒下星尘；C 切换花色；G 重播生长；↑↓ 调整速度。", "从层叠的花心到向外舒展的花瓣，一朵带着星河微光的玫瑰在深色夜幕中展开。",
          "#F2A6D4", "flower", ("浪漫光影", "短视频", "抖音", "tiktok", "玫瑰", "rose", "galaxy"), featured=True, entry_class="GalaxyRose", autoplay=True),
    _work(28, "霓光蝶舞", "对称蝶翼 · 渐变鳞片 · 点击追光", "28_霓光蝶舞.py", "几何绘画",
          "点击引蝶追光；C 切换色彩；M 切换悬停与漫游。", "渐变蝶翼、细密翅脉与星点鳞片组成一只发光的蝶，随着呼吸般的振翅追逐你留下的光。",
          "#ADAEFF", "butterfly", ("浪漫光影", "短视频", "抖音", "tiktok", "蝴蝶", "butterfly", "neon"), featured=True, entry_class="NeonButterfly"),
]


def get_work(value):
    """按整数或数字字符串查找作品，例如 1、'01'；未知编号返回 None。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return next((work for work in WORKS if work["id"] == number), None)
