#!/bin/bash

KAFKA_TMPFS=${1:-false}
KAFKA_TMPFS_SIZE=${2:-"5G"}
KAFKA_TMPFS_LOG_DIR="/mnt/kafka-logs"

if [ -d "bin" ]; then
  echo "kafka already downloaded."
else
  curl --retry 5 --retry-max-time 120 -L -o kafka.tgz https://dlcdn.apache.org/kafka/3.8.0/kafka_2.13-3.8.0.tgz && tar --strip-components=1 -xzf kafka.tgz && rm kafka.tgz && echo "Downloaded Kafka 3.8.0"
fi

# Create a tmpfs in RAM to allow faster I/O operations.
# This prevent Kafka broker freezes when deleting large amounts of logs.
if [ "$KAFKA_TMPFS" = "true" ]; then
  if ! findmnt "$KAFKA_TMPFS_LOG_DIR" > /dev/null; then
    echo "Creating tmpfs for Kafka (${KAFKA_TMPFS_SIZE})"
    echo "Administrator privileges are required"
    sudo mkdir -p ${KAFKA_TMPFS_LOG_DIR}
    sudo mount -t tmpfs tmpfs ${KAFKA_TMPFS_LOG_DIR} -o size=${KAFKA_TMPFS_SIZE}
  else
    echo "tmpfs already mounted at ${KAFKA_TMPFS_LOG_DIR}"
  fi
fi
