#!/bin/bash

bin/kafka-console-consumer.sh --topic $1 --from-beginning --bootstrap-server localhost:9092