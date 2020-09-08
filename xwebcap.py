#!/usr/bin/env python3
import os, time, re
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

class WebCap:
    def __init__(self, x_res = 1280,
                       y_res = 720,
                       framerate = 10,
                       ffmpeg_opts = '',
                       url = "https://example.com",
                       out_file = 'output.mkv',
                       duration = 0,
                       interactive = False):
        self.sink_module_id = None
        self.xvfb_process = None
        self.ffmpeg_process = None
        self.x_res = x_res
        self.y_res = y_res
        self.framerate = framerate
        self.ffmpeg_opts = ffmpeg_opts
        self.browser = None
        self.url = url
        self.out_file = out_file
        self.exit = False
        self.interactive = interactive
        self.duration = duration
        self.start_time = None
        self.random_ids()

    def random_ids(self):
        self.display_id = random.randint(100, 999)
        self.sink_id = 'webcap'+str(self.display_id)

    def start_xvfb(self):
        pc = f"Xvfb -listen tcp :{self.display_id} -screen 1 {self.x_res}x{self.y_res}x24"
        print('Starting Xvfb server:\n', pc)
        self.xvfb_process = subprocess.Popen(pc, shell = True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        time.sleep(1)
        if self.xvfb_process.returncode == None:
            print('Server started with id:', self.display_id)
        else:
            self.random_ids()
            self.start_xvfb()

    def create_sink(self):
        pc = f'pactl load-module module-null-sink sink_name={self.sink_id}'
        print('Creating new audio sink:\n',pc)
        self.sink_module_id = int(subprocess.check_output(pc, shell=True).decode().strip())
        print('Sync created with name:', self.sink_id, 'as id:', self.sink_module_id)

    def start_browser(self):
        print('Starting browser')
        os.environ["DISPLAY"] = f":{self.display_id}.1"
        fp = webdriver.FirefoxProfile()
        fp.set_preference("permissions.default.microphone", 1)
        fp.set_preference("permissions.default.camera", 1)
        self.browser = webdriver.Firefox(firefox_profile = fp)
        self.browser.set_window_size(self.x_res, self.y_res)
        self.browser.maximize_window()
        print('Browser started')


    def load_page(self):
        print('Loading page', self.url)
        self.browser.get(self.url)
        time.sleep(2)
        self.browser.fullscreen_window()
        time.sleep(1)

    def on_capture(self):
        if self.interactive:
            code.interact(local={'browser':self.browser})
        else:
            self.start_time = datetime.datetime.now()
            print('Press Ctrl-C to exit, or send SIGUSR1 to creating new file.')
            while not self.exit:
                time.sleep(1)
                if self.duration > 0 and (datetime.datetime.now() - self.start_time).seconds > self.duration:
                    break

    def change_audio_sink(self):
        sinks = subprocess.check_output(['pacmd', 'list-sink-inputs']).decode()
        sinks = sinks.split('\n')
        index_re = re.compile(r"\s+index:\s+([0-9]+)")
        pid_re = re.compile(r"\s+window.x11.display\s+=\s+\":([0-9]+)\.1\"")
        current_index = None
        current_display = None
        browser_sink_index = None
        for line in sinks:
            t = index_re.match(line)
            if t:
                current_index = int(t.group(1))
            t = pid_re.match(line)
            if t:
                current_display = int(t.group(1))
                if self.display_id == current_display:
                    browser_sink_index = current_index
                    break

        if browser_sink_index == None:
            print('Browser audio sink not found!')
        else:
            pc = f'pactl move-sink-input {browser_sink_index} {self.sink_id}'
            print('Moving browser to virtual device:\n', pc)
            os.system(pc)

    def start_capturing(self):
        print('Capturing into', self.out_file)
        pc = f"ffmpeg -y -f x11grab -video_size {self.x_res}x{self.y_res} -framerate {self.framerate} -i 127.0.0.1:{self.display_id}.1 -f pulse -i {self.sink_id}.monitor {self.ffmpeg_opts} {self.out_file}"
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
        time.sleep(3)
        self.start_xvfb()
        try:
            self.proc_sink()
        finally:
            self.stop_xvfb()
            time.sleep(1)

    def proc_sink(self):
        time.sleep(3)
        self.create_sink()
        try:
            self.proc_browser()
        finally:
            self.remove_sink()
            time.sleep(1)

    def proc_browser(self):
        time.sleep(3)
        self.start_browser()
        try:
            self.proc_page()
        finally:
            self.stop_browser()
            time.sleep(1)

    def proc_page(self):
        time.sleep(3)
        self.load_page()
        self.change_audio_sink()
        self.start_capturing()
        time.sleep(1)
        print('Capturing...')

        try:
            self.on_capture()
        finally:
            self.stop_capturing()
            time.sleep(1)

profiles = {'default':WebCap}

class JitsiCap(WebCap):

    def load_page(self):
        super().load_page()

        try:
            c = self.browser.find_element_by_name('displayName')
            c.send_keys('Record Bot')
            c.send_keys(webdriver.common.keys.Keys.ENTER)
        except NoSuchElementException:
            pass

        self.browser.find_element_by_xpath('/html/body').send_keys('w')
        time.sleep(1)

profiles['jitsi']=JitsiCap

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

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', "--profile", default='default', help="Web application profile to capture: "+str(list(profiles.keys())))
    parser.add_argument('-x', "--xres", type=int, default=1280, help="Virtual screen X")
    parser.add_argument('-y', "--yres", type=int, default=720, help="Virtual screen Y")
    parser.add_argument('-f', "--framerate", type=int, default=10, help="Capture frame rate")
    parser.add_argument('-i', "--interactive", action='store_true', default=False, help="Run interactive python console with browser object after starting capturing")
    parser.add_argument('-m', "--ffmpeg", default='', help="Additional ffmpeg arguments")
    parser.add_argument('-o', "--output", default='webcap.'+datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+'.mkv', help="Output file")
    parser.add_argument('-u', "--url", required=True, help="Target url")
    parser.add_argument('-d', "--duration", type=int, default=0, help="Capture duration in sec")

    args = parser.parse_args()

    cap_object = profiles[args.profile](x_res = args.xres,
                                        y_res = args.yres,
                                        framerate = args.framerate,
                                        ffmpeg_opts = args.ffmpeg,
                                        url = args.url,
                                        out_file = args.output,
                                        duration = args.duration,
                                        interactive = args.interactive)

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)
    signal.signal(signal.SIGUSR1, new_file_handler)

    cap_object.start()
