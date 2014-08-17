import struct
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ChunkData:
  def __init__(self, data):
    self.read_header(data[:5])

    print data.encode('hex')
    #quit()

  def read_header(self, header):
    """Specification here: https://github.com/loldevs/leaguespec/wiki/Chunk-Specification#header"""
    AA = header[0].encode('hex') # Is either 03 or 04

    self.timestamp = struct.unpack("<f", header[1:])[0]
    logger.info('Reading chunk with timestamp %f' % self.timestamp)
