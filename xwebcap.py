#!/usr/bin/env python3
import os, time, re, math, threading
import subprocess, signal
import random, datetime, code
from shutil import which

try:
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException
    from selenium.webdriver.common.keys import Keys
except:
    raise OSError('Python package selenium not found')

if which('firefox') is None:
    raise OSError('Firefox not found')

if which('Xvfb') is None:
    raise OSError('Xvfb not found')

if which('pactl') is None:
    raise OSError('pactl not found')

if which('pacmd') is None:
    raise OSError('pactl not found')

if which('ffmpeg') is None:
    raise OSError('ffmpeg not found')


cap_object = None
profiles = {}

class WebCap:
    def __init__(self, x_res = 1280,
                       y_res = 720,
                       extent = '',
                       depth = 24,
                       framerate = 10,
                       screen = 0,
                       ffmpeg_opts = '',
                       windowed = False,
                       load = False,
                       url = "https://example.com",
                       out_file = 'output.mp4',
                       duration = 0,
                       interactive = False):
        self.sink_module_id = None
        self.xvfb_process = None
        self.ffmpeg_process = None
        self.sink_mon_thread = None
        self.sink_mon_exit = True
        self.x_res = x_res
        self.y_res = y_res
        self.extent = extent
        self.depth = depth
        self.framerate = framerate
        self.ffmpeg_opts = ffmpeg_opts
        self.browser = None
        self.url = url
        self.out_file = out_file
        self.exit = False
        self.interactive = interactive
        self.duration = duration
        self.screen = screen
        self.windowed = windowed
        self.load = load
        self.start_time = None
        self.random_ids()

    def random_ids(self):
        self.display_id = random.randint(100, 999)
        self.sink_id = 'webcap'+str(self.display_id)

    def start_xvfb(self):
        #TODO: why 10/9 scale requried?
        pc = f"Xvfb -listen tcp :{self.display_id} -screen {self.screen} {math.ceil(self.x_res*10/9)}x{math.ceil(self.y_res*10/9)}x{self.depth}"
        print('Starting Xvfb server:\n', pc)
        self.xvfb_process = subprocess.Popen(pc, shell = True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        time.sleep(1)
        if self.xvfb_process.returncode == None:
            print('Server started with id:', self.display_id)
        else:
            #TODO: check if screen id currently in use
            raise SystemError('Can\'t start Xvfb')

    def create_sink(self):
        pc = f'pactl load-module module-null-sink sink_name={self.sink_id}'
        print('Creating new audio sink:\n',pc)
        self.sink_module_id = int(subprocess.check_output(pc, shell=True).decode().strip())
        print('Sync created with name:', self.sink_id, 'and id:', self.sink_module_id)

    def start_browser(self):
        print('Starting browser')
        os.environ["DISPLAY"] = f":{self.display_id}.{self.screen}"
        fp = webdriver.FirefoxProfile()
        fp.set_preference("permissions.default.microphone", 1)
        fp.set_preference("permissions.default.camera", 1)
        self.browser = webdriver.Firefox(firefox_profile = fp)
        self.browser.maximize_window()
        print('Browser started')

    def before_capture(self):
        if not self.load:
            print('Loading page', self.url)
            self.browser.get(self.url)
        if not self.windowed:
            self.browser.fullscreen_window()

    def on_capture(self):
        if self.load:
            print('Loading page', self.url)
            self.browser.get(self.url)

    def capture_loop(self):
        if self.interactive:
            code.interact(local={'browser':self.browser})
        else:
            self.start_time = datetime.datetime.now()
            print('Press Ctrl-C (send SIGINT) to exit, or send SIGUSR1 to creating new file. My pid is', os.getpid())
            while not self.exit:
                time.sleep(1)
                if self.duration > 0 and (datetime.datetime.now() - self.start_time).seconds > self.duration:
                    break

    def start_sink_changer(self):
        print('Starting audio sink changer')
        self.sink_mon_exit = False
        self.sink_mon_thread = threading.Thread(target=self.change_audio_sink)
        self.sink_mon_thread.start()

    def stop_sink_changer(self):
        self.sink_mon_exit = True
        self.sink_mon_thread.join()
        print('Sink changer stopped')

    def change_audio_sink(self):
        sink_timeout = 0.1
        while not self.sink_mon_exit:

            sinks = subprocess.check_output(['pacmd', 'list-sink-inputs']).decode()
            sinks = sinks.split('\n')
            index_re = re.compile(r"\s+index:\s+([0-9]+)")
            pid_re = re.compile(r"\s+window.x11.display\s+=\s+\":([0-9]+)\.[0-9]\"")
            sink_re = re.compile(r"\s+sink:\s+[0-9]+\s+<(.*?)>")

            current_index = None
            current_display = None
            current_sink = None
            browser_sink_index = None
            for line in sinks:
                t = index_re.match(line)
                if t:
                    current_index = int(t.group(1))
                t = sink_re.match(line)
                if t:
                    current_sink = t.group(1)
                t = pid_re.match(line)
                if t:
                    current_display = int(t.group(1))
                    if self.display_id == current_display:
                        browser_sink_index = current_index
                        break

            if browser_sink_index != None and current_sink!=self.sink_id:
                pc = f'pactl move-sink-input {browser_sink_index} {self.sink_id}'
                print('Moving browser to virtual audio device:\n', pc)
                os.system(pc)
                sink_timeout = 1
            time.sleep(sink_timeout)

    def start_capturing(self):
        print('Capturing into', self.out_file)
        wsz = self.browser.get_window_size()
        print('Browser frame:', wsz)
        extent = f"{wsz['width']}x{wsz['height']}"
        offset = ""
        if self.extent != '':
            extent, offset = self.extent.split('+')
            offset = '+'+offset

        pc = f"ffmpeg -y -f x11grab -video_size {extent} -framerate {self.framerate} -draw_mouse 0 -i 127.0.0.1:{self.display_id}.{self.screen}{offset} -f pulse -i {self.sink_id}.monitor {self.ffmpeg_opts} {self.out_file}"
        print('Starting capturing:\n', pc)
        self.ffmpeg_process = subprocess.Popen(pc, shell = True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,  preexec_fn=os.setsid)
        print('Capturing started.')

    def stop_capturing(self):
        os.killpg(os.getpgid(self.ffmpeg_process.pid), signal.SIGINT)
        os.waitpid(self.ffmpeg_process.pid, 0)
        print('Capturing stoped.')

    def stop_browser(self):
        self.browser.quit()
        print('Browser closed.')

    def remove_sink(self):
        os.system(f'pactl unload-module {self.sink_module_id}')
        print('Sink removed.')

    def stop_xvfb(self):
        os.killpg(os.getpgid(self.xvfb_process.pid), signal.SIGINT)
        os.waitpid(self.xvfb_process.pid, 0)
        print('xvfb stoped.')


    def start(self):
        self.start_xvfb()
        try:
            self.proc_sink()
        finally:
            self.stop_xvfb()
            time.sleep(1)

    def stop(self):
        self.exit = True

    def proc_sink(self):
        self.create_sink()
        try:
            self.proc_browser()
        finally:
            self.remove_sink()
            time.sleep(1)

    def proc_browser(self):
        self.start_browser()
        try:
            self.proc_page()
        finally:
            self.stop_browser()
            time.sleep(1)

    def proc_page(self):
        self.start_sink_changer()
        try:
            self.before_capture()
            self.start_capturing()
            print('Capturing...')
            self.on_capture()
            self.capture_loop()
        finally:
            self.stop_capturing()
            self.stop_sink_changer()
            time.sleep(1)

profiles['default'] = WebCap

class JitsiCap(WebCap):

    def before_capture(self):
        print('Loading page', self.url)
        self.browser.get(self.url)
        time.sleep(5)

        try:
            c = self.browser.find_element_by_name('displayName')
            c.send_keys('Record Bot')
            c.send_keys(webdriver.common.keys.Keys.ENTER)
        except NoSuchElementException:
            pass

        self.browser.find_element_by_xpath('/html/body').send_keys('s')
        time.sleep(2)
        self.browser.find_element_by_xpath('/html/body').send_keys('w')
        time.sleep(2)


profiles['jitsi'] = JitsiCap

cap_object = None

def exit_handler(sig, frame):
    global cap_object
    cap_object.exit = True

def new_file_handler(sig, frame):
    global cap_object
    cap_object.stop_capturing()
    filename, file_extension = os.path.splitext(cap_object.out_file)
    if '.' in filename:
        filename = filename.split('.')[0]
    cap_object.out_file = filename+'.'+datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+file_extension
    cap_object.start_capturing()


def install_hooks(cap_obj):
    global cap_object
    cap_object = cap_obj
    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)
    signal.signal(signal.SIGUSR1, new_file_handler)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', "--profile", default='default', help="Web application profile to capture: "+str(list(profiles.keys())))
    parser.add_argument('-x', "--xres", type=int, default=1280, help="Virtual screen X, default 1280")
    parser.add_argument('-y', "--yres", type=int, default=720, help="Virtual screen Y, default 740")
    parser.add_argument('-e', "--depth", type=int, default=24, help="Virtual screen color depth, default 24")
    parser.add_argument('-t', "--extent", default='', help="Capturing extent ex. 400x500+100,100, default as screen")
    parser.add_argument('-s', "--screen", type=int, default=0, help="Virtual screen number, default 0")
    parser.add_argument('-f', "--framerate", type=int, default=10, help="Capture frame rate, default 10")
    parser.add_argument('-i', "--interactive", action='store_true', default=False, help="Run interactive python console with browser object after starting capturing")
    parser.add_argument('-m', "--ffmpeg", default='', help="Additional ffmpeg arguments")
    parser.add_argument('-o', "--output", default='webcap.'+datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+'.mp4', help="Output file")
    parser.add_argument('-w', "--windowed", action='store_true', default=False, help="Do not turn browser into fullscreen mode")
    parser.add_argument('-u', "--url", required=True, help="Target url")
    parser.add_argument('-l', "--load", action='store_true', default=False, help="Loading page after capturing started")
    parser.add_argument('-d', "--duration", type=int, default=0, help="Capture duration in sec, default no limit")

    args = parser.parse_args()

    cap_object = profiles[args.profile](x_res = args.xres,
                                        y_res = args.yres,
                                        extent = args.extent,
                                        depth = args.depth,
                                        framerate = args.framerate,
                                        screen = args.screen,
                                        ffmpeg_opts = args.ffmpeg,
                                        windowed = args.windowed,
                                        load = args.load,
                                        url = args.url,
                                        out_file = args.output,
                                        duration = args.duration,
                                        interactive = args.interactive)

    install_hooks(cap_object)

    cap_object.start()

