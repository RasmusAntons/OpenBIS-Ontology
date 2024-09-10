import json
import os
import unittest

from main import parse_dict, write_ontology

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

print(__location__)


class TestMain(unittest.TestCase):
    # def test_user(self):
    #     with open(os.path.join(__location__, "tests", "user.json")) as f:
    #         data = json.load(f)
    #     onto = parse_dict(data)
    #     output_file = os.path.join(__location__, "tests", "user.ttl")
    #     write_ontology(onto, output_file, target_format="turtle")
    #     self.assertTrue(os.path.exists(output_file))

    # def test_collection(self):
    #     with open(os.path.join(__location__, "tests", "collection.json")) as f:
    #         data = json.load(f)
    #     onto = parse_dict(data)
    #     output_file = os.path.join(__location__, "tests", "collection.ttl")
    #     write_ontology(onto, output_file, target_format="turtle")
    #     self.assertTrue(os.path.exists(output_file))

    # def test_object(self):
    #     with open(os.path.join(__location__, "tests", "object.json")) as f:
    #         data = json.load(f)
    #     onto = parse_dict(data)
    #     output_file = os.path.join(__location__, "tests", "object.ttl")
    #     write_ontology(onto, output_file, target_format="turtle")
    #     self.assertTrue(os.path.exists(output_file))

    # def test_project(self):
    #     with open(os.path.join(__location__, "tests", "project.json")) as f:
    #         data = json.load(f)
    #     onto = parse_dict(data)
    #     output_file = os.path.join(__location__, "tests", "project.ttl")
    #     write_ontology(onto, output_file, target_format="turtle")
    #     self.assertTrue(os.path.exists(output_file))

    # def test_space(self):
    #     with open(os.path.join(__location__, "tests", "space.json")) as f:
    #         data = json.load(f)
    #     onto = parse_dict(data)
    #     output_file = os.path.join(__location__, "tests", "space.ttl")
    #     write_ontology(onto, output_file, target_format="turtle")
    #     self.assertTrue(os.path.exists(output_file))
    def test_dataset(self):
        with open(os.path.join(__location__, "tests", "dataset.json")) as f:
            data = json.load(f)
        onto = parse_dict(data)
        output_file = os.path.join(__location__, "tests", "dataset.ttl")
        write_ontology(onto, output_file, target_format="turtle")
        self.assertTrue(os.path.exists(output_file))

if __name__ == "__main__":
    unittest.main()
