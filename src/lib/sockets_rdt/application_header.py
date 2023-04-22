
import ctypes
import struct

from lib.constant import SelectedTransferType
from crc import Calculator, Crc8


calculator = Calculator(Crc8.CCITT, optimized=True)


class ApplicationHeaderRDT():

    MAX_FILE_NAME = 40
    PACKET_FORMAT = '!B40sIB'

    CHECKSUM_SIZE = 1

    def __init__(self, transfer_type: SelectedTransferType,
                 file_name: str, file_size):
        self.transfer_type: ctypes.c_uint8 = transfer_type
        self.file_name: str = file_name
        self.file_size: ctypes.c_uint32 = file_size
        self.data_checksum: ctypes.c_uint8 = None
        self.header_checksum: ctypes.c_uint8 = None

    def equals(self, app_header: 'ApplicationHeaderRDT'):
        return self.transfer_type == app_header.transfer_type and \
            self.file_name == app_header.file_name and \
            self.file_size == app_header.file_size and \
            self.data_checksum == app_header.data_checksum and \
            self.header_checksum == app_header.header_checksum

    @classmethod
    def size(cls):
        return struct.calcsize(cls.PACKET_FORMAT) + cls.CHECKSUM_SIZE

    def as_bytes(self):
        packed_bytes = struct.pack(self.PACKET_FORMAT, self.transfer_type,
                                   self.file_name.encode('utf-8'),
                                   self.file_size, self.data_checksum)
        self.checksum = calculator.checksum(packed_bytes).to_bytes(
            1, byteorder='big'
        )

        return packed_bytes + self.checksum

    @classmethod
    def from_bytes(cls, data):

        if len(data) < cls.size():
            raise ValueError("Received data size is less than header size")

        checksum = data[-1]
        data = data[:-1]

        if calculator.verify(data, checksum) is False:
            raise ValueError("Checksum of ApplicationHeaderRDT is not correct")

        transfer_type, protocol, file_name, file_size, sha1_hash = \
            struct.unpack(
                cls.PACKET_FORMAT, data
            )

        file_name = file_name.decode('utf-8').strip('\x00')
        return cls(transfer_type, protocol, file_name, file_size, sha1_hash)

    # TODO: agregar un método para que se cree a partir de un
    # TransferInformation
