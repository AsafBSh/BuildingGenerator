import tkinter as tk
import customtkinter as Ctk
import threading
import time
import tkinter.messagebox as messagebox
import logging
import traceback
import os
from enum import Enum
from typing import Callable, Optional, Any, Dict, Union

# Set up logging - use standard pattern to inherit from main application
logger = logging.getLogger(__name__)

class ProcessType(Enum):
    """Enum of process types that can use the ProcessingWindow"""
    OBJECTIVE_TEMPLATE_GENERATION = "objective_template_generation"
    CT_TEMPLATE_GENERATION = "ct_template_generation"
    CALCULATE_DEFAULT_VALUES = "calculate_default_values"


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
        width: int = 400,
        height: int = 180,
        process_type: Optional[ProcessType] = None,
        show_progress: bool = False,
        show_details: bool = False
    ):
        logger.debug(f"Initializing ProcessingWindow: title='{title}', size={width}x{height}")
        self.parent = parent
        self.title = title
        self.message = message
        self.width = width
        self.height = height
        self.is_open = False
        self.process_type = process_type
        self.show_progress = show_progress
        self.show_details = show_details
        self.current_progress = 0
        self.max_progress = 100
        self.status_details = []
        self._create_window()
    
    def _create_window(self):
        """Create the processing window."""
        # Create the window with error handling for CustomTkinter scaling issues
        try:
            self.window = Ctk.CTkToplevel(self.parent)
            self.window.title(self.title)
            self.window.geometry(f"{self.width}x{self.height}")
            self.window.resizable(False, False)
            self.window.transient(self.parent)  # Set as transient to parent
            self.window.grab_set()  # Make window modal
            
            # Center the window relative to the parent
            self.center_window()
        except AttributeError as e:
            # Handle CustomTkinter scaling issues by patching the missing method
            if "block_update_dimensions_event" in str(e):
                logger.debug("Handling CustomTkinter scaling issue in window creation")
                # Add the missing method as a no-op function to prevent errors
                setattr(self.window.tk, 'block_update_dimensions_event', lambda: None)
                # Try again after patching
                self.window.title(self.title)
                self.window.geometry(f"{self.width}x{self.height}")
                self.window.resizable(False, False)
                self.window.transient(self.parent)
                self.window.grab_set()
                self.center_window()
            else:
                # Re-raise other attribute errors
                raise
        
        # Configure grid
        self.window.grid_columnconfigure(0, weight=1)
        
        # Add message label
        self.message_label = Ctk.CTkLabel(
            self.window, 
            text=self.message,
            font=("Inter", 14)
        )
        self.message_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        current_row = 1
        
        # Add progress bar - either determinate or indeterminate based on settings
        if self.show_progress:
            # Determinate progress bar with percentage
            self.progress_frame = Ctk.CTkFrame(self.window, fg_color="transparent")
            self.progress_frame.grid(row=current_row, column=0, padx=20, pady=5, sticky="ew")
            self.progress_frame.grid_columnconfigure(0, weight=1)
            self.progress_frame.grid_columnconfigure(1, weight=0)
            
            self.progress_bar = Ctk.CTkProgressBar(
                self.progress_frame,
                mode="determinate",
                width=self.width - 80
            )
            self.progress_bar.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
            self.progress_bar.set(0)  # Initialize to 0
            
            self.progress_label = Ctk.CTkLabel(
                self.progress_frame,
                text="0%",
                width=40,
                font=("Inter", 12)
            )
            self.progress_label.grid(row=0, column=1, padx=0, pady=0, sticky="e")
        else:
            # Indeterminate progress bar (simple animation)
            self.progress_indicator = Ctk.CTkProgressBar(
                self.window,
                mode="indeterminate",
                width=self.width - 40
            )
            self.progress_indicator.grid(row=current_row, column=0, padx=20, pady=5, sticky="ew")
            self.progress_indicator.start()  # Start the animation
        
        current_row += 1
        
        # Add details section if enabled
        if self.show_details:
            # Process type specific label
            if self.process_type == ProcessType.OBJECTIVE_TEMPLATE_GENERATION:
                details_title = "Objective Template Generation Progress"
            elif self.process_type == ProcessType.CT_TEMPLATE_GENERATION:
                details_title = "CT Template Generation Progress"
            elif self.process_type == ProcessType.CALCULATE_DEFAULT_VALUES:
                details_title = "Calculating Default Values Progress"
            else:
                details_title = "Processing Details"
                
            Ctk.CTkLabel(
                self.window,
                text=details_title,
                font=("Inter", 12, "bold")
            ).grid(row=current_row, column=0, padx=20, pady=(10, 0), sticky="w")
            
            current_row += 1
            
            # Details frame with scrollable text area
            self.details_frame = Ctk.CTkFrame(self.window)
            self.details_frame.grid(row=current_row, column=0, padx=20, pady=5, sticky="nsew")
            self.window.grid_rowconfigure(current_row, weight=1)  # Allow details to expand
            
            # Create a text widget for the details
            self.details_text = Ctk.CTkTextbox(
                self.details_frame,
                width=self.width - 40,
                height=80,  # Will expand if window is resized
                font=("Inter", 11)
            )
            self.details_text.pack(fill="both", expand=True)
            self.details_text.configure(state="disabled")  # Make read-only
        
        self.is_open = True
        
        # Disable closing the window with the X button to prevent interrupting processes
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)
    
    def center_window(self):
        """Center the processing window relative to the parent window."""
        try:
            self.parent.update_idletasks()
            
            # Get parent and window geometry
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            
            # Calculate position
            x = parent_x + (parent_width // 2) - (self.width // 2)
            y = parent_y + (parent_height // 2) - (self.height // 2)
            
            # Apply the geometry
            self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
        except AttributeError as e:
            # Handle CustomTkinter scaling issues
            if "block_update_dimensions_event" in str(e):
                logger.debug("Handling CustomTkinter scaling issue in center_window")
                # Add the missing method as a no-op function
                setattr(self.window.tk, 'block_update_dimensions_event', lambda: None)
                try:
                    # Try again after patching
                    self.parent.update_idletasks()
                    
                    # Get parent and window geometry
                    parent_width = self.parent.winfo_width()
                    parent_height = self.parent.winfo_height()
                    parent_x = self.parent.winfo_rootx()
                    parent_y = self.parent.winfo_rooty()
                    
                    # Calculate position
                    x = parent_x + (parent_width // 2) - (self.width // 2)
                    y = parent_y + (parent_height // 2) - (self.height // 2)
                    
                    # Apply the geometry
                    self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
                except Exception as nested_e:
                    # If still fails, use a default position
                    logger.warning(f"Could not center window: {nested_e}")
                    self.window.geometry(f"{self.width}x{self.height}+100+100")
            else:
                # Other attribute errors, just use default positioning
                logger.warning(f"Error in center_window: {e}")
                self.window.geometry(f"{self.width}x{self.height}+100+100")
        
        # Geometry is already set in the try/except blocks
    
    def update_message(self, message: str):
        """Update the message displayed in the window."""
        if self.is_open:
            logger.debug(f"Updating processing window message: {message}")
            # Use after method to ensure thread safety when updating from worker thread
            self.window.after(0, lambda: self._update_message_safe(message))
    
    def _update_message_safe(self, message: str):
        """Thread-safe implementation to update the message on the main thread."""
        if self.is_open:
            self.message_label.configure(text=message)
            self.window.update_idletasks()
    
    def update_progress(self, current: int, maximum: int = None):
        """
        Update the progress bar with a new value.
        
        Args:
            current: Current progress value
            maximum: Optional new maximum value
        """
        if not self.show_progress or not self.is_open:
            return
            
        logger.debug(f"Updating progress: {current}/{maximum if maximum else self.max_progress}")
        # Use after method to ensure thread safety when updating from worker thread
        self.window.after(0, lambda: self._update_progress_safe(current, maximum))
    
    def _update_progress_safe(self, current: int, maximum: int = None):
        """Thread-safe implementation to update the progress on the main thread."""
        if not self.is_open or not self.show_progress:
            return
            
        # Update max_progress if provided
        if maximum is not None:
            self.max_progress = max(1, maximum)  # Ensure max is at least 1 to avoid division by zero
        
        # Update current progress
        self.current_progress = min(current, self.max_progress)  # Cap at maximum
        
        # Calculate percentage for progress bar
        percentage = self.current_progress / self.max_progress
        self.progress_bar.set(percentage)
        
        # Update percentage label
        percent_text = f"{int(percentage * 100)}%"
        self.progress_label.configure(text=percent_text)
        
        # Ensure UI is updated
        self.window.update_idletasks()
    
    def add_detail(self, message: str):
        """
        Add a new detail message to the details section.
        
        Args:
            message: Status message to add
        """
        if not self.show_details or not self.is_open:
            return
            
        # Use after method to ensure thread safety when updating from worker thread
        self.window.after(0, lambda: self._add_detail_safe(message))
    
    def _add_detail_safe(self, message: str):
        """Thread-safe implementation to add a detail message on the main thread."""
        if not self.is_open or not self.show_details:
            return
            
        # Create a timestamped message
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        # Add to internal list for tracking
        self.status_details.append(full_message)
        
        # Update the text widget
        self.details_text.configure(state="normal")  # Allow editing
        
        # Add message with newline
        if self.details_text.get("1.0", "end-1c"):
            # If there's already content, add a newline first
            self.details_text.insert("end", f"\n{full_message}")
        else:
            # First line, no newline needed
            self.details_text.insert("end", full_message)
            
        # Auto-scroll to the bottom
        self.details_text.see("end")
        
        # Make read-only again
        self.details_text.configure(state="disabled")
        
        # Ensure UI is updated
        self.window.update_idletasks()
    
    def close(self):
        """Close the processing window."""
        if self.is_open:
            logger.debug(f"Closing processing window: {self.title}")
            # Use after method to ensure thread safety when closing from worker thread
            self.window.after(0, self._close_safe)
    
    def _close_safe(self):
        """Thread-safe implementation to close the window on the main thread."""
        if self.is_open:
            # Stop animations/progress
            if self.show_progress:
                pass  # No need to stop determinate progress bar
            else:
                # Stop indeterminate animation
                self.progress_indicator.stop()
            
            # Destroy the window
            self.window.grab_release()
            self.window.destroy()
            self.is_open = False
            

def run_with_processing(parent, task_function, title="Processing", message="Please wait...", 
                       process_type=None, show_progress=False, show_details=False, width=400, height=180):
    """
    Run a task function with a processing window displayed.
    
    This creates a processing window to display while the task is executed in a
    background thread, then returns the result of the task function.
    
    Args:
        parent: The parent window
        task_function: The function to execute in the background
        title: Title for the processing window
        message: Message to display in the processing window
        process_type: ProcessType enum value (for specialized processing)
        show_progress: Whether to show a progress bar
        show_details: Whether to show a details section
        width: Width of the processing window
        height: Height of the processing window
        
    Returns:
        The result of the task function
    """
    import tkinter as tk
    from tkinter import ttk
    import queue
    import threading
    import time
    import logging
    import traceback
    
    logger.info(f"Starting background task with processing window: {title}")
    
    # Use standard tkinter Toplevel instead of CustomTkinter to avoid scaling issues
    processing_window = tk.Toplevel(parent)
    processing_window.title(title)
    processing_window.geometry(f"{width}x{height}")
    processing_window.resizable(False, False)
    processing_window.transient(parent)  # Set as transient to parent
    processing_window.grab_set()  # Make window modal
    
    # Center the window
    try:
        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2)
        py = parent.winfo_rooty() + (parent.winfo_height() // 2)
        x = px - (width // 2)
        y = py - (height // 2)
        processing_window.geometry(f"{width}x{height}+{x}+{y}")
        logger.debug(f"Created processing window '{title}' at position {x},{y}")
    except Exception as e:
        logger.warning(f"Error centering window: {e}")
        processing_window.geometry(f"{width}x{height}+100+100")
    
    # Configure grid
    processing_window.grid_columnconfigure(0, weight=1)
    
    # Add message label
    label = tk.Label(
        processing_window, 
        text=message,
        font=("Arial", 12)
    )
    label.pack(pady=(20, 10), padx=20)
    
    # Add a progress bar (indeterminate for tasks without progress reporting)
    progress = ttk.Progressbar(
        processing_window, 
        mode='indeterminate',
        length=width-40
    )
    progress.pack(pady=10, padx=20)
    progress.start(10)  # Start the animation
    
    # Make sure the window can't be closed with the X button
    processing_window.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # Create a queue for the task thread to return results
    result_queue = queue.Queue()
    
    # Flag to track if the window is destroyed
    window_destroyed = False
    
    # Function for the background thread
    def background_task():
        try:
            # Call the task function with the processing window parameter
            try:
                # Pass the processing window to the task function
                task_result = task_function(processing_window)
                # Only convert None to True, preserve all other return values
                if task_result is None:
                    # For backward compatibility, convert None to True
                    task_result = True
            except Exception as e:
                # Handle exceptions from the task - reduced verbosity
                import traceback
                # Just log errors instead of printing them
                logger.error(f"Error in task execution: {e}")
                logger.debug(traceback.format_exc())
                # In case of an error, return False to indicate failure
                task_result = False
            
            # Put the actual result in the queue, preserving its type and structure
            result_queue.put(("result", task_result))
            
            # Schedule completion in the main thread
            parent.after(0, completion_handler)
        except Exception as e:
            # Put the error in the queue
            result_queue.put(("error", e))
            
            # Schedule error handling in the main thread
            parent.after(0, error_handler)
    
    # Handler for successful completion
    def completion_handler():
        try:
            processing_window.grab_release()
            processing_window.destroy()
            logger.debug("Processing window closed successfully")
        except Exception as e:
            logger.warning(f"Error closing window: {e}")
    
    # Handler for errors
    def error_handler():
        try:
            processing_window.grab_release()
            processing_window.destroy()
        except Exception as e:
            logger.warning(f"Error closing window: {e}")
            
        try:
            error_details = traceback.format_exc()
            error_data = result_queue.get()[1]
            
            # Show error in message box
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"An error occurred during processing:\n{str(error_data)}"
            )
            
            # Log the error
            logger.error(f"Error in background task: {error_details}")
        except Exception as e:
            logger.warning(f"Error showing error message: {e}")
    
    # Start the background thread
    thread = threading.Thread(target=background_task)
    thread.daemon = True  # Thread will be terminated when main thread exits
    logger.debug(f"Starting background thread for task: {title}")
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
            # No result yet, keep waiting
            time.sleep(0.05)  # Small delay to prevent CPU hogging


def create_template_generation_window(parent, process_type, title=None, message=None):
    """
    Create a simple processing window for template generation processes.
    
    Args:
        parent: The parent window
        process_type: ProcessType enum value (OBJECTIVE_TEMPLATE_GENERATION or CT_TEMPLATE_GENERATION)
        title: Optional custom title (if None, a default based on process_type will be used)
        message: Optional custom message (if None, a default based on process_type will be used)
        
    Returns:
        A standard ProcessingWindow instance for template generation
    """
    # Set defaults based on process type
    if process_type == ProcessType.OBJECTIVE_TEMPLATE_GENERATION:
        default_title = "Generating Objective Templates"
        default_message = "Generating objective templates"
    elif process_type == ProcessType.CT_TEMPLATE_GENERATION:
        default_title = "Generating CT Templates"
        default_message = "Generating CT templates"
    elif process_type == ProcessType.CALCULATE_DEFAULT_VALUES:
        default_title = "Calculating Default Values"
        default_message = "Calculating median values from existing objectives"
    else:
        default_title = "Processing"
        default_message = "Please wait..."
    
    # Use provided values or defaults
    title = title or default_title
    message = message or default_message
    
    # Create a standard processing window without extra details
    return ProcessingWindow(
        parent=parent,
        title=title,
        message=message,
        process_type=process_type,  # Keep process_type for identification only
        show_progress=False,  # Use indeterminate progress bar
        show_details=False,   # No details section
        width=350,           # Standard width
        height=120           # Standard height
    )


def run_template_generation(parent, task_function, process_type, title=None, message=None):
    """
    Convenience function to run a template generation task with standard UI.
    
    Args:
        parent: The parent window
        task_function: The function to execute in the background
        process_type: ProcessType enum value (OBJECTIVE_TEMPLATE_GENERATION or CT_TEMPLATE_GENERATION)
        title: Optional custom title
        message: Optional custom message
        
    Returns:
        The result of the task function
    """
    # Log debug info about the process type to track loading
    logger.debug(f"Starting template generation with process type: {process_type.name}")
    
    # Set defaults based on process type
    if process_type == ProcessType.OBJECTIVE_TEMPLATE_GENERATION:
        default_title = "Generating Objective Templates"
        default_message = "Generating objective templates..."
    elif process_type == ProcessType.CT_TEMPLATE_GENERATION:
        default_title = "Generating CT Templates"
        default_message = "Generating CT templates..."
    elif process_type == ProcessType.CALCULATE_DEFAULT_VALUES:
        default_title = "Calculating Default Values"
        default_message = "Calculating median values from existing objectives..."
    else:
        default_title = "Processing"
        default_message = "Please wait..."
    
    # Use provided values or defaults
    title = title or default_title
    message = message or default_message
    
    # Run the task with a standard processing window
    logger.info(f"Running task with processing window: {title}")
    result = run_with_processing(
        parent=parent,
        task_function=task_function,
        title=title,
        message=message,
        process_type=process_type,  # Keep process_type for identification only
        show_progress=False,  # Use indeterminate progress bar
        show_details=False,   # No details section
        width=350,           # Standard width
        height=120           # Standard height
    )
    logger.debug(f"Task completed for {process_type.name}")
    return result