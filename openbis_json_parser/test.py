import unittest
import json
import os
from parser import parse_dict, write_ontology

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

print(__location__)
class TestMain(unittest.TestCase):
    def test_main(self):
        with open(os.path.join(__location__,'tests','test_in.json')) as f:
            data = json.load(f)
        onto = parse_dict(data)
        output_file = os.path.join(__location__,'tests','test_out.ttl')
        write_ontology(onto, output_file, target_format='turtle')
        self.assertTrue(os.path.exists(output_file))

if __name__ == '__main__':
    unittest.main()