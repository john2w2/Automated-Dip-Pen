from serial import Serial

class Sola:
    def __init__(self, port="COM5"):
        self.box = Serial(port=port, baudrate=9600)


    def sendInit(self):
        self.box.write(b'\x57\x02\xff\x50')
        self.box.write(b'\x57\x02\xfd\x50')

    def enable(self):
            self.box.write(b'\x4f\x7d\x50')
    
    def disable(self):
            self.box.write(b'\x4f\x7f\x50')



    # TODO: this is good, move it into the class when we have it
    def setIntensity(self, val):
        if (val > 255 or val < 0): raise ValueError("badbabdabadbad!!!!!")
        inv = 255 - val # note, sola inverts intensity, so 0x00 is max while 0xFF is min
        upper = (inv//16) + 240  # need an F to prefix this
        lower = (inv%16) * 16   # need a 0 to follow this, so it's fine

        self.box.write(b'\x53\x18\x03\x04%b%b\x50' % (upper.to_bytes(1, 'big'), lower.to_bytes(1, 'big')))

    def close(self):
        # TODO: maybe disable signal before closing
        self.box.close()