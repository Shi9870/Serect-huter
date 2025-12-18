import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import time
from main_function.detector import MLDetector

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SecretHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Sensitive Detector")
        self.geometry("1100x750")
        
        # Initialize the AI detector instance
        self.detector = MLDetector()
        self.scanning = False
        self.stop_event = threading.Event() # Event to handle thread stopping safely

        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar setup ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="Leak Detection", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(padx=20, pady=(20, 10))

        self.btn_select = ctk.CTkButton(self.sidebar, text="Select Folder", command=self.select_folder)
        self.btn_select.pack(padx=20, pady=10)
        
        self.path_label = ctk.CTkLabel(self.sidebar, text="Not selected", text_color="gray", wraplength=180)
        self.path_label.pack(padx=20, pady=(0, 20))

        # Button command is dynamic (Start or Cancel)
        # Initial State: GREEN for "Start" (User Friendly)
        self.btn_action = ctk.CTkButton(
            self.sidebar, 
            text="Start Scanning", 
            fg_color="#2CC985",      # Green color for START
            hover_color="#25A96F",   # Darker green for hover
            command=self.toggle_scan
        )
        self.btn_action.pack(padx=20, pady=10)

        # --- Main content area setup ---
        self.main_area = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_area.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1) # Result area expands
        self.main_area.grid_columnconfigure(0, weight=1)

        # --- 1. Fixed Progress Display Area ---
        self.status_frame = ctk.CTkFrame(self.main_area, height=40)
        self.status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.status_frame.grid_columnconfigure(1, weight=1) # Progress bar expands

        # Col 0: Status Text (Fixed width or left aligned)
        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready", anchor="w", width=250)
        self.status_label.grid(row=0, column=0, padx=10, pady=5)

        # Col 1: Progress Bar (Stretches)
        self.progress_bar = ctk.CTkProgressBar(self.status_frame)
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=10)
        self.progress_bar.set(0)

        # Col 2: Percentage (Fixed location on the right)
        self.pct_label = ctk.CTkLabel(self.status_frame, text="0%", width=50, anchor="e")
        self.pct_label.grid(row=0, column=2, padx=10)

        # --- 2. Grouped Results (Tabview) ---
        self.result_tabs = ctk.CTkTabview(self.main_area)
        self.result_tabs.grid(row=1, column=0, sticky="nsew")
        
        # Create tabs for risk levels
        self.tabs = {
            "CRITICAL": self.result_tabs.add("CRITICAL"),
            "HIGH": self.result_tabs.add("HIGH"),
            "MEDIUM": self.result_tabs.add("MEDIUM"),
            "LOW": self.result_tabs.add("LOW"),
            "ALL": self.result_tabs.add("ALL LOGS")
        }
        
        # Create a text box inside each tab
        self.text_widgets = {}
        for level, tab in self.tabs.items():
            # Configure grid for the tab
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
            
            # Textbox
            tb = ctk.CTkTextbox(tab, font=("Consolas", 14))
            tb.grid(row=0, column=0, sticky="nsew")
            
            # --- FIX: Access internal tkinter widget to avoid AttributeError on 'font' ---
            # 1. Configure default match text color
            tb._textbox.tag_config("match", foreground="#CCCCCC")
            
            # 2. Configure file name style (Bold + White)
            tb._textbox.tag_config("file", font=("Consolas", 14, "bold"), foreground="white")
            
            # 3. Configure risk level colors
            if level == "CRITICAL": tb._textbox.tag_config("risk", foreground="#FF4444")
            elif level == "HIGH": tb._textbox.tag_config("risk", foreground="#FF8800")
            elif level == "MEDIUM": tb._textbox.tag_config("risk", foreground="#FFCC00")
            elif level == "LOW": tb._textbox.tag_config("risk", foreground="#00CC00")
            else: tb._textbox.tag_config("risk", foreground="#CCCCCC") # All logs
            
            self.text_widgets[level] = tb

        # Initial check for model loading
        if self.detector.model:
            self.log_to_tab("ALL", "System: ML Model loaded successfully.\n", "risk")
        else:
            self.log_to_tab("ALL", "System: Failed to load ML model.\n", "risk")

    def select_folder(self):
        """Open a dialog to select the target directory."""
        folder = filedialog.askdirectory()
        if folder:
            self.path_label.configure(text=os.path.basename(folder))
            self.target_path = folder
            self.status_label.configure(text="Target selected.")

    def log_to_tab(self, level, message, tag=None):
        """Helper to write logs to specific tabs safely."""
        # Always log to the 'ALL' tab
        self.text_widgets["ALL"].insert(tk.END, message, tag)
        self.text_widgets["ALL"].see(tk.END)
        
        # Log to the specific risk tab if applicable (and not 'ALL')
        if level in self.text_widgets and level != "ALL":
            self.text_widgets[level].insert(tk.END, message, tag)
            self.text_widgets[level].see(tk.END)

    def toggle_scan(self):
        """Handles the logic for both Start and Cancel actions."""
        if self.scanning:
            # Action: STOP / CANCEL
            self.scanning = False
            self.stop_event.set() # Signal the thread to stop
            self.btn_action.configure(text="Stopping...", state="disabled")
        else:
            # Action: START
            self.start_scan_thread()

    def start_scan_thread(self):
        """Prepares UI and starts the scanning thread."""
        if not hasattr(self, 'target_path'):
            messagebox.showwarning("Hint", "Please select target folder first")
            return
        
        self.scanning = True
        self.stop_event.clear()
        
        # Clear previous results
        for tb in self.text_widgets.values():
            tb.delete("1.0", tk.END)

        # UI Update: Change button to RED "STOP" state
        self.btn_action.configure(
            text="STOP SCANNING", 
            fg_color="#e63946",    # Red for STOP
            hover_color="#d62828"  # Darker red
        )
        
        threading.Thread(target=self.run_scan, daemon=True).start()

    def run_scan(self):
        """Background thread function to perform the file scanning."""
        file_list = []
        
        # Gather files recursively
        for root, dirs, files in os.walk(self.target_path):
            # Exclude common non-source directories
            if '.git' in dirs: dirs.remove('.git') 
            if 'venv' in dirs: dirs.remove('venv') 
            if '__pycache__' in dirs: dirs.remove('__pycache__')
            
            # Check for cancellation signal
            if self.stop_event.is_set(): break

            for f in files:
                # Filter by common code file extensions
                if f.endswith(('.py', '.js', '.json', '.txt', '.md', '.env', '.yml', '.xml', '.html')):
                    file_list.append(os.path.join(root, f))

        total = len(file_list)
        if total == 0:
            self.after(0, lambda: self.status_label.configure(text="No target files found."))
            self.after(0, lambda: self.finish_scan(0))
            return

        found_issues = 0
        
        for i, filepath in enumerate(file_list):
            # --- 1. Check Cancellation ---
            if self.stop_event.is_set():
                self.after(0, lambda: self.log_to_tab("ALL", "\n[!] Scan cancelled by user.", "risk"))
                break 

            # --- 2. Update Progress UI ---
            # Calculate progress
            progress = (i + 1) / total
            fname = os.path.basename(filepath)
            
            # Truncate filename if too long for the status label
            display_name = (fname[:30] + '..') if len(fname) > 30 else fname
            
            # Schedule UI update on main thread
            self.after(0, self.update_progress_ui, display_name, progress)
            
            try:
                # Skip empty files
                if os.path.getsize(filepath) == 0: continue

                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.splitlines()

                    for line_idx, line in enumerate(lines, 1):
                        # Call ML detector
                        results = self.detector.scan_line(line, line_idx)
                        
                        for res in results:
                            found_issues += 1
                            risk = res['risk'].upper()
                            
                            # Format output
                            header = f"\n[{risk}] {os.path.basename(filepath)} : Line {res['line']}\n"
                            details = f"      Match: {res['word']} (Score: {res['score']}%)\n"
                            
                            # Log result via main thread
                            self.after(0, self.log_to_tab, risk, header, "file")
                            self.after(0, self.log_to_tab, risk, details, "risk")
                            
            except Exception:
                pass

        # Use after() to ensure finish_scan runs on main thread
        self.after(0, self.finish_scan, found_issues)

    def update_progress_ui(self, filename, progress):
        """Update progress bar and labels."""
        self.status_label.configure(text=f"Scanning: {filename}")
        self.progress_bar.set(progress)
        self.pct_label.configure(text=f"{int(progress * 100)}%")

    def finish_scan(self, found_issues=0):
        """Reset UI state after scanning finishes or is cancelled."""
        self.scanning = False
        
        # Reset button to GREEN "Start" state
        self.btn_action.configure(
            state="normal", 
            text="Start Scanning", 
            fg_color="#2CC985",    # Back to Green
            hover_color="#25A96F"
        )
        
        if self.stop_event.is_set():
            self.status_label.configure(text="Scan Cancelled")
        else:
            self.status_label.configure(text="Scan Complete")
            self.pct_label.configure(text="100%")
            self.progress_bar.set(1)

        if found_issues > 0:
            # We don't block the thread with messagebox here; it's already in main thread or called via after
            messagebox.showinfo("Result", f"Found {found_issues} potential leaks.")

if __name__ == "__main__":
    app = SecretHunterApp()
    app.mainloop()