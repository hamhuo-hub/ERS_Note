import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QCheckBox, QLabel, QLineEdit, QDateEdit, QSpinBox,
                             QPushButton, QDialog, QListWidget, QListWidgetItem,
                             QFileDialog)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QIcon
import re

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".task_notebook"
DEFAULT_DATA_FILE = DEFAULT_CONFIG_DIR / "tasks.json"
DEFAULT_NOTES_DIR = r"C:\Users\HuoZihang\Desktop\笔记"
SETTINGS_FILE = DEFAULT_CONFIG_DIR / "settings.json"


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setWindowIcon(QIcon("icon.png"))
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # JSON file path
        self.json_label = QLabel("任务JSON文件路径:")
        self.json_edit = QLineEdit(self.parent().data_file)
        self.json_browse = QPushButton("浏览")
        self.json_browse.clicked.connect(self.browse_json)
        json_layout = QHBoxLayout()
        json_layout.addWidget(self.json_edit)
        json_layout.addWidget(self.json_browse)
        layout.addWidget(self.json_label)
        layout.addLayout(json_layout)

        # Notes directory path
        self.notes_label = QLabel("笔记文件夹路径:")
        self.notes_edit = QLineEdit(self.parent().notes_dir)
        self.notes_browse = QPushButton("浏览")
        self.notes_browse.clicked.connect(self.browse_notes)
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(self.notes_edit)
        notes_layout.addWidget(self.notes_browse)
        layout.addWidget(self.notes_label)
        layout.addLayout(notes_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Styles
        self.setStyleSheet("""
            QDialog {
                background-color: #333333;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit {
                background-color: #444444;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:nth-child(2) {
                background-color: #FF5555;
            }
            QPushButton:nth-child(2):hover {
                background-color: #FF3333;
            }
        """)

    def browse_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "选择JSON文件", str(DEFAULT_DATA_FILE), "JSON Files (*.json)")
        if file_path:
            self.json_edit.setText(file_path)

    def browse_notes(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择笔记文件夹", str(DEFAULT_NOTES_DIR))
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
            self.parent().load_stages()
            self.parent().load_stage_cards()
            self.accept()
        except Exception as e:
            print(f"Failed to save settings: {e}")


class StageDialog(QDialog):
    def __init__(self, stage, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.setWindowTitle(f"阶段: {stage['name']}")
        self.setWindowIcon(QIcon("icon.png"))
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Stage name
        self.name_label = QLabel("阶段名称:")
        self.name_edit = QLineEdit(self.stage["name"])
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        # Due date
        self.due_date_label = QLabel("截止日期:")
        self.due_date_edit = QDateEdit(QDate.fromString(self.stage["due_date"], "yyyy-MM-dd"))
        self.due_date_edit.setCalendarPopup(True)
        layout.addWidget(self.due_date_label)
        layout.addWidget(self.due_date_edit)

        # Expected time
        self.expected_time_label = QLabel("预期耗时 (小时):")
        self.expected_time_spin = QSpinBox()
        self.expected_time_spin.setValue(self.stage["expected_time"])
        layout.addWidget(self.expected_time_label)
        layout.addWidget(self.expected_time_spin)

        # Actual time
        self.actual_time_label = QLabel("实际耗时 (小时):")
        self.actual_time_spin = QSpinBox()
        self.actual_time_spin.setValue(self.stage["actual_time"] if self.stage["actual_time"] else 0)
        layout.addWidget(self.actual_time_label)
        layout.addWidget(self.actual_time_spin)

        # Knowledge points
        self.kp_label = QLabel("知识点 (任务):")
        self.kp_list = QListWidget()
        self.populate_kp_list()
        layout.addWidget(self.kp_label)
        layout.addWidget(self.kp_list)

        # Add knowledge point
        self.kp_input = QLineEdit()
        self.kp_input.setPlaceholderText("输入知识点名称并按回车添加...")
        try:
            self.kp_input.returnPressed.disconnect()
        except:
            pass
        self.kp_input.returnPressed.connect(self.add_knowledge_point)
        layout.addWidget(self.kp_input)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_details)
        self.delete_button = QPushButton("删除阶段")
        self.delete_button.clicked.connect(self.delete_stage)
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Styles
        self.setStyleSheet("""
            QDialog {
                background-color: #333333;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit, QDateEdit, QSpinBox, QListWidget {
                background-color: #444444;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:nth-child(2) {
                background-color: #FF5555;
            }
            QPushButton:nth-child(2):hover {
                background-color: #FF3333;
            }
        """)

    def populate_kp_list(self):
        self.kp_list.clear()
        for kp in self.stage.get("knowledge_points", []):
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout()
            checkbox = QCheckBox(kp["name"])
            checkbox.setChecked(kp["completed"])
            checkbox.stateChanged.connect(lambda state, k=kp: self.update_kp_completion(k, state))
            layout.addWidget(checkbox)
            layout.addStretch()
            widget.setLayout(layout)
            item.setSizeHint(widget.sizeHint())
            self.kp_list.addItem(item)
            self.kp_list.setItemWidget(item, widget)

    def update_kp_completion(self, kp, state):
        kp["completed"] = bool(state)
        self.parent().save_stages()

    def add_knowledge_point(self):
        print("Adding knowledge point")
        kp_name = self.kp_input.text().strip()
        if kp_name:
            try:
                if "knowledge_points" not in self.stage:
                    self.stage["knowledge_points"] = []
                self.stage["knowledge_points"].append({"name": kp_name, "completed": False})
                self.update_daily_note_kp(kp_name)
                self.populate_kp_list()
                self.parent().save_stages()
                self.kp_input.clear()
            except Exception as e:
                print(f"Error adding knowledge point: {e}")

    def update_daily_note_kp(self, kp_name):
        daily_note_path = Path(self.stage.get("daily_note", ""))
        if not daily_note_path.exists():
            return
        try:
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()
            task_section = self.extract_task_section(content, self.stage["name"])
            if "Related Knowledge Points:" in task_section:
                new_section = task_section + f", [[{kp_name}]]"
                content = content.replace(task_section, new_section)
            else:
                new_section = task_section + f"\n- Related Knowledge Points: [[{kp_name}]]"
                content = content.replace(task_section, new_section)
            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to update daily note with knowledge point: {e}")

    def save_details(self):
        old_name = self.stage["name"]
        new_name = self.name_edit.text()
        self.stage["name"] = new_name
        self.stage["due_date"] = self.due_date_edit.date().toString("yyyy-MM-dd")
        self.stage["expected_time"] = self.expected_time_spin.value()
        self.stage["actual_time"] = self.actual_time_spin.value()
        if self.stage["actual_time"] > 0:
            self.adjust_review_interval()
        if old_name != new_name and self.stage.get("daily_note"):
            self.update_daily_note_name(old_name, new_name)
        self.parent().save_stages()
        self.accept()

    def delete_stage(self):
        self.parent().delete_stage(self.stage)
        self.accept()

    def adjust_review_interval(self):
        last_review = self.stage["completed_reviews"][-1] if self.stage["completed_reviews"] else {
            "date": self.stage["created"], "actual_time": self.stage["expected_time"]}
        base_intervals = [1, 2, 4, 7, 15, 30]
        review_index = len(self.stage["completed_reviews"])
        interval = base_intervals[min(review_index, len(base_intervals) - 1)]

        time_ratio = self.stage["actual_time"] / self.stage["expected_time"]
        interval *= (0.8 if time_ratio > 1 else 1.2 if time_ratio < 1 else 1)

        last_date = datetime.strptime(last_review["date"], "%Y-%m-%d")
        next_date = last_date + timedelta(days=int(interval))
        self.stage["review_dates"] = [next_date.strftime("%Y-%m-%d")]
        self.stage["completed_reviews"].append(
            {"date": datetime.now().strftime("%Y-%m-%d"), "actual_time": self.stage["actual_time"]})

    def update_daily_note_name(self, old_name, new_name):
        daily_note_path = Path(self.stage.get("daily_note", ""))
        if not daily_note_path.exists():
            return
        try:
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(f"# {old_name}", f"# {new_name}")
            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to update daily note name: {e}")

    def extract_task_section(self, content, stage_name):
        pattern = rf'# {re.escape(stage_name)}\n(.*?)(?=\n# |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""


class StageCard(QWidget):
    def __init__(self, stage_data, parent=None):
        super().__init__(parent)
        self.stage = stage_data
        self.parent_widget = parent  # Reference to parent TaskNotebook for saving
        self.is_expanded = False  # Track expansion state
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        # Header: Toggle button with stage name and review arrow
        self.header_layout = QHBoxLayout()
        self.toggle_button = QPushButton(f"▶ {self.stage['name']}")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.toggle_knowledge_points)
        self.header_layout.addWidget(self.toggle_button)
        self.arrow_label = QLabel()
        self.update_arrow()
        self.header_layout.addWidget(self.arrow_label)
        self.layout.addLayout(self.header_layout)

        # Knowledge points container
        self.kp_container = QWidget()
        self.kp_layout = QVBoxLayout()
        self.kp_container.setLayout(self.kp_layout)
        self.kp_container.setVisible(False)  # Initially collapsed
        self.populate_kp_list()
        self.layout.addWidget(self.kp_container)

        self.setLayout(self.layout)

        # Enable clicking card to open dialog, excluding toggle button and checkboxes
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        # Styles
        today = datetime.now().strftime("%Y-%m-%d")
        is_due_today = today in self.stage.get("review_dates", [])
        self.setStyleSheet("""
            QWidget {
                background-color: %s;
                border-radius: 8px;
                padding: 8px;
                margin: 5px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
            }
            QWidget:hover {
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.7);
            }
            QPushButton {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                text-align: left;
                font-size: 12px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #555555;
                border-radius: 5px;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
            }
            QCheckBox {
                color: #BBBBBB;
                font-size: 11px;
                padding: 3px;
                margin-left: 20px;  /* Indent knowledge points */
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #BBBBBB;
                background-color: #444444;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #4CAF50;
            }
        """ % ("#333333" if is_due_today else "#444444"))

    def toggle_knowledge_points(self):
        self.is_expanded = self.toggle_button.isChecked()
        self.kp_container.setVisible(self.is_expanded)
        # Update the arrow indicator
        self.toggle_button.setText(f"{'▼' if self.is_expanded else '▶'} {self.stage['name']}")

    def populate_kp_list(self):
        # Clear existing items
        for i in reversed(range(self.kp_layout.count())):
            item = self.kp_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        kps = self.stage.get("knowledge_points", [])
        if not kps:
            label = QLabel("无知识点")
            label.setStyleSheet("color: #BBBBBB; font-size: 11px; padding: 3px; margin-left: 20px;")
            self.kp_layout.addWidget(label)
            return

        # Add each knowledge point as a checkbox
        for kp in kps:
            checkbox = QCheckBox(kp["name"])
            checkbox.setChecked(kp["completed"])
            checkbox.stateChanged.connect(lambda state, k=kp: self.update_kp_completion(k, state))
            self.kp_layout.addWidget(checkbox)

    def update_kp_completion(self, kp, state):
        kp["completed"] = bool(state)
        self.parent_widget.save_stages()  # Save changes via parent TaskNotebook

    def update_arrow(self):
        if not self.stage["review_dates"]:
            self.arrow_label.setText("")
            return
        next_review = datetime.strptime(self.stage["review_dates"][0], "%Y-%m-%d")
        today = datetime.now()
        diff_days = (next_review - today).days
        color = "color: red;" if diff_days <= 0 else "color: yellow;" if diff_days <= 3 else "color: green;"
        date_str = next_review.strftime("%m-%d")
        self.arrow_label.setText(f"➜ {date_str}")
        self.arrow_label.setStyleSheet(color)

    def mousePressEvent(self, event):
        # Prevent dialog from opening if clicking on a checkbox or toggle button
        if event.button() == Qt.MouseButton.LeftButton:
            widget = self.childAt(event.pos())
            if isinstance(widget, (QCheckBox, QPushButton)):
                return  # Let the checkbox or toggle button handle the click
            dialog = StageDialog(self.stage, self.parent())
            dialog.exec()
            self.toggle_button.setText(f"{'▼' if self.is_expanded else '▶'} {self.stage['name']}")
            self.populate_kp_list()  # Refresh knowledge points
            self.update_arrow()


class TaskNotebook(QWidget):
    def __init__(self):
        super().__init__()
        self.stages = []
        self.data_file = str(DEFAULT_DATA_FILE)
        self.notes_dir = DEFAULT_NOTES_DIR
        self.load_settings()
        self.load_stages()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        # Stage input
        self.stage_input = QLineEdit()
        self.stage_input.setPlaceholderText("输入阶段名称并按回车创建...")
        self.stage_input.returnPressed.connect(self.add_stage)
        self.layout.addWidget(self.stage_input)

        # Settings button
        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self.open_settings)
        self.layout.addWidget(self.settings_button)

        # Stage list
        self.stage_list = QVBoxLayout()
        self.layout.addLayout(self.stage_list)

        self.setLayout(self.layout)
        self.setWindowTitle("火腿肠御用记忆管理器")
        self.setWindowIcon(QIcon("icon.png"))
        self.setStyleSheet("""
            QWidget {
                background-color: #1C1C1C;
            }
            QLineEdit, QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                padding: 10px;
            }
        """)
        self.resize(600, 400)
        self.show()

        self.load_stage_cards()

    def load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.data_file = settings.get("data_file", str(DEFAULT_DATA_FILE))
                self.notes_dir = settings.get("notes_dir", DEFAULT_NOTES_DIR)
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def load_stages(self):
        print(f"Loading stages from: {self.data_file}")
        try:
            data_file = Path(self.data_file)
            if not data_file.parent.exists():
                data_file.parent.mkdir(parents=True)
            if not data_file.exists():
                with open(data_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            with open(data_file, "r", encoding="utf-8") as f:
                self.stages = json.load(f)
            modified = False
            for stage in self.stages:
                if "completed" in stage:
                    del stage["completed"]
                    modified = True
                if "daily_note" not in stage:
                    stage["daily_note"] = ""
                    modified = True
                if "knowledge_points" not in stage:
                    stage["knowledge_points"] = []
                    modified = True
            if modified:
                self.save_stages()
            print(f"Loaded {len(self.stages)} stages")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {self.data_file}: {e}. Initializing empty stage list.")
            self.stages = []
            self.save_stages()
        except PermissionError as e:
            print(f"Permission error accessing {self.data_file}: {e}. Using empty stage list.")
            self.stages = []
        except Exception as e:
            print(f"Unexpected error loading stages from {self.data_file}: {e}. Using empty stage list.")
            self.stages = []

    def save_stages(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.stages, f, ensure_ascii=False, indent=2)
        except PermissionError as e:
            print(f"Permission error saving to {self.data_file}: {e}")
        except Exception as e:
            print(f"Unexpected error saving to {self.data_file}: {e}")

    def load_stage_cards(self):
        for i in reversed(range(self.stage_list.count())):
            self.stage_list.itemAt(i).widget().setParent(None)

        if not self.stages:
            encouraging_label = QLabel("No stages yet! Create one to get started!")
            self.stage_list.addWidget(encouraging_label)
        else:
            for stage in self.stages:
                stage_card = StageCard(stage, self)
                self.stage_list.addWidget(stage_card)

    def add_stage(self):
        stage_name = self.stage_input.text().strip()
        if stage_name:
            today = datetime.now().strftime("%Y-%m-%d")
            category = stage_name.split("-")[0] if "-" in stage_name else "未分类"
            daily_note_path = self.create_daily_note(today, stage_name)
            stage = {
                "name": stage_name,
                "category": category,
                "created": today,
                "due_date": today,
                "daily_note": str(daily_note_path),
                "expected_time": 10,
                "actual_time": None,
                "review_dates": [(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")],
                "completed_reviews": [],
                "knowledge_points": []
            }
            self.stages.append(stage)
            self.save_stages()
            stage_card = StageCard(stage, self)
            for i in reversed(range(self.stage_list.count())):
                self.stage_list.itemAt(i).widget().setParent(None)
            self.stage_list.addWidget(stage_card)
            for other_stage in self.stages:
                if other_stage != stage:
                    other_stage_card = StageCard(other_stage, self)
                    self.stage_list.addWidget(other_stage_card)
            self.stage_input.clear()

    def create_daily_note(self, date_str, stage_name):
        daily_notes_dir = Path(self.notes_dir) / "daily_notes"
        daily_notes_dir.mkdir(parents=True, exist_ok=True)
        daily_note_path = daily_notes_dir / f"{date_str}.md"

        content = f"# {stage_name}\n- Related Knowledge Points: \n"
        if daily_note_path.exists():
            with open(daily_note_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            if f"# {stage_name}" not in existing_content:
                content = existing_content.rstrip() + "\n\n" + content
            else:
                content = existing_content
        with open(daily_note_path, "w", encoding="utf-8") as f:
            f.write(content)

        return daily_note_path

    def delete_stage(self, stage):
        daily_note_path = Path(stage.get("daily_note", ""))
        if daily_note_path.exists():
            try:
                with open(daily_note_path, "r", encoding="utf-8") as f:
                    content = f.read()
                pattern = rf'# {re.escape(stage["name"])}\n(.*?)(?=\n# |\Z)'
                content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
                with open(daily_note_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                print(f"Failed to update daily note on delete: {e}")
        self.stages.remove(stage)
        self.save_stages()
        self.load_stage_cards()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.png"))
    window = TaskNotebook()
    sys.exit(app.exec())