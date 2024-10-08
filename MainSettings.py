import tkinter as tk


class ValuesDictionary(tk.Toplevel):
    def __init__(self, filepath=None, callback=None):
        tk.Toplevel.__init__(self)
        self.title("Values Window")
        self.filepath = filepath
        self.geometry("680x450")
