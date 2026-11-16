import unittest

from deploy.ollama_forward import socks_connect_request


class SocksRequestTest(unittest.TestCase):
    def test_ipv4_connect_request(self) -> None:
        request = socks_connect_request("100.116.169.56", 11434)
        self.assertEqual(request[:4], b"\x05\x01\x00\x01")
        self.assertEqual(request[4:8], bytes([100, 116, 169, 56]))
        self.assertEqual(request[8:], (11434).to_bytes(2, "big"))

    def test_hostname_connect_request(self) -> None:
        request = socks_connect_request("ollama.local", 11434)
        self.assertEqual(request[3], 3)
        self.assertEqual(request[4], len(b"ollama.local"))
        self.assertIn(b"ollama.local", request)


if __name__ == "__main__":
    unittest.main()
