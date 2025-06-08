import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QCheckBox, QLabel, QLineEdit, QDateEdit, QSpinBox,
                             QPushButton, QDialog, QListWidget, QListWidgetItem,
                             QFileDialog, QInputDialog)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QIcon
import re

# --- 全局常量和样式定义 ---

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".task_notebook"
DEFAULT_DATA_FILE = DEFAULT_CONFIG_DIR / "tasks.json"
DEFAULT_NOTES_DIR = r"C:\Users\HuoZihang\Desktop\笔记"
SETTINGS_FILE = DEFAULT_CONFIG_DIR / "settings.json"

# Stylesheet for StageCard
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
    QPushButton#toggleButton {{
        background-color: transparent;
        color: #FFFFFF;
        border: none;
        text-align: left;
        font-size: 14px;
        font-weight: bold;
        padding: 5px;
    }}
    QPushButton#toggleButton:hover {{
        background-color: #2E2E2E;
        border-radius: 5px;
    }}
    QPushButton#toggleButton:checked {{
        background-color: #2E2E2E;
        border-radius: 5px;
    }}
    QLabel {{
        color: #FFFFFF;
        font-size: 14px;
        background-color: transparent;
    }}
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
            QDialog { background-color: #1A1A1A; border-radius: 8px; }
            QLabel { color: #FFFFFF; font-size: 14px; }
            QLineEdit { background-color: #2E2E2E; color: #FFFFFF; border: 1px solid #444444; border-radius: 5px; padding: 5px; }
            QPushButton { background-color: #007BFF; color: white; border-radius: 5px; padding: 5px 10px; }
            QPushButton:hover { background-color: #0056b3; }
        """)

    def browse_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "选择JSON文件", str(self.parent().data_file),
                                                   "JSON Files (*.json)")
        if file_path: self.json_edit.setText(file_path)

    def browse_notes(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择笔记文件夹", str(self.parent().notes_dir))
        if dir_path: self.notes_edit.setText(dir_path)

    def save_settings(self):
        settings = {"data_file": self.json_edit.text(), "notes_dir": self.notes_edit.text()}
        try:
            if not DEFAULT_CONFIG_DIR.exists(): DEFAULT_CONFIG_DIR.mkdir(parents=True)
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
        self.setWindowTitle(f"阶段详情: {stage['name']}")
        self.setWindowIcon(QIcon("icon.png"))
        self.setModal(True)
        self.initUI()
        self.calculate_and_update_ers()

    def initUI(self):
        layout = QVBoxLayout()
        self.name_label = QLabel("阶段名称:")
        self.name_edit = QLineEdit(self.stage["name"])
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        ers_layout = QHBoxLayout()
        self.ers_label = QLabel("考试准备得分 (ERS): 尚未计算")
        self.ers_label.setStyleSheet("font-weight: bold; color: #00C4B4; font-size: 16pt;")
        ers_layout.addWidget(self.ers_label)
        ers_layout.addStretch()
        layout.addLayout(ers_layout)

        exam_score_layout = QHBoxLayout()
        self.exam_score_input = QLineEdit()
        self.exam_score_input.setPlaceholderText("输入新模考分数(%)")
        self.add_score_button = QPushButton("添加模考分数")
        self.add_score_button.clicked.connect(self.add_practice_exam_score)
        exam_score_layout.addWidget(self.exam_score_input)
        exam_score_layout.addWidget(self.add_score_button)
        layout.addLayout(exam_score_layout)

        self.scores_display_label = QLabel(f"最近分数: {self.stage.get('practice_exam_scores', [])}")
        self.scores_display_label.setStyleSheet("color: #AAAAAA; font-size: 11pt;")
        layout.addWidget(self.scores_display_label)

        self.kp_label = QLabel("知识点 (任务):")
        self.kp_list = QListWidget()
        self.populate_kp_list()
        layout.addWidget(self.kp_label)
        layout.addWidget(self.kp_list)

        kp_add_layout = QHBoxLayout()
        self.kp_input = QLineEdit()
        self.kp_input.setPlaceholderText("输入新知识点名称...")
        self.kp_input.returnPressed.connect(self.add_knowledge_point)
        self.add_kp_button = QPushButton("添加知识点")
        self.add_kp_button.clicked.connect(self.add_knowledge_point)
        kp_add_layout.addWidget(self.kp_input)
        kp_add_layout.addWidget(self.add_kp_button)
        layout.addLayout(kp_add_layout)

        time_layout = QHBoxLayout()
        self.expected_time_label = QLabel("阶段预期耗时(h):")
        self.expected_time_spin = QSpinBox()
        self.expected_time_spin.setValue(self.stage.get("expected_time", 10))
        self.actual_time_label = QLabel("本次实际复习耗时(h):")
        self.actual_time_spin = QSpinBox()
        self.actual_time_spin.setValue(0)
        time_layout.addWidget(self.expected_time_label)
        time_layout.addWidget(self.expected_time_spin)
        time_layout.addWidget(self.actual_time_label)
        time_layout.addWidget(self.actual_time_spin)
        layout.addLayout(time_layout)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存并更新复习计划")
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

        self.setStyleSheet("""
            QDialog { background-color: #1A1A1A; }
            QLabel { color: #FFFFFF; font-size: 14px; }
            QLineEdit, QSpinBox, QListWidget { background-color: #2E2E2E; color: #FFFFFF; border: 1px solid #444444; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #007BFF; color: white; border: none; border-radius: 4px; padding: 8px 12px; font-size: 12px; }
            QPushButton:hover { background-color: #0056b3; }
        """)
        self.delete_button.setStyleSheet("background-color: #DC3545; color: white; border: none; border-radius: 4px; padding: 8px 12px; font-size: 12px;")
        self.close_button.setStyleSheet("background-color: #6c757d; color: white; border: none; border-radius: 4px; padding: 8px 12px; font-size: 12px;")

    def populate_kp_list(self):
        self.kp_list.clear()
        for kp_index, kp in enumerate(self.stage.get("knowledge_points", [])):
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(5, 2, 5, 2)
            confidence = kp.get('confidence_level', 0)
            kp_label = QLabel(f"{kp['name']} (信心: {confidence}/5)")
            layout.addWidget(kp_label)
            layout.addStretch()
            confidence_button = QPushButton("设置信心")
            confidence_button.setProperty("kp_index", kp_index)
            confidence_button.clicked.connect(self.handle_set_confidence)
            confidence_button.setStyleSheet("background-color: #007BFF; color: white; border: none; border-radius: 4px; padding: 5px 8px; font-size: 12px;")
            layout.addWidget(confidence_button)
            delete_button = QPushButton("删除")
            delete_button.setProperty("kp_index", kp_index)
            delete_button.clicked.connect(self.delete_knowledge_point)
            delete_button.setStyleSheet("background-color: #DC3545; color: white; border: none; border-radius: 4px; padding: 5px 8px; font-size: 12px;")
            layout.addWidget(delete_button)
            item.setSizeHint(widget.sizeHint())
            self.kp_list.addItem(item)
            self.kp_list.setItemWidget(item, widget)

    def handle_set_confidence(self):
        sender = self.sender()
        kp_index = sender.property("kp_index")
        kp = self.stage["knowledge_points"][kp_index]
        current_confidence = kp.get("confidence_level", 0)
        new_confidence, ok = QInputDialog.getInt(self, "设置信心水平", f"为 '{kp['name']}' 设置信心 (1-5):",
                                                 current_confidence, 1, 5, 1)
        if ok:
            kp['confidence_level'] = new_confidence
            self.populate_kp_list()
            self.calculate_and_update_ers()
            self.parent().save_stages()

    def add_practice_exam_score(self):
        score_text = self.exam_score_input.text().strip().replace('%', '')
        try:
            score = int(score_text)
            if 0 <= score <= 100:
                if "practice_exam_scores" not in self.stage: self.stage["practice_exam_scores"] = []
                self.stage["practice_exam_scores"].append(score)
                self.scores_display_label.setText(f"最近分数: {self.stage['practice_exam_scores']}")
                self.exam_score_input.clear()
                self.calculate_and_update_ers()
                self.parent().save_stages()
            else:
                print("分数必须在 0-100 之间。")
        except ValueError:
            print("请输入有效的数字分数。")

    def calculate_and_update_ers(self):
        kps = self.stage.get("knowledge_points", [])
        total_kps = len(kps)
        if total_kps == 0:
            self.ers_label.setText("ERS: N/A (无知识点)")
            self.stage['ers_score'] = 0
            return
        mastered_kps = sum(1 for kp in kps if kp.get('confidence_level', 0) >= 4)
        percentage_mastered = (mastered_kps / total_kps)
        scores = self.stage.get("practice_exam_scores", [])
        last_n_scores = scores[-3:]
        avg_score = (sum(last_n_scores) / len(last_n_scores)) / 100.0 if last_n_scores else 0.0
        ers = avg_score * percentage_mastered * 100
        self.stage['ers_score'] = round(ers, 2)
        self.ers_label.setText(f"ERS: {self.stage['ers_score']:.2f}%")

    def add_knowledge_point(self):
        kp_name = self.kp_input.text().strip()
        if kp_name:
            if "knowledge_points" not in self.stage: self.stage["knowledge_points"] = []
            new_kp = {"name": kp_name, "confidence_level": 0}
            self.stage["knowledge_points"].append(new_kp)
            self.update_daily_note_kp(kp_name)
            self.populate_kp_list()
            self.calculate_and_update_ers()
            self.parent().save_stages()
            self.kp_input.clear()

    def delete_knowledge_point(self):
        sender = self.sender()
        kp_index = sender.property("kp_index")
        kp_to_delete = self.stage["knowledge_points"][kp_index]
        kp_name_to_delete = kp_to_delete["name"]
        self.remove_kp_from_daily_note(kp_name_to_delete)
        self.stage["knowledge_points"].pop(kp_index)
        self.populate_kp_list()
        self.calculate_and_update_ers()
        self.parent().save_stages()

    def save_details(self):
        old_name = self.stage["name"]
        new_name = self.name_edit.text()
        self.stage["name"] = new_name
        self.stage["expected_time"] = self.expected_time_spin.value()
        actual_time = self.actual_time_spin.value()
        if actual_time > 0: self.adjust_review_interval(actual_time)
        if old_name != new_name and self.stage.get("daily_note"):
            self.update_daily_note_name(old_name, new_name)
        self.parent().save_stages()
        self.parent().load_stage_cards()
        self.accept()

    def adjust_review_interval(self, actual_time_spent):
        base_intervals = [1, 2, 4, 7, 15, 30, 60]
        if "completed_reviews" not in self.stage: self.stage["completed_reviews"] = []
        review_index = len(self.stage["completed_reviews"])
        interval_days = base_intervals[min(review_index, len(base_intervals) - 1)]
        expected_time = self.stage.get("expected_time", 1)
        if expected_time > 0:
            time_ratio = actual_time_spent / expected_time
            if time_ratio > 1.2:
                interval_days *= 0.8
            elif time_ratio < 0.8:
                interval_days *= 1.2
        interval_days = max(1, int(round(interval_days)))
        last_date = datetime.now()
        next_date = last_date + timedelta(days=interval_days)
        self.stage["review_dates"] = [next_date.strftime("%Y-%m-%d")]
        self.stage["completed_reviews"].append(
            {"date": last_date.strftime("%Y-%m-%d"), "actual_time": actual_time_spent})
        print(f"阶段 '{self.stage['name']}' 下次复习日期已更新为: {self.stage['review_dates'][0]}")

    def delete_stage(self):
        self.parent().delete_stage(self.stage)
        self.accept()

    def update_daily_note_kp(self, kp_name):
        daily_note_path = Path(self.stage.get("daily_note", ""))
        if not daily_note_path.exists(): return
        try:
            if not os.access(daily_note_path, os.W_OK):
                print(f"笔记文件不可写: {daily_note_path}")
                return
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()
            stage_heading_pattern = rf"(^# {re.escape(self.stage['name'])}.*?)(?=\n^# |\Z)"
            stage_match = re.search(stage_heading_pattern, content, re.MULTILINE | re.DOTALL)
            if stage_match:
                stage_section_content = stage_match.group(1)
                kp_line_pattern = r"(- Related Knowledge Points:.*?)$"
                kp_line_match = re.search(kp_line_pattern, stage_section_content, re.MULTILINE)
                new_kp_link = f"[[{kp_name}]]"
                if kp_line_match:
                    existing_kp_line = kp_line_match.group(1)
                    if new_kp_link not in existing_kp_line:
                        updated_kp_line = existing_kp_line.rstrip() + f", {new_kp_link}"
                        content = content.replace(existing_kp_line, updated_kp_line)
                else:
                    new_kp_section_line = f"\n- Related Knowledge Points: {new_kp_link}"
                    content = content.replace(stage_section_content,
                                              stage_section_content.rstrip() + new_kp_section_line)
                with open(daily_note_path, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception as e:
            print(f"更新笔记中的知识点失败: {e}")

    def remove_kp_from_daily_note(self, kp_name):
        daily_note_path = Path(self.stage.get("daily_note", ""))
        if not daily_note_path.exists(): return
        try:
            if not os.access(daily_note_path, os.W_OK):
                print(f"笔记文件不可写: {daily_note_path}")
                return
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()
            stage_heading_pattern = rf"(^# {re.escape(self.stage['name'])}.*?)(?=\n^# |\Z)"
            stage_match = re.search(stage_heading_pattern, content, re.MULTILINE | re.DOTALL)
            if stage_match:
                stage_section_content = stage_match.group(1)
                kp_line_pattern = r"(- Related Knowledge Points:.*?)$"
                kp_line_match = re.search(kp_line_pattern, stage_section_content, re.MULTILINE)
                if kp_line_match:
                    original_kp_line = kp_line_match.group(1)
                    kp_list_str = original_kp_line.replace("- Related Knowledge Points:", "").strip()
                    current_kps_linked = re.findall(r"(\[\[.*?\]\])", kp_list_str)
                    kp_link_to_remove = f"[[{kp_name}]]"
                    if kp_link_to_remove in current_kps_linked:
                        current_kps_linked.remove(kp_link_to_remove)
                    new_kp_list_str = ", ".join(current_kps_linked)
                    updated_kp_line = f"- Related Knowledge Points: {new_kp_list_str}"
                    modified_stage_section = stage_section_content.replace(original_kp_line, updated_kp_line)
                    content = content.replace(stage_section_content, modified_stage_section)
                    with open(daily_note_path, "w", encoding="utf-8") as f:
                        f.write(content)
        except Exception as e:
            print(f"从笔记中移除知识点链接失败: {e}")

    def update_daily_note_name(self, old_name, new_name):
        daily_note_path = Path(self.stage.get("daily_note", ""))
        if not daily_note_path.exists(): return
        try:
            if not os.access(daily_note_path, os.W_OK):
                print(f"笔记文件不可写: {daily_note_path}")
                return
            with open(daily_note_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = re.sub(rf"(^# {re.escape(old_name)}\n)", f"# {new_name}\n", content, flags=re.MULTILINE)
            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"更新笔记中的阶段名称失败: {e}")

class StageCard(QWidget):
    def __init__(self, stage_data, parent=None):
        super().__init__(parent)
        self.stage = stage_data
        self.parent_widget = parent
        self.is_expanded = False
        self.initUI()
        self.update_visuals()

    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.header_layout = QHBoxLayout()
        self.toggle_button = QPushButton(f"▶ {self.stage['name']}")
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_knowledge_points)
        self.ers_label = QLabel()
        self.arrow_label = QLabel()
        self.header_layout.addWidget(self.toggle_button)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.ers_label)
        self.header_layout.addWidget(self.arrow_label)
        self.main_layout.addLayout(self.header_layout)
        self.kp_container = QWidget()
        self.kp_layout = QVBoxLayout(self.kp_container)
        self.kp_container.setVisible(False)
        self.populate_kp_list_in_card()
        self.main_layout.addWidget(self.kp_container)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def update_visuals(self):
        today = datetime.now().date()
        is_due = False
        if self.stage.get("review_dates"):
            next_review_date = datetime.strptime(self.stage["review_dates"][0], "%Y-%m-%d").date()
            if next_review_date <= today: is_due = True
        background_color = "#FF4500" if is_due else "#2E2E2E"
        self.setStyleSheet(STAGE_CARD_STYLE_TEMPLATE.format(background_color=background_color))
        self.toggle_button.setText(f"{'▼' if self.is_expanded else '▶'} {self.stage['name']}")
        self.update_ers_and_arrow()

    def update_ers_and_arrow(self):
        ers_score = self.stage.get('ers_score', 0)
        self.ers_label.setText(f"<b>ERS: {ers_score:.2f}%</b>")
        self.ers_label.setStyleSheet("color: #00C4B4; margin-right: 15px;")
        if not self.stage.get("review_dates"): self.arrow_label.setText(""); return
        next_review = datetime.strptime(self.stage["review_dates"][0], "%Y-%m-%d")
        today = datetime.now()
        diff_days = (next_review.date() - today.date()).days
        color = "color: #FF6347;" if diff_days < 0 else "color: #FFA500;" if diff_days == 0 else "color: #00C4B4;" if diff_days <= 3 else "color: #90EE90;"
        date_str = next_review.strftime("%m-%d")
        self.arrow_label.setText(f"➜ {date_str}")
        self.arrow_label.setStyleSheet(f"font-weight: bold; {color}")

    def populate_kp_list_in_card(self):
        while self.kp_layout.count():
            child = self.kp_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        kps = self.stage.get("knowledge_points", [])
        if not kps: self.kp_layout.addWidget(QLabel("无知识点")); return
        for kp in kps:
            confidence = kp.get('confidence_level', 0)
            kp_label = QLabel(f"- {kp['name']} (信心: {confidence}/5)")
            color = "#AAAAAA"
            if confidence >= 4:
                color = "#90EE90"
            elif confidence >= 2:
                color = "#00C4B4"
            else:
                color = "#FF6347"
            kp_label.setStyleSheet(f"color: {color}; font-size: 12pt; margin-left: 20px;")
            self.kp_layout.addWidget(kp_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child_widget = self.childAt(event.pos())
            if isinstance(child_widget, QPushButton): return
            dialog = StageDialog(self.stage, self.parent_widget)
            dialog.exec()
            self.update_visuals()

    def toggle_knowledge_points(self):
        self.is_expanded = self.toggle_button.isChecked()
        self.kp_container.setVisible(self.is_expanded)
        self.update_visuals()

class TaskNotebook(QWidget):
    def __init__(self):
        super().__init__()
        self.stages = []
        self.data_file = str(DEFAULT_DATA_FILE)
        self.notes_dir = str(DEFAULT_NOTES_DIR)
        self.load_settings()
        self.load_stages()
        self.initUI()

    def initUI(self):
        self.main_v_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()
        self.stage_input = QLineEdit()
        self.stage_input.setPlaceholderText("输入新课程/阶段名称并按回车创建...")
        self.stage_input.returnPressed.connect(self.add_stage)
        top_bar_layout.addWidget(self.stage_input)
        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self.open_settings)
        top_bar_layout.addWidget(self.settings_button)
        self.main_v_layout.addLayout(top_bar_layout)
        self.stage_list_container_widget = QWidget()
        self.stage_list_layout = QVBoxLayout(self.stage_list_container_widget)
        self.stage_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_v_layout.addWidget(self.stage_list_container_widget)
        self.setWindowTitle("火腿肠ERS管理器")
        self.setWindowIcon(QIcon("icon.png"))
        self.setStyleSheet("background-color: #1A1A1A;")
        self.resize(700, 600)
        self.show()
        self.load_stage_cards()

    def load_stages(self):
        print(f"从 {self.data_file} 加载阶段数据...")
        try:
            if not Path(self.data_file).exists():
                with open(self.data_file, 'w', encoding="utf-8") as f: json.dump([], f)
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.stages = json.load(f)
            modified = False
            for stage in self.stages:
                if 'practice_exam_scores' not in stage: stage['practice_exam_scores'] = []; modified = True
                if 'ers_score' not in stage: stage['ers_score'] = 0; modified = True
                if 'review_dates' not in stage: stage['review_dates'] = [
                    (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")]; modified = True
                if 'completed_reviews' not in stage: stage['completed_reviews'] = []; modified = True
                if 'daily_note' not in stage: stage['daily_note'] = ""; modified = True
                if 'knowledge_points' in stage:
                    for kp in stage['knowledge_points']:
                        if 'kp_review_dates' in kp: del kp['kp_review_dates']; modified = True
                        if 'kp_completed_reviews' in kp: del kp['kp_completed_reviews']; modified = True
                        if 'confidence_level' not in kp:
                            if kp.get('kp_mastered') is True:
                                kp['confidence_level'] = 5
                            else:
                                kp['confidence_level'] = 0
                            modified = True
                        if 'kp_mastered' in kp: del kp['kp_mastered']; modified = True
            if modified: print("数据模型已更新，正在保存..."); self.save_stages()
        except Exception as e:
            print(f"加载或迁移阶段数据时出错: {e}"); self.stages = []

    def save_stages(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.stages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存阶段数据失败: {e}")

    def load_stage_cards(self):
        while self.stage_list_layout.count():
            child = self.stage_list_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        sorted_stages = sorted(self.stages, key=lambda s: s.get('review_dates', ['9999-99-99'])[0])
        for stage_data in sorted_stages:
            stage_card = StageCard(stage_data, self)
            self.stage_list_layout.addWidget(stage_card)
        self.stage_list_layout.addStretch()

    def add_stage(self):
        stage_name = self.stage_input.text().strip()
        if stage_name:
            today_str = datetime.now().strftime("%Y-%m-%d")
            daily_note_path = self.create_daily_note(today_str, stage_name)
            new_stage = {
                "name": stage_name,
                "category": stage_name.split("-")[0].strip() if "-" in stage_name else "未分类",
                "created": today_str,
                "review_dates": [(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")],
                "completed_reviews": [], "expected_time": 10, "knowledge_points": [],
                "practice_exam_scores": [], "ers_score": 0,
                "daily_note": str(daily_note_path) if daily_note_path else ""
            }
            self.stages.append(new_stage)
            self.save_stages()
            self.load_stage_cards()
            self.stage_input.clear()

    def delete_stage(self, stage_to_delete):
        daily_note_path = Path(stage_to_delete.get("daily_note", ""))
        if daily_note_path.exists():
            try:
                if not os.access(daily_note_path, os.W_OK):
                    print(f"笔记文件不可写: {daily_note_path}")
                else:
                    with open(daily_note_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    pattern = rf'^# {re.escape(stage_to_delete["name"])}\n(.*?)(?=\n^# |\Z)'
                    new_content = re.sub(pattern, '', content, flags=re.DOTALL | re.MULTILINE).strip()
                    with open(daily_note_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
            except Exception as e:
                print(f"删除笔记中的阶段内容失败: {e}")
        self.stages.remove(stage_to_delete)
        self.save_stages()
        self.load_stage_cards()

    def load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f: settings = json.load(f)
                self.data_file = settings.get("data_file", str(DEFAULT_DATA_FILE))
                self.notes_dir = settings.get("notes_dir", str(DEFAULT_NOTES_DIR))
        except Exception as e:
            print(f"加载设置失败: {e}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def create_daily_note(self, date_str, stage_name):
        notes_dir_path = Path(self.notes_dir)
        if not notes_dir_path.is_dir(): return ""
        daily_notes_dir = notes_dir_path / "daily_notes"
        daily_notes_dir.mkdir(parents=True, exist_ok=True)
        daily_note_file_path = daily_notes_dir / f"{date_str}.md"
        stage_header_content = f"\n\n# {stage_name}\n- Related Knowledge Points: \n"
        try:
            if not os.access(daily_notes_dir, os.W_OK):
                print(f"笔记目录不可写: {daily_notes_dir}")
                return ""
            if daily_note_file_path.exists():
                with open(daily_note_file_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                if f"# {stage_name}" not in existing_content:
                    with open(daily_note_file_path, "a", encoding="utf-8") as f:
                        f.write(stage_header_content)
            else:
                with open(daily_note_file_path, "w", encoding="utf-8") as f:
                    f.write(f"# Daily Note - {date_str}{stage_header_content}")
            return daily_note_file_path
        except Exception as e:
            print(f"创建或更新笔记失败: {e}"); return ""

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskNotebook()
    sys.exit(app.exec())