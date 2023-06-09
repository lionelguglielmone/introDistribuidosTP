import logging
from lib.utils.constant import SelectedTransferType
from lib.utils.file_handling import FileHandler
from lib.segment_encoding.application_header import ApplicationHeaderRDT


class Uploader():
    def __init__(self, stream,  file_handler: FileHandler):
        self.stream = stream
        self.file_handler = file_handler

    def transfer_type(self):
        return SelectedTransferType.UPLOAD

    def run(self):
        logging.info("[UPLOADER] Checking file existence")
        if FileHandler.file_exists(self.file_handler.get_file_path()) is False:
            raise ValueError("[UPLOADER] File doesn't exist")

        logging.info("[UPLOADER] Sending application header")
        app_header = ApplicationHeaderRDT(
            self.transfer_type(), self.file_handler.get_file_name(), self.file_handler.size()
        )
        self.stream.send(app_header.as_bytes())

        chunk_size = FileHandler.MAX_RW_SIZE

        logging.info("[UPLOADER] Sending file data in chunks")
        for _ in range(0, self.file_handler.size(), chunk_size):
            data = self.file_handler.read(chunk_size)
            self.stream.send(data)

        logging.info("[UPLOADER] Upload finished, closing connection")
