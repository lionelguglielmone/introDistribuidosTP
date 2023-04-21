
import ctypes
import struct

from lib.constant import SelectedProtocol, SelectedTransferType


class ApplicationHeaderRDT():

    MAX_FILE_NAME = 40
    PACKET_FORMAT = '!BB40sI20s'

    def __init__(self, transfer_type: SelectedTransferType,
                 protocol: SelectedProtocol,
                 file_name: str, file_size, sha1_hash):
        self.transfer_type: ctypes.c_uint8 = transfer_type
        self.protocol: ctypes.c_uint8 = protocol
        self.file_name: str = file_name
        self.file_size: ctypes.c_uint32 = file_size
        self.sha1_hash = sha1_hash

    def equals(self, app_header: 'ApplicationHeaderRDT'):
        return self.transfer_type == app_header.transfer_type and \
            self.protocol == app_header.protocol and \
            self.file_name == app_header.file_name and \
            self.file_size == app_header.file_size and \
            self.sha1_hash == app_header.sha1_hash

    @classmethod
    def size(cls):
        return struct.calcsize(cls.PACKET_FORMAT)

    def as_bytes(self):
        return struct.pack(self.PACKET_FORMAT, self.transfer_type,
                           self.protocol, self.file_name.encode('utf-8'),
                           self.file_size, self.sha1_hash)

    @classmethod
    def from_bytes(cls, data):
        transfer_type, protocol, file_name, file_size, sha1_hash = \
            struct.unpack(
                cls.PACKET_FORMAT, data
            )
        file_name = file_name.decode('utf-8').strip('\x00')
        return cls(transfer_type, protocol, file_name, file_size, sha1_hash)

    # TODO: agregar un método para que se cree a partir de un TransferInformation