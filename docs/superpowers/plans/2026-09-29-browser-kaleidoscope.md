# 在线万花筒实现计划

## 设计与范围

沿已授权的 M3 路线增加 03 在线创作。旋转、镜像与颜色沿用桌面作品；浏览器版先做静态手绘，提供 3–16 份对称、三种配色、示例花瓣、按整笔撤销、清空和 1080×1080 PNG 下载。改变份数或配色重新呈现已有笔迹。无持续自动动画，无第三方浏览器依赖，无新增 Python 运行依赖。

初次呈现静态示例。用户主动点击“开始手绘”后清除示例并进入空白画布（保留自己已有的手绘）；绘画模式使用 `touch-action: none`，退出后允许滚动与缩放。触摸取消、越界、失焦、隐藏页面、第二触点取消当前未完成笔画，不连接返回后的坐标；已完成笔画保留。鼠标 / 触笔 / 单指均支持。键盘可操作参数与全部按钮；示例按钮让不用指针的访客也能组合图案和保存。

画幅 560×560，半径 246；DPR 上限 2。最多 60 笔、总计 2400 点、每笔最多 400 点，达到上限提示撤销或清空，禁止无声丢弃旧笔迹。撤销单位为完整笔画。PNG 绘制到独立 1080×1080 画布，保留边框和作品，排除光标与操作提示；通过浏览器下载，不上传图片。

## 文件和接口

- `社团展示/万花筒参数.py`：VIEW=(560,560)、RADIUS=246、MIN_COUNT=3、MAX_COUNT=16，以及 `mirror_points(points, count)` 返回每个旋转镜像的点列。桌面 `add_ink` 调用此纯公式，保留其坐标缩放与线条规则。
- `tools/export_gallery.py`：额外生成 `docs/play/kaleidoscope-config.json`，含 `{version:1,view:[560,560],radius:246,min_count:3,max_count:16,max_strokes:60,max_points:2400,max_stroke_points:400,fixtures:[{points,count,result}]}`。
- `kaleidoscope-model.js`：`KaleidoscopeModel(config)`；字段 count=10,palette=0,strokes=[],current=null,isExample=true；方法 begin(x,y), move(x,y), end(), cancel(), undo(), clear(), example(), setCount(n), setPalette(n)。begin/move 返回 bool 是否接纳，end 返回 bool 是否完成可撤销笔画；拒绝越界与非有限坐标，`limitReached` 指示限额。export `mirrorPoints(points,count)`。stroke 为 `[[x,y],...]`，颜色由序号及当前 palette 决定。example() 放入可见花瓣点列、isExample=true；用户开始手绘 clear()，isExample=false。
- `kaleidoscope-view.js`：绘制边框、当前及已完成笔迹、三种配色；同函数用于预览与 PNG。
- `kaleidoscope.html/css/js`：沿用现有试玩布局 / 控制样式，新的方形画布和输入流程，不改动烟花控制逻辑。
- `tools/check_kaleidoscope.py`：复用现有浏览器检查的临时服务器与工具；检查画笔、撤销、参数、上限、PNG、手机触摸及异常取消、无 JS / 配置缺失降级。

## 步骤与验证

- [x] 先写模型测试并观察失败，提取 Python 公式、导出样例、实现 JS 模型；验证桌面原有镜像坐标不变。
- [x] 完成页面、绘制与事件管理；验收真实浏览器操作及 PNG 文件尺寸 / 非空像素。
- [x] 首页与作品卡接入 03；01 / 03 页面提供互相访问入口；更新指南、截图、路线图。
- [x] CI 检查第三份生成配置，运行两类 Node 模型测试；本地 Python / 浏览器回归及独立审查。

本地验证：153 项 Python 测试（152 通过、1 项可选桌面字体检查跳过），24 项 Node 模型测试通过，Edge 154 的万花筒 7 组、烟花 6 组浏览器检查通过。首页原有搜索、筛选、动图和手机模拟布局回归通过。真实截图与范围见 `docs/benchmarks/kaleidoscope-m3.json`。

独立审查发现大量历史笔迹的重复绘制开销，已改为每个画布缓存一张底图，仅叠加当前笔，并忽略未被接纳的微小移动。新增缓存与全新画布图像一致性检查，覆盖参数、同笔数替换、取消、撤销、尺寸与示例变化。完成笔迹按不可变点列维护。

首次远端 Linux 检查发现三角函数结果的末位浮点差异造成配置文本不同，已将导出样例坐标统一为 9 位小数，保持实际绘图公式精度不变。新增正负浮点扰动的导出一致性回归测试。

发布按既有授权提交并推送，检查对应提交的 CI、Pages 与正式网址。移动浏览器模拟不宣称实体手机验收完成；26 爱心、视频导出与 M2 十分钟巡展仍保持待办。
