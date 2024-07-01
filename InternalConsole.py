import tkinter as tk
import sys
import os


class InternalConsole(tk.Toplevel):
    def __init__(self_console):
        super().__init__()
        self_console.title("Internal Console")
        self_console.geometry("800x400")
        icon_path = os.path.abspath("icon_128.ico")
        self_console.iconbitmap(icon_path)

        # Create a Text widget for the internal console
        self_console.console = tk.Text(self_console, wrap=tk.WORD, height=10)
        self_console.console.grid(row=0, column=0, sticky="nsew")

        # Create a vertical scrollbar
        scrollbar = tk.Scrollbar(self_console, command=self_console.console.yview)
        self_console.console.config(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Redirect stdout to the console
        sys.stdout = self_console.ConsoleRedirector(self_console.console)
        sys.stderr = self_console.ConsoleRedirector(self_console.console)

        # Override the destroy method to restore sys.stdout and sys.stderr
        self_console.protocol("WM_DELETE_WINDOW", self_console.close_window)

        # Configure grid weights for resizing
        self_console.grid_rowconfigure(0, weight=1)
        self_console.grid_columnconfigure(0, weight=1)

        self_console.mainloop()

    def close_window(self_console):
        # Restore original sys.stdout and sys.stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self_console.destroy()

    class ConsoleRedirector:
        def __init__(self_console, text_widget):
            self_console.text_widget = text_widget

        def write(self_console, text):
            self_console.text_widget.insert(tk.END, text)
            self_console.text_widget.see(tk.END)  # Scroll to the end

        def flush(self_console):
            pass  # Needed for file-like object
