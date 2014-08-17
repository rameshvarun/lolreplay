import struct
import json
from cStringIO import StringIO
import os
import logging
import base64
import gzip

from Crypto.Cipher import Blowfish


'''
The code for this module was strongly based on the following ruby
script by https://github.com/robertabcd
Script Link: https://github.com/robertabcd/lol-ob/blob/master/lrf.rb
'''

'''
PKCS5 padding formula, from
https://gist.github.com/crmccreary/5610068
'''
unpad = lambda s : s[0:-ord(s[-1])]


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

    # Cipher required to decrypt data
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
  def __init__(self, file, cipher):

    self.type = file.read(1).encode("hex")
    self.size = struct.unpack("<L", file.read(4))[0]

    if self.type != '4e':
      raise Exception("Unkown stream type 0x%s" % self.type)

    # Calculate the position of the end of this stream
    stream_end = file.tell() + self.size - 5

    payload_size = struct.unpack("<L", file.read(4))[0]
    assert (payload_size + 4) == (self.size - 5)

    # Read segments until the stream is over
    while file.tell() < stream_end:
      request = self.read_segment(file)
      response = self.read_segment(file)

      print request

      if "getGameDataChunk" in request or "getKeyFrame" in request:
        decrypted = unpad(cipher.decrypt(response))
        gzip_input = StringIO(decrypted)

        gzip_file = gzip.GzipFile(fileobj=gzip_input)
        unzipped = gzip_file.read()
        print unzipped

  def read_segment(self, file):
    unk0, segment_size = struct.unpack("<LL", file.read(8))
    segment = file.read(segment_size)

    ''' Every segment ends with a newline character. This helps make
    sure we haven't read garbage binary and jumped somwhere'''
    magic = file.read(1).encode("hex")
    if magic != '0a':
      raise Exception("Magic error: expected 0x0a got 0x%s" % magic)

    return segment

LRFFile("test.lrf")
