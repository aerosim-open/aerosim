#!/bin/bash

KAFKA_CLUSTER_IP=${1:-localhost}
KAFKA_TMPFS=${2:-false}

KAFKA_CONFIG="config/kraft/server.properties"
if [ "$KAFKA_TMPFS" = "true" ]; then
    KAFKA_LOG_DIR="/mnt/kafka-logs"
else
    KAFKA_LOG_DIR="/tmp/kraft-combined-logs"
fi

echo "Cleaning out all kraft metadata in ${KAFKA_LOG_DIR}"
echo "Running in: ${PWD}"
rm -rf ${KAFKA_LOG_DIR}/*

echo "IP: ${KAFKA_CLUSTER_IP}"

# Update the `log.dirs` setting in the configuration file  
#     - If `log.dirs` is already defined, update it with the new value.
#     - If `log.dirs` is not defined, add it to the end of the file  
# This ensures that Kafka stores logs in the specified directory during initialization,  
# as the kafka-storage script does not accept overridden parameters.
if grep -q "^log.dirs=" "$KAFKA_CONFIG"; then
    sed -i "s|^log.dirs=.*|log.dirs=$KAFKA_LOG_DIR|" "$KAFKA_CONFIG"
else
    echo "log.dirs=$LOG_DIR" >> "$KAFKA_CONFIG"
fi

# If cluster ID is not already set, generate a new ID and format the server config with it:
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c ${KAFKA_CONFIG}

# Launch kafka server (force to IPv4 due to WSL2 network limitation)
# The server is configured to handle large messages (up to 10MB).
# The broker has an aggressive log retention policy to prevent memory overflow.
# The retention policy is checked every 5 seconds, deleting logs older than 5 seconds or exceeding 1GB.
KAFKA_OPTS="-Djava.net.preferIPv4Stack=True" bin/kafka-server-start.sh ${KAFKA_CONFIG} \
   --override log.dirs=${KAFKA_LOG_DIR} \
   --override advertised.listeners=PLAINTEXT://${KAFKA_CLUSTER_IP}:9092 \
   --override socket.send.buffer.bytes=1048576 \
   --override socket.receive.buffer.bytes=1048576 \
   --override message.max.bytes=10485760 \
   --override replica.fetch.max.bytes=12485760 \
   --override log.retention.ms=5000 \
   --override log.retention.check.interval.ms=5000 \
   --override log.segment.delete.delay.ms=1000 \
   --override log.cleaner.enable=true \
   --override log.cleanup.policy=delete
