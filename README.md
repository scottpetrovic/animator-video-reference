# Animator Video Reference Plugin
A Python plugin for Krita 4.2 that allows you to load a video for reference and import frames to your document.

![alt text](preview.png)


# Installation
You need to have FFMPEG installed/hooked up for this to work. This is generally needed to do things with animation in Krita and does most of the work for this plugin. I probably could add a warning to the plugin if it FFMPEG isn't found. 

Just download the plugin and insert it into your pykrita folder that contains all your other plugins. On linux this will be in your .local > share > krita > pykrita. On Windows this will be in your %APPDATA% folder, then Krita > pykrita. Make sure the readme is in this directory instead of just the folder that contains the contents.

# Usage
This script is started from the main menu Tools > Animator Video Reference. Once the window loads, select a file. The video loads a thumbnail where you can scrube through the timeline. You can also export out a frame range so it goes into a new Krita document and populate the timeline
