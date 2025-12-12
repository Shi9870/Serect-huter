import os 
import re
import tkinter as tk
from tkinter import filedialog,messagebox,scrolledtext

# core function 
def load_KeyWords():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path =os.path.join(current_dir,"keyword.txt")

    keywords = []

    if os.path.exists(config_path):
        try:
            with open(config_path,'r',encoding='utf-8') as f:
                for line in f:
                    clean_word = line.strip()
                    if clean_word:
                        keywords.append(clean_word)

            return "|".join(keywords)
        except:
            return None
    return None

#regex load the string 
regex_string = load_KeyWords()

if regex_string:
    Keywords_pattern = re.compile(regex_string, re.IGNORECASE)
else:
    Keywords_pattern = None

#GUI

def select_folder():

    folder_selected = filedialog.askdirectory()

    if folder_selected:
        path_entry.delete(0,tk.END)
        path_entry.insert(0,folder_selected)

def start_scan():

    target_path = path_entry.get()

    if not target_path:
        messagebox.showwarning("warning","Please select one folder")
        return
    if not os.path.exists(target_path):
        messagebox.showerror("Error",f"Can not find {target_path}, please check the route ")
        return
    if not Keywords_pattern:
        messagebox.showerror("Error","Can not find rules or the file is empty")
        return
    

    result_area.delete(1.0,tk.END)
    result_area.insert(tk.END,f"Scanning Start in  {target_path}\n")
    result_area.insert(tk.END,"="*50+"\n")


    found_count =0
    #scanning logic
    for root, dirs, files in os.walk(target_path):
        if '.git' in dirs: dirs.remove(".git")

        for file_name in files:

            if file_name.endswith('.py') or file_name == 'keywords.txt':
                continue

            full_path = os.path.join(root,file_name)

            try:
                with open(full_path,'r', encoding='utf-8',errors='ignore') as f:
                    for line_num, line in enumerate(f,1):
                        if Keywords_pattern.search(line):
                            found_count +=1
                            result_area.insert(tk.END,f"Found leaking in {file_name} at line {line_num}")
                            result_area.insert(tk.END,f"content {line.strip()}")
                            result_area.insert(tk.END,"-"*30+"\n")

                            result_area.see(tk.END)
                            
                            window.update()
                            continue
            except Exception as e:
                result_area.insert(tk.END,f"Can not read {file_name}")

    result_area.insert(tk.END,f"Scanning end. Found {found_count} possible leaks\n")
    messagebox.showinfo("Done",f"Scanning end. Found {found_count} possible leaks")

window = tk.Tk()
window.title("Secret Hunter v1.0")
window.geometry("600x500")


frame_top = tk.Frame(window, pady=10)
frame_top.pack()

tk.Label(frame_top,text="Target file:").pack(side=tk.LEFT)
path_entry =  tk.Entry(frame_top, width=40)
path_entry.pack(side=tk.LEFT,padx=5)
btn_select = tk.Button(frame_top,text=" File viewing",command=select_folder)
btn_select.pack(side=tk.LEFT)

btn_start = tk.Button(window, text="Start Scanning",command=start_scan,bg="#ffcccc", font=("Arial", 12, "bold"))
btn_start.pack(pady=5)

tk.Label(window, text="Result").pack(anchor=tk.W,padx=10)
result_area = scrolledtext.ScrolledText(window,width = 70,height = 20)
result_area.pack(padx=10,pady=10)

window.mainloop()