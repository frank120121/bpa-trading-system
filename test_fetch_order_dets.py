import unittest
from utils import fetch_order_details




class TestUtils(unittest.TestCase):
    def test_fetch_order_details(self):
        # Replace 'sample_order_no' with an actual order number for the test
        sample_order_no = 20534096348670504960
        data = fetch_order_details(sample_order_no)
        self.assertIsNotNone(data)  # replace with more specific assertions based on expected data structure

if __name__ == '__main__':
    unittest.main()