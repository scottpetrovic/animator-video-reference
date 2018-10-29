import os.path # for accessing files and directories
from os import listdir
from os.path import isfile, join

import subprocess # for calling terminal tools like FFMPEG and FFProbea
import shlex
import json

from PyQt5.QtCore import (Qt, QTimer)
from krita import (Extension, krita)
from PyQt5 import uic # convert UI files from XML with *.ui to something python can work with
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QDialogButtonBox, QDialog, QMessageBox, QComboBox, QDoubleSpinBox,
                             QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, QSlider,
                             QToolButton, QAction, QPushButton, QSpinBox, QSpacerItem, QSizePolicy)


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
		self.textInfo += " Duration: "  +  self.ffprobeOutput['streams'][0]['duration']  + " s"
		self.textInfo += " Total Frames: " + self.ffprobeOutput['streams'][0]['nb_frames']
		self.textInfo += " Frame Rate: " + self.ffprobeOutput['streams'][0]['r_frame_rate']



		self.fileLoadedDetails.setText(self.textInfo)

		self.totalVideoDuration = float(self.ffprobeOutput['streams'][0]['duration']);

		# subtract 1 second for the qslider since the end of the video won't have a image
		self.videoPreviewScrubber.setRange(0.0, (self.totalVideoDuration*1000-1000)) 


		# print(self.fileName[0])
		if self.fileName[0] == "":
			self.startButton.setEnabled(0)
		else:
			self.startButton.setEnabled(1)
			self.update_video_thumbnail()


	#def videoPreviewChanaged(self):
		#update thumbnail for video preview				
		#self.update_video_thumbnail()

	def videoScrubberValueChanged(self):
		self.videoSliderValueLabel.setText(str(self.videoPreviewScrubber.value()/1000).join(" s"))

		if self.videoSliderTimer.isActive() == 0:			
			self.videoSliderTimer.start(300) # 0.5 second update rate



	def update_video_thumbnail(self):
		#run ffmpeg to export out a frame from the video
		# ffmpeg -ss 01:23:45 -i input -vframes 1 -q:v 2 output.jpg
		video_directory = os.path.dirname(self.fileName[0]) 
		temp_thumbnail_location = video_directory + '/temp_thumbnail.png'
		
		# -vf scale="720:480"
		subprocess.call(['ffmpeg', '-ss', str(self.videoPreviewScrubber.value()/1000) , '-i', self.fileName[0], '-s', '520x320', '-vframes', '1', temp_thumbnail_location])

		#store it in a QLabel and delete the image reference on the file system
		# self.thumbnailImageHolder 
		self.thumbnailImageHolder.setPixmap(QPixmap(temp_thumbnail_location))
		self.thumbnailImageHolder.show() # You were missing this.

		#remove temp file
		os.remove(temp_thumbnail_location)


	def start_video_processing(self):

		if self.fileName[0] == "":
			return


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


		# if export duration goes over the total length, change the duration to go to the end
		final_endTime = self.startExportingAtSpinbox.value() + self.exportDurationSpinbox.value()

		if final_endTime > self.totalVideoDuration:
			adjustedEndTime = self.totalVideoDuration - self.startExportingAtSpinbox.value() 
			self.exportDurationSpinbox.setValue(adjustedEndTime)



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
		
		# print(self.height, self.width)
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

		# setup the UI objects
		self.dialog = QDialog(app.activeWindow().qwindow())
		uic.loadUi(os.path.dirname(os.path.realpath(__file__)) + '/animatorWidget.ui', self.dialog)
		self.dialog.setWindowTitle("Import Video for Animation Reference")

		self.filePickerButton = QToolButton()  # Until we have a proper icon
		self.filePickerButton.setIcon(app.icon("folder"))
		self.filePickerButton.clicked.connect(self.signal_change_location) # click event

		self.fileLocationLabel = QLabel("Choose a video file")
		self.fileLoadedDetails = QLabel("") # video details go here to show to people

		self.fileName = ""

		self.fpsLabel = QLabel("Exported FPS: ")
		self.fpsSpinbox = QSpinBox()
		self.fpsSpinbox.setValue(24.0)
		self.fpsSpinbox.setSuffix(" FPS")

		self.frameSkipLabel = QLabel("Skip Interval (1 is all frames):")
		self.frameSkipSpinbox = QSpinBox()
		self.frameSkipSpinbox.setValue(1)
		self.frameSkipSpinbox.setRange(1, 20)

		self.startExportingAtXSecondsLabel = QLabel("Start Exporting at: ")
		self.startExportingAtSpinbox = QDoubleSpinBox()
		self.startExportingAtSpinbox.setValue(0.0)
		self.startExportingAtSpinbox.setSuffix (" s")

		# this will store milliseconds since QSlider has to store int values
		self.videoPreviewScrubber = QSlider(Qt.Horizontal) 
		self.videoPreviewScrubber.setTickInterval(1) # QSlider has to work with int
		#self.videoPreviewScrubber.sliderReleased.connect(self.videoPreviewChanaged)
		self.videoPreviewScrubber.valueChanged.connect(self.videoScrubberValueChanged)
		self.videoPreviewScrubber.setValue(0.0)


		#create a Timer that will help compress slider value change events
		self.videoSliderTimer = QTimer()
		self.videoSliderTimer.setSingleShot(1)
		self.videoSliderTimer.timeout.connect(self.update_video_thumbnail)


		# add a layout for the video slider
		self.thumbnailImageHolder = QLabel("")
		self.videoSliderValueLabel = QLabel("")
		self.videoSliderValueLabel.setText(str(self.videoPreviewScrubber.value()).join(" s"))

		self.exportDurationLabel = QLabel("Export duration:")
		self.exportDurationSpinbox = QDoubleSpinBox()
		self.exportDurationSpinbox.setValue(4.0)
		self.exportDurationSpinbox.setSuffix (" s")
		self.exportDurationSpinbox.setValue(3.0)

		self.ffprobeOutput = ""

		self.startButton = QPushButton("Start")
		self.startButton.setEnabled(0)
		self.startButton.clicked.connect(self.start_video_processing) # click event


		self.hSpacer = QSpacerItem(5, 5, QSizePolicy.Expanding, QSizePolicy.Minimum)





		# arrange and add the UI elements
		self.vbox = QVBoxLayout(self.dialog) # main layout
		self.hboxFileUploadOptions = QHBoxLayout(self.dialog)

		self.videoHSliderLayout = QHBoxLayout(self.dialog) # for video playback controls
		self.hboxOptionsLayout = QHBoxLayout(self.dialog) # export settings
		self.hboxOptionsTwoLayout = QHBoxLayout(self.dialog) # export settings 2
		self.fileDetailsLayout = QHBoxLayout(self.dialog) #mostly added to add margins


		self.hboxFileUploadOptions.addWidget(self.fileLocationLabel)
		self.hboxFileUploadOptions.addWidget(self.filePickerButton)
		self.hboxFileUploadOptions.addSpacerItem(self.hSpacer)
		self.vbox.addLayout(self.hboxFileUploadOptions)

		self.vbox.addWidget(self.thumbnailImageHolder)

		self.videoHSliderLayout.addWidget(self.videoPreviewScrubber)
		self.videoHSliderLayout.addWidget(self.videoSliderValueLabel)
		

		self.vbox.addLayout(self.videoHSliderLayout)
		


		self.fileDetailsLayout.addWidget(self.fileLoadedDetails)
		self.fileDetailsLayout.setContentsMargins(0,10,0,20) #left, top, right, bottom
		self.vbox.addLayout(self.fileDetailsLayout)

		

		# add frames per second UI
		self.hboxOptionsLayout.addWidget(self.fpsLabel)    
		self.hboxOptionsLayout.addWidget(self.fpsSpinbox)

		self.hboxOptionsLayout.addSpacerItem(self.hSpacer)
		
		self.hboxOptionsLayout.addWidget(self.frameSkipLabel)
		self.hboxOptionsLayout.addWidget(self.frameSkipSpinbox)
		self.vbox.addLayout(self.hboxOptionsLayout)
		
		# export starting at thing
		self.hboxOptionsTwoLayout.addWidget(self.startExportingAtXSecondsLabel)
		self.hboxOptionsTwoLayout.addWidget(self.startExportingAtSpinbox)
		
		self.hboxOptionsTwoLayout.addSpacerItem(self.hSpacer)

		self.hboxOptionsTwoLayout.addWidget(self.exportDurationLabel)
		self.hboxOptionsTwoLayout.addWidget(self.exportDurationSpinbox)

		self.vbox.addLayout(self.hboxOptionsTwoLayout)

		self.vbox.addWidget(self.startButton) # add this last to kick off the process


		self.dialog.show()
		self.dialog.activateWindow()
		self.dialog.exec_()



# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = Animationimporter(parent=app) #instantiate your class
app.addExtension(extension)
