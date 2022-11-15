import serial

class SolaEngine:
    """
    A SolaEngine controls the sola light engine box,
    which emits a light at varying, controllable intensities

    It connects to the device using a serial connection, the port
    of which must be determined by the client

    For the implementer: ALl commands consist of a series of bytes
    
    They are documented in: 
    https://cms.lumencor.com/system/uploads/fae/file/asset/151/57-10028_SOLA_Command_Reference.pdf?_gl=1*5rcb2s*_ga*OTQwMzMwMTMuMTY2NTAwMzEwMA..*_ga_364GJZVK77*MTY2ODU1MDk5MC4zLjAuMTY2ODU1MDk5Ny41My4wLjA.
    """
    def __init__(self, comport: str):
        """
        Create a new SolaEngine instance
        Note: does not connect to the engine's serial port

        :param comport: The string indicating the comport
                        the engine is tied to
        :type comport: str
        """
        # initalize members
        self.comport = comport
        self.serialConnection = None

    def connect(self):
        """
        connects to the light engine, reservering its serial port 

        :raises ConnectionError: If the connection with the specified
        serial port is unable to be connected to
        """
        try:
            self.serialConnection = \
                serial.Serial(port=self.comport, baudrate=9600)

            self.sendInitCode()
        except serial.SerialException as e:
            print(e)
            raise(ConnectionError("Could not connect to the sola engine"))

    def changePort(self, port:str):
        """
        Changes which port the engine will try to connect
        to. This does not attempt to connect to the serial
        port, nor does it check if the new serial port
        is accessible. The new connection must be opened with 
        'connect()' 
        
        The engine must not have an open connection,
        or an error will be thrown

        :param port: string of the form "COM{X}" 
        :type port: str
        :raises ValueError: If the engine has an open connection
        to its current serial port
        """
        if self.serialConnection!= None and self.serialConnection.open():
            raise ValueError("Cannot change port due to open connection\n"
                            f"please close the connection to {self.comport} first")
        # otherwise, our connection is either closed or doesn't exist
        self.comport = port

    def sendInitCode(self):
        """
        Sends the initializer commands to the light engine. This step
        is required after every power cycle to properly configure the 
        engine for commands 

        Requires: serial port is open 
        Raises: ValueError if the serial port is not open
        """
        self.__assertSerialOpen()

        # Sends the bytes to enable the box
        # setup GIO0-3
        self.serialConnection.write(b'\x57\x02\xff\x50')
        # setup GIO5-7
        self.serialConnection.write(b'\x57\x03\xfd\x50')

    def toggleOn(self):
        """
        Enables the light to shine, shining at its previously
        set intensity

        Raises: ValueError if the serial port is not open
        """
        self.__assertSerialOpen()
        # 4F 7D 50 = enabled
        self.serialConnection.write(b'\x4f\x7d\x50')
    
    def toggleOff(self):
        """
        Disables the light, which can be reenabled
        with toggleOn()

        Raises: ValueError if the serial port is not open
        """
        self.__assertSerialOpen()
        # 4F 7f 50 = disabled
        self.serialConnection.write(b'\x4f\x7f\x50')

    def setIntensity(self, val: int):
        """
        :param val: The desired intensity to set the light to
        :type val: The intensity to set the light to in [0,255]
                    if the value is to large, it it clipped to 255.
                    if it is too small, it is clipped to 0
        
        Raises: ValueError if the serial port is not open
        """
        self.__assertSerialOpen()

        # clip val
        if val > 255: val = 255
        elif val < 0: val = 0

        # note, sola inverts intensity, so 0x00 is max while 0xFF is min
        inv: int = 255 - val

        # convert the desired intesity to hex
        upper: int = (inv//16) + 240  # The value of the upper byte
        lower: int = (inv%16) * 16    # The value of the lower byte
        
        # Write the command
        self.serialConnection.write(b'\x53\x18\x03\x04%b%b\x50' % 
                  (upper.to_bytes(1, 'big'), lower.to_bytes(1, 'big')))

    def close(self):
        """
        Closes the engine's serial connection.
        If there is no connection, this function
        does nothing
        """
        if self.serialConnection != None:
            self.serialConnection.close()

    def __assertSerialOpen(self):
        """
        Checks if the serial port is open, raising
        a ValueError if not 

        :raises ValueError: if the port isn't open
        """
        if self.serialConnection == None or \
            not self.serialConnection.isOpen():
            raise ValueError("Serial Port is in invalid state, cannot be initialized")