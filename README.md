# xwebcap
Simple script to capture video and audio from Web-browser

# Features

- Recording video and audio from web-browser through command line
- Streaming video and audio from web-browser by ffmpeg
- Recording jitsi video conferences (as an separate participant)

# Usage examples

Record 5 seconds video from https://example.com

```
python3 xwebcap.py -d 5 -u https://example.com
```

Record jitsi video conference

```
python3 xwebcap.py -p jitsi -u https://meet.jit.si/[YOUROOM]
```

Starting new video file

```
kill -s SIGUSR1 [xwebcap pid]
```

# Requestments

- Linux
- Python3
- Firefox
- Xvfb
- pulseaudio

# Help

```
usage: xwebcap.py [-h] [-p PROFILE] [-x XRES] [-y YRES] [-f FRAMERATE] [-i]
                  [-m FFMPEG] [-o OUTPUT] -u URL [-d DURATION]

optional arguments:
  -h, --help            show this help message and exit
  -p PROFILE, --profile PROFILE
                        Web application profile to capture: ['default',
                        'jitsi']
  -x XRES, --xres XRES  Virtual screen X
  -y YRES, --yres YRES  Virtual screen Y
  -f FRAMERATE, --framerate FRAMERATE
                        Capture frame rate
  -i, --interactive     Run interactive python console with browser object
                        after starting capturing
  -m FFMPEG, --ffmpeg FFMPEG
                        Additional ffmpeg arguments
  -o OUTPUT, --output OUTPUT
                        Output file
  -u URL, --url URL     Target url
  -d DURATION, --duration DURATION
                        Capture duration in sec
```

# How it works

- Creates virtual X11 screen (Xvfb)
- Creates virtual audio device (pulseaudio)
- Starts Firefox (selenium)
- Starts recording (ffmpeg)
- Waits for the end of the recording
- Cleans up

# API

```python
from xwebcap import WebCap

class MyWebCap(WebCap):

    #Called before recording started
    def load_page(self):
        super().load_page()
        # works with selenium browser object as self.browser

    #Called when recording started
    def on_capture(self):
        # works with selenium browser object as self.browser
        pass

c = MyWebCap()
c.start()

```
