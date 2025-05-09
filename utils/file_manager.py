import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from tkinter import messagebox
from components.overwrite_dialog import OverwriteDialog

class FileManager:
    """Utility class for managing file operations with overwrite protection."""
    
    # Class variable to store last used directory
    _last_save_directory = None
    
    @staticmethod
    def get_temp_dir() -> Path:
        """Get the temporary directory path, creating it if needed."""
        temp_dir = Path("generated_tmp")
        temp_dir.mkdir(exist_ok=True)
        return temp_dir
        
    @staticmethod
    def get_temp_path(filepath: str) -> Path:
        """Get temporary file path for a given filepath."""
        filename = Path(filepath).name
        return FileManager.get_temp_dir() / f"{filename}.tmp"
    
    @staticmethod
    def check_file_exists(filepath: str) -> bool:
        """Check if a file exists at the given path."""
        return os.path.isfile(filepath)
    
    @staticmethod
    def get_unique_filename(filepath: str) -> str:
        """Generate a unique filename by appending a number if file exists."""
        if not os.path.exists(filepath):
            return filepath
            
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_filepath = os.path.join(directory, new_filename)
            if not os.path.exists(new_filepath):
                return new_filepath
            counter += 1
    
    @staticmethod
    def save_with_confirmation(parent, filepath: str, save_func) -> Tuple[bool, Optional[str]]:
        """Save a file with overwrite protection.
        
        Args:
            parent: Parent window for dialog
            filepath: Target file path
            save_func: Function to call to perform the actual save
            
        Returns:
            Tuple of (success, filepath)
        """
        try:
            # Store directory for future use
            FileManager._last_save_directory = os.path.dirname(os.path.abspath(filepath))
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Get temporary file path
            temp_path = FileManager.get_temp_path(filepath)
            
            # Always save to temp file first
            try:
                save_func(str(temp_path))
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
            
            if os.path.exists(filepath):
                # Show confirmation dialog
                dialog = OverwriteDialog(parent, filepath)
                dialog.wait_window()
                
                if dialog.result == "overwrite":
                    try:
                        # Create backup before overwriting
                        backup_path = str(temp_path) + ".bak"
                        if os.path.exists(filepath):
                            shutil.copy2(filepath, backup_path)
                            
                        # Move temp file to final location
                        shutil.move(str(temp_path), filepath)
                        
                        # Clean up backup
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                            
                        return True, filepath
                    except Exception as e:
                        # Restore from backup if save fails
                        if os.path.exists(backup_path):
                            shutil.move(backup_path, filepath)
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        raise e
                        
                elif dialog.result == "saveas":
                    if dialog.new_filepath:
                        try:
                            # Move temp file to new location
                            shutil.move(str(temp_path), dialog.new_filepath)
                            return True, dialog.new_filepath
                        except Exception as e:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            raise e
                    return False, None
                    
                else:  # Cancel
                    # Keep temp file and return
                    return False, None
                    
            else:
                try:
                    # Create target directory if it doesn't exist
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    
                    # Move temp file to final location
                    shutil.move(str(temp_path), filepath)
                    return True, filepath
                except Exception as e:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise e
                
        except PermissionError:
            messagebox.showerror(
                "Error",
                "Permission denied. Please check file permissions and try again."
            )
            return False, None
            
        except OSError as e:
            messagebox.showerror(
                "Error",
                f"Failed to save file: {str(e)}"
            )
            return False, None
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"An unexpected error occurred: {str(e)}"
            )
            return False, None
            
    @staticmethod
    def get_last_save_directory() -> Optional[str]:
        """Get the last directory used for saving."""
        return FileManager._last_save_directory
        
    @staticmethod
    def cleanup_temp_files():
        """Clean up any remaining temporary files."""
        temp_dir = FileManager.get_temp_dir()
        if temp_dir.exists():
            for temp_file in temp_dir.glob("*.tmp*"):
                try:
                    temp_file.unlink()
                except:
                    pass 