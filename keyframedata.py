import struct
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class KeyframeData:
  def __init__(self, data):
    self.read_header(data[:16])

  def read_header(self, header):
    """ Specification Here: https://github.com/loldevs/leaguespec/wiki/Keyframe-Specification#keyframe-header """
    self.timestamp = struct.unpack("<f", header[1:5])[0]
    logger.info('Reading keyframe with timestamp %f' % self.timestamp)
