import unittest
import unittest.mock as mock
import src.sola as sola
from serial import SerialException


class TestSolaMethods(unittest.TestCase):

    # replaces the actual serial class in 
    # src.sola with this mock version,
    # so we can check if things were called correctly
    @mock.patch('src.sola.serial')
    def test_connection(self, mock_serial):
        sol = sola.SolaEngine("COM5")
        self.assertEqual(sol.serialConnection, None)
        sol.connect()
        mock_serial.Serial.assert_called_with(port="COM5", baudrate=9600)
        
    @mock.patch('src.sola.serial')
    def test_ConnectRaisesException(self, mock_serial):
        mock_serial.Serial = mock.Mock(side_effect=Exception)
        sol = sola.SolaEngine("COM5")

        with self.assertRaises(Exception) as _:
            sol.connect()