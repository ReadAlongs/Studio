import os, sys

from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QMainWindow, QMessageBox
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
        # TODO: here we only mimic the config from Studio
        #       need to add options later.
        self.config = {
            "language": "",
            "textfile": "",
            "audiofile": "",
            "text_input": True,
            "force_overwrite": True,
            "output_base": os.path.join(os.getcwd(), "desktop", "current"),
            "bare": False,
            "config": None,
            "closed_captioning": False,
            "debug": True,
            "unit": "w",
            "save_temps": False,
            "text_grid": False,
            "output_xhtml": False,
            "g2p_fallback": None,
            "g2p_verbose": False,
        }

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
        self.config["language"] = self.mappingDropDown.currentText()
        print()
        self.popupMessage("LANGS = " + self.config["language"])

    def getTextFile(self):
        response = QFileDialog.getOpenFileName(
            parent=self,
            caption="Select a text file",
            directory=os.getcwd(),
            filter="Text File (*.txt *csv);;Just another type (*.mp3 *.mp4)",
            initialFilter="Text File (*.txt *csv)",
        )
        self.config["textfile"] = response[0]
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
        self.config["audiofile"] = response[0]
        self.audioPathDisplay.setText("<i>Audio file path:</i> " + response[0])
        print(response[0])
        return response

    def popupMessage(self, message):
        popup = QMessageBox()
        popup.setWindowTitle("Message:")
        popup.setText(message)
        popup.setGeometry(100, 200, 100, 100)
        popup.exec_()

    def callMajorProcess(self):
        """
        1. align
        2. prepare
        3. tokenize
        4. g2p
        5. call an interactive web
        """
        # input check
        print("hummm")
        if not all(
            [
                self.config["language"],
                self.config["textfile"],
                self.config["audiofile"],
            ]
        ):
            self.popupMessage(
                "At least one of the following three parameters is \
                    missing: text file path, audio file path, mapping."
            )
            return  # kill and go back

        self.align()
        self.prepare()
        self.tokenize()
        self.g2p()

        # import subprocess

        # subprocess.run(["python3", "-m", "http.server"])

    def align(self):
        from readalongs.align import create_input_tei

        temp_base = None
        tempfile, self.config["textfile"] = create_input_tei(
            input_file_name=self.config["textfile"],
            text_language=self.config["language"],
            save_temps=temp_base,
        )
        from readalongs.align import align_audio
        from readalongs.utility import parse_g2p_fallback

        results = align_audio(
            self.config["textfile"],
            self.config["audiofile"],
            unit=self.config["unit"],
            bare=self.config["bare"],
            config=self.config["config"],
            save_temps=temp_base,
            g2p_fallbacks=parse_g2p_fallback(self.config["g2p_fallback"]),
            verbose_g2p_warnings=self.config["g2p_verbose"],
        )

        # save the files into local address
        from readalongs.text.make_smil import make_smil

        # TODO: replace the "current" in the saving pathes
        tokenized_xml_path = os.path.join(self.config["output_base"], "current.xml")
        audio_path = os.path.join(self.config["output_base"], "current.m4a")
        smil = make_smil(
            os.path.basename(tokenized_xml_path), os.path.basename(audio_path), results
        )
        from readalongs.text.util import save_txt, save_xml, save_minimal_index_html

        smil_path = os.path.join(self.config["output_base"], "current.smil")
        save_xml(tokenized_xml_path, results["tokenized"])

        import shutil

        shutil.copy(self.config["audiofile"], audio_path)

        save_txt(smil_path, smil)
        save_minimal_index_html(
            os.path.join(self.config["output_base"], "index.html"),
            os.path.basename(tokenized_xml_path),
            os.path.basename(smil_path),
            os.path.basename(audio_path),
        )

    def prepare(self):
        pass

    def tokenize(self):
        pass

    def g2p(self):
        pass


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
