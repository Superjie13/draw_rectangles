import sys
import json
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout,
                             QHBoxLayout, QFileDialog, QWidget, QTextEdit, QSlider, QScrollArea)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QPalette
from PyQt5.QtCore import Qt, QPoint, QEvent, QRect


class ImageLabeler(QMainWindow):
    """
    A GUI application for labeling images with rectangles.

    Attributes:
        meta_img (numpy.ndarray): The original image as a numpy array.
        original_img_size (QSize): The size of the original image.
        original_ratio (float): The ratio of the original image.
        original_img (QPixmap): The original image as a QPixmap.
        current_img (QPixmap): The current displayed image as a QPixmap.
        scaled_img (QPixmap): The scaled image as a QPixmap.
        current_scale (float): The current scale factor for zooming.
        last_rect (QRect): The last drawn rectangle.
        start_point (QPoint): The starting point of the current drawing.
        end_point (QPoint): The ending point of the current drawing.
        is_drawing (bool): Indicates whether a rectangle is being drawn.
        rectangles (list): A list of drawn rectangles.
        min_rect_area (int): The minimum area required for a rectangle to be considered valid.
    """

    def __init__(self):
        super().__init__()
        self.meta_img = None
        self.original_img_size = None
        self.original_ratio = None
        self.original_img = None
        self.current_img = None
        self.scaled_img = None
        self.current_scale = 1.0
        self.last_rect = None
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_drawing = False
        self.rectangles = []
        self.min_rect_area = 10
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface of the ImageLabeler application.
        """
        self.setWindowTitle('Image Labeler')
        self.setGeometry(100, 100, 1440, 800)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.imageLabel = QLabel(self)
        # self.imageLabel.setFixedSize(1440, 760)  # Fixed size for simplicity
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.imageLabel)
        self.imageLabel.setMouseTracking(True)  # Enable mouse tracking

        self.scrollArea = QScrollArea()  # Add scroll area
        self.scrollArea.setFixedSize(1440, 760)
        self.scrollArea.setBackgroundRole(QPalette.Dark)  # Set background color
        self.scrollArea.setWidgetResizable(True)  # Make scroll area resizable
        self.scrollArea.setWidget(self.imageLabel)  # Set image label as the widget
        self.scrollArea.setVisible(True)  # Hide scroll area initially (will be shown when an image is loaded)
        self.layout.addWidget(self.scrollArea)

        self.btn_load = QPushButton('Load Image', self)
        self.btn_load.clicked.connect(self.loadImage)
        self.layout.addWidget(self.btn_load)

        # Scale slider for zooming
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setMinimum(10)  # 10% scale
        self.scale_slider.setMaximum(200)  # 200% scale
        self.scale_slider.setValue(100)  # 100% scale (no scaling)
        self.scale_slider.setTickInterval(10)
        self.scale_slider.setTickPosition(QSlider.TicksBelow)
        self.scale_slider.valueChanged.connect(self.scaleImage)
        self.layout.addWidget(self.scale_slider)

        self.scaleValueLabel = QLabel('100%', self)  # 100% by default
        self.layout.addWidget(self.scaleValueLabel)

        self.scaleLayout = QHBoxLayout()  # Horizontal layout for scale slider and value label
        self.scaleLayout.addWidget(self.scale_slider)
        self.scaleLayout.addWidget(self.scaleValueLabel)
        self.layout.addLayout(self.scaleLayout)  # Add scale layout to main layout

        # self.btn_save = QPushButton('Save Rectangles', self)
        # # self.saveButton.move(850, 100)
        # self.btn_save.clicked.connect(self.saveRectangles)
        # self.layout.addWidget(self.btn_save)

        self.msgLayout = QHBoxLayout()
        # message display
        self.messageLayout = QVBoxLayout()

        self.messageLabel = QLabel('message:')
        self.messageLayout.addWidget(self.messageLabel)
        self.messageText = QTextEdit(self)
        self.messageText.setReadOnly(True)
        self.messageLayout.addWidget(self.messageText)

        self.msgLayout.addLayout(self.messageLayout)

        # record display
        self.recordLayout = QVBoxLayout()
        self.recordLabel = QLabel('seleted area (top left bottom right):')
        self.recordLayout.addWidget(self.recordLabel)
        self.recordText = QTextEdit(self)
        self.recordText.setReadOnly(True)
        self.recordLayout.addWidget(self.recordText)

        self.msgLayout.addLayout(self.recordLayout)

        self.ctlLayout = QVBoxLayout()
        # add undo button
        self.undoButton = QPushButton('undo', self)
        self.undoButton.clicked.connect(self.undoLastRectangle)
        self.ctlLayout.addWidget(self.undoButton)
        self.saveButton = QPushButton('save', self)
        self.saveButton.clicked.connect(self.saveRectangles)
        self.ctlLayout.addWidget(self.saveButton)

        self.msgLayout.addLayout(self.ctlLayout)

        self.layout.addLayout(self.msgLayout)

        self.mousePosLabel = QLabel('Mouse Pos:', self)
        self.layout.addWidget(self.mousePosLabel)

        self.main_widget.setLayout(self.layout)
        # self.imageLabel.installEventFilter(self)  # Install event filter

    def loadImage(self):
        filePath, _ = QFileDialog.getOpenFileName(self, 'Open matrix file', '', 'matrix files(*.txt)') 
        if filePath:
            mat = self.load_matrix_from_txt(filePath)
            mat = (mat - mat.min()) / (mat.max() - mat.min())
            if len(mat.shape) == 2:
                mat = np.repeat(mat[:, :, np.newaxis], 3, axis=2)
                mat[:, :, 1:] = 0
            elif len(mat.shape) == 3 and mat.shape[2] == 1:
                mat = np.repeat(mat, 3, axis=2)
                mat[:, :, 1:] = 0
            elif len(mat.shape) == 3 and mat.shape[2] == 3:
                mat = mat
            else:
                self.statusLabel.setText('Status: Invalid image shape')
                return
            
            # convert a numpy array to QImage
            mat = (mat * 255).astype(np.uint8)
            h, w, c = mat.shape
            bytes_per_line = c * w
            qImg = QImage(mat.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.meta_img = mat
            self.original_img = QPixmap.fromImage(qImg)
            self.original_img_size = self.original_img.size()
            self.scaled_img = self.original_img
            # self.imageLabel.setPixmap(self.original_img.scaled(self.imageLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.displayImage()
    
    def undoLastRectangle(self):
        if len(self.rectangles) > 0:
            self.rectangles.pop()
            self.updateRecord(self.rect2Text(self.rectangles))
            self.update()
    
    def saveRectangles(self):
        # find the file path to save the json file
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Save Rectangles", "", "JSON Files (*.json);;Text Files (*.txt)", options=options)

        if fileName.endswith('.json'):
            rects_data = []
            for idx, rect in enumerate(self.rectangles, start=1): 
                top_left = rect[0]  # top left corner of QRect
                bottom_right = rect[1]  # bottom right corner of QRect
                t = min(top_left.y(), bottom_right.y())
                l = min(top_left.x(), bottom_right.x())
                b = max(top_left.y(), bottom_right.y())
                w = max(top_left.x(), bottom_right.x())
                rect_dict = {
                    'id': idx,
                    'tlbw': [t, l, b, w]
                }
                rects_data.append(rect_dict)

            jaon_data = {'rects': rects_data}

            with open(fileName, 'w') as f:
                json.dump(jaon_data, f)
            self.updateMessage(f"Rectangles saved to {fileName}")

        if fileName.endswith('.txt'):
            with open(fileName, 'w') as f:
                for rect in self.rectangles:
                    f.write(f'{rect[0].x()} {rect[0].y()} {rect[1].x()} {rect[1].y()}\n')
            self.updateMessage(f"Rectangles saved to {fileName}")

    def displayImage(self):
        if self.scaled_img:
            self.scaled_img = self.original_img.scaled(self.original_img_size * self.current_scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.imageLabel.setPixmap(self.scaled_img)
            self.imageLabel.adjustSize()  # Adjust size of the label to fit the image
            self.imageLabel.setCursor(Qt.CrossCursor)

    def scaleImage(self):
        self.current_scale = self.scale_slider.value() / 100.0
        # update scale value label
        self.scaleValueLabel.setText(f'{self.scale_slider.value()}%')
        if self.original_img:
            self.displayImage()

    def updateMessage(self, message):
        self.messageText.append(message)

    def updateRecord(self, message):
        self.recordText.setText(message)

    def rect2Text(self, rectangles):
        text = ''
        for i, rect in enumerate(rectangles):
            text += f'Area {i+1}: {rect[0].x()}, {rect[0].y()}, {rect[1].x()}, {rect[1].y()}\n'
        return text
    
    def toTLBR(self, p1, p2):
        x1, y1, x2, y2 = p1.x(), p1.y(), p2.x(), p2.y()
        t, l, b, r = min(y1, y2), min(x1, x2), max(y1, y2), max(x1, x2)
        return (QPoint(l, t), QPoint(r, b))
        

    @staticmethod
    def load_matrix_from_txt(file_path):
        """ Load matrix from .txt file """
        with open(file_path, 'r') as f:
            lines = f.readlines()
            matrix = []
            for line in lines:
                matrix.append(list(map(float, line.split())))
        return np.array(matrix)
    
    def mouseMoveEvent(self, event):
        if self.scaled_img and self.imageLabel.rect().contains(event.pos()):
            # Convert to original image coordinates
            offset_cursor_pos = QPoint(event.pos().x() - 10, event.pos().y() - 10)
            original_pos = self.convertToOriginalImageCoords(offset_cursor_pos)
            original_pos = self.cropPoint(original_pos)
            self.mousePosLabel.setText(f'Mouse Pos: {original_pos.x()}, {original_pos.y()}')
            if self.is_drawing:
                self.end_point = original_pos
                self.update()
        else:
            self.mousePosLabel.setText('Mouse Pos:')

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.scaled_img and self.imageLabel.rect().contains(event.pos()):
            self.is_drawing = True
            offset_cursor_pos = QPoint(event.pos().x() - 10, event.pos().y() - 10)
            self.start_point = self.convertToOriginalImageCoords(offset_cursor_pos)
            self.start_point = self.cropPoint(self.start_point)
            self.end_point = self.start_point  # Initialize end_point
            self.updateMessage(f"Start: x={self.start_point.x()}, y={self.start_point.y()}")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            offset_cursor_pos = QPoint(event.pos().x() - 10, event.pos().y() - 10)
            self.end_point = self.convertToOriginalImageCoords(offset_cursor_pos)
            self.end_point = self.cropPoint(self.end_point)
            # If the area of rectangle larger than threshold, add it to the list
            if abs(self.end_point.x() - self.start_point.x()) * abs(self.end_point.y() - self.start_point.y())\
                  > self.min_rect_area:
                self.rectangles.append(self.toTLBR(self.start_point, self.end_point))
            self.updateMessage(f"End: x={self.end_point.x()}, y={self.end_point.y()}")
            self.updateRecord(self.rect2Text(self.rectangles))
            self.update()

    def paintEvent(self, event):
        if self.scaled_img:
            # create a pixmap to draw on
            pixmap = self.scaled_img.copy()
            
            painter = QPainter(pixmap)
            painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))

            for rect in self.rectangles:
                scaled_start = self.convertToScaledImageCoords(rect[0])
                scaled_end = self.convertToScaledImageCoords(rect[1])
                painter.drawRect(QRect(scaled_start, scaled_end))
            
            # if currently drawing, draw the rectangle
            if self.is_drawing:
                scaled_start = self.convertToScaledImageCoords(self.start_point)
                scaled_end = self.convertToScaledImageCoords(self.end_point)
                painter.drawRect(QRect(scaled_start, scaled_end))

            # draw the pixmap to the imageLabel
            self.imageLabel.setPixmap(pixmap)

            self.imageLabel.update()
            painter.end()

        else:
            super().paintEvent(event)  # if no image is loaded, call the original paintEvent

    def cropPoint(self, pos):
        # crop the point to the image boundary
        x = max(0, min(pos.x(), self.original_img.width()))
        y = max(0, min(pos.y(), self.original_img.height()))
        return QPoint(x, y)

    def convertToOriginalImageCoords(self, pos):
        # calculate the margin of QLabel to the image
        offsetX = (self.imageLabel.width() - self.scaled_img.width()) / 2 if self.scaled_img else 0
        offsetY = (self.imageLabel.height() - self.scaled_img.height()) / 2 if self.scaled_img else 0

        # get the current scroll bar values
        h_scroll = self.scrollArea.horizontalScrollBar().value()
        v_scroll = self.scrollArea.verticalScrollBar().value()

        # correct the mouse position
        corrected_pos = QPoint(pos.x() - offsetX + h_scroll, pos.y() - offsetY + v_scroll)

        # convert the corrected position to the original image coordinates
        if self.original_img:
            scale_w = self.original_img.width() / self.scaled_img.width()
            scale_h = self.original_img.height() / self.scaled_img.height()
            return QPoint(corrected_pos.x() * scale_w, corrected_pos.y() * scale_h)

        return corrected_pos
    
    def convertToScaledImageCoords(self, original_pos):
        # convert the original image coordinates to the scaled image coordinates
        if self.original_img and self.scaled_img:
            scale_w = self.scaled_img.width() / self.original_img.width()
            scale_h = self.scaled_img.height() / self.original_img.height()
            return QPoint(original_pos.x() * scale_w, original_pos.y() * scale_h)
        return original_pos

    

def main():
    app = QApplication(sys.argv)
    labeler = ImageLabeler()
    labeler.show()
    sys.exit(app.exec_())
    

if __name__ == '__main__':
    main()