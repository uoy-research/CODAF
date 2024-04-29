# -*- coding: utf-8 -*-
"""
Created in 2024

@author: University of York, center for assuring autonomy

Written and tested in Python 3.11.7, Windows 11.

The following libraries are required:
sys, os, PyQt5, pandas, matplotlib, schemdraw, io

This GUI is developed as part of the project at the university of York. The authors have no intention of maintaining the code. Use at your own risk.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QTextEdit, QSizePolicy, QTableWidget, QTableWidgetItem, QMainWindow
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from schemdraw import Drawing
from schemdraw import flow
from PyQt5.QtWidgets import QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap
from io import BytesIO
from matplotlib.offsetbox import AnchoredOffsetbox, VPacker, TextArea, DrawingArea
from matplotlib.patches import Rectangle
import matplotlib.font_manager as fm

class MyApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CODAF Case Study")
        self.initUI()

    def initUI(self):
        # Create a Horizontal layout for the main window
        main_layout = QHBoxLayout(self)

        # Create a vertical layout for the top row (canvas, text, values, and buttons)
        first_column_layout = QVBoxLayout()
        first_column_layout.setSizeConstraint(100)
        
        text_area_layout = QVBoxLayout()
        text_area_layout.setAlignment(Qt.AlignCenter)

        simulation_time_layout = QHBoxLayout()
        
        # Simulation Time Label
        self.simulation_time_label = QLabel("Simulation Time:")
        self.simulation_time_label.setAlignment(Qt.AlignLeft)
        self.simulation_time_label.setFixedHeight(20)
        simulation_time_layout.addWidget(self.simulation_time_label)
        simulation_time_layout.setSpacing(5)
        

        # Simulation Time Text Area
        self.simulation_time_text_area = QTextEdit()
        self.simulation_time_text_area.setFixedHeight(50)
        self.simulation_time_text_area.setFixedWidth(100)
        simulation_time_layout.addWidget(self.simulation_time_text_area)

        text_area_layout.addLayout(simulation_time_layout)
        
        soc_layout = QHBoxLayout()
        
        # Estimated SoC
        self.soc_label = QLabel("Estimated SoC:")
        self.soc_label.setAlignment(Qt.AlignLeft)
        self.soc_label.setFixedHeight(20)
        soc_layout.addWidget(self.soc_label)

        self.soc_text_area = QTextEdit()
        self.soc_text_area.setFixedHeight(50)
        self.soc_text_area.setFixedWidth(100)
        soc_layout.addWidget(self.soc_text_area)
        
        text_area_layout.addLayout(soc_layout)
        
        uncertainty_layout = QHBoxLayout()

        # Normalized Uncertainty
        self.uncertainty_label = QLabel("Normalized Uncertainty:")
        self.uncertainty_label.setAlignment(Qt.AlignLeft)
        self.uncertainty_label.setFixedHeight(20)
        uncertainty_layout.addWidget(self.uncertainty_label)

        self.uncertainty_text_area = QTextEdit()
        self.uncertainty_text_area.setFixedHeight(50)
        self.uncertainty_text_area.setFixedWidth(100)
        uncertainty_layout.addWidget(self.uncertainty_text_area)
        
        text_area_layout.addLayout(uncertainty_layout)
        
        first_column_layout.addLayout(text_area_layout)

        # Create a Horizontal layout for buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Buttons
        self.start_button = QPushButton("Start")
        #self.start_button.setEnabled(False)
        self.start_button.setFixedWidth(80)
        self.start_button.clicked.connect(self.startProcessing)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.setFixedWidth(80)
        self.stop_button.clicked.connect(self.stopProcessing)
        buttons_layout.addWidget(self.stop_button)
        
        # Assurance button
        self.assurance_button = QPushButton("Assurance")
        self.assurance_button.setFixedWidth(80)
        self.assurance_button.clicked.connect(self.show_assurance_window)
        buttons_layout.addWidget(self.assurance_button)
        
        # Add buttons_layout to first_column_layout
        first_column_layout.addLayout(buttons_layout)
        
        label_layout = QHBoxLayout()
        
        # Info Label
        self.info_label = QLabel()
        label_layout.addWidget(self.info_label)
        
        first_column_layout.addLayout(label_layout)
        
        # Add first_column_layout to main_layout
        main_layout.addLayout(first_column_layout)
    
        # Add some space between the columns
        main_layout.addSpacing(20)

        # Add first_column_layout to main_layout
        main_layout.addLayout(first_column_layout)
    
        # Add some space between the columns
        main_layout.addSpacing(20)

        # Create a Vertical layout for the second column (canvas plot)
        second_column_layout = QVBoxLayout()
        
        # Create a plot canvas
        self.plot_canvas = self.create_plot_canvas()
        second_column_layout.addWidget(self.plot_canvas)
        
        # Add second_column_layout to main_layout
        main_layout.addLayout(second_column_layout)
        
        # Add some space between the columns
        main_layout.addSpacing(20)
        
        # Create a Vertical layout for the third column (table)
        third_column_layout = QVBoxLayout()
        
        # Create a table widget
        self.table_widget = QTableWidget()
        self.table_widget.setFixedWidth(610)
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["Config", "Predicted Slack Time(ms)", "Predicted Energy Consumption(J)", "Confidence Level"])
        third_column_layout.addWidget(self.table_widget)
        
        # Set column widths
        column_widths = [50, 180, 225, 130]  # Set the desired width for each column
        for i, width in enumerate(column_widths):
            self.table_widget.setColumnWidth(i, width)
            
        # Insert the first row into the table
        self.table_widget.setRowCount(1)
        self.table_widget.setItem(0, 0, QTableWidgetItem("Z"))
        
        # Add third_column_layout to main_layout
        main_layout.addLayout(third_column_layout)
        
        self.assurance_window = AssuranceWindow(self)

        # Initialize variables
        self.file_name = None
        self.processing = False
        self.timer = QTimer(self)
        self.current_index = 0
        self.df = None

    def create_plot_canvas(self, width=7, height=7, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        axes = fig.add_subplot(111)
        axes.set_xlabel('Longitude')
        axes.set_ylabel('Latitude')
        
        # Hide ticks and tick labels
        axes.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False)
        axes.set_xticklabels([])
        axes.set_yticklabels([])
        
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        canvas.setFixedSize(width * dpi, height * dpi)

        # Set background color with transparency
        axes.set_facecolor((0, 0.4, 0, 0.4))  # (R, G, B, alpha)

        # Initialize scale bar
        canvas.scale_bar = None

        return canvas

    def update_plot(self, canvas, x_position, y_position):
        axes = canvas.figure.axes[0]
        axes.plot(x_position, y_position, 'ko', markersize=5)  # Plot new data

        # Set axis labels
        axes.set_xlabel('Longitude')
        axes.set_ylabel('Latitude')

        # Hide ticks and tick labels
        axes.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False)
        axes.set_xticklabels([])
        axes.set_yticklabels([])

        # Remove previous scale bar if exists
        if canvas.scale_bar:
            canvas.scale_bar.remove()

        # Get x-axis limits
        x_min, x_max = axes.get_xlim()

        # Calculate extent of data
        x_extent = x_max - x_min

        # Add scale bar if it fits in the plot
        if x_extent > 1:  # Adjust threshold as needed
            scale_length_km = x_extent / 5  # Set scale bar length to 1/5th of x-axis limit

            # Format scale length to display only two decimal places
            scale_length_km_formatted = "{:.2f}".format(scale_length_km)

            # Create scale bar
            fontprops = fm.FontProperties(size=10)
            scale_text = f"{scale_length_km_formatted} km"
            scale_text_area = TextArea(scale_text, textprops=dict(color='black', fontproperties=fontprops))
            scale_line = Rectangle((0, 0), scale_length_km, 0.1, color='black')
            scale_drawing_area = DrawingArea(100, 10, 0, 0)
            scale_drawing_area.add_artist(scale_line)

            # Pack text and line into an anchored offset box
            scale_box = AnchoredOffsetbox(loc='lower left', child=VPacker(children=[scale_text_area, scale_drawing_area]), pad=0.1)
            canvas.scale_bar = axes.add_artist(scale_box)

        canvas.draw()
        
    def show_assurance_window(self):
        if self.df is not None and self.current_index < len(self.df):
            self.assurance_window.update_values()
            self.assurance_window.show()

    def startProcessing(self):
        if not self.processing:
            self.info_label.setText("Processing started...")

            try:
                # Read the Excel file directly
                file_path = os.path.join(os.path.dirname(__file__), "BatteryMonitorSample100.xlsx")
                self.df = pd.read_excel(file_path)

                # Start the timer to update the text areas
                if self.current_index < len(self.df):
                    self.timer.timeout.connect(self.updateTextAreas)
                    self.timer.start(1000)  # Adjust the interval (in milliseconds) as needed

            except FileNotFoundError:
                self.info_label.setText("Error: File BatteryData.xlsx not found.")
            except Exception as e:
                self.info_label.setText(f"Error: {e}")
                print(e)

            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.processing = True
        else:  # If processing was previously paused, resume from the current index
            self.info_label.setText("Processing resumed...")
            self.timer.start(1000)  # Restart the timer
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

    def updateTextAreas(self):
        if self.current_index < len(self.df):
            estimated_soc_value = self.df["Estimated SoC"][self.current_index]
            self.uncertainty_value = self.df["Normalized Uncertainty"][self.current_index]
            self.simulation_time_value = self.df["Time"][self.current_index]
            x_position = self.df["X"][self.current_index]
            y_position = self.df["Y"][self.current_index]

            # Display only 3 digits for Estimated SoC and Uncertainty
            formatted_soc_value = f"{estimated_soc_value:.3f}"
            formatted_uncertainty_value = f"{self.uncertainty_value:.3f}"

            self.soc_text_area.clear()
            self.soc_text_area.setFontPointSize(14)  # Set font size to 14
            self.soc_text_area.append(formatted_soc_value)

            self.uncertainty_text_area.clear()
            self.uncertainty_text_area.setFontPointSize(14)  # Set font size to 14
            self.uncertainty_text_area.append(str(formatted_uncertainty_value))

            self.simulation_time_text_area.clear()
            self.simulation_time_text_area.setFontPointSize(14)  # Set font size to 14
            self.simulation_time_text_area.append(str(self.simulation_time_value))
            
            self.assurance_window.generate_flowchart()

            # Update the plot canvas with current X and Y positions
            self.update_plot(self.plot_canvas, x_position, y_position)
            
            # Update table
            config = self.df.iloc[self.current_index]["Config"]
            slack = self.df.iloc[self.current_index]["Slack"]
            energy = self.df.iloc[self.current_index]["PredictedEnergyConsumption"]
            level = self.df.iloc[self.current_index]["AssuranceLevel"]

            # Check if the config already exists in the table
            config_exists = False

            # Reset font style for all rows
            for row in range(self.table_widget.rowCount()):
                font = QFont()
                font.setBold(False)
                font.setPointSize(8)
                self.table_widget.item(row, 0).setFont(font)

            # Update font style for the current configuration
            for row in range(self.table_widget.rowCount()):
                if self.table_widget.item(row, 0).text() == config:
                    config_exists = True
                    # Make the font bold and set font size to 14
                    font = QFont()
                    font.setBold(True)
                    font.setPointSize(14)
                    self.table_widget.item(row, 0).setFont(font)

                    # Update the "Predicted Slack Time", "Predicted Energy Consumption", and "Assurance Level" columns for the current configuration
                    self.table_widget.setItem(row, 1, QTableWidgetItem(f"{slack:.4f}"))
                    self.table_widget.setItem(row, 2, QTableWidgetItem(f"{energy:.4f}"))
                    self.table_widget.setItem(row, 3, QTableWidgetItem(f"{level:.4f}"))
                else:
                    # Clear the values for other configurations
                    self.table_widget.setItem(row, 1, QTableWidgetItem(""))
                    self.table_widget.setItem(row, 2, QTableWidgetItem(""))
                    self.table_widget.setItem(row, 3, QTableWidgetItem(""))

            # If the config doesn't exist, add a new row
            if not config_exists:
                row_position = self.table_widget.rowCount()
                self.table_widget.insertRow(row_position)
                self.table_widget.setItem(row_position, 0, QTableWidgetItem(config))
                self.table_widget.setItem(row_position, 1, QTableWidgetItem(f"{slack:.4f}"))
                self.table_widget.setItem(row_position, 2, QTableWidgetItem(f"{energy:.4f}"))
                self.table_widget.setItem(row_position, 3, QTableWidgetItem(f"{level:.4f}"))

                sky_blue = QColor(135, 206, 235)
                for column in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row_position, column)
                    if item is not None:
                        # Set the background color
                        item.setBackground(sky_blue)

            self.current_index += 1
        else:
            # Stop the timer when all values are displayed
            self.timer.stop()
            self.info_label.setText("Processing completed.")

    def stopProcessing(self):
        # Pause processing if the first stop button is clicked
        if self.stop_button.text() == "Stop":
            self.timer.stop()
            self.info_label.setText("Processing paused.")
            self.start_button.setEnabled(True)
            #self.stop_button.setText("Clear")
            # Continue processing if the second stop button is clicked
        else:
            if self.processing:
                self.info_label.setText("Processing resumed...")
                self.timer.start(1000)  # Restart the timer
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.stop_button.setText("Stop")  # Reset the button text
            else:
                self.info_label.setText("Processing stopped.")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.stop_button.setText("Stop")  # Reset the button text

class AssuranceWindow(QMainWindow):
    def __init__(self, my_app):
        super().__init__()

        self.setWindowTitle("Assurance Window")
        #self.setFixedSize(1500, 1400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()
        flowchart_layout = QHBoxLayout()

        # Create a QGraphicsScene for the flowchart
        self.flowchart_scene = QGraphicsScene()
        self.flowchart_view = QGraphicsView(self.flowchart_scene)
        #self.flowchart_view.setFixedSize(1500, 1000)
        layout.addWidget(self.flowchart_view)
        layout.addLayout(flowchart_layout)
        
        self.central_widget.setLayout(layout)

        self.my_app = my_app  # Store the current index

        # Connect the timer to update the simulation time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_values)

    def update_values(self):
        self.generate_flowchart()
    
    def generate_flowchart(self):
        # Clear the scene before generating a new flowchart
        self.flowchart_scene.clear()

        # Create a simple flowchart using schemdraw
        with Drawing() as d:
            d.config()
            flow.Terminal().label('ConTop1\nCurrent mission\nvalues').drop('E')
            flow.Arrow(arrow='<-')
            Ctop = flow.Process().label('Ctop\nSoC accurately indicates\nmission success for\ncurrent mission goals')
            flow.Arrow().right(d.unit/2).at(Ctop.E)
            flow.Terminal().anchor('W').label('ConTop2\nCurrent mission\ngoals')
             
            flow.Arrow().down(d.unit/3).at(Ctop.S)
            strategy = flow.Data().anchor('N').label('Argue that individual\nestimates are valid,\nthen examine\ncomparison')
            C1 = flow.Process().anchor('N').label('C1\nSOC charge estimate\nis within tolerable\nbounds').at((2,-7))
            flow.ArcN(arrow='<-').at(C1.N).to(strategy.S)
            flow.Arrow().down(d.unit/2).at(C1.S)
             # Define color based on confidence level
            if 0<=self.my_app.uncertainty_value<10:
                gcolor = self.calculate_color(100-self.my_app.uncertainty_value)
                Sn1 = flow.State(r=1.6, fill=gcolor).anchor('N').label('Sn1\nCharge estimate')
                Sn1 = flow.State(r=1.6).anchor('N').label('Sn1\nCharge estimate')
            elif 10 <= self.my_app.uncertainty_value <= 65:
                gcolor = self.calculate_color(self.my_app.uncertainty_value)
                 #Sn1.fill = QColor(color_hex)
                Sn1 = flow.State(r=1.6, fill=gcolor).anchor('N').label('Sn1\nCharge estimate')
            else:
                Sn1 = flow.State(r=1.6, fill='white').anchor('N').label('Sn1\nCharge estimate')
                flow.Line().theta(35).drop('NW').at((0.6,-13.2)).color('red').length(3.2)
                flow.Line().theta(-35).drop('NW').at((0.7,-11.5)).color('red').length(3.2)

            C2 = flow.Process().anchor('N').label('C2\nSOC charge\nestimate indicates\nmission success for\ncurrent goals').at((8,-7))
            flow.ArcN(arrow='<-').at(C2.N).to(strategy.S)
            flow.Arrow().down(d.unit/2).at(C2.S)
            if 0 <=self.my_app.uncertainty_value<=65:
                Sn2Color = self.calculate_color(100-(100-0.6*self.my_app.uncertainty_value))
                Sn2 = flow.State(r=2, fill=Sn2Color).anchor('N').label('Sn2\nCharge\nestimate\ncomparison with\nrequired power\nconsumption')
            else:
                Sn2 = flow.State(r=2, fill='white').anchor('N').label('Sn2\nCharge\nestimate\ncomparison with\nrequired power\nconsumption')
                flow.Line().theta(45).drop('NW').at((6.5,-14.4)).color('red').length(3.94)
                flow.Line().theta(-42).drop('NW').at((6.45,-12)).color('red').length(3.95)
            C3 = flow.Process().anchor('N').label('C3\nRequired power\nconsumption estimate for\nmission is within\ntolerable bounds').at((14,-7))
            flow.ArcN(arrow='<-').at(C3.N).to(strategy.S)
            flow.Arrow().down(d.unit/2).at(C3.S)    
            Sn3Color= self.calculate_color(0.8*self.my_app.uncertainty_value)
            Sn3 = flow.State(r=1.8, fill=Sn3Color).anchor('N').label('Sn3\nRequired power\nconsumption\nestimate')
            weightedColor = self.calculate_color(100-0.8*self.my_app.uncertainty_value)  
            CC4 = flow.Process(fill=weightedColor).anchor('W').label('CC4\nMonitor indicates\nrisk of inaccurate\nestimate beyond\ntolerable bounds').at((18, -13)).drop('W')
            flow.Arrow().left(2.25)
            CR2 = flow.Process().anchor('N').label('CR2\nHistorical data\nindicate no\nintolerable estimate').at((20, -16))
            if self.my_app.uncertainty_value>65:
            #CR2 cross
                flow.Line().theta(27).drop('NW').at((17.8,-18.2)).color('red').length(4.9)
                flow.Line().theta(-27).drop('NW').at((17.8,-16)).color('red').length(4.9)

            flow.Arrow().at(CR2.N).up(1.7)
            color = self.calculate_color(100-self.my_app.uncertainty_value)
            CC2 = flow.Process(fill=color).anchor('E').label('CC2\nConfidence monitor\nindicates overestimation\nof remaining capacity').at((-2.5, -10))
            flow.ArcZ(arrow='->').at(CC2.E).to(Sn1.W)       
            CC3 = flow.Process().label('CC3\nConfidence monitor\nindicates underestimation\nof remaining capacity').at((-5,-17.25)).color('red')
            flow.Line().theta(21).drop('NW').at((-7.8,-17.2)).color('red').length(6)
            flow.Line().theta(-21.8).drop('NW').at((-7.76,-15)).color('red').length(5.9)
            flow.ArcZ(arrow='<-').at(Sn1.W).to(CC3.E).color('red')
            CR1 = flow.Process().anchor('E').label('CR1\nHistorical data\nindicate no\nover/underestimate').at((-10, -13))
            flow.ArcZ(arrow='<-').at(CC2.W).to(CR1.E).color('red')
            flow.ArcZ(arrow='<-').at(CC3.W).to(CR1.E).color('red')
            if self.my_app.uncertainty_value > 65:
                CR1.color('red')
                flow.ArcZ(arrow='<-').at(CC2.W).to(CR1.E).color('red')
                flow.ArcZ(arrow='<-').at(CC3.W).to(CR1.E).color('red')
                flow.Line().theta(27).drop('NW').at((-14.35,-14.1)).color('red').length(4.9)
                flow.Line().theta(-27).drop('NW').at((-14.35,-11.9)).color('red').length(4.9)
                
            else:
                flow.ArcZ(arrow='<-').at(CC2.W).to(CR1.E)
                flow.ArcZ(arrow='<-').at(CC3.W).to(CR1.E)
           
            if self.my_app.simulation_time_value < 600:
                CC1 = flow.Process().label('CC1\nSoC temporarily\naffected by transient\ntime of filter').at((-8,-4.5))
                flow.ArcZ(arrow='<-').at(Sn1.NW).to(CC1.E)       

        # Convert the flowchart to an image
        img = BytesIO()
        d.save(img)
        img.seek(0)

        # Convert the image to a QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(img.getvalue())
        
        pixmap = pixmap.scaled(1500, 1400, Qt.KeepAspectRatio)

        # Add the image to the QGraphicsScene
        pixmap_item = QGraphicsPixmapItem(pixmap)
        self.flowchart_scene.addItem(pixmap_item)
        
    def calculate_color(self, parameter):
        # Calculate the RGB components based on the parameter value
        if parameter <= 50:
            red = min(255, max(0, parameter * 5.1))
            green = 255
        else:
            red = 255
            green = max(0, 255 - (parameter - 50) * 5.1)
        blue = 0
        
        # Create a QColor object with the calculated RGB components
        color = QColor(int(red), int(green), int(blue))
        # Convert the QColor object to a hex string
        color_hex = color.name()
        return color_hex

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())