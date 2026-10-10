# 画廊观看入口与日常更新计划

> **For agentic workers:** 使用 superpowers:executing-plans 按下列任务实施与验收。

**Goal:** 让访客在画廊观看真实演示、找到作者账号，并为每天约一小时的持续更新建立明确产出。

**Architecture:** 沿用 GitHub Pages 静态画廊，在现有沉浸艺术区域复用已经发布的 MP4 和封面，添加原生播放器与 WebVTT。日计划记录在 Markdown 中。

**Tech Stack:** HTML、CSS、WebVTT；标准库测试；可选 Playwright / Edge 浏览器检查。

**Spec:** 本文“确定的范围”及 [30 天日计划](../../NEXT_30_DAYS.md)。

## 确定的范围

- 用户每天可投入约 60 分钟；目标仍为作品质量、社团展示与个人账号关注。
- 使用已发布的 BV1VhpY66EsQ、账号 UID 3546966168438889 和实际程序成片。
- 播放需手动触发，不循环；保留字幕、播放控件、下载和 B 站观看入口。
- 桌面、390 像素手机模拟、320 像素窄屏和禁用 JavaScript 时都能看到观看入口。
- 修改限于展示页面、字幕、检查工具与计划文档；影片对应的程序源码和制作记录继续保持可核对。
- 日计划包括复盘、制作、验证与维护时间。自动定时执行尚未设置。

## 验收重点

初始不下载 MP4；手动播放能够推进；字幕与成片一致；窄屏不横向溢出；媒体失败时仍能打开原片或下载。

## 任务一：观看与作者入口

**Files:** `docs/index.html`、`docs/gallery.css`、`docs/captions/immersive.zh.vtt`、`tests/test_immersive_video.py`、`tools/check_gallery_film.py`。

- [x] 增加字幕一致性检查，确认缺少 WebVTT 时测试失败。
- [x] 在 `#immersive` 放入 `#gallery-film` 原生播放器、常驻观看 / 下载链接和作者主页入口。
- [x] 添加随视口变为一列的版式，保持现有颜色与排版。
- [x] 运行字幕测试及真实浏览器检查，查看桌面和手机模拟截图。

## 任务二：可持续的日工作量

**Files:** `docs/NEXT_30_DAYS.md`、`docs/ROADMAP.md`、`README.md`、`README.en.md`、`docs/CONTRIBUTING.md`。

- [x] 每天列出任务、分钟预算与可验收产物；标明缓冲日和未完成事项的顺延规则。
- [x] 校对 30 个日期、总工时与录制能力，区分已完成事项和未来计划。
- [x] 连接现有路线图、README 与维护指南，检查相对链接。

发布按仓库流程提交并推送，以该提交的 Pages 与 CI 回执为准。

## 本地验证结果（2026-10-10）

- `tests.test_immersive_video`：4 项通过；包含素材 / 源码哈希、时间线和新 WebVTT。
- Edge 154.0.4258.62：6 场景通过，覆盖桌面、390 / 320 像素触摸模拟、无 JavaScript、减少动态效果及媒体请求失败。
- 已查看桌面与手机模拟截图；真实手机、Safari、Firefox 尚未验证。
- 30 个日期连续，每天不超过 60 分钟，总计 1,650 分钟；检查了 6 份文档的 233 个本地链接。
