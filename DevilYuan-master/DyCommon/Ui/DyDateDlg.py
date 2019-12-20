from datetime import datetime

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton

#股票数据，历史日线，强制更新UI
class DyDateDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('日期')
 
        # 控件，具体日期是每个类得实例所以放到self
        startDateLable = QLabel('开始日期')
        self._startDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        endDateLable = QLabel('结束日期')
        self._endDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(startDateLable, 0, 0)
        grid.addWidget(self._startDateLineEdit, 1, 0)

        grid.addWidget(endDateLable, 0, 1)
        grid.addWidget(self._endDateLineEdit, 1, 1)

        grid.addWidget(okPushButton, 2, 1)
        grid.addWidget(cancelPushButton, 2, 0)
 
 
        self.setLayout(grid)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()

        self.accept()

    def _cancel(self):
        self.reject()
