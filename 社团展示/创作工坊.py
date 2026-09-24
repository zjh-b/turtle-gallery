"""两款试点作品的可视化创作面板；配方的验证与读写由纯数据模块负责。"""
from pathlib import Path
from datetime import datetime
import json
import random
import tkinter as tk
from tkinter import filedialog, ttk

from 创作配方 import (PRESETS, TITLES, default_parameters, load_recipe,
                    parameter_specs, preset_parameters, save_recipe)


BG, PANEL, TEXT, MUTED, ACCENT = "#0B1424", "#17263B", "#ECF1F5", "#9AACC3", "#A8E1CC"
FONT = "Microsoft YaHei"
ROOT = Path(__file__).resolve().parent.parent


class CreatorPanel:
    def __init__(self, stage, app):
        self.stage, self.app, self.work_id = stage, app, app.WORK_ID
        self.window = tk.Toplevel(stage.root)
        self.window.title(TITLES[self.work_id] + " · 创作工坊")
        self.window.configure(bg=BG)
        self.window.transient(stage.root)
        self.window.minsize(380, 540)
        height = min(850, self.window.winfo_screenheight() - 90)
        x = min(stage.root.winfo_rootx() + stage.root.winfo_width() - 100,
                self.window.winfo_screenwidth() - 445)
        self.window.geometry(f"420x{height}+{max(0, x)}+40")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Escape>", lambda event: self.close() or "break")
        self._closed, self._syncing = False, False
        self._apply_job = self._poll_job = None
        self.variables, self.value_labels = {}, {}
        self._seen = None
        style = ttk.Style(self.window)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Creator.TCombobox", fieldbackground=PANEL, background=PANEL,
                        foreground=TEXT, arrowcolor=ACCENT, bordercolor="#30445A",
                        lightcolor=PANEL, darkcolor=PANEL, padding=5)
        style.map("Creator.TCombobox", fieldbackground=[("readonly", PANEL)],
                  foreground=[("readonly", TEXT)], selectbackground=[("readonly", PANEL)],
                  selectforeground=[("readonly", TEXT)])
        style.configure("Creator.Horizontal.TScale", background=ACCENT, troughcolor=PANEL,
                        bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure("Creator.Vertical.TScrollbar", background="#31465C", troughcolor=BG,
                        bordercolor=BG, lightcolor=BG, darkcolor=BG, arrowcolor=MUTED, arrowsize=10)
        self.window.option_add("*TCombobox*Listbox.background", PANEL)
        self.window.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.window.option_add("*TCombobox*Listbox.selectBackground", "#29483F")
        self.window.option_add("*TCombobox*Listbox.selectForeground", TEXT)

        header = tk.Frame(self.window, bg=BG)
        header.pack(fill="x", padx=22, pady=(20, 12))
        self.label(header, "MAKE IT YOURS", color=ACCENT, size=9).pack(anchor="w")
        self.label(header, "创作工坊", size=22, bold=True).pack(anchor="w", pady=(3, 2))
        self.label(header, TITLES[self.work_id] + "  /  参数变化会实时映入画面", color=MUTED, size=9).pack(anchor="w")

        footer = tk.Frame(self.window, bg=BG)
        footer.pack(side="bottom", fill="x", padx=22, pady=(10, 16))
        self.status = tk.StringVar(value="调好以后保存配方，下次继续这一幅。")
        for column in range(2):
            footer.columnconfigure(column, weight=1)
        for row, actions in enumerate((("保存配方…", self.save, "载入配方…", self.load),
                                       ("恢复默认", self.restore_defaults, "重播作品", self.restart))):
            self.button(footer, actions[0], actions[1]).grid(row=row, column=0, sticky="ew", padx=(0, 5), pady=4)
            self.button(footer, actions[2], actions[3]).grid(row=row, column=1, sticky="ew", padx=(5, 0), pady=4)
        export_button = self.button(footer, "导出当前画面 PNG…", self.export_png)
        export_button.configure(bg=ACCENT, fg=BG, activebackground="#C5EFDF", activeforeground=BG)
        export_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        status_label = tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED, justify="left",
                               width=1, wraplength=340, anchor="w", font=(FONT, 9))
        status_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        status_label.bind("<Configure>", lambda event: status_label.configure(wraplength=max(240, event.width)))

        viewport = tk.Frame(self.window, bg=BG)
        viewport.pack(fill="both", expand=True, padx=(22, 10))
        canvas = tk.Canvas(viewport, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview,
                                  style="Creator.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=BG)
        body_id = canvas.create_window(0, 0, window=body, anchor="nw")
        body.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(body_id, width=event.width))
        self.window.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"))
        self.window.bind("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        self.window.bind("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

        self.label(body, "灵感预设", color=MUTED).pack(anchor="w", pady=(0, 6))
        self.presets = ttk.Combobox(body, state="readonly", values=[name for name, _ in PRESETS[self.work_id]],
                                    font=(FONT, 10), style="Creator.TCombobox")
        self.presets.set("选择一组配色与参数")
        self.presets.pack(fill="x", pady=(0, 15), ipady=3)
        self.presets.bind("<<ComboboxSelected>>", self.choose_preset)
        for spec in parameter_specs(self.work_id):
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=(0, 13))
            heading = tk.Frame(row, bg=BG)
            heading.pack(fill="x")
            self.label(heading, spec.label, size=10).pack(side="left")
            if spec.kind == "choice":
                variable = tk.StringVar()
                widget = ttk.Combobox(row, textvariable=variable, values=spec.choices,
                                      state="readonly", font=(FONT, 10), style="Creator.TCombobox")
                widget.pack(fill="x", pady=(6, 0), ipady=3)
                widget.bind("<<ComboboxSelected>>", self.schedule_apply)
            elif spec.key == "seed":
                variable = tk.StringVar()
                line = tk.Frame(row, bg=BG)
                line.pack(fill="x", pady=(6, 0))
                widget = tk.Entry(line, textvariable=variable, bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                                  font=(FONT, 10), relief="flat", width=15)
                widget.pack(side="left", fill="x", expand=True, ipady=7)
                widget.bind("<Return>", lambda event: self.apply_now())
                widget.bind("<FocusOut>", self.schedule_apply)
                self.button(line, "换一幅", self.new_seed).pack(side="right", padx=(9, 0))
            else:
                variable = tk.DoubleVar()
                display = tk.StringVar()
                self.value_labels[spec.key] = display
                tk.Label(heading, textvariable=display, bg=BG, fg=ACCENT, font=(FONT, 9)).pack(side="right")
                widget = ttk.Scale(row, variable=variable, from_=spec.low, to=spec.high,
                                   orient="horizontal", style="Creator.Horizontal.TScale",
                                   command=lambda value, item=spec: self.move_slider(item, value))
                widget.pack(fill="x", pady=(6, 0))
                for key, direction in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1)):
                    widget.bind("<" + key + ">", lambda event, item=spec, step=direction:
                                self.step_slider(item, step))
            self.variables[spec.key] = variable
        self.refresh()
        self._poll_job = self.window.after(250, self.poll)

    @staticmethod
    def label(parent, text, color=TEXT, size=10, bold=False):
        return tk.Label(parent, text=text, bg=BG, fg=color, font=(FONT, size, "bold" if bold else "normal"))

    @staticmethod
    def button(parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=PANEL, fg=ACCENT,
                         activebackground="#29483F", activeforeground=TEXT, relief="flat",
                         font=(FONT, 10), cursor="hand2", padx=10, pady=8)

    def show(self):
        self.window.deiconify()
        self.window.lift()

    def refresh(self):
        values = self.app.get_parameters()
        self._syncing = True
        try:
            for spec in parameter_specs(self.work_id):
                value = values[spec.key]
                self.variables[spec.key].set(spec.choices[value] if spec.kind == "choice" else value)
                if spec.key in self.value_labels:
                    self.value_labels[spec.key].set(f"{value:g}")
            self._seen = values
            self.presets.set(next((name for index, (name, _) in enumerate(PRESETS[self.work_id])
                                   if preset_parameters(self.work_id, index) == values), "自定义参数"))
        finally:
            self._syncing = False

    def poll(self):
        self._poll_job = None
        if self._closed:
            return
        if self._apply_job is None and self.app.get_parameters() != self._seen:
            self.refresh()
        self._poll_job = self.window.after(250, self.poll)

    def schedule_apply(self, *_):
        if self._syncing or self._closed:
            return
        # Scale arrow keys consume their event before the global tour binding.
        # Editing a parameter must still keep this work on screen.
        if getattr(self.stage, "tour", None) is not None:
            self.stage.tour.pause()
        for key, label in self.value_labels.items():
            label.set(f"{self.variables[key].get():g}")
        if self._apply_job is not None:
            self.window.after_cancel(self._apply_job)
        self._apply_job = self.window.after(85, self.apply_now)

    def move_slider(self, spec, value):
        if self._syncing:
            return
        snapped = spec.low + round((float(value) - spec.low) / spec.step) * spec.step
        self.variables[spec.key].set(round(max(spec.low, min(spec.high, snapped)), 6))
        self.schedule_apply()

    def step_slider(self, spec, direction):
        self.move_slider(spec, self.variables[spec.key].get() + direction * spec.step)
        return "break"

    def cancel_pending(self):
        if self._apply_job is not None:
            self.window.after_cancel(self._apply_job)
            self._apply_job = None

    def apply_now(self):
        self.cancel_pending()
        try:
            values = {}
            for spec in parameter_specs(self.work_id):
                value = self.variables[spec.key].get()
                if spec.kind == "choice":
                    value = spec.choices.index(value)
                elif spec.kind == "int":
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        raise ValueError(f"{spec.label}需要整数。") from None
                else:
                    value = round(float(value), 6)
                values[spec.key] = value
            if values != self.app.get_parameters():
                self.app.apply_parameters(values)
                self.presets.set("自定义参数")
                self.status.set("已映入画面 · 保存配方可以留住这组参数。")
            self._seen = self.app.get_parameters()
            return True
        except (ValueError, tk.TclError) as exc:
            self.status.set(str(exc))
            return False

    def use_parameters(self, values, message):
        self.cancel_pending()
        self.app.apply_parameters(values)
        self.stage.reset()
        self.refresh()
        self.status.set(message)

    def choose_preset(self, event=None):
        self.use_parameters(preset_parameters(self.work_id, self.presets.current()), "预设已载入，作品从头播放。")

    def new_seed(self):
        if not self.apply_now():
            return
        values = self.app.get_parameters()
        values["seed"] = random.SystemRandom().randrange(2147483648)
        self.use_parameters(values, "换了一幅新构图 · 其他参数已保留。")

    def restore_defaults(self):
        self.presets.set("选择一组配色与参数")
        self.use_parameters(default_parameters(self.work_id), "已恢复默认参数，作品从头播放。")

    def restart(self):
        if self.apply_now():
            self.stage.reset()
            self.status.set("使用当前配方重新播放。")

    def recipe_directory(self):
        directory = ROOT / "creations"
        directory.mkdir(exist_ok=True)
        return directory

    def save(self):
        if not self.apply_now():
            return
        try:
            path = filedialog.asksaveasfilename(parent=self.window, title="保存我的创作配方",
                initialdir=str(self.recipe_directory()), defaultextension=".json",
                initialfile=f"{self.work_id}-{self.app.get_parameters()['seed']}.json",
                filetypes=[("创作配方 JSON", "*.json")])
            if path:
                save_recipe(path, self.work_id, self.app.get_parameters())
                self.status.set("已保存：" + str(Path(path)))
        except (OSError, ValueError) as exc:
            self.status.set("保存失败：" + str(exc))

    def load(self):
        # Flush valid slider edits before opening the modal picker. Canceling it
        # must not leave displayed values ahead of the actual artwork.
        self.apply_now()
        try:
            path = filedialog.askopenfilename(parent=self.window, title="载入我的创作配方",
                initialdir=str(self.recipe_directory()), filetypes=[("创作配方 JSON", "*.json")])
            if path:
                recipe = load_recipe(path, expected_work_id=self.work_id)
                self.presets.set("选择一组配色与参数")
                self.use_parameters(recipe["parameters"], "已载入：" + Path(path).name + " · 从头播放")
        except (OSError, ValueError) as exc:
            self.status.set("载入失败：" + str(exc))

    def export_png(self):
        if not self.apply_now():
            return
        try:
            from 作品导出 import capture_artwork, save_png
            # Snapshot before the modal dialog, while the clicked frame is current.
            # No event-loop reentry or change to the user's pause state is needed.
            if self.stage.frame:
                self.stage.frame(0)
            picture = capture_artwork(self.stage)
            parameters = self.app.get_parameters()
            directory = ROOT / "exports"
            directory.mkdir(exist_ok=True)
            name = f"{self.work_id}-{datetime.now():%Y%m%d-%H%M%S}.png"
            path = filedialog.asksaveasfilename(parent=self.window, title="导出当前画面",
                initialdir=str(directory), initialfile=name, defaultextension=".png",
                filetypes=[("PNG 图片", "*.png")])
            if not path:
                self.status.set("已取消导出，作品继续保留当前设置。")
                return
            width, height = save_png(picture, path, metadata={
                "Software": "Turtle Gallery", "Work": str(self.work_id),
                "Parameters": json.dumps(parameters, ensure_ascii=False),
            })
            self.status.set(f"已保存 {width} × {height} px：{Path(path).resolve()}")
        except (OSError, ValueError, RuntimeError, tk.TclError) as exc:
            self.status.set("导出失败：" + str(exc))

    def close(self):
        if self._closed:
            return
        self.cancel_pending()
        if self._poll_job is not None:
            self.window.after_cancel(self._poll_job)
        self._closed = True
        self.stage.creator_panel = None
        self.window.destroy()
        if not self.stage.closed:
            self.stage.screen.listen()
