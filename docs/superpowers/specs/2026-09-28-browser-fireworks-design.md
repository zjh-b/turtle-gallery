# 在线烟花试玩设计

## 目标与范围

沿已授权的 M3 路线，让 GitHub 访客直接在浏览器体验 01 烟花，适合社团展示、鼠标点击、手机触摸与键盘操作。本轮是独立静态试玩页，入口来自画廊首页和 01 作品卡。继续保留 Python 源码与桌面运行入口。

## 体验

- 城市、月夜与湖面倒影沿用桌面作品的视觉主题；四种花型、配色选择、发射一束、烟花齐放、自动表演、暂停和重置。
- 初次打开显示静态完整烟花，点击或按钮启动；自动表演默认关闭。键盘操作只在画布焦点内生效，Space 暂停，Enter 发射，F 齐放，A 自动，R 重置。
- 点击或触摸松手后发射，手指滑动、取消、第二触点、移出画布不发射；页面保留正常纵向滚动。
- 提供减少动态效果开关，尊重系统偏好：停用自动与动画，点击直接生成静态绽放。页面隐藏 / pagehide 停止帧循环，返回时按原有运行状态继续；不会补跑离开期间的时间。
- 小屏使用适合触摸的按钮和可完整看到的舞台；高 DPI 绘图上限为 2，粒子上限 600、火箭与倒影上限各 8。
- Canvas 或脚本不可用时提供现有静态预览和桌面入口，状态说明位于 HTML 中。

## 技术与接口

无浏览器第三方库，无构建流程。Canvas 2D，ES modules，requestAnimationFrame，Pointer Events。Node 内置测试仅用于维护，Python 运行仍只需标准库。

`社团展示/烟花参数.py` 为常量、粒子初速和阻力轨迹公式的共用来源；桌面作品调用此模块。`tools/export_gallery.py` 同时生成 `docs/play/fireworks-config.json`，包含参数及固定公式样例，CI 检查生成文件一致性。浏览器实现用这些样例验证公式，随机数不宣称与 Python 逐帧相同。

`docs/play/fireworks-model.js` 导出 `FireworksModel` 与 `location(particle, age, config)`。模型构造器 `(config, {seed=22}={})`；字段 `time, particles, rockets, blooms, kind, palette, auto`，palette=-1 表示随花型。`reset()` 恢复初始静态三束、关闭自动，`clear()` 清除动态对象，`launch(x,y,kind=this.kind)`、`burst(x,y,kind=this.kind,age=0)`、`finale()`、`step(dt)`；坐标采用桌面 x 向右、y 向上，1020×580。粒子字段与 Python 相同，火箭记录发射时配色。

`fireworks-view.js` 负责背景与模型绘制。`fireworks.js` 负责 DOM、状态、输入与帧调度。画布在所有屏宽下保持同一逻辑构图，输入依据实际显示矩形换算，桌面用横屏，窄屏舞台可以保持横屏完整构图。模块使用 `.js` 扩展名兼容 Windows 本地 HTTP 服务的 MIME 类型；同目录 `package.json` 仅声明 Node 测试导入时使用 ES module，无第三方依赖。

## 验证与边界

Node 模型测试：固定样例、零时间步、连续齐放上限、粒子消退、种子可复现。浏览器测试：点击、键盘、配色、暂停、重置、减少动态、隐藏页面、resize / DPI、触摸滑动与取消、多点触摸、网络失败降级；检查桌面和移动宽度截图。模拟移动测试不宣称真实手机验收完成。

不增加音频、GIF / MP4 导出或其他作品浏览器实现。M2 十分钟巡展与视频待办保持原状态。
