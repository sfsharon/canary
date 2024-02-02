"""
Monitor log file script.
Meant to work inside the DUT, therefore code fits with python2
"""

import pyinotify
import sys

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

def monitor_file (input_file, output_file) :
    """
    Monitor input_file. If updated, write updates to output_file    
    """
    # Create a new watch manager
    wm = pyinotify.WatchManager()

    # Set up the event handler
    handler = MyEventHandler(input_file, output_file)

    # Create a notifier
    notifier = pyinotify.Notifier(wm, handler)

    # Add the file to be monitored
    wm.add_watch(input_file, pyinotify.IN_MODIFY)

    # Start the notifier
    notifier.loop()

if __name__ == "__main__" :
    input_file = '/vbox/lc_image/root/var/log/bcmrm_bsl_trace_buffer.trace'
    output_file = '/root/workspace/bcmrm_bsl_trace_buffer.trace'
    monitor_file(input_file, output_file)
