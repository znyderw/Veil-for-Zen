#!/usr/bin/env python3
"""Build using setuptools' standard PEP 517 backend (no network access)."""
import argparse
import os
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--wheel',action='store_true',help='Build wheel (default)')
parser.add_argument('--sdist',action='store_true')
args=parser.parse_args()
os.chdir(Path(__file__).resolve().parents[1])
from setuptools import build_meta
Path('dist').mkdir(exist_ok=True)
print(build_meta.build_sdist('dist') if args.sdist else build_meta.build_wheel('dist'))
