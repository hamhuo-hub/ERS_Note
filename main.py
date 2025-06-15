import sys
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QDialog, QListWidget,
                             QListWidgetItem, QFileDialog, QInputDialog, QGridLayout,
                             QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import random

# --- Global Constants and Styles ---

DEFAULT_CONFIG_DIR = Path.home() / ".task_notebook"
DEFAULT_DATA_FILE = DEFAULT_CONFIG_DIR / "tasks.json"
DEFAULT_NOTES_DIR = r"C:\Users\HuoZihang\Desktop\笔记"
SETTINGS_FILE = DEFAULT_CONFIG_DIR / "settings.json"

CARD_STYLE = """
    QWidget {
        background-color: #2D2D2D;
        border-radius: 8px;
        padding: 8px;
        margin: 5px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
    }
    QLabel {
        color: #FFFFFF;
        font-size: 14px;
        background-color: transparent;
    }
"""

APP_STYLE = """
    QWidget {
        background-color: #1A1A1A;
        color: #FFFFFF;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QPushButton {
        background-color: #007BFF;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 12px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #0056b3;
    }
    QLineEdit, QComboBox {
        background-color: #2E2E2E;
        color: #FFFFFF;
        border: 1px solid #444444;
        border-radius: 4px;
        padding: 5px;
    }
"""

ENCOURAGE_MESSAGES = [
    "今天的复习任务已完成！继续保持，明天见 💪",
    "没有题目要复习，棒棒哒，明天再接再厉！",
    "今天轻松一下，为接下来的学习储备能量！"
]


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
        settings = {"data_file": self.json_edit.text(), "notes_dir": self.notes_edit.text()}
        try:
            if not DEFAULT_CONFIG_DIR.exists():
                DEFAULT_CONFIG_DIR.mkdir(parents=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.parent().data_file = self.json_edit.text()
            self.parent().notes_dir = self.notes_edit.text()
            self.parent().load_subjects()
            self.parent().load_daily_problems()
            self.accept()
        except Exception as e:
            print(f"保存设置失败: {e}")


class QuickAddDialog(QDialog):
    def __init__(self, subjects, parent=None):
        super().__init__(parent)
        self.subjects = subjects
        self.setWindowTitle("快速录题")
        self.setWindowIcon(QIcon("icon.png"))
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.code_label = QLabel("题目编号:")
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例: P301-15")
        layout.addWidget(self.code_label)
        layout.addWidget(self.code_edit)

        self.subject_label = QLabel("学习主题:")
        self.subject_combo = QLineEdit()
        self.subject_combo.setPlaceholderText("输入或选择主题")
        layout.addWidget(self.subject_label)
        layout.addWidget(self.subject_combo)

        self.tags_label = QLabel("主题与技巧（可选）:")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("例: 微积分,极限-洛必达法则,换元法")
        layout.addWidget(self.tags_label)
        layout.addWidget(self.tags_edit)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("添加并记录")
        self.add_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_data(self):
        return {
            "description": self.code_edit.text().strip(),
            "subject": self.subject_combo.text().strip(),
            "tags": self.tags_edit.text().strip()
        }


class SubjectOverviewDialog(QDialog):
    def __init__(self, subjects, parent=None):
        super().__init__(parent)
        self.subjects = subjects
        self.setWindowTitle("学习主题概览")
        self.setWindowIcon(QIcon("icon.png"))
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.subject_list = QListWidget()
        self.populate_subject_list()
        layout.addWidget(QLabel("学习主题列表："))
        layout.addWidget(self.subject_list)
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        self.setLayout(layout)

    def populate_subject_list(self):
        self.subject_list.clear()
        for idx, subject in enumerate(self.subjects):
            item = QListWidgetItem(
                f"{subject['name']} (ERS: {subject['ers_score']:.1f}%, 题目: {len(subject['problems'])}, 概念: {len(subject['concepts'])})")
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.subject_list.addItem(item)


class ExamScoreDialog(QDialog):
    def __init__(self, subjects, parent=None):
        super().__init__(parent)
        self.subjects = subjects
        self.setWindowTitle("录入模考成绩")
        self.setWindowIcon(QIcon("icon.png"))
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.subject_label = QLabel("学习主题:")
        self.subject_combo = QLineEdit()
        self.subject_combo.setPlaceholderText("输入或选择主题")
        layout.addWidget(self.subject_label)
        layout.addWidget(self.subject_combo)

        self.score_label = QLabel("分数（0-100）:")
        self.score_edit = QLineEdit()
        self.score_edit.setPlaceholderText("例: 85")
        layout.addWidget(self.score_label)
        layout.addWidget(self.score_edit)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("添加")
        self.add_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_data(self):
        return {
            "subject": self.subject_combo.text().strip(),
            "score": self.score_edit.text().strip()
        }


class ProblemCard(QWidget):
    def __init__(self, problem, subject, parent=None):
        super().__init__(parent)
        self.problem = problem
        self.subject = subject
        self.parent_widget = parent
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        confidence = self.problem.get("confidence", 0)
        subjects = ", ".join(self.problem.get("subjects", []))
        skills = ", ".join(self.problem.get("skills", []))
        review_date = self.problem.get("review_dates", [""])[0]
        color = "#FF6347" if confidence <= 2 else "#FFD700" if confidence == 3 else "#90EE90"
        label = QLabel(
            f"{self.problem['description']} (信心: {confidence}/5, 主题: {subjects}, 技巧: {skills}) ➜ {review_date}")
        label.setStyleSheet(f"color: {color}; font-size: 12pt;")
        layout.addWidget(label)
        layout.addStretch()
        for level in range(1, 6):
            btn = QPushButton(str(level))
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#007BFF' if level <= confidence else '#444444'};
                    color: white;
                    border-radius: 15px;
                    font-size: 10pt;
                }}
                QPushButton:hover {{
                    background-color: #0056b3;
                }}
            """)
            btn.clicked.connect(lambda _, l=level: self.update_confidence(l))
            layout.addWidget(btn)
        self.setStyleSheet(CARD_STYLE)

    def update_confidence(self, new_confidence):
        self.problem["confidence"] = new_confidence
        self.parent_widget.adjust_problem_review_interval(self.problem, new_confidence, self.subject)
        self.parent_widget.save_subjects()
        self.parent_widget.load_daily_problems()
        if new_confidence >= 4:
            reply = QMessageBox.question(self, "建议删除",
                                         f"题目 '{self.problem['description']}' 信心已达 {new_confidence}，建议删除以避免题海战术，是否删除？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.subject["problems"].remove(self.problem)
                self.parent_widget.remove_problem_from_daily_note(self.problem["description"],
                                                                  self.subject["daily_note"])
                self.parent_widget.save_subjects()
                self.parent_widget.load_daily_problems()


class TaskNotebook(QWidget):
    def __init__(self):
        super().__init__()
        self.subjects = []
        self.data_file = str(DEFAULT_DATA_FILE)
        self.notes_dir = str(DEFAULT_NOTES_DIR)
        self.load_settings()
        self.load_subjects()
        self.initUI()

    def initUI(self):
        self.main_v_layout = QVBoxLayout(self)

        # Header
        header_layout = QVBoxLayout()
        title = QLabel("ERS 学习管理")
        title.setStyleSheet("color: #00C4B4; font-size: 24pt; font-weight: bold;")
        subtitle = QLabel("今日复习 · 智能提醒")
        subtitle.setStyleSheet("color: #AAAAAA; font-size: 12pt;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        button_layout = QHBoxLayout()
        self.quick_add_btn = QPushButton("快速录题")
        self.quick_add_btn.clicked.connect(self.show_quick_add)
        self.view_subjects_btn = QPushButton("查看所有主题")
        self.view_subjects_btn.clicked.connect(self.view_all_subjects)
        self.exam_score_btn = QPushButton("模考成绩")
        self.exam_score_btn.clicked.connect(self.show_exam_score)
        self.open_obsidian_btn = QPushButton("打开Obsidian笔记")
        self.open_obsidian_btn.clicked.connect(self.open_obsidian_notes)
        button_layout.addWidget(self.quick_add_btn)
        button_layout.addWidget(self.view_subjects_btn)
        button_layout.addWidget(self.exam_score_btn)
        button_layout.addWidget(self.open_obsidian_btn)
        header_layout.addLayout(button_layout)
        self.main_v_layout.addLayout(header_layout)

        # Overview Cards
        overview_layout = QGridLayout()
        self.tasks_card = QWidget()
        tasks_layout = QVBoxLayout(self.tasks_card)
        tasks_label = QLabel("今日任务")
        tasks_label.setStyleSheet("color: #00C4B4; font-size: 16pt; font-weight: bold;")
        self.tasks_count = QLabel("0")
        self.tasks_count.setStyleSheet("color: #00C4B4; font-size: 24pt; font-weight: bold;")
        tasks_sub = QLabel("道题待复习")
        tasks_sub.setStyleSheet("color: #AAAAAA; font-size: 10pt;")
        tasks_layout.addWidget(tasks_label)
        tasks_layout.addWidget(self.tasks_count)
        tasks_layout.addWidget(tasks_sub)
        self.tasks_card.setStyleSheet(CARD_STYLE)

        self.ers_card = QWidget()
        ers_layout = QVBoxLayout(self.ers_card)
        ers_label = QLabel("平均ERS")
        ers_label.setStyleSheet("color: #90EE90; font-size: 16pt; font-weight: bold;")
        self.ers_count = QLabel("0.0")
        self.ers_count.setStyleSheet("color: #90EE90; font-size: 24pt; font-weight: bold;")
        ers_sub = QLabel("考试准备度")
        ers_sub.setStyleSheet("color: #AAAAAA; font-size: 10pt;")
        ers_layout.addWidget(ers_label)
        ers_layout.addWidget(self.ers_count)
        ers_layout.addWidget(ers_sub)
        self.ers_card.setStyleSheet(CARD_STYLE)

        self.total_card = QWidget()
        total_layout = QVBoxLayout(self.total_card)
        total_label = QLabel("题库总数")
        total_label.setStyleSheet("color: #FF69B4; font-size: 16pt; font-weight: bold;")
        self.total_count = QLabel("0")
        self.total_count.setStyleSheet("color: #FF69B4; font-size: 24pt; font-weight: bold;")
        total_sub = QLabel("道错题")
        total_sub.setStyleSheet("color: #AAAAAA; font-size: 10pt;")
        total_layout.addWidget(total_label)
        total_layout.addWidget(self.total_count)
        total_layout.addWidget(total_sub)
        self.total_card.setStyleSheet(CARD_STYLE)

        overview_layout.addWidget(self.tasks_card, 0, 0)
        overview_layout.addWidget(self.ers_card, 0, 1)
        overview_layout.addWidget(self.total_card, 0, 2)
        self.main_v_layout.addLayout(overview_layout)

        # Today's Revision
        self.daily_label = QLabel("今日复习计划")
        self.daily_label.setStyleSheet("color: #FFFFFF; font-size: 16pt; font-weight: bold;")
        self.main_v_layout.addWidget(self.daily_label)
        self.problem_list_container = QWidget()
        self.problem_list_layout = QVBoxLayout(self.problem_list_container)
        self.problem_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_v_layout.addWidget(self.problem_list_container)
        self.main_v_layout.addStretch()

        self.setWindowTitle("火腿肠ERS管理器")
        self.setWindowIcon(QIcon("icon.png"))
        self.setStyleSheet(APP_STYLE)
        self.resize(900, 600)
        self.show()
        self.load_daily_problems()

    def load_subjects(self):
        try:
            if not Path(self.data_file).exists():
                with open(self.data_file, 'w', encoding="utf-8") as f:
                    json.dump([], f)
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.subjects = json.load(f)
            modified = False
            for subject in self.subjects:
                if 'practice_exam_scores' not in subject:
                    subject['practice_exam_scores'] = []
                    modified = True
                if 'ers_score' not in subject:
                    subject['ers_score'] = 0
                    modified = True
                if 'daily_note' not in subject:
                    subject['daily_note'] = ""
                    modified = True
                if 'problems' not in subject:
                    subject['problems'] = []
                    modified = True
                if 'concepts' not in subject:
                    subject['concepts'] = []
                    modified = True
                for problem in subject.get("problems", []):
                    if 'review_dates' not in problem:
                        problem['review_dates'] = [(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")]
                        modified = True
                    if 'completed_reviews' not in problem:
                        problem['completed_reviews'] = []
                        modified = True
                    if 'confidence' not in problem:
                        problem['confidence'] = problem.get('mastery_level', 1)
                        if 'mastery_level' in problem:
                            del problem['mastery_level']
                        modified = True
                    if 'subjects' not in problem or 'skills' not in problem:
                        if 'tags' in problem:
                            subjects, skills = [], []
                            for tag in problem['tags']:
                                if '-' in tag:
                                    sub, sk = tag.split('-', 1)
                                    subjects.append(sub.strip())
                                    skills.append(sk.strip())
                                else:
                                    subjects.append(tag.strip())
                            problem['subjects'] = subjects
                            problem['skills'] = skills
                            del problem['tags']
                            modified = True
                        else:
                            problem['subjects'] = []
                            problem['skills'] = []
                            modified = True
                for concept in subject.get("concepts", []):
                    if 'subjects' not in concept or 'skills' not in concept:
                        if 'tags' in concept:
                            subjects, skills = [], []
                            for tag in concept['tags']:
                                if '-' in tag:
                                    sub, sk = tag.split('-', 1)
                                    subjects.append(sub.strip())
                                    skills.append(sk.strip())
                                else:
                                    subjects.append(tag.strip())
                            concept['subjects'] = subjects
                            concept['skills'] = skills
                            del concept['tags']
                            modified = True
                        else:
                            concept['subjects'] = []
                            concept['skills'] = []
                            modified = True
            if modified:
                print("数据模型已更新，正在保存...")
                self.save_subjects()
        except Exception as e:
            print(f"加载或迁移主题数据时出错: {e}")
            self.subjects = []

    def save_subjects(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.subjects, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存主题数据失败: {e}")

    def load_daily_problems(self):
        while self.problem_list_layout.count():
            child = self.problem_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        today = datetime.now().date()
        daily_problems = []
        for subject in self.subjects:
            for problem in subject.get("problems", []):
                if problem.get("review_dates"):
                    review_date = datetime.strptime(problem["review_dates"][0], "%Y-%m-%d").date()
                    if review_date <= today:
                        daily_problems.append((problem, subject))
        daily_problems.sort(key=lambda x: x[0].get("confidence", 0))
        for problem, subject in daily_problems:
            card = ProblemCard(problem, subject, self)
            self.problem_list_layout.addWidget(card)
        if not daily_problems:
            encourage_label = QLabel(random.choice(ENCOURAGE_MESSAGES))
            encourage_label.setStyleSheet(
                "color: #90EE90; font-size: 16pt; font-weight: bold; text-align: center; padding: 50px;")
            self.problem_list_layout.addWidget(encourage_label)
        self.problem_list_layout.addStretch()

        # Update Overview Cards
        self.tasks_count.setText(str(len(daily_problems)))
        total_problems = sum(len(s['problems']) for s in self.subjects)
        self.total_count.setText(str(total_problems))
        avg_ers = sum(s['ers_score'] for s in self.subjects) / len(self.subjects) if self.subjects else 0
        self.ers_count.setText(f"{avg_ers:.1f}")

    def show_quick_add(self):
        dialog = QuickAddDialog([s['name'] for s in self.subjects], self)
        if dialog.exec():
            data = dialog.get_data()
            if data['description'] and data['subject']:
                self.add_problem(data['description'], data['subject'], data['tags'])

    def add_problem(self, description, subject_name, tags):
        subjects, skills = [], []
        if tags and '-' in tags:
            subject_part, skill_part = tags.split('-', 1)
            subjects = [s.strip() for s in subject_part.split(',') if s.strip()]
            skills = [s.strip() for s in skill_part.split(',') if s.strip()]
        elif tags:
            subjects = [s.strip() for s in tags.split(',') if s.strip()]

        today_str = datetime.now().strftime("%Y-%m-%d")
        subject = next((s for s in self.subjects if s['name'] == subject_name), None)
        if not subject:
            daily_note_path = self.create_daily_note(today_str, subject_name)
            subject = {
                "name": subject_name,
                "created": today_str,
                "daily_note": str(daily_note_path) if daily_note_path else "",
                "practice_exam_scores": [],
                "ers_score": 0,
                "problems": [],
                "concepts": []
            }
            self.subjects.append(subject)
        new_problem = {
            "description": description,
            "confidence": 1,
            "subjects": subjects,
            "skills": skills,
            "review_dates": [(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")],
            "completed_reviews": [{"date": today_str}]
        }
        subject["problems"].append(new_problem)
        self.update_daily_note_problem(description, subjects, skills, subject["daily_note"])
        subject["ers_score"] = self.calculate_ers(subject)
        self.save_subjects()
        self.load_daily_problems()
        QMessageBox.information(self, "提示", f"题目 '{description}' 已添加，请在Obsidian打开今日笔记补充解析。")

    def show_exam_score(self):
        dialog = ExamScoreDialog([s['name'] for s in self.subjects], self)
        if dialog.exec():
            data = dialog.get_data()
            if data['subject'] and data['score']:
                try:
                    score = int(data['score'])
                    if 0 <= score <= 100:
                        self.add_exam_score(data['subject'], score)
                    else:
                        QMessageBox.warning(self, "错误", "分数必须在0-100之间。")
                except ValueError:
                    QMessageBox.warning(self, "错误", "请输入有效的数字分数。")

    def add_exam_score(self, subject_name, score):
        subject = next((s for s in self.subjects if s['name'] == subject_name), None)
        if subject:
            subject["practice_exam_scores"].append(score)
            subject["ers_score"] = self.calculate_ers(subject)
            self.save_subjects()
            self.load_daily_problems()

    def calculate_ers(self, subject):
        problems = subject.get("problems", [])
        total_problems = len(problems)
        if total_problems == 0:
            return 0
        confident_problems = sum(1 for p in problems if p.get('confidence', 0) >= 4)
        percentage_confident = confident_problems / total_problems
        scores = subject.get("practice_exam_scores", [])[-3:]
        avg_score = sum(scores) / len(scores) / 100.0 if scores else 0.0
        return round(avg_score * percentage_confident * 100, 2)

    def adjust_problem_review_interval(self, problem, confidence, subject):
        base_intervals = [1, 2, 4, 7, 15, 30, 60]
        review_index = len(problem.get("completed_reviews", []))
        interval_days = base_intervals[min(review_index, len(base_intervals) - 1)]
        ers = subject.get('ers_score', 0)
        if ers > 0:
            ers_factor = min(1.5, max(0.5, 100 / ers))
            interval_days *= ers_factor
        if confidence >= 4:
            interval_days *= 1.5
        elif confidence <= 2:
            interval_days *= 0.7
        interval_days = max(1, int(round(interval_days)))
        last_date = datetime.now()
        next_date = last_date + timedelta(days=interval_days)
        problem["review_dates"] = [next_date.strftime("%Y-%m-%d")]
        problem["completed_reviews"].append({"date": last_date.strftime("%Y-%m-%d")})

    def view_all_subjects(self):
        dialog = SubjectOverviewDialog(self.subjects, self)
        dialog.exec()

    def open_obsidian_notes(self):
        notes_dir = Path(self.notes_dir) / "daily_notes"
        try:
            subprocess.run(['explorer', str(notes_dir)], shell=True)  # Windows
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开笔记目录: {e}\n请手动打开 {notes_dir}")

    def update_daily_note_problem(self, description, subjects, skills, note_path):
        note_path = Path(note_path) if note_path else self.create_daily_note(datetime.now().strftime("%Y-%m-%d"),
                                                                             "Default")
        try:
            with open(note_path, "a", encoding="utf-8") as f:
                f.write(
                    f"\n### 题目: {description}\n主题: {', '.join(subjects)}\n技巧: {', '.join(skills)}\n图片解析: [待补充图片]\n心得: [待补充技巧或心得]\n")
        except Exception as e:
            print(f"更新笔记中的题目失败: {e}")

    def remove_problem_from_daily_note(self, description, note_path):
        if not note_path or not Path(note_path).exists():
            return
        try:
            with open(note_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            pattern = rf"\n### 题目: {re.escape(description)}\n.*?\n心得:.*?(?=\n###|\Z)"
            new_content = re.sub(pattern, "", content, flags=re.DOTALL)
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            print(f"从笔记中移除题目失败: {e}")

    def create_daily_note(self, date_str, subject_name):
        notes_dir_path = Path(self.notes_dir) / "daily_notes"
        if not notes_dir_path.is_dir():
            return ""
        notes_dir_path.mkdir(parents=True, exist_ok=True)
        daily_note_file_path = notes_dir_path / f"{date_str}.md"
        content = f"# Daily Note - {date_str}\n"
        try:
            if not os.access(notes_dir_path, os.W_OK):
                print(f"笔记目录不可写: {notes_dir_path}")
                return ""
            if not daily_note_file_path.exists():
                with open(daily_note_file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            return daily_note_file_path
        except Exception as e:
            print(f"创建笔记失败: {e}")
            return ""

    def load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.data_file = settings.get("data_file", str(DEFAULT_DATA_FILE))
                self.notes_dir = settings.get("notes_dir", str(DEFAULT_NOTES_DIR))
        except Exception as e:
            print(f"加载设置失败: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskNotebook()
    sys.exit(app.exec())