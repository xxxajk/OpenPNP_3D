#!/usr/bin/env python3

try:
        import threading
        import cv2
        import numpy as np
        import socket
        import struct
        import time
        import sys
        import os
        import fcntl
        import v4l2
        import gc
        import tty
        import termios
        import pigpio
        import traceback
except:
        sys.exit(1)


MAX_DGRAM = 2**16

img = None

def dump_buffer(s):
        """ Emptying buffer frame """
        while True:
                seg, addr = s.recvfrom(MAX_DGRAM)
                #print(seg[0])
                count, packets, pp = struct.unpack("BBB", seg[0:3])
                #if struct.unpack("B", seg[0:1])[0] == 1:
                #print("finish emptying buffer")
                if count == 1:
                        break
        pp += 1
        if pp > 255:
                pp = 0
        return pp


#struct.pack("<cL")
# x for x rez
# y for y rez
# r for frame rate
# a for rotation angle
# 

class UDPv4l2 (threading.Thread):
        def __init__(self, daddr, dport, port, viddev, xres, yres, rate, angle):
                threading.Thread.__init__(self)
                self.going = False
                self.daddr = daddr
                self.dport = dport
                self.port = port
                self.viddev = viddev
                self.xres = xres
                self.yres = yres
                self.rate = rate
                self.angle = angle
                self.s = None
                self.pi = None
                self.I2C = -1
                self.device = None
                self.packs=[b'' for q in range(256)]
                self.dropped = 0
                self.total = 0
                self.currentshape = None
                self.focal_distance = 0
        
        def get_focus(self):
                return self.focal_distance

        def sendparams(self, key, val):
                self.s.sendto(struct.pack("<cL", key, val), (self.daddr, self.dport))
        
        # Note: this uses pigpio
        def set_focus(self, val):
                if val < 0:
                        val = 0
                if val > 1023:
                        val = 1023
                self.focal_distance = val
                if self.I2C > 0:
                        value = (val << 4) & 0x3ff0
                        data1 = (value >> 8) & 0x3f
                        data2 = value & 0xf0
                        while 1:
                                try:
                                        print("")
                                        print("focus: {}".format(val))
                                        self.pi.i2c_write_device(self.I2C, [data1, data2])
                                        break
                                except:
                                        pass
                
        def set_xrez(self, val):
                self.sendparams(b'x', val)

        def set_yrez(self, val):
                self.sendparams(b'y', val)

        def set_fps(self, val):
                self.sendparams(b'r', val)

        def set_rotation(self, val):
                self.sendparams(b'a', val)
        
        def set_stream_on(self):
                self.sendparams(b's',0)
        
        def set_stream_off(self):
                self.sendparams(b'q',0)
        
        def ping_cam(self):
                self.sendparams(b'p',0)

        def run(self):
                self.going = True
                self.s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                self.s.bind(('', self.port))
                self.device=open(self.viddev, 'wb')
                self.pi=pigpio.pi(self.daddr)
                self.I2C=self.pi.i2c_open(0, 0x0c)
                self.set_xrez(self.xres)
                self.set_yrez(self.yres)
                self.set_fps(self.rate)
                self.set_rotation(self.angle)
                self.set_xrez(self.xres)
                self.set_yrez(self.yres)
                self.set_fps(self.rate)
                self.set_rotation(self.angle)
                self.ping_cam()
                self.set_focus(self.focal_distance)
                # start streaming
                self.set_stream_on()
                cp = dump_buffer(self.s)
                prev_frame_time = time.time()
                self.going = True
                print("going...")
                try:
                        while self.going:
                                seg, addr = self.s.recvfrom(MAX_DGRAM)
                                count, packets, pp = struct.unpack("BBB", seg[0:3])
                                if count == packets:
                                        cp = pp
                                        packs=[b'' for q in range(packets)]
                                if cp != pp:
                                        cp = pp
                                        packs=[b'' for q in range(packets)]
                                        self.dropped += 1
                                        print(" Dropped: {} Total: {}".format(self.dropped, self.total), end='\r', flush=True)
                                packs[packets-count] = seg[3:]
                                if not (b'' in packs):
                                        dat = b''.join(packs)
                                        new_frame_time = time.time()
                                        fps = str(int(1/(new_frame_time-prev_frame_time)))
                                        prev_frame_time = new_frame_time
                                        img = cv2.imdecode(np.frombuffer(dat, dtype=np.uint8), 1)
                                        cv2.putText(img,fps, (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)
                                        if img.shape != self.currentshape:
                                                self.device.close()
                                                self.device = open(self.viddev, 'wb')
                                                self.currentshape = img.shape
                                                height, width, channels = img.shape
                                                format = v4l2.v4l2_format()
                                                format.type = v4l2.V4L2_BUF_TYPE_VIDEO_OUTPUT
                                                format.fmt.pix.field = v4l2.V4L2_FIELD_NONE
                                                format.fmt.pix.pixelformat = v4l2.V4L2_PIX_FMT_BGR24
                                                format.fmt.pix.width = width
                                                format.fmt.pix.height = height
                                                format.fmt.pix.bytesperline = width * channels
                                                format.fmt.pix.sizeimage    = width * height * channels
                                                fcntl.ioctl(self.device, v4l2.VIDIOC_S_FMT, format)
                                        self.device.write(img)
                                        dat = b''
                                        packs=[b'' for q in range(256)]
                                        cp += 1
                                        self.total += 1
                                        print(" Dropped: {} Total: {}".format(self.dropped, self.total), end='\r', flush=True)
                finally:
                        self.set_stream_off()
                        self.s.close()
                        self.device.close()

        def death(self):
                self.going = False

class raw(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()
    def __enter__(self):
        self.original_stty = termios.tcgetattr(self.stream)
        tty.setcbreak(self.stream)
    def __exit__(self, type, value, traceback):
        termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)

class nonblocking(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()
    def __enter__(self):
        self.orig_fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)
    def __exit__(self, *args):
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl)


if __name__ == "__main__":
        x = 1024
        y = 768
        fps = 30
        rotate = 0
        cam0 = UDPv4l2('fd00:f00d:dead:beef::1', 12345, 12346, '/dev/video0', x, y, fps, rotate)
        cam0.start()
        tick = 0.0
        try:
                with raw(sys.stdin):
                        with nonblocking(sys.stdin):
                                while True:
                                        c = sys.stdin.read(1)
                                        if c == 'a':
                                                cam0.set_focus(cam0.get_focus()+16)
                                        elif c == 'z':
                                                cam0.set_focus(cam0.get_focus()-16)
                                        time.sleep(0.1)
                                        tick += 0.1
                                        if tick > 0.9:
                                                tick = 0.0
                                                cam0.ping_cam()
        finally:
                cam0.death()
                cam0.join()
