import tkinter as tk
from tkinter import ttk
import customtkinter as Ctk
import sys
import os
import logging

class InternalConsole(tk.Toplevel):
    """Modern internal console window for the Building Generator application.
    
    Features:
    - Modern UI consistent with application styling
    - Captures stdout and stderr for logging display
    - Single instance management
    - Can be launched from the settings window
    """
    
    # Class variable to track if an instance is already open
    _instance = None
    
    def __init__(self, parent=None):
        """Initialize the Internal Console window.
        
        Args:
            parent: Parent window reference (usually MainPage)
        """
        super().__init__(parent)
        
        # Store reference to parent window
        self.parent = parent
        
        # Set this as the active instance
        InternalConsole._instance = self
        
        # Configure window properties
        self.title("Internal Console")
        self.geometry("800x500")
        self.minsize(600, 400)
        self.configure(bg="#E7E7EF")
        
        # Make it a top window
        self.attributes('-topmost', True)
        
        # Set window icon
        icon_path = os.path.abspath("assets/icon_128.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        # Create UI elements
        self._init_ui()
        
        # Redirect stdout and stderr to the console
        self.stdout_redirector = self.ConsoleRedirector(self.console)
        self.stderr_redirector = self.ConsoleRedirector(self.console, is_error=True)
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector
        
        # Override the close operation
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        
        # Center window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Disable the settings window console button if we were launched from there
        if self.parent and hasattr(self.parent, 'console_window_button'):
            self.parent.console_window_button.configure(state="disabled")
        elif hasattr(parent, 'parent') and hasattr(parent.parent, 'console_window_button'):
            # Handle case where parent is SettingsWindow
            parent.parent.console_window_button.configure(state="disabled")
        
        # Log console opening
        logging.info("Internal console window opened")
    
    @classmethod
    def get_instance(cls):
        """Return the existing console instance or None."""
        return cls._instance
    
    def _init_ui(self):
        """Initialize the user interface components."""
        # Configure the window with CustomTkinter appearance
        self.configure(bg=Ctk.ThemeManager.theme["CTk"]["fg_color"][0])
        
        # Configure the grid layout
        self.grid_rowconfigure(0, weight=0)  # Header row - fixed height
        self.grid_rowconfigure(1, weight=1)  # Console row - expands to fill space
        self.grid_rowconfigure(2, weight=0)  # Button row - fixed height
        self.grid_columnconfigure(0, weight=1)  # Full width
        
        # Create header frame
        self.header_frame = Ctk.CTkFrame(self, fg_color="#D5E3F0", corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        # Add title to header
        Ctk.CTkLabel(
            self.header_frame,
            text="Internal Console",
            font=Ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color="#000000",
            fg_color="transparent"
        ).pack(pady=8)
        
        # Create console frame - Using CTkFrame for a more modern look
        self.console_frame = Ctk.CTkFrame(self, fg_color="#F0F0F5", corner_radius=8)
        self.console_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure console frame grid
        self.console_frame.grid_rowconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(1, weight=0)
        
        # Create a text widget for console output - stick with tk.Text for better compatibility
        # but apply CTk styling to it
        self.console = tk.Text(
            self.console_frame,
            wrap="word",
            font=("Consolas", 12),
            fg="#000000",
            bg="#FFFFFF",
            relief="flat",  # Flatter look for modern style
            borderwidth=0,
            padx=5,
            pady=5
        )
        self.console.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Add scrollbar - use standard scrollbar for compatibility but style it
        scrollbar = tk.Scrollbar(self.console_frame, command=self.console.yview)
        scrollbar.config(width=10)  # Wider scrollbar for better usability
        self.console.config(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 5))
        
        # Create a visible button at the bottom of the window using CTkButton
        self.clear_button = Ctk.CTkButton(
            self,  # Attach directly to the main window
            text="Clear Console",
            font=Ctk.CTkFont(family="Arial", size=12),
            fg_color="#3B8ED0",
            hover_color="#2D7BB7",
            corner_radius=8,
            border_width=0,
            command=self.clear_console
        )
        self.clear_button.grid(row=2, column=0, sticky="e", padx=10, pady=8)
    
    def clear_console(self):
        """Clear all text from the console display."""
        self.console.delete(1.0, tk.END)
        logging.info("Console cleared")
    
    def close_window(self):
        """Handle the window close operation."""
        # Restore original stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
        # Reset instance tracking
        InternalConsole._instance = None
        
        # Re-enable the settings window console button if we were launched from there
        if self.parent and hasattr(self.parent, 'console_window_button'):
            self.parent.console_window_button.configure(state="normal")
        elif hasattr(self.parent, 'parent') and hasattr(self.parent.parent, 'console_window_button'):
            # Handle case where parent is SettingsWindow
            self.parent.parent.console_window_button.configure(state="normal")
            
        # Log console closing
        logging.info("Internal console window closed")
        
        # Destroy the window
        self.destroy()
    
    class ConsoleRedirector:
        """Redirects print outputs to the console text widget."""
        
        def __init__(self, text_widget, is_error=False):
            """Initialize the redirector.
            
            Args:
                text_widget: The text widget to redirect output to
                is_error: Whether this is for stderr (displays in red)
            """
            self.text_widget = text_widget
            self.is_error = is_error
        
        def write(self, text):
            """Write text to the console widget."""
            if self.is_error:
                # Configure tag for error text if it doesn't exist
                if not hasattr(self.text_widget, "error_tag_configured"):
                    self.text_widget.tag_configure("error", foreground="#FF0000")
                    self.text_widget.error_tag_configured = True
                
                # Insert with error tag
                self.text_widget.insert(tk.END, text, "error")
            else:
                # Regular output
                self.text_widget.insert(tk.END, text)
            
            # Scroll to bottom
            self.text_widget.see(tk.END)
            
            # Update UI
            self.text_widget.update_idletasks()
        
        def flush(self):
            """Required for file-like object compatibility."""
            pass

# Function to create or show existing console
def show_console(parent=None):
    """Show the console window, creating it if it doesn't exist.
    
    Args:
        parent: Parent window reference
        
    Returns:
        The console window instance
    """
    # Check if instance already exists
    instance = InternalConsole.get_instance()
    
    if instance is None:
        # Create new instance
        return InternalConsole(parent)
    else:
        # Bring existing window to front
        instance.lift()
        instance.focus_force()
        return instance
