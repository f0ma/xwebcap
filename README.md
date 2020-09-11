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
sage: xwebcap.py [-h] [-p PROFILE] [-x XRES] [-y YRES] [-e DEPTH] [-t EXTENT]
                  [-s SCREEN] [-f FRAMERATE] [-i] [-m FFMPEG] [-o OUTPUT] [-w]
                  -u URL [-l] [-d DURATION]

optional arguments:
  -h, --help            show this help message and exit
  -p PROFILE, --profile PROFILE
                        Web application profile to capture: ['default',
                        'jitsi']
  -x XRES, --xres XRES  Virtual screen X, default 1280
  -y YRES, --yres YRES  Virtual screen Y, default 740
  -e DEPTH, --depth DEPTH
                        Virtual screen color depth, default 24
  -t EXTENT, --extent EXTENT
                        Capturing extent ex. 400x500+100,100, default as
                        screen
  -s SCREEN, --screen SCREEN
                        Virtual screen number, default 0
  -f FRAMERATE, --framerate FRAMERATE
                        Capture frame rate, default 10
  -i, --interactive     Run interactive python console with browser object
                        after starting capturing
  -m FFMPEG, --ffmpeg FFMPEG
                        Additional ffmpeg arguments
  -o OUTPUT, --output OUTPUT
                        Output file
  -w, --windowed        Do not turn browser into fullscreen mode
  -u URL, --url URL     Target url
  -l, --load            Loading page after capturing started
  -d DURATION, --duration DURATION
                        Capture duration in sec, default no limit

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
import datetime
import xwebcap

class MyWebCap(xwebcap.WebCap):

    #Called before recording started
    def before_capture(self):
        self.browser.get(self.url)
        self.browser.fullscreen_window()

    #Called after recording started
    def on_capture(self):
        self.browser.find_element_by_xpath('/html/body').send_keys('w')
        time.sleep(1)

c = MyWebCap()

#Optional:
#install SIGINT and SIGTERM hook for graceful exit
#install SIGUSR1 for new file capturing
xwebcap.install_hooks(c)

c.start()

#call c.stop() for exit

#

```
