import logging



class SlidingWindow:

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
        return self.current_seq_num == self.final_seq_num

    def is_available_segment_to_send(self, seq_num):
        return (self.get_sent(seq_num) == False) and (self.get_ack(seq_num) == False)

    def has_available_segments_to_send(self):
        i = self.current_seq_num
        # is there any segment that is not sent and not ack in the current window?
        while i <= self.current_seq_num + self.window_size:
            if self.is_available_segment_to_send(i):
                return True
            i += 1
        return False

    def reset_sent_segments(self):
        self.sent_list = [False for _ in range(self.window_size)]

    def get_first_available_segment(self):
        i = self.current_seq_num
        while i <= self.current_seq_num + self.window_size:
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
        if (self._has_available_segment_to_pop() == False):
            return None
        seq_num, data = self.buffer.pop(0)
        self.curr_seq_num = seq_num + 1
        return data

    def _has_available_segment_to_pop(self):
        return len(self.buffer) != 0 and (self.buffer[0][0] == self.curr_seq_num) and (self.buffer[0][1] != None)


class SelectiveRepeat:

    def __init__(self, stream, window_size, mss: int):
        self.stream = stream
        self.seq_num = self.stream.seq_num
        self.ack_num = self.stream.ack_num
        self.window_size = window_size
        self.mss = mss

    def read(self):
        # create data list
        # while True:
        # read segment from stream
        # if segment has a consecutive seq num then send ack and concatenate data to data list
        # if segment has consecutive seq num check if buffer has all data consecutively then send ack and concatenate all buffer data to data list
        # if segment has a non consecutive seq num then send ack with last consecutive seq num and put data in buffer
        # if segment has a fin flag then send ack and break
        # return data list
        buf_sorter = BufferSorter(self.ack_num)

        while True:
            try:
                # Reading segment
                received_segment, external_addres = self.stream.read_segment()
            except Exception as e:
                continue
            received_seq_num = received_segment.header.seq_num
            received_ack_num = received_segment.header.ack_num
            received_segment_data = received_segment.data
            logging.info(
                f"Received segment {external_addres} seq_num: {received_seq_num} | data: {received_segment_data} | ack_num: {received_ack_num} | syn: False | fin: False")

            # send ack
            logging.info(
                f"Sending Ack segment seq_num: {self.seq_num} | data: {b''} | ack_num: {received_seq_num} | syn: False | fin: False")
            self.stream.send_segment(
                b'', self.seq_num, received_seq_num, False, False)

            buf_sorter.add_segment(received_seq_num, received_segment_data)
            read_data = buf_sorter.pop_available_data()

            return read_data

            # # if a a consecutive ack num was received
            # if self.ack_num + 1 == received_seq_num:
            #     # update ack
            #     self.ack_num += 1
            #     return received_segment_data
            # else:  # if not consecutive
            #     logging.info(
            #         f"Non Consecutive segment seq_num: {received_seq_num} | data: {received_segment_data} | ack_num: {received_ack_num} | syn: False | fin: False")

            #     # add to buffer if it does not exist
            #     if buffer.get(received_seq_num) == None:
            #         buffer[received_seq_num] = received_segment_data

            #     # sort buffer by first key of tuple
            #     sortedList = sorted(buffer.keys())
            #     # check if sortedList values consecutive
            #     if self.is_consecutive(sortedList):
            #         # if consecutive then concatenate all data to data list
            #         data = b''
            #         for key in sortedList:
            #             data += buffer[key]
            #         return data

    def send(self, data_segments):
        window = SlidingWindow(
            data_segments, self.window_size, self.seq_num)

        retries = 0
        while not window.finished() and retries < self.MAX_TIMEOUT_RETRIES:
            if not window.has_available_segments_to_send():
                try:
                    received_segment, _ = self.stream.read_segment()
                    received_seq_num = received_segment.header.seq_num
                    received_segment_data = received_segment.data
                    received_ack_num = received_segment.header.ack_num
                    logging.info(
                        f"Received segment {external_addres} seq_num: {received_seq_num} | data: {received_segment_data} | ack_num: {received_ack_num} | syn: False | fin: False")
                    window.set_ack(received_ack_num)
                    retries = 0
                    continue
                except TimeoutError:
                    window.reset_sent_segments()
                    retries += 1
                    continue
                except ValueError:
                    continue

            segment, sent_seq_num = window.get_first_available_segment()

            # send segment
            logging.info(
                f"Sending segment seq_num: {sent_seq_num} | data: {segment} | ack_num: {self.ack_num} | syn: False | fin: False")
            self.stream.send_segment(
                segment, sent_seq_num, self.ack_num, False, False)
            window.set_sent(sent_seq_num, True)

            received_segment, external_addres = self.stream.read_segment_non_blocking()
            if received_seq_num == None:
                continue
            received_seq_num = received_segment.header.seq_num
            received_segment_data = received_segment.data
            received_ack_num = received_segment.header.ack_num
            logging.info(
                f"Received segment {external_addres} seq_num: {received_seq_num} | data: {received_segment_data} | ack_num: {received_ack_num} | syn: False | fin: False")
            window.set_ack(received_ack_num)
            retries = 0
