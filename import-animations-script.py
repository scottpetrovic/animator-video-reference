from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (QDialogButtonBox, QDialog, QMessageBox, QComboBox, 
                             QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, 
                             QToolButton, QAction, QPushButton, QSpinBox)
from krita import Extension

import os.path # for accessing files and directories
from os import listdir
from os.path import isfile, join

import subprocess # for calling terminal tools like FFMPEG and FFProbea
import shlex
import json

# re-used variables
dialog = QDialog(Application.activeWindow().qwindow())
vbox = QVBoxLayout(dialog)
hboxOptionsLayout = QHBoxLayout(dialog)
filePickerButton = QToolButton()  # Until we have a proper icon
startButton = QPushButton("Start")
fileLocationLabel = QLabel("Choose a video file")
fileLoadedDetails = QLabel("Image details...") # video details go here to show to people

fileName = ""

fpsLabel = QLabel("Frames per second")
fpsSpinbox = QSpinBox()
fpsSpinbox.setValue(24)

frameSkipLabel = QLabel("Frame Skip Interval")
frameSkipSpinbox = QSpinBox()
frameSkipSpinbox.setValue(1)

startExportingAtXSecondsLabel = QLabel("Start Exporting at X seconds")
startExportingAtSpinbox = QSpinBox()
startExportingAtSpinbox.setValue(0)


exportDurationLabel = QLabel("Export duration (in seconds)")
exportDurationSpinbox = QSpinBox()
exportDurationSpinbox.setValue(4)



image_sequence_directory = ""
instructionsLabel = QLabel("For now, we will just take the for 3 seconds of the video. We can make this configurable later")
    
ffprobeOutput = ""


# make sure these are defined at the top
def signal_change_location():
    # call this with a button click -- not sure what the blank directory is going to do on different OSs
    global fileName
    global fileLocationLabels
    global fileLoadedDetails
    global ffprobeOutput
    
    fileName = QFileDialog.getOpenFileName(dialog, "Select your Video File", "", "Videos(*.mp4 *.avi *.mpg);; All files (*.*)" )
    fileLocationLabel.setText(fileName[0]) # text is returned as two parts, file path, and type of extension that was returned

    # run FFProbe to get vidoe info    
    findVideoMetada(fileName[0])    
    
   # print(ffprobeOutput['streams'][0]['height'])
    textInfo = "Height:" + str(ffprobeOutput['streams'][0]['height']) + "px  Width:" + str(ffprobeOutput['streams'][0]['width']) + "px"
    textInfo += "Duration: "  +  ffprobeOutput['streams'][0]['duration']  + " s"
    
    
    fileLoadedDetails.setText(textInfo)
   
   
   
   

def start_video_processing():
    
    global startButton
    global startExportingAtSpinbox    
    global exportDurationSpinbox
    
    startButton.setEnabled(0)
    startButton.setText("Processing...please wait")
    
    # get command line tool and navigate to the video direction
    # create a folder to store images
    print(fileName[0])


    global fpsSpinbox
    global frameSkipSpinbox
    global startExportingAtSpinbox
    global exportDurationSpinbox


    
    global image_sequence_directory    
    image_sequence_directory = os.path.dirname(fileName[0]) 
    image_sequence_directory += "/images/"
    
    print("directory to make: " + image_sequence_directory)
       
    if not os.path.exists(image_sequence_directory):
        os.makedirs(image_sequence_directory)    
    
    # make the OS move to image directory to do the exporting
    os.chdir(image_sequence_directory)
    
    video_file = "../" + os.path.basename(fileName[0])  # we are in the images folder, so go up one to reference the video
    print("video file to process: " + video_file)
    
    # calls FFMPEG and outputs it at 24 frames per second. everything goes in the images folder
    #subprocess.call(['ffmpeg', '-i', video_file, "-r", str(fpsSpinbox.value()), 'output_%04d.png'])
    subprocess.call(['ffmpeg', '-ss', str(startExportingAtSpinbox.value()) , '-i', video_file, '-t',  str(exportDurationSpinbox.value()), "-r", str(fpsSpinbox.value()), 'output_%04d.png'])
    
    
    
    # ffmpeg -ss 30 -i input.wmv -c copy -t 10 output.wmv
    
    
    # call FFProbe to get the image dimensions of the the file
    imageDimensions = findVideoMetada(fileName[0])
    
    print(imageDimensions[0], imageDimensions[1]) # height x width
    
    # create Krita document at given dimensions
    # Application.createDocument(1000, 1000, "Test", "RGBA", "U8", "", 120.0)
    newDocument = Application.createDocument(imageDimensions[1], imageDimensions[0], "Test", "RGBA", "U8", "", 120.0)
    Application.activeWindow().addView(newDocument) # shows the document in Krita
    
    
    # call the import animation frames action to grab all the images and import them into an animation layer
       
    # get list of files in directory
    imageFiles = [f for f in listdir(image_sequence_directory) if isfile(join(image_sequence_directory, f))]
    imageFiles.sort() # make alphabetical
    
    
    # get full path + filename of files to load
    fullPaths = []
    for image in imageFiles:
        fullPaths.append(image_sequence_directory + image)

    # step = 1
    firstFrame = 0    
    # void importAnimation(const QList<QString> &files, int firstFrame, int stepSize);
    newDocument.importAnimation(fullPaths, firstFrame, frameSkipSpinbox.value())
    
        
    # cleanup - delete the images and remove the directory
    print("removing the contents")
    for image in fullPaths:
        os.remove(image) 
    
    os.rmdir(image_sequence_directory)
    print("removed the contents")
    
    startButton.setEnabled(1)
    startButton.setText("Start")
        
    
    
   
def main():

    # add label with location and button to call file picker
    vbox.addWidget(fileLocationLabel)

    filePickerButton.setIcon(Application.icon("folder"))

    filePickerButton.clicked.connect(signal_change_location) # click event
    vbox.addWidget(filePickerButton)
    vbox.addWidget(fileLoadedDetails)
    
    vbox.addLayout(hboxOptionsLayout)
    

    # add frames per second UI
    hboxOptionsLayout.addWidget(fpsLabel)    
    fpsSpinbox.setValue(24.0)
    hboxOptionsLayout.addWidget(fpsSpinbox)
    
    # add frames skip interval
    frameSkipSpinbox.setValue(2)
    hboxOptionsLayout.addWidget(frameSkipLabel)
    hboxOptionsLayout.addWidget(frameSkipSpinbox)
    
    
    # export starting at thing
    vbox.addWidget(startExportingAtXSecondsLabel)
    vbox.addWidget(startExportingAtSpinbox)    

    # export duration
    vbox.addWidget(exportDurationLabel)
    vbox.addWidget(exportDurationSpinbox)  
    

    vbox.addWidget(instructionsLabel)


    startButton.clicked.connect(start_video_processing) # click event
    vbox.addWidget(startButton) # add this last to kick off the process


    dialog.show()
    dialog.activateWindow()
    dialog.exec_()


# function to find the resolution of the input video file
def findVideoMetada(pathToInputVideo):
    cmd = "ffprobe -v quiet -print_format json -show_streams"
    args = shlex.split(cmd)
    args.append(pathToInputVideo)
    
    # run the ffprobe process, decode stdout into utf-8 & convert to JSON
    global ffprobeOutput
    ffprobeOutput = subprocess.check_output(args).decode('utf-8')
    ffprobeOutput = json.loads(ffprobeOutput)

    # prints all the metadata available:
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(ffprobeOutput)

    # for example, find height and width
    height = ffprobeOutput['streams'][0]['height']
    width = ffprobeOutput['streams'][0]['width']
    
    print(height, width)
    return height, width