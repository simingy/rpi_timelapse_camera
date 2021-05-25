import os
import time
import logging
import argparse
import datetime
from io import BytesIO

from upload import GooglePhotos
from camera import take_picture, TIME_FORMAT

logger = logging.getLogger(__name__)

FILENAME_FORMAT = '%Y-%b-%dT%I:%M%p.jpg'
START_WORK = 7 # 7am
END_WORK = 20 # 8pm

HERE = os.path.dirname(__file__)

def time_until(next_timeslot):
    delta = next_timeslot - datetime.datetime.now()
    return delta - datetime.timedelta(microseconds=delta.microseconds)

def get_next_timeslot(minutes):
    now = datetime.datetime.now()
    
    start_today = now.replace(hour=START_WORK, 
                              minute=0, 
                              second=0, 
                              microsecond=0)
    end_today = now.replace(hour=END_WORK, 
                            minute=0, 
                            second=0, 
                            microsecond=0)
    if not (start_today <= now < end_today):
        # move to next day
        next_target = now + datetime.timedelta(days=1)
        next_target = next_target.replace(hour=START_WORK, 
                                          minute=0, 
                                          second=0, 
                                          microsecond=0)
        return next_target

    delta = datetime.timedelta(minutes=minutes)
    return now + (datetime.datetime.min - now) % delta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--elapse', type=int, 
                        default=30, help='minutes to wait between shots')
    parser.add_argument('--secret', type=str, default='client_secret.json')
    parser.add_argument('--album', type=str, default='', 
                        help='album to save to')
    parser.add_argument('-v', '--verbose',
                              dest='verbose',
                              action='count',
                              default=0,
                              help='Give more output, additive up to 3 times.')
    parser.add_argument('-q', '--quiet',
                              dest='quiet',
                              action='count',
                              default=0,
                              help='Give less output, additive up to 3 times, '
                              'corresponding to WARNING, ERROR, and CRITICAL '
                              'logging levels')

    args = parser.parse_args()
    
    verbosity = args.verbose - args.quiet

    # compute verbosity
    if verbosity >= 1:
        loglevel = logging.DEBUG
    elif verbosity == -1:
        loglevel = logging.WARNING
    elif verbosity == -2:
        loglevel = logging.ERROR
    elif verbosity <= -3:
        loglevel = logging.CRITICAL
    else:
        loglevel = logging.INFO

    # configure logger
    logging.basicConfig(level=loglevel)

    # login
    gp = GooglePhotos(args.secret)

    # find the desired album
    albums = gp.get_albums()
    
    if args.album:
        if args.album not in albums:
            album = gp.create_album(args.album)
        else:
            album = albums[args.album]
    else:
        album = None
        
    while True:
        # take snapshot
        buffer = BytesIO()
        filename = time.strftime(FILENAME_FORMAT)
        take_picture(stream = buffer)
        
        # go back to beginning so uploader reads it all
        buffer.seek(0)

        try:
            gp.upload_photo(album, filename, buffer)
        except Exception:
            # write to file in case i still want it
            with open(os.path.join(HERE, 'photos', filename), 'wb') as f:
                buffer.seek(0)
                f.write(buffer.read())

        # set next target
        next_timeslot = get_next_timeslot(args.elapse)
        logger.info('Next capture: %s' % next_timeslot.strftime(TIME_FORMAT))

        while datetime.datetime.now() < next_timeslot:
            delta = (next_timeslot - datetime.datetime.now()).total_seconds()
            if delta > 5:
                sleeptime = round(delta/2,2)
            else:
                sleeptime = 1

            logger.info('Time until next picture: %s, sleeping - %ss' 
                        % (time_until(next_timeslot),sleeptime))
            time.sleep(sleeptime)

if __name__ == '__main__':
    main()