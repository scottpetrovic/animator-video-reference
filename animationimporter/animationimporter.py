import os.path # for accessing files and directories
from os import listdir
from os.path import isfile, join

import subprocess # for calling terminal tools like FFMPEG and FFProbea
import shlex
import json
import platform
import math

from PyQt5.QtCore import (Qt, QTimer)
from krita import (Extension, krita)
from PyQt5 import uic # convert UI files from XML with *.ui to something python can work with
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QDialogButtonBox, QDialog, QMessageBox, QComboBox, QDoubleSpinBox,
                             QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, QSlider,
                             QToolButton, QAction, QPushButton, QSpinBox, QSpacerItem, QSizePolicy)


EXTENSION_ID = 'pykrita_animationimporter'
MENU_ENTRY = 'Animator Video Reference'


class Animationimporter(Extension):

	# make sure these are defined at the top
	def signal_change_location(self):
		
		self.fileName = QFileDialog.getOpenFileName(self.dialog, "Select your Video File", "", "Videos(*.mp4 *.avi *.mpg, *.gif);; All files (*.*)" )


		# if the person hits Cancel while picking a file, return and stop trying to load anything
		if self.fileName[0] == "":
			return
		

		self.dialog.fileLocationLabel.setText(self.fileName[0]) # text is returned as two parts, file path, and type of extension that was returned

		# run FFProbe to get vidoe info    
		self.findVideoMetada(self.fileName[0])

		# print(ffprobeOutput['streams'][0]['height'])
		self.textInfo = "Width:" + str(self.ffprobeData_width) + "px" + "<br>"
		self.textInfo += "Height:" + str(self.ffprobeData_height) + "px" + "<br>"
		self.textInfo += "Duration: "  +   str( '%.2f'%( self.ffprobeData_totalVideoDuration) )     + " s" + "<br>"
		self.textInfo += "Frames: " + str(self.ffprobeData_totalFrameCount) + "<br>"
		self.textInfo += "Frame Rate: " + str(self.ffprobeData_frameRate)

		if (self.hasOverriddenFPS):
			self.textInfo += "*<br>FPS not right in file. Modified to see full duration"


		self.dialog.fpsSpinbox.setValue(self.ffprobeData_frameRate)
		self.dialog.fileLoadedDetails.setText(self.textInfo)


		# subtract 1 second for the qslider since the end of the video won't have a image
		self.dialog.videoPreviewScrubber.setRange(0.0, self.ffprobeData_totalFrameCount) 
		self.dialog.currentFrameNumberInput.setRange(0.0, self.ffprobeData_totalFrameCount)
		self.dialog.exportDurationSpinbox.setRange(0.0, 9999.0)

		# print(self.fileName[0])
		if self.fileName[0] == "":
			self.startButton.setEnabled(0)
		else:
			self.dialog.startButton.setEnabled(1)
			self.update_video_thumbnail()


	def videoScrubberValueChanged(self):

		self.updateAndSyncCurrentFrame(self.dialog.videoPreviewScrubber.value())

		if self.videoSliderTimer.isActive() == 0:			
			self.videoSliderTimer.start(300) # 0.5 second update rate



	# updates model and any UI element that aren't in sync
	def updateAndSyncCurrentFrame(self, frameNumber):
		
		# update frame and seconds model data if they have changed
		if self.currentFrame != frameNumber:
			self.currentFrame = frameNumber
			self.currentSeconds = float(self.currentFrame) / float(self.ffprobeData_frameRate) 

		# update UI components if they are out of sync
		if self.currentFrame != self.dialog.currentFrameNumberInput.value():
			self.dialog.currentFrameNumberInput.setValue(self.currentFrame)

		if self.dialog.videoPreviewScrubber.value() != (self.currentFrame):
			self.dialog.videoPreviewScrubber.setValue(self.currentFrame)

		self.dialog.videoSliderValueLabel.setText(   str('%.2f'%(self.currentSeconds)).join(" s"))



	def update_video_thumbnail(self):
		
		#run ffmpeg to export out a frame from the video
		# ffmpeg -ss 01:23:45 -i input -vframes 1 -q:v 2 output.jpg
		video_directory = os.path.dirname(self.fileName[0]) 
		temp_thumbnail_location = video_directory + '/temp_thumbnail.png'
		
		# grab thumbnail dimensions from UI file
		thumbnailHolderSize = str(self.dialog.thumbnailImageHolder.width() ) + "x" + str(self.dialog.thumbnailImageHolder.height() )   # '320x240'

		ffmpegArgs = ['ffmpeg', 
				'-hide_banner',
				'-loglevel', 'panic',
				'-ss', str(self.currentSeconds) , 
				'-i', self.fileName[0], 
				'-s', thumbnailHolderSize, 
				'-vframes', '1', temp_thumbnail_location]
		

		# this fancy set up stuff helps suppress the command line from flashing on and off
		# whenever ffmpeg is ran. There doesn't seem to be a good global way to do it
		# so do the "BAD" way only on OSX
		# https://stackoverflow.com/questions/1765078/how-to-avoid-console-window-with-pyw-file-containing-os-system-call/12964900#12964900
				
		if platform.system() == 'Windows': 
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			startupinfo.wShowWindow = subprocess.SW_HIDE
			subprocess.call( ffmpegArgs, stdin=None, stdout=None, startupinfo=startupinfo)
		else:
			subprocess.call(ffmpegArgs)


		#store it in a QLabel and delete the image reference on the file system
		self.dialog.thumbnailImageHolder.setPixmap(QPixmap(temp_thumbnail_location))
		self.dialog.thumbnailImageHolder.show() # You were missing this.

		#remove temp file
		os.remove(temp_thumbnail_location)


	def start_video_processing(self):

		if self.fileName[0] == "":
			return


		self.dialog.startButton.setEnabled(0)
		self.dialog.startButton.setText("Processing...please wait")
		self.dialog.repaint() #forces UI to refresh to see the disabled Start button

		
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
		final_endTime = self.dialog.startExportingAtSpinbox.value() + self.dialog.exportDurationSpinbox.value()

		if final_endTime > self.ffprobeData_totalVideoDuration:
			adjustedEndTime = self.ffprobeData_totalVideoDuration - self.dialog.startExportingAtSpinbox.value() 
			self.dialog.exportDurationSpinbox.setValue(adjustedEndTime)



		ffmpegArgs = ['ffmpeg', 
			'-hide_banner',
			'-loglevel', 'panic',
			'-ss', str(self.dialog.startExportingAtSpinbox.value()) , 
			'-i', self.video_file, 
			'-t',  str(self.dialog.exportDurationSpinbox.value()), 
			'-r', str(self.dialog.fpsSpinbox.value()), 'output_%04d.png']
			
		# calls FFMPEG and outputs it at 24 frames per second. everything goes in the images folder
		subprocess.call(ffmpegArgs)
				
		
		# call FFProbe to get the image dimensions of the the file
		self.findVideoMetada(self.fileName[0])
		
		# create Krita document at given dimensions
		# Application.createDocument(1000, 1000, "Test", "RGBA", "U8", "", 120.0)
		self.newDocument = app.createDocument(self.ffprobeData_width, self.ffprobeData_height, "Test", "RGBA", "U8", "", 120.0)
		app.activeWindow().addView(self.newDocument) # shows the document in Krita
		

		self.newDocument.activeNode().setName("Canvas")

		# get list of files in directory
		self.imageFiles = [f for f in listdir(self.image_sequence_directory) if isfile(join(self.image_sequence_directory, f))]
		self.imageFiles.sort() # make alphabetical
				
		# get full path + filename of files to load
		self.fullPaths = []
		for self.image in self.imageFiles:
			self.fullPaths.append(self.image_sequence_directory + self.image)

		self.firstFrame = 0    
		# void importAnimation(const QList<QString> &files, int firstFrame, int stepSize);
		self.newDocument.importAnimation(self.fullPaths, self.firstFrame, self.dialog.frameSkipSpinbox.value())
		
		self.newDocument.setFramesPerSecond(self.dialog.fpsSpinbox.value())
		self.newDocument.setFullClipRangeStartTime(0)   
		self.newDocument.setFullClipRangeEndTime(self.dialog.exportDurationSpinbox.value() * self.dialog.fpsSpinbox.value())
		self.newDocument.activeNode().setShowInTimeline(1)
		self.newDocument.activeNode().setLocked(1)
		self.newDocument.activeNode().setName("Ref. Animation")

		app.action("add_new_paint_layer").trigger()
		self.newDocument.activeNode().setName("Draw Over")
		self.newDocument.activeNode().setShowInTimeline(1)
		
		self.newDocument.setCurrentTime(0)
		app.action("add_blank_frame").trigger()


		# cleanup - delete the images and remove the directory
		for image in self.fullPaths:
			os.remove(image) 
		
		os.rmdir(self.image_sequence_directory)
		
		self.dialog.startButton.setEnabled(1)
		self.dialog.startButton.setText("Start")


	# function to find the resolution of the input video file
	def findVideoMetada(self, pathToInputVideo):
		self.cmd = "ffprobe -v quiet -print_format json -show_streams"
		self.args = shlex.split(self.cmd)
		self.args.append(pathToInputVideo)
		
		# run the ffprobe process, decode stdout into utf-8 & convert to JSON
		self.ffprobeOutput = subprocess.check_output(self.args).decode('utf-8')

		self.ffprobeOutput = json.loads(self.ffprobeOutput)
		self.ffprobeData_height = self.ffprobeOutput['streams'][0]['height']
		self.ffprobeData_width = self.ffprobeOutput['streams'][0]['width']

		# frame rate comes back in odd format...so we need to do a bit of work so it is more usable. 
		# data will come back like "50/3"
		rawFrameRate = self.ffprobeOutput['streams'][0]['r_frame_rate'] 
		self.ffprobeData_frameRate = int(rawFrameRate.split("/")[0])  / int(rawFrameRate.split("/")[1])
		self.ffprobeData_frameRate = math.ceil(self.ffprobeData_frameRate)


		if "gif" in pathToInputVideo: # gif stores total frame count elsewhere
			# maybe first part of frame rate for GIF?
			self.ffprobeData_totalFrameCount = int(rawFrameRate.split("/")[0]) 
		else:
			self.ffprobeData_totalFrameCount = int(self.ffprobeOutput['streams'][0]['nb_frames'])


		# GIF does not bring back duration/frame data...so need to figure it out
		if "gif" in pathToInputVideo: 
			self.ffprobeData_totalVideoDuration = float(self.ffprobeData_totalFrameCount/self.ffprobeData_frameRate)
		else:
			self.ffprobeData_totalVideoDuration = float(self.ffprobeOutput['streams'][0]['duration'])


		# sometimes frame rate is not set right in video. 
		# We can try to guess this with the calculatedFrameRateDuration variable 
		# use alternate method for calculating frame rate in this case so we get the whole length
		calculatedFrameRateByDuration = float( self.ffprobeData_totalFrameCount/self.ffprobeData_totalVideoDuration)
		frameRateDifference =  abs(self.ffprobeData_frameRate - calculatedFrameRateByDuration)

		if(frameRateDifference > 1): 
			# something is not right with the frame rate with this file, so let's use our calculated value
			# to make  sure we get the whole duration
			# maybe add a warning to the UI stating something about this
			self.hasOverriddenFPS = 1
			self.ffprobeData_frameRate = calculatedFrameRateByDuration
		else:
			self.hasOverriddenFPS = 0

		


	def __init__(self, parent):
		# Always initialise the superclass, This is necessary to create the underlying C++ object 
		super().__init__(parent)


	def setup(self):
		pass

	def createActions(self, window):
		# you shouldn't have to touch this code. It should be ok where it is at
		action = window.createAction(EXTENSION_ID, MENU_ENTRY, "tools/scripts")
		action.triggered.connect(self.action_triggered) 


	def next_frame_button_clicked(self):
		self.updateAndSyncCurrentFrame(self.currentFrame+1)


	def prev_frame_button_clicked(self):
		self.updateAndSyncCurrentFrame(self.currentFrame-1)


	def	current_frame_input_changed(self):
		self.updateAndSyncCurrentFrame(self.dialog.currentFrameNumberInput.value())

	def action_triggered(self):

		# setup the UI objects
		self.dialog = QDialog(app.activeWindow().qwindow())
		uic.loadUi(os.path.dirname(os.path.realpath(__file__)) + '/animatorWidget.ui', self.dialog)

		self.dialog.filePickerButton.setIcon(app.icon("folder"))
		self.dialog.filePickerButton.clicked.connect(self.signal_change_location) # click event


		self.dialog.nextFrameButton.setIcon(app.icon("arrow-right"))
		self.dialog.nextFrameButton.clicked.connect(self.next_frame_button_clicked)

		self.dialog.prevFrameButton.setIcon(app.icon("arrow-left"))
		self.dialog.prevFrameButton.clicked.connect(self.prev_frame_button_clicked)

		self.dialog.currentFrameNumberInput.valueChanged.connect(self.current_frame_input_changed)


		self.fileName = ""
		# self.videoFrameRate = -1 # not set
		

		#create a Timer that will help compress slider value change events
		self.videoSliderTimer = QTimer()
		self.videoSliderTimer.setSingleShot(1)
		self.videoSliderTimer.timeout.connect(self.update_video_thumbnail)


		# the is the only time you should set this variable
		# afterwards always call updateAndSyncCurrentFrame
		self.currentFrame = 0
		self.currentSeconds = 0
		self.updateAndSyncCurrentFrame(0) # initialize to frame 0


		self.dialog.fpsSpinbox.setValue(24.0)
		self.dialog.fpsSpinbox.setSuffix(" FPS")

		self.dialog.frameSkipSpinbox.setValue(1)
		self.dialog.frameSkipSpinbox.setRange(1, 20)

		self.dialog.startExportingAtSpinbox.setValue(0.0)
		self.dialog.startExportingAtSpinbox.setRange(0.0, 9999.0)
		self.dialog.startExportingAtSpinbox.setSuffix (" s")

		# this will store milliseconds since QSlider has to store int values
		self.dialog.videoPreviewScrubber.setTickInterval(1) # QSlider has to work with int
		self.dialog.videoPreviewScrubber.valueChanged.connect(self.videoScrubberValueChanged)
		self.dialog.videoPreviewScrubber.setValue(0.0)



		# add a layout for the video slider
		self.dialog.exportDurationSpinbox.setValue(4.0)
		self.dialog.exportDurationSpinbox.setSuffix (" s")
		self.dialog.exportDurationSpinbox.setValue(3.0)

		self.ffprobeOutput = ""

		self.dialog.startButton.setEnabled(0)
		self.dialog.startButton.clicked.connect(self.start_video_processing) # click event



		# make sure we have everything set up to be able to use this
		self.checkFFMPegExists()
		self.checkFFProbeExists()
		self.checkKritaVersion()		
		if self.ffmpegFound == 0 or self.ffprobeFound == 0 or self.kritaVersionOk == 0  :
			self.disableUIAndShowMissingDependencyList()


		self.dialog.show()
		self.dialog.activateWindow()
		self.dialog.exec_()


	def disableUIAndShowMissingDependencyList(self):
		# we can't use this plugin because we are missing a dependency
		self.textInfo = "There are some things missing that this plugin needs. You will need to fix these and relaunch the plugin to try again.\n\n"
		
		if self.ffmpegFound == 0:
			self.textInfo +=  "\nffmpeg is not found.\nIf you are on Windows, you will additionally need to add your ffmpeg location to your PATH environment variable. I add this entry to my existing PATH variable... C:\ffmpeg\bin
		
		if self.ffprobeFound == 0:
			self.textInfo += "\n\nffprobe is not found.\nThis comes included when you install ffmpeg. This will probably start working when ffmpeg is found"
		
		if self.kritaVersionOk == 0:
			self.textInfo += "\n\nKrita not new enough.\nYour version of Krita doesn't include the animation API for this to work. You need Krita 4.2 or newer" 
		

		self.dialog.fileLoadedDetails.setText(self.textInfo)
		self.dialog.fileLoadedDetails.setMaximumWidth(500)

		# hide other UI elements to prevent clicking
		self.dialog.filePickerButton.setVisible(0)
		self.dialog.nextFrameButton.setVisible(0)
		self.dialog.prevFrameButton.setVisible(0)
		self.dialog.exportDurationSpinbox.setVisible(0)
		self.dialog.videoPreviewScrubber.setVisible(0)
		self.dialog.frameSkipSpinbox.setVisible(0)
		self.dialog.startButton.setVisible(0)
		self.dialog.thumbnailImageHolder.setVisible(0)
		self.dialog.currentFrameNumberInput.setVisible(0)
		self.dialog.videoPreviewScrubber.setVisible(0)
		self.dialog.videoSliderValueLabel.setVisible(0)
		self.dialog.fileLocationLabel.setVisible(0)
		self.dialog.exportoptionsGroup.setVisible(0)



	def checkFFMPegExists(self):
		self.findffmpegCommand = ['ffmpeg', '-v']		
		self.ffmpegFound = 0
		try:
			self.ffmpegFound = subprocess.call(self.findffmpegCommand)
		except:
			self.ffmpegFound = 0


	def checkFFProbeExists(self):
		self.findffprobeCommand = ['ffprobe', '-v']		
		self.ffprobeFound = 0
		try:
			self.ffprobeFound = subprocess.call(self.findffprobeCommand)
		except:
			self.ffprobeFound = 0


	def checkKritaVersion(self):		
		# major version should be 4 or above	
		majorVersion = app.version().split(".")[0] 	
		
		if (int(majorVersion) < 4 ):
			self.kritaVersionOk = 0
			return

		# minor version should be 2 or above
		minorVersion = app.version().split(".")[1] 
		if (int(minorVersion) < 2 ):
			self.kritaVersionOk = 0
			return

		self.kritaVersionOk = 1



# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = Animationimporter(parent=app) #instantiate your class
app.addExtension(extension)
