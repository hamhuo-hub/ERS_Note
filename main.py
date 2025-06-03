import os
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import sqlite3
from datetime import datetime, timedelta
import glob
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from collections import Counter
from tkcalendar import Calendar


class EbbinghausNoteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ebbinghaus Note Reviewer")
        self.root.geometry("900x700")
        self.vault_path = r"C:\Users\HuoZihang\Desktop\笔记"
        self.conn = None
        self.notes = []
        self.review_intervals = {
            "proficient": [1, 2, 4, 7, 15],  # days
            "not_proficient": [1, 2, 4, 7],
            "forgotten": [0]
        }
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.setup_db()
        self.create_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_db(self):
        self.conn = sqlite3.connect("notes_review.db")
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                file_path TEXT PRIMARY KEY,
                subject TEXT,
                status TEXT,
                review_count INTEGER,
                last_reviewed DATE,
                next_review DATE
            )
        ''')
        self.conn.commit()

    def create_ui(self):
        # Main frame
        main_frame = ctk.CTkFrame(self.root, corner_radius=12, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(main_frame, fg_color="#F5F5F7", segmented_button_selected_color="#007AFF")
        self.tabview.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Tabs
        self.tabview.add("Review Notes")
        self.tabview.add("Statistics")
        self.tabview.add("Check-in")

        # Review Notes tab
        self.create_review_tab(self.tabview.tab("Review Notes"))

        # Statistics tab
        self.create_stats_tab(self.tabview.tab("Statistics"))

        # Check-in tab
        self.create_checkin_tab(self.tabview.tab("Check-in"))

        # Keyboard shortcuts
        self.root.bind("<Control-a>", self.select_all_notes)
        self.root.bind("<Control-r>", lambda event: self.load_notes())
        self.root.bind("<Control-b>", lambda event: self.browse_vault())
        self.root.bind("<Control-p>", lambda event: self.update_status("proficient"))
        self.root.bind("<Control-n>", lambda event: self.update_status("not_proficient"))
        self.root.bind("<Control-f>", lambda event: self.update_status("forgotten"))
        self.root.bind("<Control-t>", lambda event: self.tabview.set("Statistics"))
        self.root.bind("<Control-k>", lambda event: self.tabview.set("Check-in"))

    def create_review_tab(self, tab):
        # Vault selection
        vault_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#F5F5F7")
        vault_frame.grid(row=0, column=0, sticky="ew", pady=10)
        ctk.CTkLabel(vault_frame, text="Obsidian Vault Path:", font=("Roboto", 14, "bold")).grid(row=0, column=0,
                                                                                                 sticky="w", padx=15,
                                                                                                 pady=10)
        self.vault_entry = ctk.CTkEntry(vault_frame, width=400, font=("Roboto", 12), corner_radius=8,
                                        border_color="#D2D2D7")
        self.vault_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        self.vault_entry.insert(0, self.vault_path)
        ctk.CTkButton(vault_frame, text="Browse (Ctrl+B)", command=self.browse_vault, font=("Roboto", 12),
                      corner_radius=8, fg_color="#007AFF", border_width=0, hover_color="#005BB5").grid(row=0, column=2,
                                                                                                       padx=10)

        # Load notes button
        self.load_button = ctk.CTkButton(tab, text="Load Notes (Ctrl+R)", command=self.load_notes, font=("Roboto", 14),
                                         corner_radius=10, fg_color="#007AFF", border_width=0, hover_color="#005BB5")
        self.load_button.grid(row=1, column=0, pady=15)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(tab, mode="indeterminate", corner_radius=5)
        self.progress_bar.grid(row=2, column=0, sticky="ew", pady=5)
        self.progress_bar.grid_remove()

        # Today's review
        ctk.CTkLabel(tab, text="Today's Notes to Review (Ctrl+A to select all)", font=("Roboto", 16, "bold")).grid(
            row=3, column=0, sticky="w", pady=10)
        self.tree = ttk.Treeview(tab, columns=("Subject", "File", "Status", "Last Reviewed"), show="headings",
                                 height=15, selectmode="extended")
        self.tree.heading("Subject", text="Subject")
        self.tree.heading("File", text="File Name")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Last Reviewed", text="Last Reviewed")
        self.tree.column("Subject", width=200)
        self.tree.column("File", width=300)
        self.tree.column("Status", width=120)
        self.tree.column("Last Reviewed", width=120)
        self.tree.grid(row=4, column=0, sticky="nsew")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(4, weight=1)

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tab, orientation="vertical", command=self.tree.yview, corner_radius=8)
        scrollbar.grid(row=4, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Status update buttons
        button_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#F5F5F7")
        button_frame.grid(row=5, column=0, pady=20)
        ctk.CTkButton(button_frame, text="Set Proficient (Ctrl+P)", command=lambda: self.update_status("proficient"),
                      font=("Roboto", 12), corner_radius=8, fg_color="#34C759", border_width=0,
                      hover_color="#2EA043").grid(row=0, column=0, padx=10)
        ctk.CTkButton(button_frame, text="Set Not Proficient (Ctrl+N)",
                      command=lambda: self.update_status("not_proficient"), font=("Roboto", 12), corner_radius=8,
                      fg_color="#FF9500", border_width=0, hover_color="#DB8000").grid(row=0, column=1, padx=10)
        ctk.CTkButton(button_frame, text="Set Forgotten (Ctrl+F)", command=lambda: self.update_status("forgotten"),
                      font=("Roboto", 12), corner_radius=8, fg_color="#FF3B30", border_width=0,
                      hover_color="#D32F2F").grid(row=0, column=2, padx=10)

        # Style Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF",
                        font=("Roboto", 10), rowheight=28)
        style.configure("Treeview.Heading", background="#E8ECEF", foreground="#000000", font=("Roboto", 11, "bold"),
                        padding=8)
        style.map("Treeview", background=[("selected", "#007AFF")], foreground=[("selected", "#FFFFFF")])

    def create_stats_tab(self, tab):
        # Fetch review data
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_reviewed FROM notes WHERE last_reviewed IS NOT NULL")
        review_dates = [row[0] for row in cursor.fetchall()]

        # Aggregate reviews by day (last 30 days)
        today = datetime.now().date()
        start_date = today - timedelta(days=30)
        date_range = [start_date + timedelta(days=x) for x in range(31)]
        review_counts = Counter(datetime.strptime(date, "%Y-%m-%d").date() for date in review_dates)
        counts = [review_counts.get(date, 0) for date in date_range]

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(date_range, counts, marker='o', color='#007AFF', linewidth=2)
        ax.set_title("Notes Reviewed Per Day (Last 30 Days)", fontsize=14, pad=10)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Number of Reviews", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()

        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=20, pady=20, fill="both", expand=True)

        # Refresh button
        ctk.CTkButton(tab, text="Refresh Chart", command=lambda: self.refresh_stats_tab(tab), font=("Roboto", 12),
                      corner_radius=8, fg_color="#007AFF", hover_color="#005BB5").pack(pady=10)

    def refresh_stats_tab(self, tab):
        # Clear existing content
        for widget in tab.winfo_children():
            widget.destroy()

        # Recreate the chart
        self.create_stats_tab(tab)

    def create_checkin_tab(self, tab):
        # Calendar
        self.calendar = Calendar(tab, selectmode="none", date_pattern="yyyy-mm-dd", font=("Roboto", 12))
        self.calendar.pack(padx=20, pady=20, fill="both", expand=True)

        # Update stickers
        self.update_calendar_stickers()

        # Refresh button
        ctk.CTkButton(tab, text="Refresh Calendar", command=self.update_calendar_stickers, font=("Roboto", 12),
                      corner_radius=8, fg_color="#007AFF", hover_color="#005BB5").pack(pady=10)

    def update_calendar_stickers(self):
        cursor = self.conn.cursor()
        today = datetime.now().date()
        start_date = today - timedelta(days=60)  # Check last 60 days for stickers
        date_range = [start_date + timedelta(days=x) for x in range(61)]

        for date in date_range:
            date_str = date.isoformat()
            # Check if all notes due on this date were reviewed
            cursor.execute(
                "SELECT COUNT(*) FROM notes WHERE next_review <= ? AND (last_reviewed != ? OR last_reviewed IS NULL)",
                (date_str, date_str))
            pending = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM notes WHERE last_reviewed = ?", (date_str,))
            reviewed = cursor.fetchone()[0]
            if pending == 0 and reviewed > 0:  # All due notes reviewed
                self.calendar.calevent_create(date, "Completed", "sticker")

        # Style completed days
        self.calendar.tag_config("sticker", background="#34C759", foreground="#FFFFFF")

    def select_all_notes(self, event=None):
        if self.tabview.get() != "Review Notes":
            return
        for item in self.tree.get_children():
            self.tree.selection_add(item)
        return "break"

    def browse_vault(self):
        path = filedialog.askdirectory()
        if path:
            self.vault_entry.delete(0, "end")
            self.vault_entry.insert(0, path)
            self.vault_path = path

    def load_notes(self):
        if not self.vault_entry.get():
            messagebox.showerror("Error", "Please select a vault path!")
            return

        self.load_button.configure(state="disabled")
        self.progress_bar.grid()
        self.progress_bar.start()
        self.root.update()

        self.vault_path = self.vault_entry.get()
        self.notes = []
        cursor = self.conn.cursor()

        # Clear treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Scan for .md files
        for folder in os.listdir(self.vault_path):
            folder_path = os.path.join(self.vault_path, folder)
            if os.path.isdir(folder_path):
                for file_path in glob.glob(os.path.join(folder_path, "*.md")):
                    rel_path = os.path.relpath(file_path, self.vault_path)
                    file_name = os.path.basename(file_path)
                    subject = folder

                    cursor.execute("SELECT * FROM notes WHERE file_path = ?", (rel_path,))
                    note = cursor.fetchone()
                    if not note:
                        cursor.execute('''
                            INSERT INTO notes (file_path, subject, status, review_count, last_reviewed, next_review)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (rel_path, subject, "not_proficient", 0, None, datetime.now().date().isoformat()))
                        self.conn.commit()

        # Load today's notes
        today = datetime.now().date().isoformat()
        cursor.execute("SELECT file_path, subject, status, last_reviewed FROM notes WHERE next_review <= ?", (today,))
        for row in cursor.fetchall():
            file_name = os.path.basename(row[0])
            status_display = {"proficient": "Proficient", "not_proficient": "Not Proficient",
                              "forgotten": "Forgotten"}.get(row[2], row[2])
            self.tree.insert("", "end", values=(row[1], file_name, status_display, row[3] or "Never"))

        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.load_button.configure(state="normal")

    def update_status(self, status):
        if self.tabview.get() != "Review Notes":
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one note to update!")
            return

        cursor = self.conn.cursor()
        today = datetime.now().date()
        for item in selected:
            file_name = self.tree.item(item)["values"][1]
            subject = self.tree.item(item)["values"][0]
            file_path = os.path.join(subject, file_name)

            cursor.execute("SELECT review_count FROM notes WHERE file_path = ?", (file_path,))
            review_count = cursor.fetchone()[0]
            intervals = self.review_intervals[status]
            interval_idx = min(review_count, len(intervals) - 1)
            next_review = (today + timedelta(days=intervals[interval_idx])).isoformat()

            cursor.execute('''
                UPDATE notes
                SET status = ?, review_count = review_count + 1, last_reviewed = ?, next_review = ?
                WHERE file_path = ?
            ''', (status, today.isoformat(), next_review, file_path))
            self.conn.commit()

        self.load_notes()
        self.update_calendar_stickers()

    def on_closing(self):
        if self.conn:
            self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = ctk.CTk()
    app = EbbinghausNoteApp(root)
    root.mainloop()