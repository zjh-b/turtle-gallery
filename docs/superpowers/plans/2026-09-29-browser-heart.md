# 在线怦然心动实现计划

**目标：** 为作品 26 增加无需安装的互动页面，延续桌面粒子心的层次、双拍心跳和散开再聚合，供社团展示与 GitHub 访客体验。

**实现：** 沿用已有静态网页、原生 Canvas 与模型/绘制/输入分层。方形 640×640 构图采用桌面 aspect 3 的等比布局，浏览器直接生成 1080×1080 PNG。Python 保持标准库运行，网页无新增依赖。

## 本轮范围

- 三种桌面主题，心跳倍率 0.45–1.8，粒子数 420 / 680 / 1000；默认 680、倍率 1、玫瑰主题。随机种子固定 260。
- 首次静态，主动播放后双拍心跳；点击画布或按钮散开并在 3.6 秒后聚合。暂停保持当前画面，重置画面清零时间和散开状态、保留所选参数。
- 减少动态效果随系统偏好初始化并可手动切换；开启后停止动画，点击仅切换静态散开/聚合。关闭后仍暂停，主动操作才恢复动画。
- 单击在松手后触发，拖动超过 12 CSS px、超过 700 ms、离开画布、第二触点、系统取消、失焦、隐藏、resize 都取消候选点击。画布允许页面滚动与双指缩放。
- Space 播放/暂停，Enter 散开，C 换主题，R 重置，仅在画布聚焦且无修饰键时响应。全部控制有标签，状态可读。
- 隐藏页面停止 RAF，返回保留手动暂停状态且不追赶后台时间；每帧最大时间步 0.05 秒，DPR 上限 2，粒子池不因连续点击增长。
- PNG 同步捕获点击保存时的画面到独立画布，包含画面文字，不含页面按钮；下载失败允许重试。脚本或配置失败保留预览和源码。

## 接口与文件责任

1. `社团展示/爱心参数.py`：THEMES、heart_point(angle)、heartbeat(beat_time)、spread_at(age)。从原桌面代码提取，桌面 26 继续调用；不改随机数、运动和画幅结果。
2. `tools/export_gallery.py`：生成 `docs/play/heart-config.json`。schema：version=1、view=[640,640]、themes、densities=[420,680,1000]、default_count=680、max_step=.05、burst_duration=3.6、rate_min=.45、rate_max=1.8、fixtures={heart:[{angle,result}],beat:[{time,result}],spread:[{age,result}]}。仅结果样例四舍五入 9 位小数，避免跨系统末位漂移。
3. `heart-model.js`：导出 heartPoint(angle)、heartbeat(time)、spreadAt(age)，HeartModel(config,{seed=260}={})。字段 theme=0、rate=1、count=680、time=beatTime=0、burstAge=null、particles、stars。step(dt) 拒绝非法/负值并钳制 .05；setTheme/setRate/setCount 拒绝非法值返回 false、有效返回 true。reset() 仅清时间/散开。burst(staticMode=false) 动态设 age=0，静态在 null 和 1.8 间切换。pose() 返回 spread,beat,pulse,turnCos,turnSin,waveSin,waveCos,lightSin,lightCos,groupScale=.9*(1-.16*spread),groupY=-4。
   particles 为深度排序的对象：x,y（已乘13和随机半径）、depth,radius,phase,velocity,angle,phaseSin,phaseCos,scatterX,scatterY；已生成几何保持稳定，点击不分配新粒子。stars 为 78 个 {x,y,radius,phase}，方形范围 x±302、y±298；随机流与密度独立。
4. `heart-view.js`：drawHeart(canvas,model,config)、resizeHeart(canvas)。共用预览和导出；保留星空、柔和氛围、前后轨道、心形轮廓、明暗粒子、中文标题/短句。同一参数和时间产生同一画面。
5. `heart.html/css/js`：复用页面基础样式，ID heart-canvas、heart-fallback、play-controls、play-status、theme、rate、rate-value、density、burst、pause、reset、reduced-motion、save-png、particle-count；默认禁用 controls，成功后启用。
6. `tools/check_heart.py`：使用已有浏览器测试工具，验证桌面、减少动态、生命周期、移动模拟、PNG、失败降级及目录入口。Node 模型测试验证共用公式、确定性、参数、时间步与数量上限；Python 测试验证桌面保持一致。

## 实施与验收

- [x] 模型测试先失败，再提取 Python 公式、导出配置、实现 JS 模型；检查桌面回归及跨平台导出。
- [x] 绘制、页面与控制器接入，真实浏览器操作和实际截图验收；检查最大密度与完全散开时边界。
- [x] 首页、作品卡、在线页面互访接入；README、玩法、维护、路线图、截图与实测记录更新。CI 校验第四份导出配置。
- [x] 独立审查未发现待修复缺陷；Python/Node 全套与受影响浏览器检查通过。

2026-09-30 本地验证：156 项 Python 测试（155 通过，1 项可选字体 GUI 测试跳过）、33 项 Node 模型测试通过；Edge 154 的爱心 8 组、烟花 6 组、万花筒 7 组浏览器检查通过。36 组桌面绘图记录与原实现相等；截图和边界记录见 `docs/benchmarks/heart-m3.json`。PNG 检查比较解码像素，以兼容不同编码方式的压缩差异。

发布沿既有授权提交、推送，并检查对应提交的 CI/Pages 和线上互动、PNG 下载。

**重点复查：** 暂停/后台不会丢失状态；减少动态不会被点击绕过；触摸滚动不触发散开；连续点击不增长粒子；导出捕获当前主题/阶段且不改变播放。实体手机、Safari/Firefox 验收与 M2 十分钟巡展保持待办。
