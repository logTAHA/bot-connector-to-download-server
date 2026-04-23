#!/bin/bash
source venv/bin/activate
python main.py &
python main_telg.py &
wait
