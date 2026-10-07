# 一起创作海龟画廊

[返回画廊](../README.md) · [创作指南](CREATIVE_GUIDE.md) · [升级路线](ROADMAP.md)

欢迎带来新的绘画、动画和小游戏，也欢迎改进现有作品的交互、性能、文字说明和其他系统上的体验。一个能被同学看懂、运行并修改的小创意，就值得展示。

## 本地运行

使用带 Tkinter 的 Python 3.9+，在仓库根目录运行：

```bash
python run.py --check
python run.py --list
python run.py
```

作品运行仅依赖标准库。预览图片属于文档和画廊缩略图；场景中的图形应由代码绘制。

## 改进已有作品

先阅读对应作品与 [创作指南](CREATIVE_GUIDE.md)，保持改动聚焦。根目录中的原作也可以直接优化画面和玩法，保留作品主题、原文件名与编号；早期版本通过 Git 历史查看。已有九份原作接入共用舞台，最近的 [11 圆阵、12 螺旋与 18 头像](ORIGINAL_STUDIES.md) 可作为几何缓存与局部动画的参考。使用定时更新、限制互动对象数量，并用 `if __name__ == "__main__"` 保护运行入口，避免导入时打开窗口。

提交时说明具体行为，例如“鱼群接近窗口边缘时转向更平缓”，并给出修改前后的截图或简短运行片段。新素材如果不是你制作的，请附上来源与使用依据。

## 添加一个作品

1. 先完成一个可以单独运行的 `.py` 文件，给出明确的作品名和操作方式。
2. 互动展品参考 `社团展示/` 下已有结构，复用 `舞台.py` 的窗口、动画与通用按键。
3. 在 [作品目录.py](../社团展示/作品目录.py) 中登记标题、编号、分类、文件位置和简介。使用共用舞台的场景需填写 `entry_class`，让基础测试与媒体工具找到场景类；升级原作继续保留 `collection="original"`，填写场景类不会改变作品集或自动开启创作面板、巡展。确保 `python run.py --list` 与菜单都能找到它。
4. 添加桌面与网页需要的真实运行截图，执行 `python tools/export_gallery.py` 更新网页作品目录，再运行 `python tools/check_catalog.py` 检查登记与资源；更新中英文 README 的介绍及操作说明。
5. 实际打开作品，确认输入、退出与从画廊再次启动的流程。

动画尽量使用定时回调，并按经过的时间更新位置。粒子、笔画和其他持续增加的对象需要数量上限；这样长时间投影展示也能维持稳定的响应。

25、26 已接入共用创作面板。扩展时参考 [创作指南](CREATION_GUIDE.md)，为作品实现 `get_parameters()` / `apply_parameters()`，先验证完整参数再改变场景状态；配方中的种子使用场景独立的随机数生成器。登记 `creation=True` 前，确认面板、预设、重播和配方恢复均可用。个人配方默认保存在被 Git 忽略的 `creations/`；精选示例可放入 `examples/recipes/`。

两件作品的画幅参数为 `aspect`：`0` 原始画幅（默认）、`1` 横屏 16:9、`2` 竖屏 9:16、`3` 方形 1:1。切换画幅应调整主体、背景与题字的布局；在创作面板切换配色预设时保留当前画幅。题字安全区参考线距四边各 6%，仅用于所选比例的预览，不写入配方，也不导出。

配方保持 `version: 1`，当前 `scene_version: 2`。加载作品版本 1 时，先确认参数恰好符合旧版结构，再补上 `aspect: 0` 并验证全部值；旧文件含 `aspect`、未知参数或缺失旧参数时必须拒绝。新版文件必须提供完整参数，包括有效画幅。再次保存统一写作品版本 2。保留 [25-blue-night.json](../examples/recipes/25-blue-night.json) 与 [26-champagne.json](../examples/recipes/26-champagne.json) 的旧版结构作为迁移样例；新版示例为 [25-portrait-night.json](../examples/recipes/25-portrait-night.json) 和 [26-square-heart.json](../examples/recipes/26-square-heart.json)。

画幅绘制复用 `Stage.artwork`，通过 `Paint(stage.artwork, tag)` 使用画幅自己的逻辑尺寸、缩放和平移；舞台工具栏仍使用舞台坐标。`artwork.bounds` 是 Turtle 物理坐标中的 `(left, top, right, bottom)`，预览遮罩与 PNG 裁剪共用此范围。鼠标坐标先经 `artwork.point(x, y)` 转为画幅坐标，再用 `artwork.in_scene(x, y)` 判断，避免画幅外留白触发作品互动。

`Paint.transform(scale=1, x=0, y=0)` 设置当前画笔的一致缩放与平移，参数使用所属视口的逻辑坐标。它替换当前变换，不累积；`begin()` 会恢复默认变换，绘完局部图形后也可调用 `transform()` 恢复。按画幅布局时保留场景的独立随机序列，避免仅切换比例就重新生成无关几何。

25、26、27 已登记 `autoplay=True`，可参与[自动巡展](EXHIBITION_GUIDE.md)。扩展前先确认作品无人操作时也能展示完整内容，并使用共用 `Stage.run()`。实际检查自动切换、点击或键盘接管、继续计时、窗口关闭和画廊关闭。Canvas 按钮涉及销毁窗口时，使用 `after_idle()` 在当前鼠标事件处理完后执行；读取完旧进程输出，再切换到下一件。

PNG 导出是独立可选能力，依赖在 [requirements-export.txt](../requirements-export.txt) 中声明。默认的“当前窗口像素”沿用窗口捕获：固定画幅裁出严格对应 16:9、9:16 或 1:1 的图片，原始画幅沿用原有范围。捕获前临时隐藏安全区参考线，成功或失败后都应恢复其预览状态。25、26 的固定画幅另外支持 1080 / 2160 高清重绘，具体输出尺寸见 [导出指南](EXHIBITION_GUIDE.md#png-保存什么)。导出尺寸属于面板状态，不加入配方参数；原始画幅不能进入高清流程。用户图片默认保存在被 Git 忽略的 `exports/`。

高清流程位于 [高清导出.py](../社团展示/高清导出.py)：主线程在文件对话框前调用 `freeze_artwork(app)`，记录当前场景的几何、参数、动画进度与字体缩放；它不推进动画、不重置随机数，也不修改正在运行的场景。`ExportJob(snapshot, path, resolution)` 在后台执行 `render_snapshot()` 与保存，通过 `poll()` 回传结果，工作线程不得调用 Tk。扩展支持作品时，要检查场景的 `frame(0)` 是否会修改共享对象；当前的场景副本与绘图记录器只针对 25、26 的行为实现。

[离屏绘制.py](../社团展示/离屏绘制.py) 提供可独立测试的 `render_commands(commands, view, size, *, font_paths, font_scale=4/3, cancel=None)`，接收按顺序排列的图形指令，在目标尺寸的两倍分辨率绘制后缩小。它不需要 Tk 窗口或屏幕捕获，Pillow 在实际绘制时才导入。应用入口目前支持 Windows，并检查微软雅黑字体；Pillow 与 Tk 的文字和抗锯齿差异不应被描述为逐像素一致，也不能把最终 PNG 宣称为 SVG 矢量文件。

高清 PNG 保存 `Recipe`、`Animation` 与 `Resolution` 元数据，当前 UI 仍只支持载入 JSON 配方。面板关闭和取消按钮都应通知后台任务取消，绘制和保存都需要检查取消信号。保存经临时文件完成后原子替换目标；失败或取消应清理临时文件并保留已有目标。改动保存流程后，检查这些行为及面板关闭后没有遗留 Tk 回调；改动截图边界后，实际检查所有画幅、窗口尺寸、面板遮挡、隐藏说明与最小化提示。

## 更新展示图片

[tools/render_media.py](../tools/render_media.py) 用于生成 README 的预览素材。这是可选的维护工具，所需 Pillow 与作品运行依赖分开记录在 [requirements-media.txt](../requirements-media.txt)。在 Windows 桌面环境、仓库根目录执行：

```bash
python -m pip install -r requirements-media.txt
python tools/render_media.py --exhibits 2 6 9
python tools/render_media.py --original-ids 11 12 18 --compose-originals
python tools/render_media.py --originals --gif --compose
python tools/render_media.py --social --compose
python tools/render_media.py --creator
python tools/render_media.py --aspects
python tools/render_media.py --hd
```

`--exhibits` 按编号重新运行互动作品，更新桌面预览、两种卡片缩略图和网页展品图片；调整已有作品画面后用它同步画廊，避免预览仍显示旧画面。例如上面的命令只刷新 02、06、09。若涉及 README 动画中的作品，再运行 `python tools/render_media.py --gif` 更新动画片段。

`--original-ids` 只复拍指定原作，`--compose-originals` 用现有原作截图更新原作总览；例如上面的命令刷新 11、12、18 并重排总览。已登记 `entry_class` 的原作由媒体工具导入、创建场景并截取实际运行画面；因此模块导入时应不创建窗口，窗口由场景实例负责。[圆阵、螺旋与头像升级记录 →](ORIGINAL_STUDIES.md)

抓取运行画面需要可用的桌面显示；仅重新排版已有截图时可使用 `python tools/render_media.py --compose`。更新后检查生成图片中的文字、构图和 GIF 播放效果。预览中的温柔便签为原文排版示意，月饼计算展示实际程序输出；其他原作使用运行截图。

## 维护在线画廊

网页位于 `docs/`，使用 HTML、CSS 和 JavaScript，作品数据由共用目录导出。无需安装前端工具，在仓库根目录执行：

```bash
python tools/export_gallery.py
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

用浏览器访问 `http://127.0.0.1:8000`，检查搜索、分类、手机宽度、预览图、源码链接和启动命令复制，以及首页和 01、03、26 作品卡上的试玩入口。网页通过 HTTP 加载 `gallery.json`，请使用本地服务器预览。GitHub Pages 使用 `main` 分支的 `/docs` 目录。

导出工具统一生成四份数据：`docs/gallery.json`、`docs/play/fireworks-config.json`、`docs/play/kaleidoscope-config.json` 和 `docs/play/heart-config.json`。修改共用目录或绘图参数后，重新导出并提交相应变化；生成文件不直接手改。

### 检查目录与资源

```bash
python tools/check_catalog.py
```

这是只读的标准库检查，不打开窗口、不运行作品，也不重写导出文件。成功返回 0；失败返回 1，并列出作品编号、字段和资源路径。可从任意工作目录使用脚本的绝对路径运行。

检查覆盖：

- `id`、规范的两位 `number` 与源文件路径唯一，编号逐条对应；当前网页预览使用两位编号，支持 01–99。
- 标题等必需字段、分类、标签与功能开关的类型正确。
- 源 `.py` 文件、目录登记的桌面预览、网页 `assets/exhibits` / `assets/originals` 预览与 `web_play` 在线页面存在。路径必须留在对应资源目录内，并使用大小写完全一致的正斜杠相对路径。
- 预览有 PNG 文件头和非零尺寸；已发布的 `docs/gallery.json` 与源目录投影一致，包括顺序、说明、预览、源码及在线链接。

例如把 01 与 03 的 `number` 交换、忘记提交截图或修改标题却没有重新导出，都会在检查中报错。先修正登记和资源，若提示 JSON 与源数据不同，再运行 `python tools/export_gallery.py` 并复查。GitHub 的六组 Windows / Linux Python 检查会在重新生成数据前运行此命令，避免重写文件掩盖目录漂移。

对应回归测试为 `tests/test_catalog_integrity.py`，使用临时目录模拟丢失资源与错误登记。PNG 文件头检查不能判断截图是否过期、画面是否正确，也不验证整个 PNG 的解码；视觉验收和浏览器交互检查仍需单独完成。

### 维护在线烟花

本地入口为 `http://127.0.0.1:8000/play/fireworks.html`，用户玩法见[在线烟花说明](BROWSER_PLAY.md)。页面采用原生 JavaScript 模块和 Canvas，不需要 `npm install`、构建步骤或浏览器第三方库。配置通过同源请求加载，请勿直接用 `file://` 打开。

[烟花参数.py](../社团展示/烟花参数.py) 是桌面烟花常量、粒子初速和阻力轨迹公式的共同来源。修改参数后运行 `python tools/export_gallery.py`，检查四份生成数据中的相应变化。`docs/play/fireworks-config.json` 包含固定公式样例，供浏览器模型测试比较；随机分布和绘制细节无需与 Python 逐帧一致。

`docs/play/` 中的 `fireworks-model.js` 管理状态与运动，`fireworks-view.js` 绘制画面，`fireworks.js` 管理输入和播放状态。该目录的 `package.json` 仅声明模块类型。使用 Node 24 运行内置测试，无需安装测试包：

```bash
node --test tests/web/*.test.mjs
```

可选的真实浏览器检查独立于 Python 作品运行依赖。Windows 默认使用已安装的 Edge，工具自行启动临时本地服务器；截图和结果写入 `.work/browser/`：

```bash
python -m pip install -r requirements-browser.txt
python tools/check_browser.py
```

也可安装 Playwright 管理的 Chromium 后运行：

```bash
python -m playwright install chromium
python tools/check_browser.py --browser chromium
```

改动后检查点击与键盘、配色、暂停和重置、减少动态效果、后台停止绘制、尺寸与 DPI 变化，以及配置加载失败时的静态预览。触摸检查需覆盖滑动、取消、多点触摸和移出画布，避免滚动时误发射。自动检查包含移动设备模拟；手机实机报告应另记设备、系统、浏览器版本和实际操作结果。

### 维护在线万花筒

本地入口为 `http://127.0.0.1:8000/play/kaleidoscope.html`，用户玩法见[一笔生花说明](BROWSER_PLAY.md#03-一笔生花)。页面使用原生 JavaScript 模块和 Canvas，无需 `npm install`、构建步骤或第三方浏览器运行库；通过上面的 HTTP 服务器预览。

[万花筒参数.py](../社团展示/万花筒参数.py) 提供桌面与网页共用的画幅、半径、对称份数范围和 `mirror_points(points, count)` 旋转镜像公式。修改后执行 `python tools/export_gallery.py`，更新四份生成数据中的相应变化。`docs/play/kaleidoscope-config.json` 包含数量上限和固定公式样例，供 JavaScript 模型与 Python 结果比较；调整公式时也应验证桌面作品原有的镜像坐标。

`docs/play/kaleidoscope-model.js` 管理笔画、示例、参数与数量上限，`kaleidoscope-view.js` 共用同一绘制函数生成预览和 PNG，`kaleidoscope.js` 管理绘画模式、输入与下载。使用 Node 24 的内置测试检查全部浏览器模型：

```bash
node --test tests/web/*.test.mjs
```

可选浏览器检查沿用 `requirements-browser.txt`，工具自行启动临时本地服务器，截图、PNG 与结果写入 `.work/kaleidoscope/`。Windows 默认使用已安装的 Edge：

```bash
python -m pip install -r requirements-browser.txt
python tools/check_kaleidoscope.py
```

也可安装 Playwright 管理的 Chromium 后指定浏览器：

```bash
python -m playwright install chromium
python tools/check_kaleidoscope.py --browser chromium
```

检查首次静态示例、3–16 份对称、三种配色、整笔撤销，以及 60 笔、合计 2400 点、每笔 400 点的上限。进入手绘只清除示例，重新进入时保留已有手绘；“清空”和“换回示例”直接替换当前作品。确认圆形越界、第二触点、系统取消、失焦和页面隐藏会取消当前未完成的一笔，已完成笔迹保留；退出绘画模式后恢复滚动与缩放。下载的 PNG 应为 1080 × 1080，含作品和边框，并检查实际图像内容。还应检查键盘操作、窄屏布局、01 / 03 / 26 互访入口，以及无脚本或配置加载失败时的静态预览与源码入口。

移动设备模拟仅用于复现触摸流程，不能作为实体手机验收；实机记录应包含设备、系统、浏览器版本，以及绘画、滚动、横竖屏切换和后台返回的结果。

绘图层为每个画布缓存一张已完成笔迹底图；当前一笔单独叠加。已完成的点列按不可变数据使用，修改参数、完成或撤销笔画、清空、换回示例、调整画布尺寸时更新缓存。浏览器检查的 `render-cache` 组比较缓存与新画布的图像结果，并确认拖动时不会再次逐点描绘全部历史。像素比较使用 PNG 快照，避免频繁读取 `getImageData` 触发浏览器绘制方式变化。

### 维护在线粒子爱心

本地入口为 `http://127.0.0.1:8000/play/heart.html`，玩法见[怦然心动说明](BROWSER_PLAY.md#26-怦然心动)。沿用原生 JavaScript 模块与 Canvas，通过 HTTP 加载配置，无需安装浏览器运行库或执行构建。

[爱心参数.py](../社团展示/爱心参数.py) 提供三套 `THEMES` 及 `heart_point(angle)`、`heartbeat(beat_time)`、`spread_at(age)` 公式，桌面 26 继续调用这些函数。`python tools/export_gallery.py` 将配置与固定公式样例写入 `docs/play/heart-config.json`，同时检查四份生成数据。Node 测试比较 Python 导出的公式结果；浏览器使用自己的确定性随机序列，不能由公式一致推出与 Python 的粒子位置或逐帧像素完全一致。

`docs/play/heart-model.js` 管理时间、心跳、散开阶段与固定粒子池，校验三种主题、420 / 680 / 1000 的密度和 0.45–1.8 的速度；`heart-view.js` 共用 `drawHeart()` 绘制预览与 PNG；`heart.js` 管理播放、输入、减少动态与下载。改动公式和参数时同时检查桌面作品回归与全部浏览器模型：

```bash
python -m unittest discover -s tests -p test_heart.py -v
node --test tests/web/*.test.mjs
```

可选浏览器检查复用 `requirements-browser.txt`。检查脚本自动启动并关闭临时本地服务器；Windows 默认使用已安装的 Edge，输出保存在 `.work/heart/`：

```bash
python -m pip install -r requirements-browser.txt
python tools/check_heart.py
```

也可使用 Playwright 管理的 Chromium：

```bash
python -m playwright install chromium
python tools/check_heart.py --browser chromium
```

脚本分为 `desktop`、`reduced-motion`、`lifecycle`、`inputs`、`mobile`、`export`、`fallback`、`gallery` 八组。默认运行全部；可用 `--only export lifecycle` 定位相关问题，用 `--output .work/heart-review` 指定输出目录。`results.json` 记录各组结果、耗时和浏览器版本，截图与下载图片用于核对实际画面。局部分组结果不能代替本轮完整验收。

检查默认静态、主动播放、3.6 秒散开再聚合、连续点击后粒子数量保持不变，以及暂停时画面不变。重置应暂停并保留主题、速度和密度；改变参数时保留动画阶段。减少动态时点击只切换静态构图，关闭后仍暂停；隐藏和离开页面时停止动画回调，恢复后不追赶后台时间。每步时间上限为 0.05 秒，画布 DPR 上限为 2。

画布聚焦时检查无修饰键的 Enter、Space、C、R，并确认快捷键不会干扰其他控件。点击在松手后触发，超过 12 CSS 像素的拖动、超过 700 毫秒的长按、离开画布、第二触点、取消、失焦、隐藏或 resize 都应取消候选点击；手机滑动和双指缩放仍可使用。

PNG 应为 1080 × 1080，包含当前主题、动画阶段与题字，不含网页控件。保存先同步绘入独立画布再异步编码，不能暂停或重置当前模型；检查下载失败后能重试。另需检查最高密度与完全散开时的画面边界、窄屏布局、三个在线作品互访，以及无脚本、配置失败时的预览和源码入口。实测记录放在 [heart-m3.json](benchmarks/heart-m3.json)，真实浏览器截图放在 [browser-heart.png](assets/browser-heart.png)。移动模拟不能替代实体手机验收；Safari、Firefox 与实体手机结果应分别记录。

## 维护首页筛选与分享

`docs/gallery.js` 从生成的 `gallery.json` 读取作品；“在线试玩”依据 `web_play` 自动筛选和计数，新增网页作品后无需再维护一份编号列表。分类与搜索分别使用 URL 的 `collection` 和 `q`，不依赖账号或本地存储。

支持 `all`、`romantic`、`interactive`、`original`、`online`；未知分类回退到全部，搜索最多 100 个字符。分类切换新增历史记录，输入搜索替换当前记录。默认值从生成的链接中省略，其他 URL 参数保留；分享链接定位到 `#gallery`。精选作品也提供可在新标签打开的真实筛选链接。

安装 `requirements-browser.txt` 后运行：

```bash
python tools/check_gallery.py
# 使用 Playwright Chromium 时先执行 python -m playwright install chromium
python tools/check_gallery.py --browser chromium
```

检查覆盖合集数量、搜索与空态、深链接、刷新与前进后退、分享成功与剪贴板拒绝、触屏模拟和键盘操作。支持 `--only` 选择分组，`--output` 指定截图和 JSON 记录目录（默认 `.work/gallery`）。手机宽度检查不能替代手机实机验收。

## 验证改动

提交前运行环境检查与现有测试，再直接体验改动涉及的作品：

```bash
python run.py --check
python tools/check_catalog.py
python -m unittest discover -s tests -v
```

[自动检查流程](../.github/workflows/checks.yml) 使用同一组命令，并检查 Python 文件能否编译，以及 `docs/gallery.json`、`docs/play/fireworks-config.json`、`docs/play/kaleidoscope-config.json`、`docs/play/heart-config.json` 是否与源数据一致。独立的 Node 24 任务通过 `node --test tests/web/*.test.mjs` 运行烟花、万花筒与爱心模型测试。Python 测试使用模拟窗口检查逻辑，仍需实际观察画面和操作；环境检查本身不会打开 GUI。

常规六组系统 / Python 检查保持仅标准库；另有一个 Windows 任务安装可选 Pillow，验证 PNG 编码、图形重绘、快照、元数据和原子保存。新增导出逻辑应同时在有、无 Pillow 的环境检查，不能让普通作品因缺少可选依赖而无法运行。

高清导出的窗口无关检查分别位于 `test_redraw.py`（快照、尺寸与后台任务）、`test_raster.py`（图形渲染与可选依赖）和 `test_hires_ui.py`（对话框前固定画面、取消与面板关闭）。可用以下命令独立运行；涉及 Pillow 或字体的检查需要相应可选依赖，不能用无窗口测试替代真实窗口的视觉检查。

```bash
python -m unittest discover -s tests -p test_redraw.py -v
python -m unittest discover -s tests -p test_raster.py -v
python -m unittest discover -s tests -p test_hires_ui.py -v
```

画幅题字另有可选的真实 Tk 字体边界检查，常规无窗口测试会跳过它。在可用桌面上用 PowerShell 执行以下命令，检查两件作品在最小窗口和较大窗口中的 6% 安全区与文字间距：

```powershell
$env:TURTLE_GALLERY_GUI_TESTS = '1'
python -m unittest discover -s tests -p test_aspect.py -v
Remove-Item Env:TURTLE_GALLERY_GUI_TESTS
```

若改动共用舞台或画廊，检查不同分类中的作品、小窗口布局、作品结束后返回画廊，以及连续启动不同作品。14 款互动展品及已接入舞台的原作 11、12、14、15、16、18、19、21、24，均需验证暂停、重置、说明开关、全屏和 Esc 退出；其余原作按各自操作验证。几何重播、分支选择和角色局部动画可参考[圆阵、螺旋与头像升级记录](ORIGINAL_STUDIES.md)，运动与时间更新可参考[彩球、太极与时钟升级记录](ORIGINAL_MOTION.md)。

项目在 Windows 上开发。若在 macOS / Linux 验证或修复了问题，请写明系统、Python / Tk 版本和实测结果，帮助补齐平台信息。

## 报告问题或提一个想法

在 [Issues](https://github.com/zjh-b/turtle-gallery/issues) 中描述：

- 使用的系统、Python 版本和启动命令。
- 作品编号、触发问题的操作与预期结果。
- 终端中的完整报错；画面问题可附截图。

提出新创意时，可以描述观众能看到什么、能做什么，以及背后想讲解的一个编程概念。[升级路线](ROADMAP.md) 列出了可参与的方向和阶段完成标准；创意表单也支持针对已有作品提出改进。尽量写出一个具体过程，例如“拖动改变风向，松手后花丝缓缓停下”，以及怎样判断完成。

每次改进聚焦一个能体验的目标，附相同构图下的对照或操作记录。参数、快捷键或支持范围改变时，同步更新作品说明；完成路线图中的任务后，更新对应勾选状态。提交 Pull Request 时写清改动、验证方式和仍需检查的地方即可。
