<div align="center">

# Turtle Gallery

**Draw an idea. Watch it come alive.**

10 interactive exhibits · 14 original experiments · Python Turtle / Tkinter

[中文](README.md) · [Get started](#get-started) · [Explore](#explore-the-gallery) · [Creative guide](docs/CREATIVE_GUIDE.md)

![Turtle Gallery: fireworks, planets, koi and generative art](docs/assets/hero.png)

</div>

Click to launch fireworks, turn a brush stroke into a kaleidoscope, or watch a recursive tree grow through four seasons. Turtle Gallery brings together animated scenes, small games and the original drawings and experiments that started the collection.

Made for club demonstrations, learning Python and trying out visual ideas. The artwork is drawn by code at runtime. **No third-party runtime packages, downloaded art assets or network connection required.**

## Get started

Use **Python 3.9+ with Tkinter**. Download and extract the repository ZIP, then double-click **[start.bat](start.bat)** on Windows, or run:

```bash
git clone https://github.com/zjh-b/turtle-gallery.git
cd turtle-gallery
python run.py
```

Browse categories or search for an exhibit in the gallery. All 24 works share this entry point; the interface and in-app instructions are primarily in Chinese.

```bash
python run.py --list       # List all 24 works and their IDs
python run.py --demo 01    # Open the fireworks exhibit
python run.py --demo 18    # Watch the original Doraemon drawing
python run.py --check      # Check dependencies and files without opening a window
```

Developed and checked on Windows. macOS and Linux need a Python build with Tk and a desktop display; their full GUI experience has not yet been verified. Use `python3` if that is your Python command. `--check` verifies dependencies and files, not display availability or GUI behavior.

## Explore the gallery

![Interactive exhibits in motion](docs/assets/showcase.gif)

### 10 interactive exhibits

| ID | Exhibit / source | Try this |
| --- | --- | --- |
| 01 | [Light Up the Night](社团展示/01_点击烟花.py) | Click for fireworks; C changes the pattern, F launches a five-rocket finale |
| 02 | [Pocket Universe](社团展示/02_旋转星系.py) | Select planets, inspect rings and moons, change speed with ↑↓ |
| 03 | [A Stroke in Bloom](社团展示/03_鼠标万花筒.py) | Drag to draw mirrored patterns; P changes colors, D toggles automatic drawing |
| 04 | [Quiet Koi Pond](社团展示/04_互动鱼塘.py) | Click to feed koi and watch them steer around one another |
| 05 | [Catch the Starlight](社团展示/05_接住星星.py) | Move with arrow keys; M toggles mouse control |
| 06 | [A Tree, Four Seasons](社团展示/06_四季分形树.py) | Choose a season with 1–4; G regrows the recursive branches |
| 07 | [Letters from the Deep](社团展示/07_深海水母.py) | Place a light for jellyfish to follow; C changes the palette |
| 08 | [Echoes in the Landscape](社团展示/08_山水画卷.py) | D switches day and night; click the lake to add a boat |
| 09 | [Circles Drawing Flowers](社团展示/09_几何绘图仪.py) | Pick a curve with 1–4; C redraws it with the moving pen |
| 10 | [Neon Breakout](社团展示/10_霓虹弹球.py) | Move with the mouse or arrows; A toggles automatic play |

Shared controls for these 10 exhibits: **Space** pause · **R** reset · **H** show/hide instructions · **F11** fullscreen · **Esc** exit the exhibit. When launched from the gallery, closing an exhibit lets you choose another. [Full controls in Chinese →](社团展示/README.md)

### 14 original experiments

![Original works: drawings, geometry and small creative experiments](docs/assets/originals.png)

Previews use runtime screenshots, with two exceptions: Kind Notes illustrates the original messages in a composed layout; the calculator card typesets actual program output.

The original filenames and drawing approaches remain in the repository root. Small scripts make useful starting points for understanding how a picture or an interaction works.

| Theme | Originals / source |
| --- | --- |
| Geometry and lines | 11 [Recursive Circles](2.py) · 12 [Rainbow Square Spiral](import%20turtle.py) · 14 [Arc Leaves](yeizi.py) · 15 [Arc Umbrella](yusan.py) |
| Draw something familiar | 13 [Red Heart](xin.py) · 17 [Random Fractal Tree](分形树.py) · 18 [Doraemon](哆啦A梦.py) |
| Make it move | 16 [Bouncing Balls](下落的小球.py) · 19 [Rotating Yin-Yang](太极.py) · 21 [Analog Clock](时钟.py) · 24 [Pinwheel](风车.py) |
| Everyday ideas and games | 20 [Kind Notes](弹窗.py) · 22 [Mooncake Packing Calculator](测试.py) · 23 [Needle Timing Game](见缝插针.py) |

Original scripts have their own controls. The needle game uses mouse clicks, the calculator accepts text input, and Kind Notes opens several small windows. Use the gallery's stop control to end an original. [Individual controls and editing ideas in Chinese →](docs/CREATIVE_GUIDE.md#14-个创意原作)

## Bring it to your club

Try **fireworks → a growing seasonal tree → audience doodles in the kaleidoscope → a breakout challenge → one small source edit**. H hides the instructions, F11 fills the screen, and Space pauses an interactive exhibit for explanation.

Start by changing the heart's fill color in [xin.py](xin.py), or compare the [original fractal tree](分形树.py) with its [seasonal exhibit](社团展示/06_四季分形树.py) to see how one recursive idea grows into a scene.

For code entry points and small experiments, see the [creative guide](docs/CREATIVE_GUIDE.md). To add a work or report a problem, see [contributing](docs/CONTRIBUTING.md) and [Issues](https://github.com/zjh-b/turtle-gallery/issues). These detailed guides are currently in Chinese.
