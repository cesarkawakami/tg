#!/bin/bash
ab -n 10 -c 1 -p ./deftest.post -T "application/x-www-form-urlencoded" \
    http://localhost:8888/ide/run
