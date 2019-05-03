import configparser
import datetime
import os
import re
import logging
import requests
import subprocess
import sys
import time

if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
from queue import Queue
from livestreamer import Livestreamer
from threading import Thread

config = configparser.ConfigParser()
config.read(sys.path[0] + "/config.conf")
log = logging.getLogger("ChaturbateRecorder")
log_level = str(config.get('settings', 'log_level'))
log.setLevel(log_level)
save_directory = config.get('paths', 'save_directory')
wishlist = config.get('paths', 'wishlist')
interval = int(config.get('settings', 'check_interval'))
genders = re.sub(' ', '', config.get('settings', 'genders')).split(",")
directory_structure = config.get('paths', 'directory_structure').lower()
post_processing_command = config.get('settings', 'post_processing_command')
post_processing_threads = None
try:
    post_processing_threads = int(config.get('settings', 'post_processing_threads'))
except ValueError:
    pass
completed_directory = config.get('paths', 'completed_directory').lower()

recording = []
wanted = []


def start_recording(model):
    global post_processing_command
    global processing_queue
    try:
        result = requests.get('https://chaturbate.com/api/chatvideocontext/{}/'.format(model)).json()
        session = Livestreamer()
        session.set_option('http-headers', "referer=https://www.chaturbate.com/{}".format(model))
        streams = session.streams("hlsvariant://{}".format(result['hls_source'].rsplit('?')[0]))
        stream = streams["best"]
        fd = stream.open()
        now = datetime.datetime.now()
        file_path = directory_structure \
            .format(path=save_directory,
                    model=model,
                    gender=result['broadcaster_gender'],
                    seconds=now.strftime("%S"),
                    minutes=now.strftime("%M"),
                    hour=now.strftime("%H"),
                    day=now.strftime("%d"),
                    month=now.strftime("%m"),
                    year=now.strftime("%Y"))
        directory = file_path.rsplit('/', 1)[0] + '/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        if model in recording:
            return
        with open(file_path, 'wb') as f:
            recording.append(model)
            while model in wanted:
                try:
                    data = fd.read(1024)
                    f.write(data)
                except Exception as e:
                    log.info(e)  # stop recording
                    f.close()
                    break
        if post_processing_command:
            processing_queue.put({'model': model, 'path': file_path, 'gender': gender})
        elif completed_directory:
            finished_dir = completed_directory \
                .format(path=save_directory,
                        model=model,
                        gender=gender,
                        seconds=now.strftime("%S"),
                        minutes=now.strftime("%M"),
                        hour=now.strftime("%H"),
                        day=now.strftime("%d"),
                        month=now.strftime("%m"),
                        year=now.strftime("%Y"))
            if not os.path.exists(finished_dir):
                os.makedirs(finished_dir)
            os.rename(file_path, finished_dir + '/' + file_path.rsplit['/', 1][0])
    except Exception as e:
        log.warning(e)
        pass
    finally:
        if model in recording:
            recording.remove(model)


def post_process():
    global processing_queue
    global post_processing_command
    while True:
        while processing_queue.empty():
            time.sleep(1)
        parameters = processing_queue.get()
        model = parameters['model']
        path = parameters['path']
        filename = path.rsplit('/', 1)[1]
        gender = parameters['gender']
        directory = path.rsplit('/', 1)[0] + '/'
        subprocess.run(post_processing_command.split() + [path, filename, directory, model, gender])


def get_online_models():
    online = []
    global wanted
    for gender in genders:
        try:
            data = {'categories': gender, 'num': 127}
            result = requests.post("https://roomlister.stream.highwebmedia.com/session/start/", data=data).json()
            length = len(result['rooms'])
            online.extend([m['username'].lower() for m in result['rooms']])
            data['key'] = result['key']
            while length == 127:
                result = requests.post("https://roomlister.stream.highwebmedia.com/session/next/", data=data).json()
                length = len(result['rooms'])
                data['key'] = result['key']
                online.extend([m['username'].lower() for m in result['rooms']])
        except Exception as e:
            log.warning(e)  # failed to fetch online models
            break
    f = open(wishlist, 'r')
    wanted = list(set(f.readlines()))
    wanted = [m.strip('\n').split('chaturbate.com/')[-1].lower().strip().replace('/', '') for m in wanted]
    # wanted_models = list(set(wanted).intersection(online).difference(recording))
    '''new method for building list - testing issue #19 yet again'''
    wanted_models = [m for m in (list(set(wanted))) if m in online and m not in recording]
    for model in wanted_models:
        thread = Thread(target=start_recording, args=(model,))
        thread.start()
    f.close()


def log_recording():
    log.info("{} model(s) are being recorded. Refreshing online model list now".format(len(recording)))
    log.info("Recording the following models : {}".format(recording))


def console_log():
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)


if __name__ == '__main__':
    console_log()
    allowed_genders = ['female', 'male', 'trans', 'couple']
    for gender in genders:
        if gender.lower() not in allowed_genders:
            log.error("{} is not an acceptable gender, options are: female, male, trans, & couple".format(gender))
            exit()
    genders = [a.lower()[0] for a in genders]
    if post_processing_command != "":
        processing_queue = Queue()
        post_processing_workers = []
        for i in range(0, post_processing_threads):
            t = Thread(target=post_process)
            post_processing_workers.append(t)
            t.start()
    while True:
        log_recording()
        get_online_models()
        for i in range(interval, 0, -1):
            time.sleep(1)
