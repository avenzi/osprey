import time
import threading
from app import app
from app import mysql

rewind = False

try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident


class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                if now - event[1] > 5:
                    remove = ident
        if remove:
            del self.events[remove]

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        self.events[get_ident()][0].clear()


class BaseCamera(object):
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera
    event = CameraEvent()

    def initialize_base_camera(self):
        """Start the background camera thread if it isn't running yet."""
        if self.thread is None:
            self.last_access = time.time()

            # start background frame thread
            self.thread = threading.Thread(target=self._thread)
            self.thread.start()

            # wait until frames are available
            while self.get_frame() is None:
                time.sleep(0)

    def get_frame(self):
        """Return the current camera frame."""
        self.last_access = time.time()

        # wait for a signal from the camera thread
        self.event.wait()
        self.event.clear()

        return self.frame

    def frames(self):
        """"Generator that returns frames from the camera."""
        raise RuntimeError('Must be implemented by subclasses.')

    def _thread(self):
        """Camera background thread."""
        #print('Starting a camera thread.')
        frames_iterator = self.frames()
        for frame in frames_iterator:
            self.frame = frame
            self.event.set()  # send signal to clients
            time.sleep(0)

            # if there hasn't been any clients asking for frames in
            # the last 10 seconds then stop the thread
            if time.time() - self.last_access > 1000:
                frames_iterator.close()
                print('Stopping camera thread due to inactivity.')
                break
        self.thread = None


class Camera(BaseCamera):
    def __init__(self, session_id, rewinding):
        print("Created Camera with session_id: ", session_id)
        self.session_id = session_id
        self.rewinding = rewinding
        self.initialize_base_camera()

    """An emulated camera implementation that streams a repeated sequence of
    files 1.jpg, 2.jpg and 3.jpg at a rate of one frame per second."""
    #imgs = [open("/root/capstone-site/site/static/video/" + str(f) + '.jpg', 'rb').read() for f in range(1000)]
    
    def frames(self):
        self.rewind_index = 1
        if self.rewinding == True:
            with app.app_context():
                database_cursor = mysql.connection.cursor()
                print("sd: ", self.session_id)
                database_cursor.execute("""SELECT Frame FROM VideoFrame WHERE SessionId = %s ORDER BY FRAME DESC LIMIT 1""",
                    (str(self.session_id),))
                result = database_cursor.fetchone()
                self.max_rewind_index = result[0]
        
        last_sent = -1

        while True:
            time.sleep(0.05) # 30 FPS

            print("Camera.session_id: ", self.session_id)

            successful_read = False
            while (not successful_read):
                with app.app_context():
                    database_cursor = mysql.connection.cursor()
                    # Get the latest Frame from the latest Session id
                    if self.rewinding == False:
                        if self.session_id != -1: # for now, -1 is live streaming (change later)
                            database_cursor.execute("""SELECT id, Path FROM VideoFrame WHERE SessionId = %s ORDER BY Frame DESC LIMIT 10, 1;""",
                                (str(self.session_id),))
                        else:
                            # live feed page
                            print("Live feeding")
                            database_cursor.execute("""SELECT id, Path FROM VideoFrame WHERE SessionId = (SELECT MAX(Session.id) FROM Session) ORDER BY Frame DESC LIMIT 10, 1;""")
                    else: # Rewinding
                        database_cursor.execute("SELECT id, Path FROM VideoFrame WHERE SessionId = %s AND Frame = %s LIMIT 1",
                            (str(self.session_id), str(self.rewind_index)))
                    result = database_cursor.fetchone()
                    print(result)
                    if result != None:
                        filepath = result[1]
                        id = result[0]
                        #print("filepath: ", filepath)

                        if last_sent == id:
                            time.sleep(0.1)
                            continue

                        try:
                            image = open(filepath, 'rb').read()
                            last_sent = id
                            successful_read = True
                        except Exception as e:
                            print("Exception caught: ", e)
                            time.sleep(0.25)
                    else:
                        time.sleep(0.10)
                        print("DB result is NULL")

                        #database_cursor.execute()

                    # https://www.w3schools.com/python/python_mysql_select.asp

                    #mysql.connection.commit()

                    #try:
                    #    image = open("/root/capstone-site/app/static/video/" + str(index) + '.jpg', 'rb').read()
                    #    successful_read = True
                    #except Exception as e:
                    #    print("Exception caught: ", e)

            yield image

            if self.rewinding == True:
                self.rewind_index = self.rewind_index + 1
                if self.rewind_index > self.max_rewind_index:
                    self.rewind_index = 1

def gen(camera):
    """Video streaming generator function."""
    while True:
        print("Retrieving frame")
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')