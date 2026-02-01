import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtGui import QMovie, QFont
from PyQt6.QtCore import Qt, QTimer
import os

class SparkDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('S.P.A.R.K. Futuristic Core')
        self.setGeometry(100, 100, 600, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Animated GIF core
        self.gif_path = os.path.join(os.path.dirname(__file__), '../assets/spark_core.gif')
        self.gif_label = QLabel(self)
        self.gif_label.setGeometry(50, 50, 500, 500)
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie = QMovie(self.gif_path)
        self.gif_label.setMovie(self.movie)
        self.movie.start()
        # Status label
        self.status = 'Idle'
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont('Arial', 22, QFont.Weight.Bold))
        self.label.setGeometry(0, 500, 600, 60)
        self.update_status('Idle')
        # For demo: cycle through statuses
        self.demo_statuses = ['Listening', 'Thinking', 'Speaking', 'Idle']
        self.demo_index = 0
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.cycle_status)
        self.status_timer.start(2000)

    def update_status(self, status):
        self.status = status
        self.label.setText(f'S.P.A.R.K. is {status}')
        self.update()

    def cycle_status(self):
        self.demo_index = (self.demo_index + 1) % len(self.demo_statuses)
        self.update_status(self.demo_statuses[self.demo_index])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dash = SparkDashboard()
    dash.show()
    sys.exit(app.exec())
