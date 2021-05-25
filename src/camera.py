import time
import picamera

TIME_FORMAT = '%Y-%b-%d %I:%M%p'

camera = picamera.PiCamera()

MAX_RESOLUTION = (3280, 2464)
HD_RESOLUTION = (1920, 1080)

def take_picture(stream, warmup = 2, format = 'jpeg'):
    camera.resolution = MAX_RESOLUTION
    camera.start_preview()
    camera.annotate_text = time.strftime(TIME_FORMAT)
    camera.annotate_background = picamera.Color('black')
    # Camera warm-up time
    time.sleep(warmup)
    camera.capture(stream, format)
    camera.stop_preview()
