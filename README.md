# skype-wrapper
Wrapper to show skype in the messaging menu and use notify-send to show incoming messages. Only works in Ubuntu Unity and with python 2.x (because the skype python api os only available in python 2.x)

# Installation

1. Install `Skype4Py` https://github.com/awahlig/skype4py
2. Clone the repository `git clone https://github.com/wa4557/skype-wrapper`
3. cd to `/usr/local/bin` and create a symlink to the script `sudo ln -s /path/to/script/skype-wrapper.py skype`

That's it. Everytime you start skype first the skype wrapper is started, and skype is included in the Messaging Menu. Click on it in the Messaging Menu to actually open skype.
