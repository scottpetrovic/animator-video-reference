import os.path # for accessing files and directories
from os import listdir
from os.path import isfile, join

import subprocess # for calling terminal tools like FFMPEG and FFProbea
import shlex
import json

from PyQt5.QtCore import Qt
from krita import (Extension, krita)
from PyQt5.QtWidgets import (QDialogButtonBox, QDialog, QMessageBox, QComboBox, 
                             QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, 
                             QToolButton, QAction, QPushButton, QSpinBox)


EXTENSION_ID = 'pykrita_animationimporter'
MENU_ENTRY = 'Animation Importer'


class Animationimporter(Extension):

	# make sure these are defined at the top
	def signal_change_location(self):
		
		self.fileName = QFileDialog.getOpenFileName(self.dialog, "Select your Video File", "", "Videos(*.mp4 *.avi *.mpg);; All files (*.*)" )
		self.fileLocationLabel.setText(self.fileName[0]) # text is returned as two parts, file path, and type of extension that was returned

		# run FFProbe to get vidoe info    
		self.findVideoMetada(self.fileName[0])    
		
		# print(ffprobeOutput['streams'][0]['height'])
		self.textInfo = "Height:" + str(self.ffprobeOutput['streams'][0]['height']) + "px  Width:" + str(self.ffprobeOutput['streams'][0]['width']) + "px"
		self.textInfo += "Duration: "  +  self.ffprobeOutput['streams'][0]['duration']  + " s"
		
		self.fileLoadedDetails.setText(self.textInfo)

	def start_video_processing(self):
		self.startButton.setEnabled(0)
		self.startButton.setText("Processing...please wait")
		
		
		# global image_sequence_directory    
		self.image_sequence_directory = os.path.dirname(self.fileName[0]) 
		self.image_sequence_directory += "/images/"
		
		# print("directory to make: " + image_sequence_directory)
		   
		if not os.path.exists(self.image_sequence_directory):
			os.makedirs(self.image_sequence_directory)    
		
		# make the OS move to image directory to do the exporting
		os.chdir(self.image_sequence_directory)
		
		self.video_file = "../" + os.path.basename(self.fileName[0])  # we are in the images folder, so go up one to reference the video
		# print("video file to process: " + video_file)
		
		# calls FFMPEG and outputs it at 24 frames per second. everything goes in the images folder
		subprocess.call(['ffmpeg', '-ss', str(self.startExportingAtSpinbox.value()) , '-i', self.video_file, '-t',  str(self.exportDurationSpinbox.value()), "-r", str(self.fpsSpinbox.value()), 'output_%04d.png'])
				
		
		# call FFProbe to get the image dimensions of the the file
		self.imageDimensions = self.findVideoMetada(self.fileName[0])
		
		# create Krita document at given dimensions
		# Application.createDocument(1000, 1000, "Test", "RGBA", "U8", "", 120.0)
		self.newDocument = app.createDocument(self.imageDimensions[1], self.imageDimensions[0], "Test", "RGBA", "U8", "", 120.0)
		app.activeWindow().addView(self.newDocument) # shows the document in Krita
		
		# get list of files in directory
		self.imageFiles = [f for f in listdir(self.image_sequence_directory) if isfile(join(self.image_sequence_directory, f))]
		self.imageFiles.sort() # make alphabetical
				
		# get full path + filename of files to load
		self.fullPaths = []
		for self.image in self.imageFiles:
			self.fullPaths.append(self.image_sequence_directory + self.image)

		self.firstFrame = 0    
		# void importAnimation(const QList<QString> &files, int firstFrame, int stepSize);
		self.newDocument.importAnimation(self.fullPaths, self.firstFrame, self.frameSkipSpinbox.value())
		
		    
		# cleanup - delete the images and remove the directory
		for image in self.fullPaths:
			os.remove(image) 
		
		os.rmdir(self.image_sequence_directory)
		
		self.startButton.setEnabled(1)
		self.startButton.setText("Start")


	# function to find the resolution of the input video file
	def findVideoMetada(self, pathToInputVideo):
		self.cmd = "ffprobe -v quiet -print_format json -show_streams"
		self.args = shlex.split(self.cmd)
		self.args.append(pathToInputVideo)
		
		# run the ffprobe process, decode stdout into utf-8 & convert to JSON
		self.ffprobeOutput = subprocess.check_output(self.args).decode('utf-8')
		self.ffprobeOutput = json.loads(self.ffprobeOutput)

		# prints all the metadata available:
		import pprint
		self.pp = pprint.PrettyPrinter(indent=2)
		self.pp.pprint(self.ffprobeOutput)

		# for example, find height and width
		self.height = self.ffprobeOutput['streams'][0]['height']
		self.width = self.ffprobeOutput['streams'][0]['width']
		
		print(self.height, self.width)
		return self.height, self.width


	def __init__(self, parent):
		# Always initialise the superclass, This is necessary to create the underlying C++ object 
		super().__init__(parent)

	def setup(self):
		pass

	def createActions(self, window):
		# you shouldn't have to touch this code. It should be ok where it is at
		action = window.createAction(EXTENSION_ID, MENU_ENTRY, "tools/scripts")
		action.triggered.connect(self.action_triggered)        

	def action_triggered(self):

		# UI variables
		self.dialog = QDialog(app.activeWindow().qwindow())
		self.vbox = QVBoxLayout(self.dialog)
		self.hboxOptionsLayout = QHBoxLayout(self.dialog)
		self.filePickerButton = QToolButton()  # Until we have a proper icon
		self.startButton = QPushButton("Start")
		self.fileLocationLabel = QLabel("Choose a video file")
		self.fileLoadedDetails = QLabel("Image details...") # video details go here to show to people

		self.fileName = ""

		self.fpsLabel = QLabel("Frames per second")
		self.fpsSpinbox = QSpinBox()
		self.fpsSpinbox.setValue(24)

		self.frameSkipLabel = QLabel("Frame Skip Interval")
		self.frameSkipSpinbox = QSpinBox()
		self.frameSkipSpinbox.setValue(1)

		self.startExportingAtXSecondsLabel = QLabel("Start Exporting at X seconds")
		self.startExportingAtSpinbox = QSpinBox()
		self.startExportingAtSpinbox.setValue(0)


		self.exportDurationLabel = QLabel("Export duration (in seconds)")
		self.exportDurationSpinbox = QSpinBox()
		self.exportDurationSpinbox.setValue(4)



		# image_sequence_directory = ""
		self.instructionsLabel = QLabel("For now, we will just take the for 3 seconds of the video. We can make this configurable later")
		self.ffprobeOutput = ""


		# add label with location and button to call file picker
		self.vbox.addWidget(self.fileLocationLabel)

		self.filePickerButton.setIcon(app.icon("folder"))

		self.filePickerButton.clicked.connect(self.signal_change_location) # click event
		self.vbox.addWidget(self.filePickerButton)
		self.vbox.addWidget(self.fileLoadedDetails)
		
		self.vbox.addLayout(self.hboxOptionsLayout)
		

		# add frames per second UI
		self.hboxOptionsLayout.addWidget(self.fpsLabel)    
		self.fpsSpinbox.setValue(24.0)
		self.hboxOptionsLayout.addWidget(self.fpsSpinbox)
		
		# add frames skip interval
		self.frameSkipSpinbox.setValue(2)
		self.hboxOptionsLayout.addWidget(self.frameSkipLabel)
		self.hboxOptionsLayout.addWidget(self.frameSkipSpinbox)
		
		
		# export starting at thing
		self.vbox.addWidget(self.startExportingAtXSecondsLabel)
		self.vbox.addWidget(self.startExportingAtSpinbox)    

		# export duration
		self.vbox.addWidget(self.exportDurationLabel)
		self.vbox.addWidget(self.exportDurationSpinbox)  
		

		self.vbox.addWidget(self.instructionsLabel)


		self.startButton.clicked.connect(self.start_video_processing) # click event
		self.vbox.addWidget(self.startButton) # add this last to kick off the process

		self.dialog.show()
		self.dialog.activateWindow()
		self.dialog.exec_()



# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = Animationimporter(parent=app) #instantiate your class
app.addExtension(extension)