import argparse
import json
import sys
import urllib.request

from openbis_json_parser.parser import parse_dict, parse_json, write_ontology


def main():
    parser = argparse.ArgumentParser(prog="OpenBIS JSON Parser")
    parser.add_argument("json_file", metavar="json-file")
    parser.add_argument("-o", "--output-file", help="Resulting ntriples")
    parser.add_argument(
        "-f",
        "--format",
        choices=["ntriples", "nquads", "rdfxml", "turtle", "ttl", "json-ld"],
        default="ntriples",
    )
    parser.add_argument(
        "-b",
        "--base-url",
        help="OpenBIS base URL",
        default="https://openbis.matolab.org/",
    )
    args = parser.parse_args()
    if args.json_file.startswith("http://") or args.json_file.startswith("https://"):
        with urllib.request.urlopen(args.json_file) as resp:
            data = json.load(resp)
        onto = parse_dict(data, base_url=args.base_url)
    elif args.json_file == "-":
        onto = parse_dict(json.load(sys.stdin.buffer), base_url=args.base_url)
    else:
        onto = parse_json(args.json_file, base_url=args.base_url)
    if args.output_file is None or args.output_file == "-":
        write_ontology(onto, sys.stdout.buffer, target_format=args.format)
    else:
        write_ontology(onto, args.output_file, target_format=args.format)


if __name__ == "__main__":
    main()
