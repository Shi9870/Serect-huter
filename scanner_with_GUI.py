import os 
import re
import tkinter as tk
from tkinter import filedialog,messagebox,scrolledtext
import sqlite3
from db_mannger import KeywordDB
from PIL import Image,ImageTk

#GUI Setting
ICON_SIZE = (32,32)
# core function 
def load_KeyWords():
    try:
        db = KeywordDB()

        keyword_list = db.get_all_keyword()

        print(f"Keyword List:{keyword_list}")

        if keyword_list and len(keyword_list) > 0:
            return "|".join(keyword_list)
        else:
            return None
    except Exception as e:
        print("Fail to connect the database")
        return None


#regex load the string 
regex_string = load_KeyWords()

if regex_string:
    Keywords_pattern = re.compile(regex_string, re.IGNORECASE)
    print("You got the key word")
else:
    Keywords_pattern = None
    print("You fail to get the word")
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

#setting section
def open_settings():
    db = KeywordDB()
    keyword_list = db.get_all_keyword()
    setting_win = tk.Toplevel(window)
    setting_win.title("Setting")
    setting_win.geometry("400x300")
    tk.Label(setting_win,text="Keyword List").pack(pady=5)
    
    setting_win.grab_set()
    list_frame = tk.Frame(setting_win)
    list_frame.pack(pady=10)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT,fill=tk.Y)

    keyword_listbox = tk.Listbox(list_frame,width=40,height=10,yscrollcommand=scrollbar.set)
    keyword_listbox.pack(side=tk.LEFT)
    scrollbar.config(command=keyword_listbox.yview)

    words = load_KeyWords()

    keyword_listbox.insert(tk.END,words)

    # Entry Button
    add_frame = tk.Frame(setting_win)
    add_frame.pack(pady=5)
    tk.Label(add_frame,text="Add New Keyword").pack(side=tk.LEFT)

    new_word_entry = tk.Entry(add_frame, width=20)
    new_word_entry.pack(side=tk.LEFT,padx=5)

    #Refresh list view
    def refresh_listbox():
        keyword_listbox.delete(0,tk.END)
        latest_word = db.get_all_keyword()

        for w in latest_word:
            keyword_listbox.insert(tk.END,w)

    # add_keyword function
    def add_words():
        word = new_word_entry.get().strip()
        if not word:
            return
        success =db.add_keyword(word=word)
        if success:
            messagebox.showinfo(title="Happy insert",message=f"Word {word} insert successfully")
            new_word_entry.delete(0,tk.END)
            refresh_listbox()
        else:
            messagebox.showwarning(title="Oops same word",message=f"The keyword {word} already exist in the list")
    
    def delete_words():
        selection = keyword_listbox.curselection()

        if not selection:
            messagebox.showwarning("Warring","Please select a keyword to delete")
            return
        
        index = selection[0]
        word_to_delete = keyword_listbox.get(index)
        confirm = messagebox.askyesno("Confirm",f"Are you sure you want to delete {word_to_delete}")

        if confirm:
            db.delete_keyword(word_to_delete)

            refresh_listbox()
            messagebox.showinfo("Delete",f"Word {word_to_delete} has beenn removed")

    btn_add = tk.Button(add_frame,text= "Add",bg="#ccffcc",command=add_words)
    btn_add.pack(side=tk.LEFT)


    #建立delete_key function
    btn_del = tk.Button(setting_win,text="Choose the one you want to delete",bg="#ffcccc",command=delete_words)
    btn_del.pack(pady=10)
    refresh_listbox()

window = tk.Tk()
window.title("Secret Hunter v1.0")
window.geometry("600x500")


frame_top = tk.Frame(window, pady=10)
frame_top.pack()

tk.Label(frame_top,text="Target file:").pack(side=tk.LEFT)

#Path area
path_entry =  tk.Entry(frame_top, width=40)
path_entry.pack(side=tk.LEFT,padx=5)
btn_select = tk.Button(frame_top,text=" File viewing",command=select_folder)
btn_select.pack(side=tk.LEFT)

#Start Button
btn_start = tk.Button(window, text="Start Scanning",command=start_scan,bg="#ffcccc", font=("Arial", 12, "bold"))
btn_start.pack(pady=5)

#Setting Button 
current_dir = os.path.dirname(os.path.abspath(__file__))
img_folder = os.path.join(current_dir,"img")
setting_path = os.path.join(img_folder, "setting.png")

setting_img = None

try:
    pil_img = Image.open(setting_path)

    resize_image = pil_img.resize(ICON_SIZE,Image.LANCZOS)

    setting_img = ImageTk.PhotoImage(resize_image)
    print("success to loaded and resize the image")

except FileNotFoundError:
    print(f"Error Fail to find the image:{setting_path}")
except Exception as e:
    print(f"Failed to load / resize the image:{e}")

if setting_img:

    btn_setting = tk.Button(frame_top, image=setting_img, bd=0, command=open_settings)
    btn_setting.image = setting_img 
else:
    btn_setting = tk.Button(frame_top, text="Setting", command=open_settings)

btn_setting.pack(side=tk.LEFT, padx=10)

tk.Label(window, text="Result").pack(anchor=tk.W,padx=10)
result_area = scrolledtext.ScrolledText(window,width = 70,height = 20)
result_area.pack(padx=10,pady=10)

window.mainloop()