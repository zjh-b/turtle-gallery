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

先阅读对应作品与 [创作指南](CREATIVE_GUIDE.md)，保持改动聚焦。根目录中的原作保留早期创作的画法和文件名；修复兼容问题时尽量小改，若要重新设计视觉或玩法，适合另做一个作品。

提交时说明具体行为，例如“鱼群接近窗口边缘时转向更平缓”，并给出修改前后的截图或简短运行片段。新素材如果不是你制作的，请附上来源与使用依据。

## 添加一个作品

1. 先完成一个可以单独运行的 `.py` 文件，给出明确的作品名和操作方式。
2. 互动展品参考 `社团展示/` 下已有结构，复用 `舞台.py` 的窗口、动画与通用按键。
3. 在 [作品目录.py](../社团展示/作品目录.py) 中登记标题、编号、分类、文件位置和简介。互动作品还需填写 `entry_class`，让基础测试与媒体工具找到场景类。确保 `python run.py --list` 与菜单都能找到它。
4. 添加真实运行截图，执行 `python tools/export_gallery.py` 更新网页作品目录，并更新中英文 README 的介绍及操作说明。
5. 实际打开作品，确认输入、退出与从画廊再次启动的流程。

动画尽量使用定时回调，并按经过的时间更新位置。粒子、笔画和其他持续增加的对象需要数量上限；这样长时间投影展示也能维持稳定的响应。

25、26 已接入共用创作面板。扩展时参考 [创作指南](CREATION_GUIDE.md)，为作品实现 `get_parameters()` / `apply_parameters()`，先验证完整参数再改变场景状态；配方中的种子使用场景独立的随机数生成器。登记 `creation=True` 前，确认面板、预设、重播和配方恢复均可用。个人配方默认保存在被 Git 忽略的 `creations/`；精选示例可放入 `examples/recipes/`。

25、26、27 已登记 `autoplay=True`，可参与[自动巡展](EXHIBITION_GUIDE.md)。扩展前先确认作品无人操作时也能展示完整内容，并使用共用 `Stage.run()`。实际检查自动切换、点击或键盘接管、继续计时、窗口关闭和画廊关闭。Canvas 按钮涉及销毁窗口时，使用 `after_idle()` 在当前鼠标事件处理完后执行；读取完旧进程输出，再切换到下一件。

PNG 导出是独立可选能力，依赖在 [requirements-export.txt](../requirements-export.txt) 中声明。改动截图边界后，实际检查窗口尺寸、面板遮挡、隐藏说明与最小化提示；改动保存流程后，检查取消和写入失败是否保留旧文件。用户图片默认保存在被 Git 忽略的 `exports/`。

## 更新展示图片

[tools/render_media.py](../tools/render_media.py) 用于生成 README 的预览素材。这是可选的维护工具，所需 Pillow 与作品运行依赖分开记录在 [requirements-media.txt](../requirements-media.txt)。在 Windows 桌面环境、仓库根目录执行：

```bash
python -m pip install -r requirements-media.txt
python tools/render_media.py --originals --gif --compose
python tools/render_media.py --social --compose
python tools/render_media.py --creator
```

抓取运行画面需要可用的桌面显示；仅重新排版已有截图时可使用 `python tools/render_media.py --compose`。更新后检查生成图片中的文字、构图和 GIF 播放效果。预览中的温柔便签为原文排版示意，月饼计算展示实际程序输出；其他原作使用运行截图。

## 维护在线画廊

网页位于 `docs/`，使用 HTML、CSS 和 JavaScript，作品数据由共用目录导出。无需安装前端工具，在仓库根目录执行：

```bash
python tools/export_gallery.py
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

用浏览器访问 `http://127.0.0.1:8000`，检查搜索、分类、手机宽度、预览图、源码链接和启动命令复制。网页通过 HTTP 加载 `gallery.json`，请使用本地服务器预览。GitHub Pages 使用 `main` 分支的 `/docs` 目录。

## 验证改动

提交前运行环境检查与现有测试，再直接体验改动涉及的作品：

```bash
python run.py --check
python -m unittest discover -s tests -v
```

[自动检查流程](../.github/workflows/checks.yml) 使用同一组命令，并检查 Python 文件能否编译、网页目录是否与源目录一致。测试使用模拟窗口检查逻辑，仍需实际观察画面和操作；环境检查本身不会打开 GUI。

常规六组系统 / Python 检查保持仅标准库；另有一个 Windows 任务安装可选 Pillow，验证 PNG 编码、元数据和原子保存。新增导出逻辑应同时在有、无 Pillow 的环境检查，不能让普通作品因缺少可选依赖而无法运行。

若改动共用舞台或画廊，检查不同分类中的作品、小窗口布局、作品结束后返回画廊，以及连续启动不同作品。涉及 14 款互动展品时，验证暂停、重置、说明开关、全屏和 Esc 退出；原作按各自操作验证。

项目在 Windows 上开发。若在 macOS / Linux 验证或修复了问题，请写明系统、Python / Tk 版本和实测结果，帮助补齐平台信息。

## 报告问题或提一个想法

在 [Issues](https://github.com/zjh-b/turtle-gallery/issues) 中描述：

- 使用的系统、Python 版本和启动命令。
- 作品编号、触发问题的操作与预期结果。
- 终端中的完整报错；画面问题可附截图。

提出新创意时，可以描述观众能看到什么、能做什么，以及背后想讲解的一个编程概念。[升级路线](ROADMAP.md) 列出了可参与的方向和阶段完成标准；创意表单也支持针对已有作品提出改进。尽量写出一个具体过程，例如“拖动改变风向，松手后花丝缓缓停下”，以及怎样判断完成。

每次改进聚焦一个能体验的目标，附相同构图下的对照或操作记录。参数、快捷键或支持范围改变时，同步更新作品说明；完成路线图中的任务后，更新对应勾选状态。提交 Pull Request 时写清改动、验证方式和仍需检查的地方即可。
