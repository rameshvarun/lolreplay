import struct
import json
from cStringIO import StringIO
import os
import logging
import base64
import gzip

from keyframedata import KeyframeData
from chunkdata import ChunkData

from Crypto.Cipher import Blowfish

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

"""
The code for this module was strongly based on the following ruby
script by https://github.com/robertabcd
Script Link: https://github.com/robertabcd/lol-ob/blob/master/lrf.rb
"""

def unpad(s):
  """
  PKCS5 padding formula, from
  https://gist.github.com/crmccreary/5610068
  The padding is used during to ensure that a byte sequence
  is a multiple of 8. Because the original data has been padded
  we must unpad
  """
  return s[0:-ord(s[-1])]


class LRFFile:
  """Class that can be used to parse the information in a .lrf replay file"""

  def __init__(self, filename):
    # Open file in read-binary mode
    self.file = open(filename, "rb")

    '''For portability concerns, all the binary data is stored in
    little endian format'''

    # First four bytes are version number, second four bytes are meta data size
    self.version, self.meta_size = struct.unpack("<LL", self.file.read(8))

    # Meta data is a large json
    self.metadata = json.loads(self.file.read(self.meta_size))
    self.gameid = self.metadata['matchID']

    '''
    To get the actual encryption key, you must decrypt the given
    encryptionKey, using the gameID as a key. Then, this cipher is
    used to decrypt chunk and keyframe data
    '''
    self.encryptedKey = base64.b64decode(self.metadata['encryptionKey'])

    gameidCipher = Blowfish.new(str(self.gameid), Blowfish.MODE_ECB)
    self.key = unpad(gameidCipher.decrypt(self.encryptedKey))
    self.cipher = Blowfish.new(self.key, Blowfish.MODE_ECB)

    # Store the current position as where the data section starts
    data_offset = self.file.tell()

    # Iterate through all of the "parts" in the data
    self.parts = {}
    for index in self.metadata["dataIndex"]:
      key = index['Key']
      offset = index['Value']['offset']
      size = index['Value']['size']

      self.file.seek(data_offset + offset)
      if key == "stream":
        self.parts[key] = LRFStream(self.file, self.cipher)
      else:
        raise Exception("Unkown key %s in dataIndex list." % key)

class LRFStream:
  """Represents a single stream of data in a .lrf file"""

  def __init__(self, file, cipher):

    # First byte is the type, next four bytes are the size
    self.type = file.read(1).encode("hex")
    self.size = struct.unpack("<L", file.read(4))[0]

    # The only stream type we know how to decode
    if self.type != '4e':
      raise Exception("Unkown stream type 0x%s" % self.type)

    # Calculate the position of the end of this stream
    stream_end = file.tell() + self.size - 5

    payload_size = struct.unpack("<L", file.read(4))[0]
    assert (payload_size + 4) == (self.size - 5)

    # Read segments until the stream is over
    while file.tell() < stream_end:
      request = self.read_segment(file) # The url that was sent to the server
      response = self.read_segment(file) # The response that the server sent back

      if "getGameDataChunk" in request or "getKeyFrame" in request:
        # Decrypt the data
        decrypted = unpad(cipher.decrypt(response))

        # Unzip the data as a gzip file
        gzip_input = StringIO(decrypted)
        gzip_file = gzip.GzipFile(fileobj=gzip_input)
        unzipped = gzip_file.read()

        if "getGameDataChunk" in request:
          response = ChunkData(unzipped)
        elif "getKeyFrame" in request:
          response = KeyframeData(unzipped)


  def read_segment(self, file):
    """Reads one segment of a string"""

    unk0, segment_size = struct.unpack("<LL", file.read(8))
    segment = file.read(segment_size)

    ''' Every segment ends with a newline character. This helps make
    sure we haven't read garbage binary and jumped somwhere'''
    magic = file.read(1).encode("hex")
    if magic != '0a':
      raise Exception("Magic error: expected 0x0a got 0x%s" % magic)

    return segment

if __name__ == "__main__":
  # create console handler and set level to debug
  ch = logging.StreamHandler()
  ch.setLevel(logging.DEBUG)

  # create formatter
  formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  # add formatter to ch
  ch.setFormatter(formatter)

  # Add this handler to the loggers
  logging.getLogger("keyframedata").addHandler(ch)
  logging.getLogger("__main__").addHandler(ch)
  logging.getLogger("chunkdata").addHandler(ch)

  LRFFile("test.lrf")
