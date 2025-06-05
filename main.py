import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QCheckBox, QLabel, QLineEdit, QDateEdit, QSpinBox,
                             QPushButton, QDialog, QListWidget, QListWidgetItem,
                             QFileDialog, QInputDialog, QMessageBox)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QIcon
import re

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".task_notebook"
DEFAULT_DATA_FILE = DEFAULT_CONFIG_DIR / "tasks.json"
DEFAULT_NOTES_DIR = r"C:\Users\HuoZihang\Desktop\笔记"  # Keep user's path
SETTINGS_FILE = DEFAULT_CONFIG_DIR / "settings.json"

# Base Stylesheet for StageCard for easier dynamic background
STAGE_CARD_STYLE_TEMPLATE = """
    QWidget {{
        background-color: {background_color};
        border-radius: 8px;
        padding: 8px;
        margin: 5px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
    }}
    QWidget:hover {{
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.7);
    }}
    QPushButton {{ /* Toggle button in StageCard header */
        background-color: transparent;
        color: #FFFFFF;
        border: none;
        text-align: left;
        font-size: 12px;
        padding: 5px;
    }}
    QPushButton:hover {{
        background-color: #555555;
        border-radius: 5px;
    }}
    QPushButton:checked {{ /* For the toggle button when expanded */
        background-color: #555555;
        border-radius: 5px;
    }}
    QLabel {{ /* General labels within StageCard, like the arrow */
        color: #FFFFFF;
        font-size: 12px;
    }}
    /* Styles for KPs listed in StageCard dropdown */
    QLabel.kpNameLabel {{
        color: #DDDDDD; 
        font-size: 11px; 
        padding: 3px; 
        margin-left: 15px;
    }}
    QLabel.kpReviewLabel {{
        color: #BBBBBB; 
        font-size: 10px; 
        padding: 3px;
    }}
    /* Individual KP text color overrides will be applied dynamically */
"""


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setWindowIcon(QIcon("icon.png"))
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.json_label = QLabel("任务JSON文件路径:")
        self.json_edit = QLineEdit(self.parent().data_file)
        self.json_browse = QPushButton("浏览")
        self.json_browse.clicked.connect(self.browse_json)
        json_layout = QHBoxLayout()
        json_layout.addWidget(self.json_edit)
        json_layout.addWidget(self.json_browse)
        layout.addWidget(self.json_label)
        layout.addLayout(json_layout)

        self.notes_label = QLabel("笔记文件夹路径:")
        self.notes_edit = QLineEdit(self.parent().notes_dir)
        self.notes_browse = QPushButton("浏览")
        self.notes_browse.clicked.connect(self.browse_notes)
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(self.notes_edit)
        notes_layout.addWidget(self.notes_browse)
        layout.addWidget(self.notes_label)
        layout.addLayout(notes_layout)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background-color: #333333;
                border-radius: 8px;
            }
            QLabel { color: #FFFFFF; }
            QLineEdit {
                background-color: #444444; color: #FFFFFF;
                border: 1px solid #555555; border-radius: 5px; padding: 5px;
            }
            QPushButton {
                background-color: #4CAF50; color: white;
                border-radius: 5px; padding: 5px 10px; /* Added more padding */
            }
            QPushButton:hover { background-color: #45A049; }
            /* Specific style for cancel button if it's the second one */
            QPushButton:nth-child(2) { background-color: #FF5555; } /* Assuming Cancel is 2nd */
            QPushButton:nth-child(2):hover { background-color: #FF3333; }
        """)

    def browse_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "选择JSON文件", str(self.parent().data_file),
                                                   "JSON Files (*.json)")
        if file_path:
            self.json_edit.setText(file_path)

    def browse_notes(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择笔记文件夹", str(self.parent().notes_dir))
        if dir_path:
            self.notes_edit.setText(dir_path)

    def save_settings(self):
        settings = {
            "data_file": self.json_edit.text(),
            "notes_dir": self.notes_edit.text()
        }
        try:
            if not DEFAULT_CONFIG_DIR.exists():
                DEFAULT_CONFIG_DIR.mkdir(parents=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.parent().data_file = self.json_edit.text()
            self.parent().notes_dir = self.notes_edit.text()
            self.parent().load_stages()  # Reload stages with new path
            self.parent().load_stage_cards()  # Refresh UI
            self.accept()
        except Exception as e:
            print(f"Failed to save settings: {e}")


class StageDialog(QDialog):
    def __init__(self, stage, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.setWindowTitle(f"阶段详情: {stage['name']}")
        self.setWindowIcon(QIcon("icon.png"))
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.name_label = QLabel("阶段名称:")
        self.name_edit = QLineEdit(self.stage["name"])
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        self.due_date_label = QLabel("阶段截止日期 (可选):")
        self.due_date_edit = QDateEdit(QDate.fromString(self.stage["due_date"], "yyyy-MM-dd"))
        self.due_date_edit.setCalendarPopup(True)
        layout.addWidget(self.due_date_label)
        layout.addWidget(self.due_date_edit)

        self.expected_time_label = QLabel("阶段预期总耗时 (小时, 参考):")
        self.expected_time_spin = QSpinBox()
        self.expected_time_spin.setValue(self.stage.get("expected_time", 10))  # Use .get for safety
        layout.addWidget(self.expected_time_label)
        layout.addWidget(self.expected_time_spin)

        # Stage Actual Time - now informational or manually set
        self.actual_time_label = QLabel("阶段实际总耗时 (小时, 参考):")
        self.actual_time_spin = QSpinBox()
        self.actual_time_spin.setValue(self.stage.get("actual_time", 0) if self.stage.get("actual_time") else 0)
        layout.addWidget(self.actual_time_label)
        layout.addWidget(self.actual_time_spin)

        self.kp_label = QLabel("知识点 (任务):")
        self.kp_list = QListWidget()
        self.populate_kp_list()
        layout.addWidget(self.kp_label)
        layout.addWidget(self.kp_list)

        self.kp_input_layout = QHBoxLayout()
        self.kp_input = QLineEdit()
        self.kp_input.setPlaceholderText("输入新知识点名称...")
        self.kp_input_layout.addWidget(self.kp_input)

        # Updated to support minutes
        self.kp_expected_time_label = QLabel("预期耗时 (h):")
        self.kp_input_layout.addWidget(self.kp_expected_time_label)
        self.kp_expected_time_spin = QSpinBox()
        self.kp_expected_time_spin.setMinimum(1)
        self.kp_expected_time_spin.setMaximum(999)  # Increased max value
        self.kp_expected_time_spin.setSuffix(" 分钟")  # Change suffix to minutes
        self.kp_expected_time_spin.setValue(60)  # Default to 60 minutes
        self.kp_expected_time_spin.setSingleStep(5)  # Allow 5-minute increments
        self.kp_input_layout.addWidget(self.kp_expected_time_spin)

        self.add_kp_button = QPushButton("添加知识点")
        self.add_kp_button.clicked.connect(self.add_knowledge_point)
        self.kp_input_layout.addWidget(self.add_kp_button)
        layout.addLayout(self.kp_input_layout)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存阶段")
        self.save_button.clicked.connect(self.save_details)
        self.delete_button = QPushButton("删除阶段")  # This button might be styled as "danger"
        self.delete_button.clicked.connect(self.delete_stage)
        self.close_button = QPushButton("关闭")  # This one too, or make it neutral
        self.close_button.clicked.connect(self.reject)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333333; border-radius: 8px; }
            QLabel { color: #FFFFFF; }
            QLineEdit, QDateEdit, QSpinBox, QListWidget {
                background-color: #444444; color: #FFFFFF;
                border: 1px solid #555555; border-radius: 5px; padding: 5px;
            }
            QListWidget QWidget { /* Ensure items in list widget have transparent background */
                background-color: transparent; border: none;
            }
            QPushButton {
                background-color: #4CAF50; color: white;
                border-radius: 5px; padding: 5px 10px; margin-top: 5px;
            }
            QPushButton:hover { background-color: #45A049; }
            /* Style for delete_button and close_button if they are indexed e.g. 2nd and 3rd in their layout */
            /* This assumes order in button_layout. Adjust if needed or use object names */
            /* QPushButton[text='删除阶段'] { background-color: #FF5555; } */
            /* QPushButton[text='删除阶段']:hover { background-color: #FF3333; } */
            /* For now, apply general styling. Specific styling can be done by objectName */
        """)
        # Specific styling for buttons
        self.delete_button.setStyleSheet(
            "background-color: #FF5555; color: white; border-radius: 5px; padding: 5px 10px; margin-top: 5px;")
        self.close_button.setStyleSheet(
            "background-color: #777777; color: white; border-radius: 5px; padding: 5px 10px; margin-top: 5px;")

    def populate_kp_list(self):
        self.kp_list.clear()
        for kp_index, kp in enumerate(self.stage.get("knowledge_points", [])):
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout(widget)  # Set layout on widget
            layout.setContentsMargins(0, 0, 0, 0)

            kp_name_label = QLabel(kp["name"])
            kp_name_label.setStyleSheet("color: #FFFFFF; background-color: transparent;")
            layout.addWidget(kp_name_label)

            next_review_str = "N/A (Mastered)" if kp.get("kp_mastered") else \
                (kp.get("kp_review_dates")[0] if kp.get("kp_review_dates") else "N/A")

            # Display expected time in minutes
            kp_expected_time_minutes = kp.get('kp_expected_time', 60)  # Default to 60 minutes
            review_date_label = QLabel(f"Next: {next_review_str} (Exp: {kp_expected_time_minutes}min)")
            review_date_label.setStyleSheet("color: #BBBBBB; font-size: 9pt; background-color: transparent;")
            layout.addWidget(review_date_label)

            layout.addStretch()

            if not kp.get("kp_mastered", False):
                review_button = QPushButton("Mark Reviewed")
                review_button.setProperty("kp_index", kp_index)
                review_button.clicked.connect(self.handle_kp_review_action)
                review_button.setStyleSheet(
                    "font-size: 9pt; padding: 3px 5px; margin: 0px; background-color: #007BFF; color: white;")
                layout.addWidget(review_button)

            # Toggle Mastered Button
            mastered_button_text = "Unmaster" if kp.get("kp_mastered") else "Master"
            mastered_button = QPushButton(mastered_button_text)
            mastered_button.setProperty("kp_index", kp_index)
            mastered_button.clicked.connect(self.toggle_kp_mastered)
            mastered_button.setStyleSheet(
                "font-size: 9pt; padding: 3px 5px; margin: 0px; background-color: #6c757d; color: white;")  # Grey
            layout.addWidget(mastered_button)

            # Delete KP Button
            delete_kp_button = QPushButton("Del KP")
            delete_kp_button.setProperty("kp_index", kp_index)
            delete_kp_button.clicked.connect(self.delete_knowledge_point)
            delete_kp_button.setStyleSheet(
                "font-size: 9pt; padding: 3px 5px; margin: 0px; background-color: #DC3545; color: white;")  # Red
            layout.addWidget(delete_kp_button)

            # widget.setLayout(layout) # Already set in QHBoxLayout constructor
            item.setSizeHint(widget.sizeHint())
            self.kp_list.addItem(item)
            self.kp_list.setItemWidget(item, widget)

    def toggle_kp_mastered(self):
        sender_button = self.sender()
        kp_index = sender_button.property("kp_index")
        kp_to_toggle = self.stage["knowledge_points"][kp_index]
        kp_to_toggle["kp_mastered"] = not kp_to_toggle.get("kp_mastered", False)

        if kp_to_toggle["kp_mastered"]:
            kp_to_toggle["kp_review_dates"] = []  # Clear review dates if mastered
        else:  # If unmastered, set next review, e.g., tomorrow or last review + 1 day
            last_date_str = kp_to_toggle.get("kp_completed_reviews", [])[-1]["date"] if kp_to_toggle.get(
                "kp_completed_reviews") else kp_to_toggle["kp_created_date"]
            last_date_dt = datetime.strptime(last_date_str, "%Y-%m-%d")
            kp_to_toggle["kp_review_dates"] = [(last_date_dt + timedelta(days=1)).strftime("%Y-%m-%d")]

        self.parent().save_stages()
        self.populate_kp_list()

    def add_knowledge_point(self):
        kp_name = self.kp_input.text().strip()
        kp_expected_time = self.kp_expected_time_spin.value()  # This is now in minutes
        if kp_name:
            today_str = datetime.now().strftime("%Y-%m-%d")
            new_kp = {
                "name": kp_name,
                "kp_created_date": today_str,
                "kp_expected_time": kp_expected_time,  # Stored in minutes
                "kp_review_dates": [(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")],
                "kp_completed_reviews": [],
                "kp_mastered": False
            }
            if "knowledge_points" not in self.stage:
                self.stage["knowledge_points"] = []
            self.stage["knowledge_points"].append(new_kp)
            # Call update_daily_note_kp when a KP is added
            self.update_daily_note_kp(kp_name)
            self.populate_kp_list()
            self.parent().save_stages()
            self.kp_input.clear()
            self.kp_expected_time_spin.setValue(60)  # Reset to 60 minutes
        else:
            print("KP name cannot be empty.")

    def delete_knowledge_point(self):
        sender_button = self.sender()
        kp_index = sender_button.property("kp_index")

        if 0 <= kp_index < len(self.stage["knowledge_points"]):
            kp_name_to_delete = self.stage['knowledge_points'][kp_index]['name']

            reply = QMessageBox.question(self, '删除知识点',
                                         f"您确定要删除知识点: \"{kp_name_to_delete}\" 吗？同时将从笔记中删除对应的链接。",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.remove_daily_note_kp(kp_name_to_delete)
                del self.stage["knowledge_points"][kp_index]
                self.parent().save_stages()
                self.populate_kp_list()

    def handle_kp_review_action(self):
        sender_button = self.sender()
        kp_index = sender_button.property("kp_index")
        kp_to_review = self.stage["knowledge_points"][kp_index]

        # Input actual time in minutes
        actual_time_minutes, ok = QInputDialog.getInt(self, f"复习知识点: {kp_to_review['name']}",
                                                      f"实际耗时 (分钟):",
                                                      int(kp_to_review.get("kp_expected_time", 60)), 1, 999,
                                                      5)  # Default to 60, min 1, max 999, step 5
        if not ok:
            return

        if "kp_completed_reviews" not in kp_to_review:
            kp_to_review["kp_completed_reviews"] = []
        kp_to_review["kp_completed_reviews"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "actual_time": actual_time_minutes  # Stored in minutes
        })

        self.adjust_review_interval_for_kp(kp_to_review, actual_time_minutes)
        self.parent().save_stages()
        self.populate_kp_list()

    def adjust_review_interval_for_kp(self, kp, actual_time_spent_minutes):
        if kp.get("kp_mastered", False):  # Do not adjust if mastered
            kp["kp_review_dates"] = []
            return

        last_review_event = kp["kp_completed_reviews"][-1] if kp["kp_completed_reviews"] else None

        if last_review_event:
            last_review_date_str = last_review_event["date"]
        else:
            last_review_date_str = kp["kp_created_date"]

        base_intervals = [1, 2, 4, 7, 15, 30, 60, 120]
        review_index = len(kp["kp_completed_reviews"])
        interval_days = base_intervals[min(review_index - 1, len(base_intervals) - 1)] if review_index > 0 else \
            base_intervals[0]

        kp_expected_time_minutes = kp.get("kp_expected_time", 60)  # Default to 60 minutes
        if kp_expected_time_minutes <= 0: kp_expected_time_minutes = 60  # Avoid division by zero or negative

        time_ratio = actual_time_spent_minutes / kp_expected_time_minutes

        adjustment_factor = 1.0
        if time_ratio > 1.5:  # Took much longer
            adjustment_factor = 0.75
        elif time_ratio > 1.2:  # Took somewhat longer
            adjustment_factor = 0.9
        elif time_ratio < 0.5:  # Took much less time
            adjustment_factor = 1.25
        elif time_ratio < 0.8:  # Took somewhat less time
            adjustment_factor = 1.1

        interval_days = interval_days * adjustment_factor
        interval_days = max(1, int(round(interval_days)))

        last_date_dt = datetime.strptime(last_review_date_str, "%Y-%m-%d")
        next_date_dt = last_date_dt + timedelta(days=interval_days)

        kp["kp_review_dates"] = [next_date_dt.strftime("%Y-%m-%d")]
        print(f"KP '{kp['name']}' next review set to: {kp['kp_review_dates'][0]} (interval: {interval_days} days)")

    def save_details(self):
        old_name = self.stage["name"]
        new_name = self.name_edit.text()
        self.stage["name"] = new_name
        self.stage["due_date"] = self.due_date_edit.date().toString("yyyy-MM-dd")
        self.stage["expected_time"] = self.expected_time_spin.value()
        self.stage["actual_time"] = self.actual_time_spin.value()  # Informational

        if old_name != new_name and self.stage.get("daily_note"):
            self.update_daily_note_name(old_name, new_name)

        self.parent().save_stages()
        self.parent().load_stage_cards()  # Crucial to refresh main UI display
        self.accept()

    def delete_stage(self):
        reply = QMessageBox.question(self, '删除阶段',
                                     f"您确定要删除阶段: \"{self.stage['name']}\" 吗？这将删除所有知识点及其笔记中的相关内容。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.parent().delete_stage(self.stage)
            self.accept()

    def update_daily_note_kp(self, kp_name):  # From original, seems fine
        daily_note_path_str = self.stage.get("daily_note", "")
        if not daily_note_path_str: return
        daily_note_path = Path(daily_note_path_str)

        if not daily_note_path.exists():
            # If daily note doesn't exist, create it with the stage header first
            # This is important for newly created stages that get a KP immediately
            self.parent().create_daily_note_structure(datetime.now().strftime("%Y-%m-%d"), self.stage['name'])
            # After creation, it should exist, so re-check
            if not daily_note_path.exists():
                print(f"Failed to create daily note structure for '{self.stage['name']}'. Cannot add KP link.")
                return

        try:
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Regex to find the section for this stage
            # Use non-greedy match for stage content and ensure it starts with a line break or start of string
            stage_heading_pattern = rf"(^# {re.escape(self.stage['name'])}\s*)(.*?)(?=\n^# |\Z)"
            stage_match = re.search(stage_heading_pattern, content, re.MULTILINE | re.DOTALL)

            if stage_match:
                stage_header = stage_match.group(1)  # "# Stage Name\n"
                stage_content_within = stage_match.group(2)  # Content after header, before next # or end of file

                # Regex for "Related Knowledge Points" line
                kp_line_pattern = r"(- Related Knowledge Points:.*?)$"
                kp_line_match = re.search(kp_line_pattern, stage_content_within, re.MULTILINE)

                new_kp_link = f"[[{kp_name}]]"

                if kp_line_match:
                    existing_kp_line = kp_line_match.group(1)
                    if new_kp_link not in existing_kp_line:
                        # Ensure no double commas or leading/trailing commas after adding
                        updated_kp_line = existing_kp_line.rstrip()
                        if updated_kp_line.endswith(":") or updated_kp_line.endswith(":,"):
                            # If only "Related Knowledge Points:" exists, just append link
                            updated_kp_line = f"{updated_kp_line.rstrip(':').strip()}: {new_kp_link}"
                        elif updated_kp_line.endswith(","):
                            updated_kp_line = f"{updated_kp_line} {new_kp_link}"  # Append with space
                        else:
                            updated_kp_line = f"{updated_kp_line}, {new_kp_link}"

                        updated_stage_content_within = stage_content_within.replace(existing_kp_line, updated_kp_line)
                    else:
                        updated_stage_content_within = stage_content_within  # No change needed if link already exists
                else:  # "Related Knowledge Points" line doesn't exist, add it
                    new_kp_section_line = f"\n- Related Knowledge Points: {new_kp_link}"
                    # Insert it before the next major heading or at the end of stage section
                    # Append to stage_content_within
                    updated_stage_content_within = stage_content_within.rstrip() + new_kp_section_line

                # Reconstruct the full content
                new_full_content = content.replace(stage_match.group(0),
                                                   f"{stage_header}{updated_stage_content_within.strip()}\n")
            else:  # Stage section not found, append new stage with KP
                # This case should ideally not happen if create_daily_note_structure worked
                # But as a fallback, add the new stage and KP
                new_full_content = content.rstrip() + f"\n\n# {self.stage['name']}\n- Related Knowledge Points: [[{kp_name}]]\n"

            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(new_full_content.strip())  # Use strip to clean up any extra newlines at the end
            print(f"Added '{kp_name}' to daily note '{daily_note_path.name}'.")

        except Exception as e:
            print(f"Failed to update daily note with knowledge point: {e}")

    def remove_daily_note_kp(self, kp_name):
        """从与阶段关联的日记笔记中删除知识点链接。"""
        daily_note_path_str = self.stage.get("daily_note", "")
        if not daily_note_path_str:
            return

        daily_note_path = Path(daily_note_path_str)
        if not daily_note_path.exists():
            return

        try:
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 找到阶段标题及其内容，直到下一个标题或文件末尾
            # 使用非贪婪匹配 .*? 来防止匹配到多个阶段
            stage_heading_pattern = rf"(^# {re.escape(self.stage['name'])}\s*)(.*?)(?=\n^# |\Z)"
            stage_match = re.search(stage_heading_pattern, content, re.MULTILINE | re.DOTALL)

            if stage_match:
                stage_header_part = stage_match.group(1)  # E.g., "# Stage Name\n"
                stage_content_within_part = stage_match.group(2)  # Content after header, before next # or end of file

                kp_link_to_remove = f"[[{kp_name}]]"

                # 找到 "Related Knowledge Points" 行
                # 确保匹配整行，包括开头的连字符和末尾的换行
                kp_line_pattern = r"(- Related Knowledge Points:\s*.*?)$"
                kp_line_match = re.search(kp_line_pattern, stage_content_within_part, re.MULTILINE)

                if kp_line_match:
                    existing_kp_line = kp_line_match.group(1)

                    # More robust removal of the link, handling commas and leading/trailing spaces
                    # This regex tries to remove ", [[link]]" or "[[link]]" if it's the first.
                    # It ensures that if the link is removed, any preceding comma+space is also removed.
                    # If it's the first item, it removes just the link.
                    updated_kp_line = re.sub(rf"(,\s*|)\s*\[\[{re.escape(kp_name)}\]\]", "", existing_kp_line).strip()

                    # If the line ends with a comma after removal (e.g., "A, B," becomes "A,"), remove trailing comma
                    updated_kp_line = re.sub(r",\s*$", "", updated_kp_line)

                    # If after removal, the line becomes just "- Related Knowledge Points:"
                    if updated_kp_line.strip() == "- Related Knowledge Points:":
                        # Remove the entire "Related Knowledge Points" line from the stage content
                        updated_stage_content_within = stage_content_within_part.replace(existing_kp_line, "").strip()
                    else:
                        updated_stage_content_within = stage_content_within_part.replace(existing_kp_line,
                                                                                         updated_kp_line).strip()

                    # --- Logic to remove entire stage if it becomes empty ---
                    # Check if the remaining content (after removing KP line) is empty
                    # and if it was ONLY the KP line or minimal content (like an empty line)
                    if not updated_stage_content_within.strip() and not \
                            re.search(r'\S', updated_stage_content_within,
                                      re.MULTILINE):  # No non-whitespace chars left
                        # If stage content (excluding header) is effectively empty, remove the whole stage section
                        new_full_content = content.replace(stage_match.group(0), "").strip()
                    else:
                        # Otherwise, reconstruct the full content with the updated stage section
                        # Ensure there's a newline after the stage content to separate it from anything following
                        # Also, handle potential double newlines if content was empty and stage_header_part already had a newline
                        new_section_content = f"{stage_header_part}{updated_stage_content_within}"
                        # Clean up multiple newlines that might arise from empty content or deletions
                        new_section_content = re.sub(r'\n{3,}', '\n\n',
                                                     new_section_content).strip() + '\n'  # Max two newlines, then add one for separation

                        new_full_content = content.replace(stage_match.group(0), new_section_content).strip()
                        # Final strip for the whole file content to avoid leading/trailing blank lines
                        if new_full_content.endswith(
                                '\n'):  # Ensure consistent single newline at end of file if not empty
                            new_full_content = new_full_content.rstrip('\n') + '\n'

            else:
                print(
                    f"Daily note '{daily_note_path.name}' does not contain stage heading for '{self.stage['name']}'. No link to remove.")
                return  # No stage heading found, nothing to do

            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(new_full_content)
            print(f"Removed '{kp_name}' from daily note '{daily_note_path.name}'.")

        except Exception as e:
            print(f"Failed to remove knowledge point '{kp_name}' from daily note '{daily_note_path.name}': {e}")

    def update_daily_note_name(self, old_name, new_name):  # From original, seems fine
        daily_note_path_str = self.stage.get("daily_note", "")
        if not daily_note_path_str: return
        daily_note_path = Path(daily_note_path_str)

        if not daily_note_path.exists(): return
        try:
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()
            # More robust regex to only match headings
            # Ensure it matches the full line to avoid partial replacements
            content = re.sub(rf"(^#\s*{re.escape(old_name)}\s*$)", f"# {new_name}", content, flags=re.MULTILINE)
            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to update daily note name: {e}")

    # extract_task_section not directly used by above, but could be useful for other daily note ops
    def extract_task_section(self, content, stage_name):
        pattern = rf'^# {re.escape(stage_name)}\n(.*?)(?=\n^# |\Z)'
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""


class StageCard(QWidget):
    def __init__(self, stage_data, parent=None):
        super().__init__(parent)
        self.stage = stage_data
        self.parent_widget = parent
        self.is_expanded = False
        self.initUI()
        self.update_visuals()  # Initial style and arrow update

    def initUI(self):
        self.main_layout = QVBoxLayout(self)  # Set layout on self
        self.main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins if card has padding

        self.header_layout = QHBoxLayout()
        self.toggle_button = QPushButton(f"▶ {self.stage['name']}")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.toggle_knowledge_points)
        self.header_layout.addWidget(self.toggle_button)

        self.arrow_label = QLabel()  # For review indicator
        self.header_layout.addWidget(self.arrow_label)
        self.main_layout.addLayout(self.header_layout)

        self.kp_container = QWidget()
        self.kp_layout = QVBoxLayout(self.kp_container)  # Set layout on container
        self.kp_container.setVisible(False)
        self.populate_kp_list_in_card()  # Distinct from dialog's populate
        self.main_layout.addWidget(self.kp_container)

        # self.setLayout(self.main_layout) # Already set via QVBoxLayout(self)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def update_visuals(self):
        self.update_card_style()
        self.update_review_arrow_indicator()
        self.toggle_button.setText(f"{'▼' if self.is_expanded else '▶'} {self.stage['name']}")

    def update_card_style(self):
        today_dt = datetime.now().date()
        is_any_kp_due_today_or_overdue = any(
            not kp.get("kp_mastered") and kp.get("kp_review_dates") and
            datetime.strptime(kp["kp_review_dates"][0], "%Y-%m-%d").date() <= today_dt
            for kp in self.stage.get("knowledge_points", [])
        )

        background_color = "#FF4500" if is_any_kp_due_today_or_overdue else "#444444"  # OrangeRed if due, dark grey otherwise
        self.setStyleSheet(STAGE_CARD_STYLE_TEMPLATE.format(background_color=background_color))

    def toggle_knowledge_points(self):
        self.is_expanded = self.toggle_button.isChecked()
        self.kp_container.setVisible(self.is_expanded)
        self.toggle_button.setText(f"{'▼' if self.is_expanded else '▶'} {self.stage['name']}")

    def populate_kp_list_in_card(self):
        # Clear existing items
        while self.kp_layout.count():
            child = self.kp_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():  # If it's a layout, delete its contents too
                while child.layout().count():
                    sub_child = child.layout().takeAt(0)
                    if sub_child.widget():
                        sub_child.widget().deleteLater()

        kps = [kp for kp in self.stage.get("knowledge_points", []) if not kp.get("kp_mastered")]
        if not kps:
            label = QLabel("无待复习知识点")
            label.setStyleSheet(
                "color: #BBBBBB; font-size: 10px; padding: 3px; margin-left: 20px; background-color: transparent;")
            self.kp_layout.addWidget(label)
            return

        today_dt = datetime.now().date()
        for kp in sorted(kps, key=lambda k: k.get("kp_review_dates")[0] if k.get("kp_review_dates") else "9999-99-99"):
            kp_entry_widget = QWidget()
            kp_entry_layout = QHBoxLayout(kp_entry_widget)
            kp_entry_layout.setContentsMargins(5, 2, 5, 2)

            kp_name_label = QLabel(kp["name"])
            kp_name_label.setObjectName("kpNameLabel")  # For STAGE_CARD_STYLE_TEMPLATE

            review_text = "Review: N/A"
            text_color = "#BBBBBB"

            if kp.get("kp_review_dates") and kp["kp_review_dates"][0]:
                next_review_dt = datetime.strptime(kp["kp_review_dates"][0], "%Y-%m-%d").date()

                # Display expected time in minutes
                kp_expected_time_minutes = kp.get('kp_expected_time', 60)  # Default to 60 minutes
                review_text = f"Review: {next_review_dt.strftime('%m-%d')} (Exp: {kp_expected_time_minutes}min)"

                days_diff = (next_review_dt - today_dt).days
                if days_diff < 0:
                    text_color = "#FF6347"  # Tomato (Overdue)
                elif days_diff == 0:
                    text_color = "#FFA500"  # Orange (Due today)
                elif days_diff <= 2:
                    text_color = "#FFD700"  # Gold (Due soon)
                else:
                    text_color = "#90EE90"  # LightGreen (Upcoming)

            kp_name_label.setStyleSheet(
                f"color: {text_color}; font-size: 11px; padding: 3px; margin-left: 15px; background-color: transparent;")

            kp_review_label = QLabel(review_text)
            kp_review_label.setObjectName("kpReviewLabel")
            kp_review_label.setStyleSheet(
                f"color: {text_color}; font-size: 10px; padding: 3px; background-color: transparent;")

            kp_entry_layout.addWidget(kp_name_label)
            kp_entry_layout.addStretch()
            kp_entry_layout.addWidget(kp_review_label)

            self.kp_layout.addWidget(kp_entry_widget)

    def update_review_arrow_indicator(self):
        active_kps = [kp for kp in self.stage.get("knowledge_points", []) if
                      not kp.get("kp_mastered") and kp.get("kp_review_dates")]
        if not active_kps:
            self.arrow_label.setText("")
            return

        soonest_review_dt = min(datetime.strptime(kp["kp_review_dates"][0], "%Y-%m-%d").date() for kp in active_kps)
        today_dt = datetime.now().date()
        due_kps_count = sum(
            1 for kp in active_kps if datetime.strptime(kp["kp_review_dates"][0], "%Y-%m-%d").date() <= today_dt)

        diff_days = (soonest_review_dt - today_dt).days

        color = "color: #FF6347;" if diff_days < 0 else \
            "color: #FFA500;" if diff_days == 0 else \
                "color: #FFD700;" if diff_days <= 3 else \
                    "color: #90EE90;"

        date_str_display = soonest_review_dt.strftime("%m-%d")

        if due_kps_count > 0:
            self.arrow_label.setText(f"➜ {date_str_display} ({due_kps_count} Due)")
        else:
            self.arrow_label.setText(f"➜ {date_str_display}")

        self.arrow_label.setStyleSheet(color + "font-weight: bold; font-size: 10pt; background-color: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child_widget = self.childAt(event.pos())
            # Prevent dialog if clicking on header toggle button itself
            if child_widget == self.toggle_button or (
                    self.toggle_button and self.toggle_button.geometry().contains(event.pos())):
                return

            dialog = StageDialog(self.stage, self.parent_widget)  # Pass TaskNotebook as parent
            if dialog.exec():  # User clicked Save in dialog
                # Stage data might have changed, refresh everything for this card
                self.populate_kp_list_in_card()
                self.update_visuals()
            else:  # User clicked Cancel or closed dialog
                # Still refresh, as KPs might have been marked reviewed without saving WHOLE stage
                self.populate_kp_list_in_card()
                self.update_visuals()


class TaskNotebook(QWidget):
    def __init__(self):
        super().__init__()
        self.stages = []
        self.data_file = str(DEFAULT_DATA_FILE)
        self.notes_dir = str(DEFAULT_NOTES_DIR)  # Ensure it's a string
        self.load_settings()
        self.load_stages()
        self.initUI()
        self.load_stage_cards()

    def initUI(self):
        self.main_v_layout = QVBoxLayout(self)  # Main layout for the window

        # Top bar for input and settings
        top_bar_layout = QHBoxLayout()
        self.stage_input = QLineEdit()
        self.stage_input.setPlaceholderText("输入新课程/阶段名称并按回车创建...")
        self.stage_input.returnPressed.connect(self.add_stage)
        top_bar_layout.addWidget(self.stage_input)

        self.settings_button = QPushButton("设置")
        self.settings_button.setIcon(QIcon("icon.png"))  # Optional: if you have an icon for settings
        self.settings_button.clicked.connect(self.open_settings)
        top_bar_layout.addWidget(self.settings_button)
        self.main_v_layout.addLayout(top_bar_layout)

        # Stage list area (will be populated with StageCard widgets)
        self.stage_list_container_widget = QWidget()  # Use a QWidget as a container for QVBoxLayout
        self.stage_list_layout = QVBoxLayout(self.stage_list_container_widget)
        self.stage_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Cards stack from top

        # ScrollArea for stage cards
        # This part is a common pattern if you expect many cards
        # from PyQt6.QtWidgets import QScrollArea
        # self.scroll_area = QScrollArea()
        # self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setWidget(self.stage_list_container_widget)
        # self.main_v_layout.addWidget(self.scroll_area)
        # For now, without scroll area, direct add:
        self.main_v_layout.addWidget(self.stage_list_container_widget)

        # self.setLayout(self.main_v_layout) # Already set
        self.setWindowTitle("火腿肠御用记忆管理器")
        self.setWindowIcon(QIcon("icon.png"))
        self.setStyleSheet("""
            QWidget { background-color: #1C1C1C; }
            QLineEdit {
                background-color: #333333; color: #FFFFFF;
                border: 1px solid #555555; border-radius: 5px; padding: 8px;
                font-size: 11pt;
            }
            QPushButton { /* General style for buttons like 'Settings' */
                background-color: #555555; color: #FFFFFF;
                border-radius: 5px; padding: 8px 12px; font-size: 10pt;
            }
            QPushButton:hover { background-color: #666666; }
            QLabel#encouragingLabel { /* For the 'No stages yet' label */
                color: #AAAAAA; font-size: 14px; padding: 20px; 
                alignment: center;
            }
        """)
        self.resize(700, 500)  # Increased size a bit
        self.show()

    def load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.data_file = settings.get("data_file", str(DEFAULT_DATA_FILE))
                self.notes_dir = settings.get("notes_dir", str(DEFAULT_NOTES_DIR))
        except Exception as e:
            print(f"Failed to load settings: {e}. Using defaults.")
            self.data_file = str(DEFAULT_DATA_FILE)
            self.notes_dir = str(DEFAULT_NOTES_DIR)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def load_stages(self):
        print(f"Loading stages from: {self.data_file}")
        try:
            data_file_path = Path(self.data_file)
            if not data_file_path.parent.exists():
                data_file_path.parent.mkdir(parents=True, exist_ok=True)
            if not data_file_path.exists():
                with open(data_file_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)

            with open(data_file_path, "r", encoding="utf-8") as f:
                self.stages = json.load(f)

            modified = False
            default_today_str = datetime.now().strftime("%Y-%m-%d")

            for stage in self.stages:
                if "daily_note" not in stage: stage["daily_note"] = ""; modified = True
                if "knowledge_points" not in stage: stage["knowledge_points"] = []; modified = True

                # Migrate KPs
                for kp_idx, kp_item in enumerate(stage.get("knowledge_points", [])):
                    # Handle case where KP might be a string (older format)
                    if isinstance(kp_item, str):
                        kp_name_str = kp_item
                        stage["knowledge_points"][kp_idx] = {
                            "name": kp_name_str,
                            "kp_created_date": stage.get("created", default_today_str),
                            "kp_expected_time": 60,  # Default to 60 minutes
                            "kp_review_dates": [(datetime.strptime(stage.get("created", default_today_str),
                                                                   "%Y-%m-%d") + timedelta(days=1)).strftime(
                                "%Y-%m-%d")],
                            "kp_completed_reviews": [],
                            "kp_mastered": False
                        }
                        modified = True
                        kp = stage["knowledge_points"][kp_idx]  # re-assign kp to the new dict
                    else:  # It's already a dict, check fields
                        kp = kp_item

                    if "kp_created_date" not in kp: kp["kp_created_date"] = stage.get("created",
                                                                                      default_today_str); modified = True
                    if "kp_expected_time" not in kp: kp[
                        "kp_expected_time"] = 60; modified = True  # Default to 60 minutes
                    if "kp_review_dates" not in kp or not kp["kp_review_dates"]:
                        created_dt = datetime.strptime(kp.get("kp_created_date", default_today_str), "%Y-%m-%d")
                        kp["kp_review_dates"] = [(created_dt + timedelta(days=1)).strftime("%Y-%m-%d")]
                        modified = True
                    if "kp_completed_reviews" not in kp: kp["kp_completed_reviews"] = []; modified = True
                    if "kp_mastered" not in kp: kp["kp_mastered"] = False; modified = True
                    if "completed" in kp: del kp["completed"]; modified = True  # Remove old flag

            if modified:
                self.save_stages()
            print(f"Loaded {len(self.stages)} stages.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {self.data_file}: {e}. Initializing empty list.")
            self.stages = []
            self.save_stages()  # Save an empty list to fix file
        except Exception as e:
            print(f"Unexpected error loading stages: {e}. Using empty list.")
            self.stages = []

    def save_stages(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.stages, f, ensure_ascii=False, indent=4)  # Indent 4 for readability
        except Exception as e:
            print(f"Error saving stages to {self.data_file}: {e}")

    def load_stage_cards(self):
        # Clear existing cards from layout
        while self.stage_list_layout.count():
            child = self.stage_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.stages:
            encouraging_label = QLabel("还没有任何学习阶段！创建一个开始吧！")
            encouraging_label.setObjectName("encouragingLabel")  # For specific styling
            encouraging_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stage_list_layout.addWidget(encouraging_label)
        else:
            # Sort stages: those with KPs due soonest first, then by creation date or name
            today = datetime.now().date()

            def sort_key(stage):
                min_review_date = today + timedelta(days=365 * 10)  # A far future date
                has_active_kp = False
                for kp in stage.get("knowledge_points", []):
                    if not kp.get("kp_mastered") and kp.get("kp_review_dates"):
                        has_active_kp = True
                        current_kp_review_date = datetime.strptime(kp["kp_review_dates"][0], "%Y-%m-%d").date()
                        if current_kp_review_date < min_review_date:
                            min_review_date = current_kp_review_date
                return (min_review_date, stage.get("created", "9999-99-99")) if has_active_kp else (
                    today + timedelta(days=365 * 11), stage.get("created", "9999-99-99"))

            sorted_stages = sorted(self.stages, key=sort_key)

            for stage_data in sorted_stages:
                stage_card = StageCard(stage_data, self)  # Pass self (TaskNotebook) as parent
                self.stage_list_layout.addWidget(stage_card)
        # Add a stretch at the end if you want cards to push upwards and not spread out
        # self.stage_list_layout.addStretch(1)

    def add_stage(self):
        stage_name = self.stage_input.text().strip()
        if stage_name:
            today_str = datetime.now().strftime("%Y-%m-%d")
            category = stage_name.split("-")[0].strip() if "-" in stage_name else "未分类"

            daily_note_path_str = ""
            if Path(self.notes_dir).exists():
                daily_note_path = self.create_daily_note_structure(today_str, stage_name)
                daily_note_path_str = str(daily_note_path)

            new_stage = {
                "name": stage_name,
                "category": category,
                "created": today_str,
                "due_date": today_str,  # Default due date, can be changed in dialog
                "daily_note": daily_note_path_str,
                "expected_time": 10,  # Default expected time for the whole stage (in hours)
                "actual_time": 0,  # Default actual time (in hours)
                "knowledge_points": []  # KPs added via dialog
            }
            self.stages.append(new_stage)
            self.save_stages()
            self.load_stage_cards()
            self.stage_input.clear()
        else:
            print("Stage name cannot be empty.")

    def create_daily_note_structure(self, date_str, stage_name):
        notes_dir_path = Path(self.notes_dir)
        if not notes_dir_path.is_dir():
            print(f"Notes directory '{self.notes_dir}' is not valid. Cannot create daily note.")
            return ""

        daily_notes_dir = notes_dir_path / "daily_notes"
        daily_notes_dir.mkdir(parents=True, exist_ok=True)
        daily_note_file_path = daily_notes_dir / f"{date_str}.md"

        stage_header_content = f"\n\n# {stage_name}\n- Related Knowledge Points: \n"  # Start with a minimal line for KPs

        try:
            current_content = ""
            if daily_note_file_path.exists():
                with open(daily_note_file_path, "r", encoding="utf-8") as f:
                    current_content = f.read()

            # Check if the stage header already exists in the file (more robust check)
            # Use regex to find the stage header
            header_exists_pattern = rf"(?m)^#\s*{re.escape(stage_name)}\s*$"
            if re.search(header_exists_pattern, current_content):
                print(f"Stage '{stage_name}' header already exists in '{daily_note_file_path.name}'. Not adding again.")
                return daily_note_file_path  # Header already present, nothing to do.

            # If file doesn't exist or header not found, append/write
            with open(daily_note_file_path, "a" if daily_note_file_path.exists() else "w", encoding="utf-8") as f:
                if not daily_note_file_path.exists() or not current_content.strip():  # For new file or empty file
                    f.write(f"# Daily Note - {date_str}\n")  # Add a daily note header if it's a new or empty file
                f.write(stage_header_content)

            print(f"Created/updated daily note '{daily_note_file_path.name}' with stage '{stage_name}'.")
            return daily_note_file_path
        except Exception as e:
            print(f"Error creating or updating daily note '{daily_note_file_path}': {e}")
            return ""

    def delete_stage(self, stage_to_delete):
        reply = QMessageBox.question(self, '确认删除',
                                     f"您确定要删除阶段 '{stage_to_delete['name']}' 吗？这将删除所有知识点及其在日记笔记中的相关内容。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            daily_note_path_str = stage_to_delete.get("daily_note", "")
            if daily_note_path_str:
                daily_note_path = Path(daily_note_path_str)
                if daily_note_path.exists():
                    try:
                        with open(daily_note_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Pattern to remove the whole stage section, including its header and all content below it
                        # until the next # heading or end of file.
                        pattern = rf'(^#\s*{re.escape(stage_to_delete["name"])}\s*.*?)(?=\n^#\s*|\Z)'
                        new_content = re.sub(pattern, '', content, count=1, flags=re.DOTALL | re.MULTILINE).strip()

                        # If the file becomes empty after removal (or only contains the daily note header),
                        # you might want to consider deleting the file or cleaning it up further.
                        # For now, just write the new content.
                        with open(daily_note_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(
                            f"Removed stage '{stage_to_delete['name']}' section from daily note '{daily_note_path.name}'.")
                    except Exception as e:
                        print(f"Failed to update daily note on stage delete: {e}")

            self.stages.remove(stage_to_delete)
            self.save_stages()
            self.load_stage_cards()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskNotebook()
    sys.exit(app.exec())