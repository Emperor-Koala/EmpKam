# Most of the code for this class credit to: u/novel_yet_trivial,
# https://www.reddit.com/r/learnpython/comments/985umy/comment/e4dj9k9/?utm_source=share&utm_medium=web2x&context=3

import tkinter as tk
from typing import Callable


class IntEntry(tk.Entry):
    def __init__(self, master=None, on_edit: Callable[[], None] = None, initial_value: int = None, **kwargs):
        self.var = tk.StringVar()
        self.on_edit = on_edit
        tk.Entry.__init__(self, master, textvariable=self.var, **kwargs)
        if initial_value is None:
            self.old_value = ''
        else:
            self.old_value = str(initial_value)
        self.var.set(self.old_value)
        self.var.trace('w', self.check)
        self.get, self.set = self.var.get, self.var.set

    def check(self, *args):
        if self.get().isdigit() or len(self.get()) == 0:
            # the current value is only digits or is empty; allow this
            self.old_value = self.get()
            if self.on_edit is not None:
                self.on_edit()
        else:
            # there's non-digit characters in the input; reject this
            self.set(self.old_value)
