import argparse
import sys
import os

# Add the script directory to path so we can import the lib if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from export_xml_lib.exporter import export_pack

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--segment", type=int, required=True)
    parser.add_argument("--format", default="premiere")
    args = parser.parse_args()

    export_pack(args.project, args.segment, args.format)
