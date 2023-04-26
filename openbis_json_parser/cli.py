import json
import argparse
import sys
import urllib.request

from openbis_json_parser.parser import parse_json, parse_dict

def main():
    parser = argparse.ArgumentParser(
        prog='OpenBIS JSON Parser'
    )
    parser.add_argument('json_file', metavar='json-file')
    parser.add_argument('-o', '--output-file', help='Resulting ntriples')
    args = parser.parse_args()
    if args.json_file.startswith('http://') or args.json_file.startswith('https://'):
        with urllib.request.urlopen(args.json_file) as resp:
            data = json.load(resp)
        onto = parse_dict(data)
    else:
        onto = parse_json(args.json_file)
    if args.output_file is None or args.output_file == '-':
        onto.save(sys.stdout.buffer, format='ntriples')
    else:
        onto.save(args.output_file, format='ntriples')


if __name__ == '__main__':
    main()
