import unittest
import unittest.mock as mock

import sys
sys.path.append('src')  # so we can load in deviceInterfaces....

from src.orcaFlash import OrcaFlashV2, DEFAULT_EXPOSURE

MMPATH = "C:\\Program Files\\Micro-Manager-2.0"
ORCACONFIG = "MMConfig_ham.cfg"

class OrcaFlashTests(unittest.TestCase):

    """
    Test that initializing an orcaflash object doesn't
    immediately connect to mmcore, also that it 
    isn't initially snapping or connected
    """
    def test_init(self):
        of = OrcaFlashV2()
        self.assertEqual(of.mm_path, MMPATH)
        self.assertEqual(of.configPath, ORCACONFIG)

        self.assertFalse(of.is_acquiring())

        self.assertFalse(of.is_connected())

    @mock.patch('src.orcaFlash.CMMCorePlus')
    def test_connection(self, mock_mmcore):
        """
        Test that the orcaflash attempts to connect to
        mmcore
        """
        of = OrcaFlashV2()
        of.connect()

        mock_mmcore.instance.assert_called_with(
            mm_path=MMPATH
        )

        of.mmc.loadSystemConfiguration.assert_called_with(
            fileName=ORCACONFIG
        )

    @mock.patch('src.orcaFlash.CMMCorePlus')
    def test_exposure(self, mock_mmcore):
        """
        Test that exposure behaves properly
        """
        of = OrcaFlashV2()
        of.connect()

        of.mmc.setExposure.assert_called_with(DEFAULT_EXPOSURE)
        of.set_exposure(-100)
        of.mmc.setExposure.assert_called_with(0.0)
        of.set_exposure(1234)
        of.mmc.setExposure.assert_called_with(1234)
