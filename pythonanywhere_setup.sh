#!/usr/bin/env bash
set -e

cd ~/lab7
python3.11 -m venv ve311
source ve311/bin/activate
pip install -r requirements.txt
cd app
python init_db.py
