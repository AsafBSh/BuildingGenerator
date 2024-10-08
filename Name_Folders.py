import os
import tkinter as tk
from tkinter import filedialog, messagebox


def select_directory():
    folder_path = filedialog.askdirectory()
    directory_entry.delete(0, tk.END)
    directory_entry.insert(0, folder_path)


def create_folders():
    start = int(start_entry.get())
    end = int(end_entry.get())
    directory = directory_entry.get()
    for i in range(start, end + 1):
        folder_path = os.path.join(directory, str(i))
        if os.path.exists(folder_path):
            messagebox.showerror("Error", f"Folder name '{i}' already exists")
            return
        else:
            os.mkdir(folder_path)
    messagebox.showinfo(
        "Success", f"Folders created from {start} to {end} in {directory}"
    )


root = tk.Tk()
root.title("Folder Creator")
root.geometry("300x200")

root.title("Folder Creator")
start_label = tk.Label(root, text="Start:")
start_label.pack()
start_entry = tk.Entry(root)
start_entry.pack()

end_label = tk.Label(root, text="End:")
end_label.pack()
end_entry = tk.Entry(root)
end_entry.pack()


select_button = tk.Button(root, text="Select Directory", command=select_directory)
select_button.pack()

directory_label = tk.Label(root, text="Directory:")
directory_label.pack()
directory_entry = tk.Entry(root)
directory_entry.pack()


create_button = tk.Button(root, text="Create folders", command=create_folders)
create_button.pack()


root.mainloop()
