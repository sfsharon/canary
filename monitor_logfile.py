import pyinotify
import sys

INPUT_FILE  = sys.argv[1]
OUTPUT_FILE = sys.argv[2]

class MyEventHandler(pyinotify.ProcessEvent):
    def __init__(self, input_pathname, output_pathname ) :
        f = open(input_pathname, 'r')
        f.seek(0,2)
        self.file_size = f.tell()
        self.output_file = output_pathname

        print "File size :", self.file_size

    def process_IN_MODIFY(self, event):
        with open(event.pathname, 'r') as f_in:
            f_in.seek(self.file_size, 0)
            # Read the newly added lines
            new_lines = f_in.readlines()
            self.file_size = f_in.tell()
            with open(self.output_file, 'w') as f_out:
                # Do something with the new lines
                for line in new_lines:
                    #print "new line: ", line.strip()
                    f_out.write(line)

# Create a new watch manager
wm = pyinotify.WatchManager()

# Set up the event handler
handler = MyEventHandler(INPUT_FILE, OUTPUT_FILE)

# Create a notifier
notifier = pyinotify.Notifier(wm, handler)

# Add the file to be monitored
#wm.add_watch('/path/to/my/file', pyinotify.IN_MODIFY)
wm.add_watch(INPUT_FILE, pyinotify.IN_MODIFY)

# Start the notifier
notifier.loop()
