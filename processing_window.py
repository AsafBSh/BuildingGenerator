import tkinter as tk
import customtkinter as Ctk
import threading
import time
import tkinter.messagebox as messagebox
import logging
import traceback

class ProcessingWindow:
    """
    A simple modal processing window that displays a basic progress animation
    and status message while long-running operations are performed.
    
    This window provides visual feedback that the application is still working
    and not frozen during lengthy operations.
    """
    
    def __init__(
        self, 
        parent: tk.Tk, 
        title: str = "Processing", 
        message: str = "Please wait...",
        width: int = 350,
        height: int = 120
    ):
        self.parent = parent
        self.title = title
        self.message = message
        self.width = width
        self.height = height
        self.is_open = False
        self._create_window()
    
    def _create_window(self):
        """Create the processing window."""
        self.window = Ctk.CTkToplevel(self.parent)
        self.window.title(self.title)
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.resizable(False, False)
        self.window.transient(self.parent)  # Set as transient to parent
        self.window.grab_set()  # Make window modal
        
        # Center the window relative to the parent
        self.center_window()
        
        # Configure grid
        self.window.grid_columnconfigure(0, weight=1)
        
        # Add message label
        self.message_label = Ctk.CTkLabel(
            self.window, 
            text=self.message,
            font=("Inter", 14)
        )
        self.message_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Add indeterminate progress bar (simple animation)
        self.progress_indicator = Ctk.CTkProgressBar(
            self.window,
            mode="indeterminate",
            width=self.width - 40
        )
        self.progress_indicator.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progress_indicator.start()  # Start the animation
        
        self.is_open = True
        
        # Disable closing the window with the X button to prevent interrupting processes
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)
    
    def center_window(self):
        """Center the processing window relative to the parent window."""
        self.parent.update_idletasks()
        
        # Get parent and window geometry
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        
        # Calculate position
        x = parent_x + (parent_width // 2) - (self.width // 2)
        y = parent_y + (parent_height // 2) - (self.height // 2)
        
        # Set geometry
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
    
    def update_message(self, message: str):
        """Update the message displayed in the window."""
        if self.is_open:
            # Use after method to ensure thread safety when updating from worker thread
            self.window.after(0, lambda: self._update_message_safe(message))
    
    def _update_message_safe(self, message: str):
        """Thread-safe implementation to update the message on the main thread."""
        if self.is_open:
            self.message_label.configure(text=message)
            self.window.update_idletasks()
    
    def close(self):
        """Close the processing window."""
        if self.is_open:
            # Use after method to ensure thread safety when closing from worker thread
            self.window.after(0, self._close_safe)
    
    def _close_safe(self):
        """Thread-safe implementation to close the window on the main thread."""
        if self.is_open:
            # Stop indeterminate animation
            self.progress_indicator.stop()
            
            # Destroy the window
            self.window.grab_release()
            self.window.destroy()
            self.is_open = False


def run_with_processing(parent, task_function, title="Processing", message="Please wait..."):
    """
    Execute a task in a background thread while displaying a processing window.
    
    Args:
        parent: The parent window
        task_function: The function to execute in the background
        title: Title for the processing window
        message: Initial message for the processing window
        
    Returns:
        The result of the task function
    """
    import threading
    import time
    import queue
    
    # Create a queue to hold the result of the task
    result_queue = queue.Queue()
    
    # Create the processing window
    processing_window = ProcessingWindow(
        parent=parent,
        title=title,
        message=message
    )
    
    # Function for the background thread
    def background_task():
        try:
            # Call the task function with the processing window for status updates
            result = task_function(processing_window)
            
            # Put the result in the queue
            result_queue.put(("result", result))
            
            # Schedule completion in the main thread
            parent.after(0, completion_handler)
        except Exception as e:
            # Put the error in the queue
            result_queue.put(("error", e))
            
            # Schedule error handling in the main thread
            parent.after(0, error_handler)
    
    # Handler for successful completion
    def completion_handler():
        processing_window.close()
    
    # Handler for errors
    def error_handler():
        processing_window.close()
        error_details = traceback.format_exc()
        
        # Show error in message box
        messagebox.showerror(
            "Error",
            f"An error occurred during processing:\n{str(result_queue.get()[1])}"
        )
        
        # Log the error
        logging.getLogger(__name__).error(f"Error in background task: {error_details}")
    
    # Start the background thread
    thread = threading.Thread(target=background_task)
    thread.daemon = True  # Thread will be terminated when main thread exits
    thread.start()
    
    # Wait for the result or error (blocking)
    while True:
        parent.update_idletasks()  # Keep the UI responsive while waiting
        parent.update()
        
        try:
            # Check if we have a result or error
            if not result_queue.empty():
                result_type, result_data = result_queue.get(block=False)
                if result_type == "error":
                    # Re-raise the error from the main thread
                    raise result_data
                else:
                    # Return the result
                    return result_data
        except queue.Empty:
            # Queue is empty, continue waiting
            pass
        
        time.sleep(0.05)  # Small sleep to avoid CPU hogging