
from itertools import count


class ConsoleTraceLog(object):

    def __init__(self):
        self.counter = count(start=1, step=1)

    def trace_order_seq(self):
        return next(self.counter)

    def send_trace_message(self, message):
        print(message)


class FileSystemTraceLog(object):

    def __init__(self, log_file):
        self.counter = count(start=1, step=1)
        self.log_file = open(log_file, 'ab', buffering=0)

    def trace_order_seq(self):
        return next(self.counter)

    def send_trace_message(self, message):
        self.log_file.write(repr(message).encode())
        self.log_file.write(b'\n')
