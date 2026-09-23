"""Turtle Gallery: searchable desktop gallery and isolated work processes."""
from fractions import Fraction
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from 作品目录 import CATEGORIES, COLLECTIONS, PROJECT_ROOT, WORKS, get_work

ROOT = Path(__file__).resolve().parent
PAGE_SIZE = 6
DEMOS = [(w['number'], w['title'], w['subtitle'], Path(w['filename']).name)
         for w in WORKS if w['collection'] == 'interactive']
BG, PANEL, LINE = '#0B1322', '#152239', '#293D55'
TEXT, MUTED, GREEN = '#EEF5F5', '#98ACC3', '#9FE7CF'
FONT = 'Microsoft YaHei'


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Turtle Gallery · 海龟画廊')
        width = min(1060, self.root.winfo_screenwidth() - 60)
        height = min(850, self.root.winfo_screenheight() - 90)
        self.root.geometry(f'{width}x{height}')
        self.root.minsize(min(860, width), min(620, height))
        self.root.configure(bg=BG)
        self.page, self.collection = 0, 'all'
        self.category = tk.StringVar(value=CATEGORIES[0])
        self.query = tk.StringVar()
        self.images, self.sources = {}, {}
        self.displayed, self.tabs = [], {}
        self.child = self.active_work = self.console = self.reader = None
        self.output = queue.Queue()
        self.output_tail = ''
        self.stopping = False
        self.resize_job = self.watch_job = None
        self.fullscreen = False
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=28, pady=(20, 14))
        tk.Label(header, text='TURTLE GALLERY', fg=GREEN, bg=BG,
                 font=(FONT, 10, 'bold')).pack(anchor='w')
        title = tk.Frame(header, bg=BG)
        title.pack(fill='x', pady=(3, 0))
        tk.Label(title, text='海龟画廊', fg=TEXT, bg=BG,
                 font=(FONT, 27, 'bold')).pack(side='left')
        tk.Label(title, text=f'{len(WORKS)} 个创意  /  从一笔画，到会动的小世界', fg=MUTED,
                 bg=BG, font=(FONT, 10)).pack(side='left', padx=20, pady=(12, 0))
        filters = tk.Frame(self.root, bg=BG)
        filters.pack(fill='x', padx=28, pady=(0, 10))
        for key, label in COLLECTIONS.items():
            count = len(WORKS) if key == 'all' else sum(w['collection'] == key for w in WORKS)
            button = self.button(filters, f'{label}  {count}', lambda k=key: self.select_collection(k))
            button.pack(side='left', padx=(0, 8))
            self.tabs[key] = button
        self.search = tk.Entry(filters, textvariable=self.query, bg=PANEL, fg=TEXT,
                               insertbackground=GREEN, relief='flat', font=(FONT, 10),
                               highlightthickness=1, highlightbackground=LINE,
                               highlightcolor=GREEN, width=18)
        self.search.pack(side='right', ipady=7, padx=(7, 0))
        tk.Label(filters, text='搜索  Ctrl+F', fg=MUTED, bg=BG,
                 font=(FONT, 9)).pack(side='right')
        themes = tk.Frame(self.root, bg=BG)
        themes.pack(fill='x', padx=28, pady=(0, 2))
        self.theme_buttons = {}
        for category in CATEGORIES:
            button = self.button(themes, category, lambda c=category: self.select_category(c), small=True)
            button.pack(side='left', padx=(0, 7))
            self.theme_buttons[category] = button
        featured_count = sum(work.get('featured', False) for work in WORKS)
        if featured_count:
            featured = self.button(themes, f'✦ 浪漫光影  {featured_count}',
                                   lambda: self.select_collection('romantic'), small=True)
            featured.pack(side='right')
            self.tabs['romantic'] = featured
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, takefocus=True)
        self.canvas.pack(fill='both', expand=True, padx=20, pady=(7, 0))
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill='x', padx=28, pady=(7, 6))
        self.previous = self.button(footer, '← 上一页', lambda: self.change_page(-1), small=True)
        self.previous.pack(side='left')
        self.page_text = tk.StringVar()
        tk.Label(footer, textvariable=self.page_text, bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(side='left', padx=13)
        self.next = self.button(footer, '下一页 →', lambda: self.change_page(1), small=True)
        self.next.pack(side='left')
        self.stop_button = self.button(footer, '结束作品', self.stop, small=True)
        self.stop_button.pack(side='right')
        self.stop_button.configure(state='disabled')
        self.status = tk.StringVar(value='点击预览开始 · 1–6 打开当前页作品 · ←→ 翻页 · F11 全屏')
        tk.Label(self.root, textvariable=self.status, bg=BG, fg=MUTED,
                 font=(FONT, 9), anchor='w').pack(fill='x', padx=28, pady=(0, 15))
        self.query.trace_add('write', self.filter_changed)
        self.canvas.bind('<Configure>', self.resize)
        for slot in range(PAGE_SIZE):
            self.root.bind(str(slot + 1), lambda event, s=slot: self.shortcut(event, s))
        self.root.bind('<Left>', lambda event: self.page_shortcut(event, -1))
        self.root.bind('<Right>', lambda event: self.page_shortcut(event, 1))
        self.root.bind('<Control-f>', self.focus_search)
        self.root.bind('<Control-F>', self.focus_search)
        self.root.bind('<F11>', self.toggle_fullscreen)
        self.root.bind('<Escape>', self.escape)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after_idle(self.draw_cards)

    @staticmethod
    def button(parent, text, command, small=False):
        return tk.Button(parent, text=text, command=command, font=(FONT, 9 if small else 10),
                         bg=PANEL, fg=MUTED, activebackground='#294841', activeforeground=TEXT,
                         disabledforeground='#51647D', relief='flat', bd=0,
                         highlightthickness=1, highlightbackground=LINE,
                         highlightcolor=GREEN, padx=10, pady=4 if small else 7, cursor='hand2')

    def typing(self, event):
        return isinstance(event.widget, (tk.Entry, tk.Text))

    def shortcut(self, event, slot):
        if not self.typing(event) and slot < len(self.displayed):
            self.launch(self.displayed[slot])

    def page_shortcut(self, event, delta):
        if not self.typing(event):
            self.change_page(delta)

    def focus_search(self, event=None):
        self.search.focus_set()
        self.search.select_range(0, 'end')
        return 'break'

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)
        return 'break'

    def escape(self, event=None):
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes('-fullscreen', False)
        elif self.query.get():
            self.query.set('')
        self.canvas.focus_set()

    def resize(self, event=None):
        if self.resize_job:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(90, self.draw_cards)

    def filtered(self):
        words = self.query.get().casefold().split()
        matches = [w for w in WORKS if (self.collection == 'all' or w['collection'] == self.collection
                                       or (self.collection == 'romantic' and w.get('featured', False)))
                and (self.category.get() == CATEGORIES[0] or w['category'] == self.category.get())
                and all(word in ' '.join((w['number'], str(w['id']), w['title'], w['subtitle'],
                                         w['category'], w['description'], w['filename'],
                                         *w['tags'])).casefold() for word in words)]
        return sorted(matches, key=lambda work: (not work.get('featured', False), work['id']))

    def filter_changed(self, *_):
        self.page = 0
        self.draw_cards()

    def select_collection(self, collection):
        self.collection = collection
        if collection == 'romantic':
            self.category.set(CATEGORIES[0])
            self.query.set('')
        self.filter_changed()

    def select_category(self, category):
        self.category.set(category)
        self.filter_changed()

    def change_page(self, delta):
        pages = max(1, math.ceil(len(self.filtered()) / PAGE_SIZE))
        self.page = max(0, min(pages - 1, self.page + delta))
        self.draw_cards()

    def get_image(self, work, width, height):
        key = (work['id'], int(width), int(height))
        if key in self.images:
            return self.images[key]
        number = work['number']
        preview = PROJECT_ROOT / work['preview']
        paths = ([ROOT / 'previews' / (number + '_thumb.png'), preview]
                 if work['collection'] == 'interactive' else
                 [preview.with_name(number + '_thumb.png'), preview])
        try:
            if work['id'] not in self.sources:
                path = next((path for path in paths if path.is_file()), None)
                if path is None:
                    return None
                self.sources[work['id']] = tk.PhotoImage(file=str(path))
            source = self.sources[work['id']]
            step = max(1, math.ceil(max(source.width() / 400, source.height() / 260)))
            base = source.subsample(step) if step > 1 else source
            ratio = min(width / base.width(), height / base.height(), 1.0)
            scale = Fraction(ratio).limit_denominator(8)
            if float(scale) > ratio:
                scale = Fraction(max(1, int(ratio * 12)), 12)
            result = base.zoom(scale.numerator).subsample(scale.denominator)
            self.images[key] = result
            return result
        except (tk.TclError, OSError):
            return None

    def draw_cards(self):
        self.resize_job = None
        self.canvas.delete('all')
        self.images.clear()
        for key, button in self.tabs.items():
            button.configure(bg='#294841' if key == self.collection else PANEL,
                             fg=GREEN if key == self.collection else MUTED)
        for category, button in self.theme_buttons.items():
            button.configure(bg='#23374C' if category == self.category.get() else BG,
                             fg=TEXT if category == self.category.get() else MUTED)
        works = self.filtered()
        pages = max(1, math.ceil(len(works) / PAGE_SIZE))
        self.page = min(self.page, pages - 1)
        self.displayed = works[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        self.page_text.set(f'{self.page + 1} / {pages} 页  ·  {len(works)} 款')
        self.previous.configure(state='normal' if self.page else 'disabled')
        self.next.configure(state='normal' if self.page + 1 < pages else 'disabled')
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 100:
            return
        if not works:
            self.canvas.create_text(width / 2, height / 2 - 18, text='还没有找到这个创意', fill=TEXT,
                                    font=(FONT, 19, 'bold'))
            self.canvas.create_text(width / 2, height / 2 + 20,
                                    text='试试“烟花”“递归”“游戏”，或清空搜索并切换分类。',
                                    fill=MUTED, font=(FONT, 10))
            return
        gap = 12
        romantic_layout = self.collection == 'romantic' and len(self.displayed) == 4
        columns = 2 if romantic_layout else 3
        cw, ch = (width - gap * (columns + 1)) / columns, (height - gap * 3) / 2
        for index, work in enumerate(self.displayed):
            x, y = gap + index % columns * (cw + gap), gap + index // columns * (ch + gap)
            tag, detail_tag = f'work-{index}', f'details-{index}'
            rect = self.canvas.create_rectangle(x, y, x + cw, y + ch, fill=PANEL, outline=LINE, tags=tag)
            self.canvas.create_rectangle(x + 1, y + 1, x + cw - 1, y + 3,
                                         fill=work['accent'], outline='', tags=tag)
            if romantic_layout:
                image_width, image_height = min(cw * .52, 240), max(45, ch - 24)
                image_x, image_y = x + image_width / 2 + 6, y + ch / 2
                title_x, title_y = x + image_width + 10, y + 22
                text_width = cw - image_width - 22
            else:
                image_width, image_height = cw - 24, max(35, ch - 100)
                image_x, image_y = x + cw / 2, y + 13 + image_height / 2
                title_x, title_y = x + 13, y + ch - 80
                text_width = cw - 26
            picture = self.get_image(work, image_width - 8, image_height)
            if picture:
                self.canvas.create_image(image_x, image_y, image=picture, tags=tag)
            else:
                self.canvas.create_text(image_x, image_y,
                                        text=work['number'], fill=work['accent'], font=(FONT, 28, 'bold'), tags=tag)
            self.canvas.create_text(title_x, title_y, text=f"{work['number']}  {work['title']}",
                                    anchor='nw', fill=TEXT, font=(FONT, 11, 'bold'), width=text_width, tags=tag)
            self.canvas.create_text(title_x, title_y + 25, text=work['subtitle'],
                                    anchor='nw', fill=MUTED, font=(FONT, 8), width=text_width, tags=tag)
            action = '了解便签 →' if work['id'] == 20 else '开始作品 →'
            self.canvas.create_text(title_x, y + ch - 16, text=f'{index + 1}  {action}',
                                    anchor='w', fill=work['accent'], font=(FONT, 9), tags=tag)
            self.canvas.create_text(x + cw - 13, y + ch - 16, text='玩法 / 源码', anchor='e',
                                    fill=MUTED, font=(FONT, 8), tags=detail_tag)
            self.canvas.tag_bind(tag, '<Button-1>', lambda event, w=work: self.launch(w))
            self.canvas.tag_bind(detail_tag, '<Button-1>', lambda event, w=work: self.details(w))
            self.canvas.tag_bind(tag, '<Enter>', lambda event, r=rect: self.hover(r, True))
            self.canvas.tag_bind(tag, '<Leave>', lambda event, r=rect: self.hover(r, False))
            self.canvas.tag_bind(detail_tag, '<Enter>', lambda event: self.canvas.configure(cursor='hand2'))
            self.canvas.tag_bind(detail_tag, '<Leave>', lambda event: self.canvas.configure(cursor=''))

    def hover(self, rectangle, active):
        self.canvas.itemconfigure(rectangle, outline=GREEN if active else LINE)
        self.canvas.configure(cursor='hand2' if active else '')

    def details(self, work):
        popup = tk.Toplevel(self.root)
        popup.title(f"{work['number']} · {work['title']}")
        popup.configure(bg=BG)
        popup.geometry('560x430')
        popup.minsize(560, 430)
        popup.transient(self.root)
        tk.Label(popup, text=f"{work['number']}  /  {COLLECTIONS[work['collection']]}  /  {work['category']}",
                 bg=BG, fg=work['accent'], font=(FONT, 10)).pack(anchor='w', padx=26, pady=(25, 8))
        tk.Label(popup, text=work['title'], bg=BG, fg=TEXT,
                 font=(FONT, 24, 'bold')).pack(anchor='w', padx=26)
        tk.Label(popup, text=work['description'], wraplength=490, justify='left', bg=BG, fg=MUTED,
                 font=(FONT, 11)).pack(fill='x', padx=26, pady=(17, 12))
        tk.Label(popup, text=work['controls'], wraplength=490, justify='left', bg=PANEL, fg=TEXT,
                 font=(FONT, 10), padx=14, pady=14).pack(fill='x', padx=26)
        tk.Label(popup, text='源码：' + work['filename'], bg=BG, fg=MUTED, font=(FONT, 9),
                 wraplength=490, justify='left').pack(anchor='w', padx=26, pady=12)
        button = self.button(popup, '开始作品 →', lambda: (popup.destroy(), self.launch(work, confirmed=True)))
        button.pack(anchor='e', padx=26, pady=(0, 18))
        popup.bind('<Escape>', lambda event: popup.destroy())
        button.focus_set()

    def launch(self, work, confirmed=False):
        if not isinstance(work, dict):
            work = get_work(work) or next((w for w in WORKS if Path(w['filename']).name == work), None)
        if work is None:
            return
        if work['id'] == 20 and not confirmed:
            self.details(work)
            return
        if self.child is not None and self.child.poll() is None:
            self.status.set(f"正在展示「{self.active_work['title']}」；结束当前作品后可开启下一款。")
            if self.console and self.console.winfo_exists():
                self.console.lift()
            return
        if self.child is not None:
            self.watch()
            if self.child is not None:
                self.root.after(60, lambda: self.launch(work, confirmed=confirmed))
                return
        if self.console and self.console.winfo_exists():
            self.console.destroy()
            self.console = None
        self.output = queue.Queue()
        self.output_tail = ''
        self.stopping = False
        environment = os.environ.copy()
        environment['PYTHONIOENCODING'] = 'utf-8'
        environment['PYTHONUNBUFFERED'] = '1'
        command = [sys.executable, '-u', str(PROJECT_ROOT / 'run.py'), '--demo', str(work['id'])]
        try:
            self.child = subprocess.Popen(command, cwd=str(PROJECT_ROOT), env=environment,
                                          stdin=subprocess.PIPE if work['console'] else subprocess.DEVNULL,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          text=True, encoding='utf-8', errors='replace', bufsize=0,
                                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as exc:
            messagebox.showerror('启动失败', str(exc), parent=self.root)
            return
        self.active_work = work
        self.reader = threading.Thread(target=self.read_output, args=(self.child.stdout, self.output), daemon=True)
        self.reader.start()
        self.stop_button.configure(state='normal')
        self.status.set(f"正在展示  {work['number']} · {work['title']}  /  关闭作品窗口或点击“结束作品”返回")
        if work['console']:
            self.open_console(work)
        self.watch_job = self.root.after(120, self.watch)

    @staticmethod
    def read_output(stream, messages):
        try:
            while True:
                character = stream.read(1)
                if not character:
                    break
                messages.put(character)
        except (OSError, ValueError):
            pass

    def open_console(self, work):
        if self.console and self.console.winfo_exists():
            self.console.destroy()
        self.console = tk.Toplevel(self.root)
        self.console.title(f"{work['title']} · Turtle Gallery")
        self.console.geometry('680x460')
        self.console.minsize(500, 340)
        self.console.configure(bg=BG)
        tk.Label(self.console, text='月饼装盒计算', fg=TEXT, bg=BG,
                 font=(FONT, 20, 'bold')).pack(anchor='w', padx=20, pady=(20, 4))
        tk.Label(self.console, text='按提示输入并回车；输入 q 退出。', fg=MUTED, bg=BG,
                 font=(FONT, 10)).pack(anchor='w', padx=20, pady=(0, 12))
        self.console_text = tk.Text(self.console, bg='#111E30', fg='#D6ECE0', insertbackground=GREEN,
                                    font=(FONT, 11), relief='flat', padx=16, pady=12,
                                    state='disabled', wrap='word')
        row = tk.Frame(self.console, bg=BG)
        row.pack(side='bottom', fill='x', padx=20, pady=16)
        self.console_text.pack(fill='both', expand=True, padx=20)
        self.console_entry = tk.Entry(row, bg=PANEL, fg=TEXT, insertbackground=GREEN,
                                       font=(FONT, 12), relief='flat')
        self.console_entry.pack(side='left', fill='x', expand=True, ipady=7)
        self.button(row, '发送 ↵', self.send_input).pack(side='right', padx=(10, 0))
        self.console_entry.bind('<Return>', self.send_input)
        self.console.protocol('WM_DELETE_WINDOW', self.close_console)
        self.console_entry.focus_set()

    def console_append(self, text):
        if self.console is not None and self.console.winfo_exists():
            self.console_text.configure(state='normal')
            self.console_text.insert('end', text)
            self.console_text.see('end')
            self.console_text.configure(state='disabled')

    def send_input(self, event=None):
        if self.child is None or self.child.poll() is not None or not self.child.stdin:
            return 'break'
        value = self.console_entry.get()
        try:
            self.child.stdin.write(value + '\n')
            self.child.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            return 'break'
        self.console_append(value + '\n')
        self.console_entry.delete(0, 'end')
        return 'break'

    def close_console(self):
        if self.active_work and self.active_work['console']:
            self.stop()
        if self.console and self.console.winfo_exists():
            self.console.destroy()
        self.console = None

    def watch(self):
        if self.watch_job:
            self.root.after_cancel(self.watch_job)
            self.watch_job = None
        # 等读取线程收完进程退出前的最后一段输出，再展示状态和关闭管道。
        if self.child is not None and self.child.poll() is not None and self.reader.is_alive():
            self.watch_job = self.root.after(50, self.watch)
            return
        chunks = []
        while True:
            try:
                chunks.append(self.output.get_nowait())
            except queue.Empty:
                break
        text = ''.join(chunks)
        self.output_tail = (self.output_tail + text)[-5000:]
        self.console_append(text)
        if self.child is not None and self.child.poll() is None:
            self.watch_job = self.root.after(120, self.watch)
            return
        if self.child is None:
            return
        code = self.child.returncode
        for stream in (self.child.stdin, self.child.stdout):
            if stream:
                stream.close()
        title = self.active_work['title']
        was_console = self.active_work['console']
        self.child = self.active_work = None
        self.stop_button.configure(state='disabled')
        self.status.set(f'「{title}」已结束 · 继续探索下一款，或用搜索找到感兴趣的创意。')
        if was_console:
            self.console_append('\n— 本次运行已结束，可关闭此窗口。 —\n')
        if code and not self.stopping:
            messagebox.showerror('作品运行出错', f'「{title}」退出码：{code}\n\n{self.output_tail[-2500:]}',
                                 parent=self.root)
        self.stopping = False

    def stop(self):
        if self.child is not None and self.child.poll() is None:
            self.stopping = True
            self.child.terminate()
            self.status.set('正在结束作品…')

    def close(self):
        if self.watch_job:
            self.root.after_cancel(self.watch_job)
        if self.resize_job:
            self.root.after_cancel(self.resize_job)
        if self.child is not None and self.child.poll() is None:
            self.child.terminate()
        self.root.destroy()


if __name__ == '__main__':
    Launcher().root.mainloop()
