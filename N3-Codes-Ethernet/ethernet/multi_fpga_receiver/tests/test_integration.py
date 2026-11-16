import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from src.receiver import Receiver
from src.packet import encode_packet


class IntegrationTests(unittest.TestCase):
    def test_live_udp_receiver_demultiplexes_all_twelve(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text('{"computer":{"bind_ip":"127.0.0.1","udp_port":51234},"fpgas":[' +
                              ','.join('{"id":%d,"ip":"192.168.1.%d"}' % (i, 100 + i) for i in range(1, 13)) + ']}')
            receiver = Receiver(config, quiet=True)
            thread = threading.Thread(target=receiver.run, kwargs={"duration": 1.0})
            thread.start(); time.sleep(0.08)
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for seq in range(4):
                for fpga_id in (1, 12, 3, 8, 2, 11, 4, 10, 5, 9, 6, 7):
                    sender.sendto(encode_packet(fpga_id, seq, seq, bytes([fpga_id, seq])), ("127.0.0.1", 51234))
            sender.close(); thread.join(2)
            self.assertFalse(thread.is_alive())
            for fpga_id, state in receiver.router.states.items():
                self.assertEqual(state.packets_received, 4, fpga_id)
                self.assertEqual(bytes(state.payload_buffer[-1]), bytes([fpga_id, 3]))
