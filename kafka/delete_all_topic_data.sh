#!/bin/bash

bin/kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic '.*'
