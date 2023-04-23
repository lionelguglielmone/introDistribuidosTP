import logging


class SlidingWindow:

    MAX_TIMEOUT_RETRIES = 3

    def __init__(self, data, window_size, initial_seq_num=0):
        self.window_size = window_size
        self.data = data
        self.current_seq_num = initial_seq_num
        self.final_seq_num = initial_seq_num + len(data) - 1

        self.ack_list = [False for _ in range(self.window_size)]
        self.sent_list = [False for _ in range(self.window_size)]

    def get_ack(self, seq_num):
        return self.ack_list[seq_num - self.current_seq_num]

    def set_ack(self, seq_num):
        if (seq_num < self.current_seq_num or seq_num > self.final_seq_num):
            return
        self.ack_list[seq_num - self.current_seq_num] = True
        self.update_sliding_window()

    def update_sliding_window(self):
        positions_to_move = 0
        for ack in self.ack_list:
            if ack:
                positions_to_move += 1
            else:
                break

        self.ack_list = self.ack_list[positions_to_move:]
        for _ in range(positions_to_move):
            self.ack_list.append(False)

        self.sent_list = self.sent_list[positions_to_move:]
        for _ in range(positions_to_move):
            self.sent_list.append(False)

        self.data = self.data[positions_to_move:]
        self.current_seq_num += positions_to_move

    def get_sent(self, seq_num):
        return self.sent_list[seq_num - self.current_seq_num]

    def set_sent(self, seq_num, value: bool):
        self.sent_list[seq_num - self.current_seq_num] = value

    def finished(self):
        # finished when all data is ack and current seq num is final seq num
        return self.current_seq_num == self.final_seq_num + 1

    def is_available_segment_to_send(self, seq_num):
        return (self.get_sent(seq_num) is False) and \
            (self.get_ack(seq_num) is False)

    def has_available_segments_to_send(self):
        i = self.current_seq_num
        # is there any segment that is not sent and not ack in
        # the current window?
        while (i <= self.final_seq_num) and (i < self.current_seq_num + self.window_size):
            if self.is_available_segment_to_send(i):
                return True
            i += 1
        return False

    def reset_sent_segments(self):
        self.sent_list = [False for _ in range(self.window_size)]

    def get_first_available_segment(self):
        i = self.current_seq_num
        while (i <= self.final_seq_num) and (i < self.current_seq_num + self.window_size):
            if self.is_available_segment_to_send(i):
                return i, self.data[i - self.current_seq_num]
            i += 1
        return None, None


class BufferSorter:
    def __init__(self, initial_seq_num=0):
        self.curr_seq_num = initial_seq_num
        self.buffer = []

    def add_segment(self, seq_num, data):
        seg_position = seq_num - self.curr_seq_num
        if seg_position < 0:
            return
        if seg_position >= len(self.buffer):
            for i in range(seg_position - len(self.buffer) + 1):
                self.buffer.append((len(self.buffer) + i, None))

        self.buffer[seg_position] = (seq_num, data)

    def pop_available_data(self):
        data_popped = b''
        while self._has_available_segment_to_pop():
            data = self._pop_first_available_segment()
            data_popped = data_popped + data
        return data_popped

    def _pop_first_available_segment(self):
        if (self._has_available_segment_to_pop() is False):
            return None
        seq_num, data = self.buffer.pop(0)
        self.curr_seq_num = seq_num + 1
        return data

    def _has_available_segment_to_pop(self):
        return len(self.buffer) != 0 and \
            (self.buffer[0][0] == self.curr_seq_num) and \
            (self.buffer[0][1] is not None)


class SelectiveRepeat:

    def __init__(self, stream, window_size, mss: int):
        self.stream = stream
        self.seq_num = self.stream.seq_num
        self.ack_num = self.stream.ack_num
        self.window_size = window_size
        self.mss = mss

    def read(self):

        buf_sorter = BufferSorter(self.ack_num)

        while True:
            try:
                # Reading segment
                received_segment, external_addres = self.stream.read_segment()
            except Exception:
                continue
            received_seq_num = received_segment.header.seq_num
            # received_ack_num = received_segment.header.ack_num
            received_segment_data = received_segment.data

            # send ack
            logging.info(
                f"[PROTOCOL] Sending Ack segment seq_num: {self.seq_num} | data: {b''} | ack_num: {received_seq_num} | syn: False | fin: False")  # noqa E501
            self.stream.send_segment(
                b'', self.seq_num, received_seq_num, False, False)

            buf_sorter.add_segment(received_seq_num, received_segment_data)
            read_data = buf_sorter.pop_available_data()

            return read_data

    def send(self, data_segments):
        window = SlidingWindow(
            data_segments, self.window_size, self.seq_num)

        retries = 0
        while not window.finished() and retries < SlidingWindow.MAX_TIMEOUT_RETRIES:
            if not window.has_available_segments_to_send():
                try:
                    received_segment, external_addres = \
                        self.stream.read_segment()
                    received_seq_num = received_segment.header.seq_num
                    received_segment_data = received_segment.data
                    received_ack_num = received_segment.header.ack_num
                    logging.info(
                        f"[PROTOCOL] Received segment {external_addres} seq_num: {received_seq_num} | data: {received_segment_data} | ack_num: {received_ack_num} | syn: False | fin: False")  # noqa E501
                    window.set_ack(received_ack_num)
                    retries = 0
                    continue
                except TimeoutError:
                    window.reset_sent_segments()
                    retries += 1
                    continue
                except ValueError:
                    continue

            sent_seq_num, segment = window.get_first_available_segment()

            # send segment
            logging.info(
                f"[PROTOCOL] Sending segment seq_num: {sent_seq_num} | ack_num: {self.ack_num} | syn: False | fin: False")  # noqa E501
            self.stream.send_segment(
                segment, sent_seq_num, self.ack_num, False, False)
            window.set_sent(sent_seq_num, True)

            received_segment, external_addres = \
                self.stream.read_segment_non_blocking()
            if received_segment is None:
                continue
            received_seq_num = received_segment.header.seq_num
            received_segment_data = received_segment.data
            received_ack_num = received_segment.header.ack_num
            logging.info(
                f"[PROTOCOL] Received segment {external_addres} seq_num: {received_seq_num} | data: {received_segment_data} | ack_num: {received_ack_num} | syn: False | fin: False")  # noqa E501
            window.set_ack(received_ack_num)
            retries = 0
