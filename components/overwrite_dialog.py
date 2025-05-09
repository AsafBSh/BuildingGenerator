import tkinter as tk
from tkinter import ttk
import os
from datetime import datetime

class OverwriteDialog(tk.Toplevel):
    """Dialog for handling file overwrite confirmations.
    
    This component provides a user interface for confirming file overwrites
    and choosing alternative actions when a file already exists.
    """
    
    def __init__(self, parent, filepath):
        super().__init__(parent)
        
        self.result = None  # Will be set to: "overwrite", "saveas", or None (cancel)
        self.new_filepath = None
        
        # Configure window
        self.title("File Already Exists")
        self.geometry("400x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Get file details
        file_size = os.path.getsize(filepath)
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        # Create main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Add warning icon and message
        ttk.Label(
            main_frame,
            text="⚠️",
            font=("Arial", 24)
        ).pack(pady=(0, 10))
        
        ttk.Label(
            main_frame,
            text="A file with this name already exists.",
            font=("Arial", 10, "bold")
        ).pack()
        
        # File details
        details_frame = ttk.LabelFrame(
            main_frame,
            text="File Details",
            padding="5"
        )
        details_frame.pack(fill="x", pady=10)
        
        ttk.Label(
            details_frame,
            text=f"Path: {filepath}"
        ).pack(anchor="w")
        
        ttk.Label(
            details_frame,
            text=f"Size: {self._format_size(file_size)}"
        ).pack(anchor="w")
        
        ttk.Label(
            details_frame,
            text=f"Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}"
        ).pack(anchor="w")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(
            button_frame,
            text="Overwrite",
            command=self._overwrite
        ).pack(side="left", padx=5)
        
        ttk.Button(
            button_frame,
            text="Save As...",
            command=self._save_as
        ).pack(side="left", padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side="right", padx=5)
        
        # Center the window
        self.center_window()
        
    def _format_size(self, size):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def center_window(self):
        """Center the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def _overwrite(self):
        """Handle overwrite button click."""
        self.result = "overwrite"
        self.destroy()
        
    def _save_as(self):
        """Handle save as button click."""
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if filepath:
            self.result = "saveas"
            self.new_filepath = filepath
            self.destroy()
        
    def _cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy() 