# Import necessary libraries
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget

class MapColouringGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Map Colouring GUI')
        self.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout()
        label = QLabel('Welcome to the Map Colouring GUI')
        button = QPushButton('Exit')
        button.clicked.connect(self.close)
        layout.addWidget(label)
        layout.addWidget(button)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MapColouringGUI()
    ex.show()
    sys.exit(app.exec_())