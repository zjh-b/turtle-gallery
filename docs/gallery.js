"use strict";

(() => {
  const grid = document.querySelector("#gallery-grid");
  const featuredGrid = document.querySelector("#featured-grid");
  const tools = document.querySelector("#gallery-tools");
  const search = document.querySelector("#gallery-search");
  const count = document.querySelector("#result-count");
  const message = document.querySelector("#gallery-message");
  const messageTitle = document.querySelector("#message-title");
  const messageDetail = document.querySelector("#message-detail");
  const messageAction = document.querySelector("#message-action");
  const status = document.querySelector("#copy-status");
  const filters = [...document.querySelectorAll("[data-collection]")];
  let works = [];
  let collection = "all";
  let statusTimer;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function announce(text) {
    clearTimeout(statusTimer);
    status.textContent = text;
    status.hidden = false;
    statusTimer = setTimeout(() => { status.hidden = true; }, 4200);
  }

  async function copyCommand(button, command) {
    try {
      if (!navigator.clipboard || !window.isSecureContext) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(command);
      announce("已复制：" + command + "。请在下载后的项目目录运行。");
    } catch (_) {
      const parent = button.closest(".art-body, .terminal");
      let code = parent.querySelector(".manual-command");
      if (!code) {
        code = element("code", "manual-command");
        code.tabIndex = 0;
        parent.append(code);
      }
      code.textContent = command;
      code.focus();
      const range = document.createRange();
      range.selectNodeContents(code);
      const selection = window.getSelection();
      if (selection) { selection.removeAllRanges(); selection.addRange(range); }
      announce("浏览器未允许自动复制。命令已显示，可手动复制。");
    }
  }

  function card(work) {
    const article = element("article", "art-card");
    article.dataset.collection = work.collection;
    article.setAttribute("aria-labelledby", "art-title-" + work.id);
    const preview = element("div", "art-preview");
    const image = element("img");
    image.src = work.preview;
    image.alt = work.title + (work.id === 20 ? "：原文排版示意" : work.id === 22 ? "：程序文字输出" : "：程序运行预览");
    image.loading = "lazy";
    image.decoding = "async";
    image.width = 800;
    image.height = 464;
    image.addEventListener("error", () => {
      image.alt = work.title + "（预览暂时不可用，请查看源码）";
    }, { once: true });
    preview.append(image, element("span", "art-number", work.number));
    const body = element("div", "art-body");
    const meta = element("div", "art-meta");
    meta.append(element("span", "collection-label", work.collection === "interactive" ? "互动展品" : "创意原作"), element("span", "art-category", work.category));
    const title = element("h3", "", work.title);
    title.id = "art-title-" + work.id;
    const controls = element("details", "art-controls");
    controls.append(element("summary", "", "在电脑上，怎样玩？"), element("p", "", work.controls));
    const actions = element("div", "art-actions");
    const source = element("a", "source-link", "查看源码 ↗");
    source.href = work.source;
    source.setAttribute("aria-label", "查看「" + work.title + "」源码");
    const copy = element("button", "copy-button", "复制运行命令");
    copy.type = "button";
    copy.dataset.copy = "python run.py --demo " + work.number;
    copy.setAttribute("aria-label", "复制「" + work.title + "」运行命令");
    actions.append(source, copy);
    body.append(meta, title, element("p", "art-subtitle", work.subtitle), element("p", "art-description", work.description), controls, actions);
    article.append(preview, body);
    return article;
  }

  function featuredCard(work) {
    const link = element("a", "featured-card");
    link.href = "#gallery";
    link.setAttribute("aria-label", "查看「" + work.title + "」的预览与运行方式");
    const preview = element("div", "featured-preview");
    const image = element("img");
    image.src = work.preview;
    image.alt = work.title + "的程序运行画面";
    image.loading = "lazy";
    image.width = 800;
    image.height = 464;
    preview.append(image);
    const caption = element("div", "featured-caption");
    caption.append(element("span", "featured-number", work.number),
                   element("strong", "", work.title),
                   element("span", "featured-arrow", "↗"));
    link.append(preview, caption);
    link.addEventListener("click", () => {
      search.value = work.number;
      setCollection("romantic");
    });
    return link;
  }

  function showMessage(title, detail, action, callback) {
    messageTitle.textContent = title;
    messageDetail.textContent = detail;
    messageAction.textContent = action;
    messageAction.onclick = callback;
    message.hidden = false;
  }

  function render() {
    const query = search.value.trim().toLocaleLowerCase();
    const filtered = works.filter(work => {
      const inCollection = collection === "all" || work.collection === collection
        || (collection === "romantic" && work.featured);
      const haystack = [work.number, work.id, work.title, work.subtitle, work.category,
        work.description, work.controls, ...(work.tags || []),
        work.collection === "interactive" ? "互动展品 动画" : "创意原作",
        work.category === "趣味挑战" ? "小游戏 游戏" : ""].join(" ").toLocaleLowerCase();
      return inCollection && (!query || query.split(/\s+/).every(term => haystack.includes(term)));
    });
    grid.replaceChildren(...filtered.map(card));
    grid.setAttribute("aria-busy", "false");
    count.textContent = "展示 " + filtered.length + " / " + works.length + " 款作品" + (query ? " · 搜索「" + search.value.trim() + "」" : " · 点击操作说明，发现每个作品的玩法");
    message.hidden = filtered.length > 0;
    if (!filtered.length) showMessage("这个小世界，还没被找到。", "试试作品名称、编号，或「几何」「风景」「小游戏」。", "重置搜索与筛选", () => {
      search.value = "";
      setCollection("all");
      search.focus();
    });
  }

  function setCollection(value) {
    collection = value;
    filters.forEach(button => {
      const active = button.dataset.collection === value;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    render();
  }

  function validWork(work) {
    return work && Number.isInteger(work.id) && work.id > 0
      && ["interactive", "original"].includes(work.collection)
      && typeof work.featured === "boolean"
      && Array.isArray(work.tags) && work.tags.every(tag => typeof tag === "string")
      && ["number", "title", "subtitle", "category", "controls", "description", "preview", "source"].every(key => typeof work[key] === "string")
      && /^assets\/(exhibits|originals)\/\d{2}\.png$/.test(work.preview)
      && work.source.startsWith("https://github.com/zjh-b/turtle-gallery/blob/main/");
  }

  async function loadGallery() {
    message.hidden = true;
    grid.setAttribute("aria-busy", "true");
    count.textContent = "正在打开画廊…";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch("gallery.json", { signal: controller.signal });
      if (!response.ok) throw new Error("Gallery request failed");
      const data = await response.json();
      if (!Array.isArray(data.works) || !data.works.length || !data.works.every(validWork)) throw new Error("Invalid gallery data");
      works = data.works;
      featuredGrid.replaceChildren(...works.filter(work => work.featured).map(featuredCard));
      tools.hidden = false;
      filters.forEach(button => {
        const number = button.querySelector("span");
        number.textContent = button.dataset.collection === "all" ? works.length
          : button.dataset.collection === "romantic" ? works.filter(work => work.featured).length
            : works.filter(work => work.collection === button.dataset.collection).length;
      });
      document.querySelectorAll("[data-count]").forEach(node => {
        const value = node.dataset.count;
        node.textContent = value === "all" ? works.length : works.filter(work => work.collection === value).length;
      });
      render();
    } catch (_) {
      grid.setAttribute("aria-busy", "false");
      count.textContent = "作品目录暂未加载";
      showMessage("画廊正在路上。", "请重试加载，或通过下方下载按钮与页面导航前往 GitHub 查看全部作品。", "重新加载", loadGallery);
    } finally {
      clearTimeout(timeout);
    }
  }

  filters.forEach(button => button.addEventListener("click", () => setCollection(button.dataset.collection)));
  document.querySelector("[data-show-featured]").addEventListener("click", () => {
    search.value = "";
    setCollection("romantic");
  });
  search.addEventListener("input", render);
  document.addEventListener("click", event => {
    const button = event.target.closest("button[data-copy]");
    if (button) copyCommand(button, button.dataset.copy);
  });

  const motionButton = document.querySelector("#motion-toggle");
  const motionImage = document.querySelector("#showcase-image");
  const motionCaption = document.querySelector("#preview-caption");
  let playing = false;
  motionButton.hidden = false;
  function setMotion(active) {
    playing = active;
    motionImage.src = active ? "assets/romantic.gif" : "assets/exhibits/25.png";
    motionImage.alt = active ? "星空彼岸花、粒子爱心、星河玫瑰与霓光蝶舞的实际运行片段" : "星空彼岸花：红色卷瓣与花丝在星空下盛开";
    motionCaption.textContent = active ? "浪漫光影 · 四款实际运行片段" : "实际运行画面 · 星空彼岸花";
    motionButton.textContent = active ? "■ 停止播放" : "▶ 播放绽放片段";
    motionButton.setAttribute("aria-pressed", String(active));
  }
  motionButton.addEventListener("click", () => setMotion(!playing));
  document.addEventListener("visibilitychange", () => { if (document.hidden && playing) setMotion(false); });
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reducedMotion.addEventListener) reducedMotion.addEventListener("change", event => { if (event.matches && playing) setMotion(false); });
  loadGallery();
})();
