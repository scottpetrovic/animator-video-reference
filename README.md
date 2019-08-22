# Animator Video Reference Plugin
A Python plugin for Krita 4.2 that allows you to load a video for reference and import frames to your document.

![alt text](preview.png)


# Installation
You need to have FFMPEG installed/hooked up for this to work. This is generally needed to do things with animation in Krita and does most of the work for this plugin. If you haven't done that, see the instructions for the official documentation.

https://docs.krita.org/en/reference_manual/render_animation.html#setting-up-krita-for-exporting-animations

Once you have that working, then continue. Download the plugin as a ZIP file from the "Clone or Download" option on this page. Krita 4.2 comes with a python script importer to make it easy to add. After the zip file is done, start Krita. Go to...

Tools > Scripts > Import Python Plugin

Select the zip file to upload. You will have to restart Krita for the plugin to show up in your plugin manager. Settings > Configure Krita > Python Plugin Manager. Make sure it is enabled and click OK.

# Usage
This script is started from the main menu Tools > Animator Video Reference. Once the window loads, select a file. The video loads a thumbnail where you can scrube through the timeline. You can also export out a frame range so it goes into a new Krita document and populate the timeline
