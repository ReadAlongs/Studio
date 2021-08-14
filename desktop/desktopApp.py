import os, sys

from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QMainWindow
from PyQt5.QtWidgets import QGridLayout, QPushButton, QComboBox, QFileDialog
from PyQt5.QtCore import Qt


# window.setLayout(layout)


class readalongsUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Readlongs App")

        self.generalLayout = QGridLayout()
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.generalLayout)

        self._createDisplay()
        self._createButtons()
        self.data = {}

    def _createDisplay(self):
        helloMsg = QLabel(
            """<h1>Welcome to Readalongs!</h1>
            <p>Please upload the text file, audio file, 
            and mapping file you want readalongs to align.</p>"""
        )

        self.generalLayout.addWidget(helloMsg, 0, 1, 1, 2)
        # helloMsg.move(60, 15)
        self.generalLayout.addWidget(QLabel("Upload Text file"), 1, 1)

        self.textPathDisplay = QLabel("<i>Text file path:</i> None selected.")
        self.generalLayout.addWidget(self.textPathDisplay, 2, 1, 1, 3)

        self.generalLayout.addWidget(QLabel("Upload Audio file"), 3, 1)

        self.audioPathDisplay = QLabel("<i>Audio file path:</i> None selected.")
        self.generalLayout.addWidget(self.audioPathDisplay, 4, 1, 1, 3)

        self.generalLayout.addWidget(QLabel("Upload Mapping "), 5, 1)

    def _createButtons(self):
        uploadTextButton = QPushButton("Browse")
        self.generalLayout.addWidget(uploadTextButton, 1, 4, 1, 1)
        uploadTextButton.clicked.connect(self.getTextFile)

        uploadAudioButton = QPushButton("Browse")
        self.generalLayout.addWidget(uploadAudioButton, 3, 4, 1, 1)
        uploadAudioButton.clicked.connect(self.getAudioFile)

        # grab the language dynamically
        from readalongs.utility import getLangs

        self.mappingOptions = getLangs()
        # self.mappingOptions = ("eng", "fra")
        self.mappingDropDown = QComboBox()
        self.mappingDropDown.addItems(self.mappingOptions)
        self.generalLayout.addWidget(self.mappingDropDown, 6, 1, 1, 2)

        mappingConfirmButton = QPushButton("Confirm")
        self.generalLayout.addWidget(mappingConfirmButton, 5, 4, 1, 1)
        mappingConfirmButton.clicked.connect(self.selectMapping)

        NextButton = QPushButton("Next Step")
        NextButton.setSizePolicy(100, 120)
        self.generalLayout.addWidget(NextButton, 7, 1)
        NextButton.clicked.connect(self.callMajorProcess)

    def selectMapping(self):
        # option = self.mappingOptions.index(self.mappingDropDown.currentText())
        # # TODO: drop down
        # if option == "eng":
        #     pass

        # unnecessary to do option, language is a plain 3-letter text
        print("OK")
        self.data["language"] = self.mappingDropDown.currentText()
        print("LANGS = ", self.data["language"])

    def getTextFile(self):
        response = QFileDialog.getOpenFileName(
            parent=self,
            caption="Select a text file",
            directory=os.getcwd(),
            filter="Text File (*.txt *csv);;Just another type (*.mp3 *.mp4)",
            initialFilter="Text File (*.txt *csv)",
        )
        self.data["textFilePath"] = response[0]
        self.textPathDisplay.setText("<i>Text file path:</i> " + response[0])
        print(response[0])
        return response

    def getAudioFile(self):
        response = QFileDialog.getOpenFileName(
            parent=self,
            caption="Select a audio file",
            directory=os.getcwd(),
            filter="Audio File (*.mp3 *.mp4)",
            initialFilter="Audio File (*.mp3 *.mp4)",
        )
        self.data["audioFilePath"] = response[0]
        self.audioPathDisplay.setText("<i>Audio file path:</i> " + response[0])
        print(response[0])
        return response

    def callMajorProcess(self):
        """
        1. align
        2. prepare
        3. tokenize
        4. g2p
        5. call an interactive web
        """
        import subprocess

        subprocess.run(["python3", "-m", "http.server"])


def main():
    # Create an instance of QApplication
    app = QApplication(sys.argv)

    # Show the calculator's GUI
    view = readalongsUI()
    view.show()

    # Create instances of the model and the controller
    # PyCalcController(view=view)

    # Execute calculator's main loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
