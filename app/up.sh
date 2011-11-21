#!/bin/bash
ssh -R 5672:localhost:5672 ubuntu@$1 "env/bin/python code/go_worker.py > /dev/null 2>&1"
