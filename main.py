import sys
import os
import threading
import csv
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableView, QHeaderView,
    QTabWidget, QProgressBar, QFrame, QMessageBox, QComboBox,
    QAbstractItemView
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QAbstractTableModel, QModelIndex, 
    QSortFilterProxyModel, QSize
)
from PyQt6.QtGui import QColor, QFont, QAction,QIcon

# === Import refactored resource modules ===
from resources.languages import LanguageManager
from resources.styles import DARK_THEME_QSS

try:
    from main_function.detector import MLDetector
except ImportError:
    class MLDetector:
        def __init__(self): self.model = True
        def scan_line(self, line, idx): return []

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ==========================================
# Data Model (ResultModel)
# ==========================================
class ResultModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["col_risk", "col_file", "col_line", "col_content", "col_score", "col_time"]

    def data(self, index, role):
        if not index.isValid():
            return None
        
        row_data = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            key = self._headers[col]
            if col == 0: return row_data['risk']
            if col == 1: return row_data['file']
            if col == 2: return str(row_data['line'])
            if col == 3: return self.mask_secret(row_data['match']) # Apply masking
            if col == 4: return f"{row_data['score']:.2f}%"
            if col == 5: return row_data['timestamp']

        if role == Qt.ItemDataRole.ForegroundRole:
            risk = row_data['risk']
            if risk == 'CRITICAL': return QColor("#ff4444")
            if risk == 'HIGH': return QColor("#ff8800")
            if risk == 'MEDIUM': return QColor("#ffcc00")
            if risk == 'LOW': return QColor("#2ecc71")
            return QColor("white")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 2, 4, 5]:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None

    def rowCount(self, index=QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return LanguageManager.get(self._headers[section])
        return None

    def add_row(self, row_data):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(row_data)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._data = []
        self.endResetModel()

    @staticmethod
    def mask_secret(text):
        """
        Masks sensitive parts of the string.
        Static method so it can be used by the Export function as well.
        """
        if not text: return ""
        if len(text) <= 8:
            return text[:2] + "****"
        return text[:4] + "********" + text[-4:]
    
    def get_all_data(self):
        return self._data

# ==========================================
# Background Scanning Thread
# ==========================================
class ScanThread(QThread):
    progress_update = pyqtSignal(str, float)
    result_found = pyqtSignal(dict)
    scan_finished = pyqtSignal()

    def __init__(self, target_path, detector):
        super().__init__()
        self.target_path = target_path
        self.detector = detector
        self.is_running = True

    def run(self):
        file_list = []
        for root, dirs, files in os.walk(self.target_path):
            if not self.is_running: break
            dirs[:] = [d for d in dirs if d not in ['.git', 'venv', '__pycache__', 'node_modules', '.idea', '.vscode']]
            
            for f in files:
                if f.lower().endswith(('.py', '.js', '.json', '.txt', '.md', '.env', '.yml', '.xml', '.html', '.properties')):
                    file_list.append(os.path.join(root, f))

        total_files = len(file_list)
        if total_files == 0:
            self.scan_finished.emit()
            return

        for i, filepath in enumerate(file_list):
            if not self.is_running: break

            progress = (i + 1) / total_files
            fname = os.path.basename(filepath)
            self.progress_update.emit(fname, progress)

            try:
                if os.path.getsize(filepath) == 0: continue
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_idx, line in enumerate(f, 1):
                        results = self.detector.scan_line(line.strip(), line_idx)
                        for res in results:
                            data = {
                                'risk': res['risk'].upper(),
                                'file': fname,
                                'path': filepath,
                                'line': line_idx,
                                'match': res['word'],
                                'score': round(res['score'], 2),
                                'timestamp': datetime.now().strftime('%H:%M:%S')
                            }
                            self.result_found.emit(data)
            except Exception:
                pass

        self.scan_finished.emit()

    def stop(self):
        self.is_running = False

# ==========================================
# Main Application Window
# ==========================================
class SecretHunterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.detector = MLDetector()
        self.scan_thread = None
        self.scanning = False
        
        self.init_ui()
        self.apply_styles()
        self.retranslate_ui()

    def init_ui(self):
        self.resize(1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 20)
        sidebar_layout.setSpacing(15)

        self.lbl_title = QLabel("CodeSentry")
        self.lbl_title.setObjectName("AppTitle")
        sidebar_layout.addWidget(self.lbl_title)

        self.combo_lang = QComboBox()
        self.combo_lang.addItem("English", "en_US")
        self.combo_lang.addItem("繁體中文", "zh_TW")
        self.combo_lang.setCurrentIndex(1)
        self.combo_lang.currentIndexChanged.connect(self.change_language)
        sidebar_layout.addWidget(self.combo_lang)

        sidebar_layout.addSpacing(20)

        self.btn_select = QPushButton()
        self.btn_select.clicked.connect(self.select_folder)
        sidebar_layout.addWidget(self.btn_select)

        self.lbl_path = QLabel()
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setObjectName("PathLabel")
        sidebar_layout.addWidget(self.lbl_path)

        self.btn_action = QPushButton()
        self.btn_action.setObjectName("ActionButton")
        self.btn_action.clicked.connect(self.toggle_scan)
        sidebar_layout.addWidget(self.btn_action)

        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self.export_report)
        sidebar_layout.addWidget(self.btn_export)

        sidebar_layout.addStretch()

        self.lbl_model_status = QLabel()
        self.lbl_model_status.setStyleSheet(f"color: {'#2ecc71' if getattr(self.detector, 'model', None) else '#e74c3c'}")
        sidebar_layout.addWidget(self.lbl_model_status)

        main_layout.addWidget(sidebar)

        # --- Content Area ---
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(10)

        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("StatusLabel")
        content_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        content_layout.addWidget(self.progress_bar)

        self.tabs = QTabWidget()
        content_layout.addWidget(self.tabs)

        self.source_model = ResultModel()
        self.proxy_models = {}
        self.stat_labels = {}

        tab_configs = [
            ("tab_all", None),
            ("tab_critical", "CRITICAL"),
            ("tab_high", "HIGH"),
            ("tab_medium", "MEDIUM"),
            ("tab_low", "LOW")
        ]

        for key, filter_str in tab_configs:
            tab = QWidget()
            vbox = QVBoxLayout(tab)
            vbox.setContentsMargins(0, 10, 0, 0)

            stat_lbl = QLabel("...")
            stat_lbl.setStyleSheet("color: #aaaaaa; font-weight: bold; margin-bottom: 5px;")
            vbox.addWidget(stat_lbl)
            self.stat_labels[key] = stat_lbl

            table = QTableView()
            table.setAlternatingRowColors(False)
            table.setShowGrid(False)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            table.horizontalHeader().setStretchLastSection(True)
            table.setSortingEnabled(True)

            proxy = QSortFilterProxyModel(self)
            proxy.setSourceModel(self.source_model)
            proxy.setFilterKeyColumn(0)
            if filter_str:
                proxy.setFilterFixedString(filter_str)
            
            table.setModel(proxy)
            table.setColumnWidth(0, 90)
            table.setColumnWidth(1, 200)
            table.setColumnWidth(2, 60)
            table.setColumnWidth(3, 300)
            table.setColumnWidth(4, 90)
            
            self.proxy_models[key] = proxy
            vbox.addWidget(table)
            
            self.tabs.addTab(tab, key)

        main_layout.addWidget(content_area)

    def apply_styles(self):
        self.setStyleSheet(DARK_THEME_QSS)

    def retranslate_ui(self):
        self.setWindowTitle(LanguageManager.get("app_title"))
        self.lbl_title.setText("CodeSentry")
        self.btn_select.setText(LanguageManager.get("select_folder"))
        self.btn_export.setText(LanguageManager.get("export_report"))
        self.lbl_path.setText(self.target_path if hasattr(self, 'target_path') else LanguageManager.get("no_folder"))
        
        if self.scanning:
            self.btn_action.setText(LanguageManager.get("stop_scan"))
        else:
            self.btn_action.setText(LanguageManager.get("start_scan"))

        self.lbl_model_status.setText(
            LanguageManager.get("model_loaded") if getattr(self.detector, 'model', None) else LanguageManager.get("model_failed")
        )

        keys = ["tab_all", "tab_critical", "tab_high", "tab_medium", "tab_low"]
        for i, key in enumerate(keys):
            self.tabs.setTabText(i, LanguageManager.get(key))
            
        self.source_model.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, 5)
        self.update_stats()

    def change_language(self, index):
        data = self.combo_lang.itemData(index)
        LanguageManager.current_lang = data
        self.retranslate_ui()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, LanguageManager.get("select_folder"))
        if folder:
            self.target_path = folder
            self.lbl_path.setText(folder)
            self.lbl_status.setText(LanguageManager.get("ready"))

    def toggle_scan(self):
        if self.scanning:
            # STOP
            if self.scan_thread:
                self.scan_thread.stop()
                self.btn_action.setEnabled(False)
                self.lbl_status.setText(LanguageManager.get("scanning"))
        else:
            # START
            # === FIXED: Check if folder is selected ===
            if not hasattr(self, 'target_path') or not self.target_path:
                QMessageBox.warning(self, LanguageManager.get("app_title"), LanguageManager.get("no_folder"))
                return
            
            self.scanning = True
            self.source_model.clear()
            self.update_stats()
            
            self.btn_action.setText(LanguageManager.get("stop_scan"))
            self.btn_action.setProperty("state", "stop")
            self.btn_action.style().unpolish(self.btn_action)
            self.btn_action.style().polish(self.btn_action)
            
            self.btn_select.setEnabled(False)
            self.combo_lang.setEnabled(False)
            self.btn_export.setEnabled(False)
            
            self.scan_thread = ScanThread(self.target_path, self.detector)
            self.scan_thread.progress_update.connect(self.on_progress)
            self.scan_thread.result_found.connect(self.on_result)
            self.scan_thread.scan_finished.connect(self.on_finished)
            self.scan_thread.start()

    def on_progress(self, filename, val):
        self.lbl_status.setText(f"{LanguageManager.get('scanning')} {filename}")
        self.progress_bar.setValue(int(val * 100))

    def on_result(self, data):
        self.source_model.add_row(data)
        self.update_stats()

    def update_stats(self):
        keys = ["tab_all", "tab_critical", "tab_high", "tab_medium", "tab_low"]
        for key in keys:
            count = self.proxy_models[key].rowCount()
            text_fmt = LanguageManager.get("stat_label")
            self.stat_labels[key].setText(text_fmt.format(count))

    def on_finished(self):
        self.scanning = False
        self.btn_action.setEnabled(True)
        self.btn_select.setEnabled(True)
        self.combo_lang.setEnabled(True)
        self.btn_export.setEnabled(True)

        status_text = LanguageManager.get("scan_stopped") if self.scan_thread and not self.scan_thread.is_running else LanguageManager.get("scan_complete")
        self.lbl_status.setText(status_text)
        
        self.btn_action.setText(LanguageManager.get("start_scan"))
        self.btn_action.setProperty("state", "start")
        self.btn_action.style().unpolish(self.btn_action)
        self.btn_action.style().polish(self.btn_action)
        
        if self.scan_thread and self.scan_thread.is_running:
             self.progress_bar.setValue(100)

    # ==========================
    # Export Feature
    # ==========================
    def export_report(self):
        data = self.source_model.get_all_data()
        if not data:
            QMessageBox.information(self, LanguageManager.get("export_report"), LanguageManager.get("no_data"))
            return

        file_path, filter_type = QFileDialog.getSaveFileName(
            self,
            LanguageManager.get("export_report"),
            f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            # === FIXED: Apply masking to exported data ===
            # Create a copy or process on the fly to avoid modifying source data if not intended,
            # though masking is usually irreversible for safety.
            
            if file_path.endswith('.json'):
                # For JSON, we construct a new list with masked values
                masked_data = []
                for row in data:
                    masked_row = row.copy()
                    masked_row['match'] = ResultModel.mask_secret(row['match'])
                    masked_data.append(masked_row)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(masked_data, f, ensure_ascii=False, indent=4)
            else:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    headers = ["Risk", "File", "Path", "Line", "Confidence", "Time", "Match Content (Masked)"]
                    writer.writerow(headers)
                    for row in data:
                        writer.writerow([
                            row['risk'],
                            row['file'],
                            row.get('path', ''),
                            row['line'],
                            f"{row['score']:.2f}%",
                            row['timestamp'],
                            ResultModel.mask_secret(row['match']) # Apply Mask
                        ])

            QMessageBox.information(
                self, 
                LanguageManager.get("export_success"), 
                LanguageManager.get("export_success_msg").format(file_path)
            )

        except Exception as e:
            QMessageBox.critical(
                self, 
                LanguageManager.get("export_error"), 
                str(e)
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("resources/img/icon.ico")))
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    try:
        from ctypes import windll
        myappid = 'mycompany.codesentry.version.1.0' # 隨便取一個唯一的字串
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass
    window = SecretHunterWindow()
    window.show()
    sys.exit(app.exec())