import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QCheckBox, QLabel, QLineEdit, QDateEdit, QSpinBox,
                             QPushButton, QDialog)
from PyQt6.QtCore import QDate, Qt

# 任务存储路径
CONFIG_DIR = Path.home() / ".task_notebook"
DATA_FILE = CONFIG_DIR / "tasks.json"
NOTES_DIR = r"C:\Users\HuoZihang\Desktop\笔记"


class TaskEditDialog(QDialog):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("编辑任务")
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 任务名称（可编辑）
        self.name_label = QLabel("任务名称:")
        self.name_edit = QLineEdit(self.task["name"])
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        # 截止日期
        self.due_date_label = QLabel("截止日期:")
        self.due_date_edit = QDateEdit(QDate.fromString(self.task["due_date"], "yyyy-MM-dd"))
        self.due_date_edit.setCalendarPopup(True)
        layout.addWidget(self.due_date_label)
        layout.addWidget(self.due_date_edit)

        # 预期耗时
        self.expected_time_label = QLabel("预期耗时 (小时):")
        self.expected_time_spin = QSpinBox()
        self.expected_time_spin.setValue(self.task["expected_time"])
        layout.addWidget(self.expected_time_label)
        layout.addWidget(self.expected_time_spin)

        # 实际耗时
        self.actual_time_label = QLabel("实际耗时 (小时):")
        self.actual_time_spin = QSpinBox()
        self.actual_time_spin.setValue(self.task["actual_time"] if self.task["actual_time"] else 0)
        layout.addWidget(self.actual_time_label)
        layout.addWidget(self.actual_time_spin)

        # 笔记内容
        self.note_label = QLabel("笔记内容:")
        self.note_content = QLabel(self.load_note())
        layout.addWidget(self.note_label)
        layout.addWidget(self.note_content)

        # 按钮
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_details)
        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_task)
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 样式
        self.setStyleSheet("""
            QDialog {
                background-color: #333333;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit, QDateEdit, QSpinBox {
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

    def save_details(self):
        old_name = self.task["name"]
        new_name = self.name_edit.text()
        self.task["name"] = new_name
        self.task["due_date"] = self.due_date_edit.date().toString("yyyy-MM-dd")
        self.task["expected_time"] = self.expected_time_spin.value()
        self.task["actual_time"] = self.actual_time_spin.value()
        if self.task["actual_time"] > 0:
            self.adjust_review_interval()
        # Update daily note if task name changed
        if old_name != new_name and self.task.get("daily_note"):
            self.update_daily_note_name(old_name, new_name)
        self.parent().save_tasks()
        self.accept()

    def delete_task(self):
        self.parent().delete_task(self.task)
        self.accept()

    def adjust_review_interval(self):
        last_review = self.task["completed_reviews"][-1] if self.task["completed_reviews"] else {
            "date": self.task["created"], "actual_time": self.task["expected_time"]}
        base_intervals = [1, 2, 4, 7, 15, 30]
        review_index = len(self.task["completed_reviews"])
        interval = base_intervals[min(review_index, len(base_intervals) - 1)]

        time_ratio = self.task["actual_time"] / self.task["expected_time"]
        interval *= (0.8 if time_ratio > 1 else 1.2 if time_ratio < 1 else 1)

        last_date = datetime.strptime(last_review["date"], "%Y-%m-%d")
        next_date = last_date + timedelta(days=int(interval))
        self.task["review_dates"] = [next_date.strftime("%Y-%m-%d")]
        self.task["completed_reviews"].append(
            {"date": datetime.now().strftime("%Y-%m-%d"), "actual_time": self.task["actual_time"]})

    def update_daily_note_name(self, old_name, new_name):
        daily_note_path = Path(self.task.get("daily_note", ""))
        if not daily_note_path.exists():
            return
        try:
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Replace old task name heading with new one
            content = content.replace(f"# {old_name}", f"# {new_name}")
            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to update daily note name: {e}")

    def load_note(self):
        from re import findall

        daily_note_path = Path(self.task.get("daily_note", ""))
        if not daily_note_path.exists():
            return "未找到每日笔记"

        # Read daily note content
        try:
            with open(daily_note_path, "r", encoding="utf-8") as f:
                daily_content = f.read()
            # Extract section for this task
            task_section = self.extract_task_section(daily_content, self.task["name"])
        except Exception as e:
            return f"读取每日笔记失败: {str(e)}"

        # Find [[link]] patterns in the task section
        links = findall(r'\[\[([^\]]+)\]\]', task_section)
        if not links:
            return task_section[:200] + "..." if len(task_section) > 200 else task_section

        # Collect content from linked files
        notes_content = []
        notes_base_dir = Path(NOTES_DIR)
        for link in links:
            note_path = notes_base_dir / f"{link}.md"
            if note_path.exists():
                try:
                    with open(note_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        notes_content.append(f"### {link}\n{content[:200]}{'...' if len(content) > 200 else ''}")
                except Exception as e:
                    notes_content.append(f"### {link}\n读取失败: {str(e)}")
            else:
                notes_content.append(f"### {link}\n未找到文件")

        # Combine task section and linked content
        combined_content = task_section[:200] + "\n\n" + "\n\n".join(notes_content)
        return combined_content[:1000] + "..." if len(combined_content) > 1000 else combined_content

    def extract_task_section(self, content, task_name):
        # Find the section starting with # task_name
        import re
        pattern = rf'# {re.escape(task_name)}\n(.*?)(?=\n# |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""


class TaskCard(QWidget):
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task = task_data
        self.initUI()

    def initUI(self):
        self.layout = QHBoxLayout()

        # Checkbox for completion
        self.checkbox = QCheckBox(self.task["name"])
        self.checkbox.setChecked(self.task.get("completed", False))
        self.checkbox.stateChanged.connect(self.toggle_completion)
        self.layout.addWidget(self.checkbox)

        # Edit button
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.open_dialog)
        self.layout.addWidget(self.edit_button)

        # Review time arrow
        self.arrow_label = QLabel()
        self.update_arrow()
        self.layout.addWidget(self.arrow_label)

        self.setLayout(self.layout)

        # Enable double-click to open dialog
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.mouseDoubleClickEvent = self.open_dialog_on_double_click

        # 样式，灰色样式用于非今日任务
        today = datetime.now().strftime("%Y-%m-%d")
        is_due_today = today in self.task.get("review_dates", [])
        self.setStyleSheet("""
            QWidget {
                background-color: %s;
                border-radius: 8px;
                padding: 5px;
                margin: 5px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
            }
            QWidget:hover {
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.7);
            }
            QCheckBox, QPushButton {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #4CAF50;
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
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
            }
        """ % ("#333333" if is_due_today else "#444444"))

    def toggle_completion(self):
        self.task["completed"] = self.checkbox.isChecked()
        self.parent().save_tasks()

    def update_arrow(self):
        if not self.task["review_dates"]:
            self.arrow_label.setText("")
            return
        next_review = datetime.strptime(self.task["review_dates"][0], "%Y-%m-%d")
        today = datetime.now()
        diff_days = (next_review - today).days
        color = "color: red;" if diff_days <= 0 else "color: yellow;" if diff_days <= 3 else "color: green;"
        date_str = next_review.strftime("%m-%d")
        self.arrow_label.setText(f"➜ {date_str}")
        self.arrow_label.setStyleSheet(color)

    def open_dialog(self, event=None):
        dialog = TaskEditDialog(self.task, self.parent())
        dialog.exec()
        self.checkbox.setText(self.task["name"])
        self.checkbox.setChecked(self.task.get("completed", False))
        self.update_arrow()

    def open_dialog_on_double_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_dialog()


class TaskNotebook(QWidget):
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.load_tasks()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        # 任务输入框
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("输入任务并按回车创建...")
        self.task_input.returnPressed.connect(self.add_task)
        self.layout.addWidget(self.task_input)

        # 任务列表
        self.task_list = QVBoxLayout()
        self.layout.addLayout(self.task_list)

        self.setLayout(self.layout)
        self.setWindowTitle("任务管理记事本")
        self.setStyleSheet("""
            QWidget {
                background-color: #1C1C1C;
            }
            QLineEdit {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                padding: 10px;
            }
        """)
        self.resize(600, 400)
        self.show()

        # 初始化任务卡片
        self.load_task_cards()

    def load_tasks(self):
        print(f"Loading tasks from: {DATA_FILE}")  # Debug file path
        try:
            if not CONFIG_DIR.exists():
                CONFIG_DIR.mkdir(parents=True)
            if not DATA_FILE.exists():
                # Initialize empty tasks file if it doesn't exist
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
            # Migrate existing tasks to include new fields
            modified = False
            for task in self.tasks:
                if "completed" not in task:
                    task["completed"] = False
                    modified = True
                if "daily_note" not in task:
                    task["daily_note"] = ""
                    modified = True
            # Save only if migration modified tasks
            if modified:
                self.save_tasks()
            print(f"Loaded {len(self.tasks)} tasks")  # Debug task count
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {DATA_FILE}: {e}. Initializing empty task list.")
            self.tasks = []
            self.save_tasks()  # Reset file to valid JSON
        except PermissionError as e:
            print(f"Permission error accessing {DATA_FILE}: {e}. Using empty task list.")
            self.tasks = []
        except Exception as e:
            print(f"Unexpected error loading tasks from {DATA_FILE}: {e}. Using empty task list.")
            self.tasks = []

    def save_tasks(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except PermissionError as e:
            print(f"Permission error saving to {DATA_FILE}: {e}")
        except Exception as e:
            print(f"Unexpected error saving to {DATA_FILE}: {e}")

    def load_task_cards(self):
        # Clear existing cards
        for i in reversed(range(self.task_list.count())):
            self.task_list.itemAt(i).widget().setParent(None)

        # Show all tasks, with visual distinction for those due today
        if not self.tasks:
            # Display encouraging message if no tasks exist
            encouraging_label = QLabel("No tasks yet! Create one to get started!")
            self.task_list.addWidget(encouraging_label)
        else:
            for task in self.tasks:
                task_card = TaskCard(task, self)
                self.task_list.addWidget(task_card)

    def create_daily_note(self, date_str, task_name):
        daily_notes_dir = Path(NOTES_DIR) / "daily_notes"
        daily_notes_dir.mkdir(parents=True, exist_ok=True)
        daily_note_path = daily_notes_dir / f"{date_str}.md"

        # Add task under its own heading
        content = f"# {task_name}\n- Related Knowledge Points: \n"
        if daily_note_path.exists():
            with open(daily_note_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            # Append new task if it doesn't exist
            if f"# {task_name}" not in existing_content:
                content = existing_content.rstrip() + "\n\n" + content
            else:
                content = existing_content
        with open(daily_note_path, "w", encoding="utf-8") as f:
            f.write(content)

        return daily_note_path

    def add_task(self):
        task_name = self.task_input.text()
        if task_name:
            today = datetime.now().strftime("%Y-%m-%d")
            category = task_name.split("-")[0] if "-" in task_name else "未分类"
            daily_note_path = self.create_daily_note(today, task_name)
            task = {
                "name": task_name,
                "category": category,
                "created": today,
                "due_date": today,
                "daily_note": str(daily_note_path),
                "expected_time": 1,
                "actual_time": None,
                "review_dates": [(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")],
                "completed_reviews": [],
                "completed": False
            }
            self.tasks.append(task)
            self.save_tasks()
            # Create and add task card immediately
            task_card = TaskCard(task, self)
            # Clear current task list (including encouraging message) and add new task
            for i in reversed(range(self.task_list.count())):
                self.task_list.itemAt(i).widget().setParent(None)
            self.task_list.addWidget(task_card)
            # Re-add other tasks
            for other_task in self.tasks:
                if other_task != task:
                    other_task_card = TaskCard(other_task, self)
                    self.task_list.addWidget(other_task_card)
            self.task_input.clear()

    def delete_task(self, task):
        # Remove task from daily note
        daily_note_path = Path(task.get("daily_note", ""))
        if daily_note_path.exists():
            try:
                with open(daily_note_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Remove section for this task
                import re
                pattern = rf'# {re.escape(task["name"])}\n(.*?)(?=\n# |\Z)'
                content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
                with open(daily_note_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                print(f"Failed to update daily note on delete: {e}")
        self.tasks.remove(task)
        self.save_tasks()
        self.load_task_cards()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskNotebook()
    sys.exit(app.exec())