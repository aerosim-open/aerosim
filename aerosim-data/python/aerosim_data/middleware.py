from aerosim_data import _aerosim_data

types = _aerosim_data.types
middleware = _aerosim_data.middleware

# re-export classes
Metadata = middleware.Metadata
BincodeSerializer = middleware.BincodeSerializer

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def get_transport(transport):
    if transport == "kafka":
        return KafkaMiddleware()
    elif transport == "dds":
        return DDSMiddleware()


class BaseMiddleware(metaclass=Singleton):
    def __init__(self, transport, serializer):
        self._transport = transport
        self._serializer = serializer

    def get_serializer(self):
        return self._serializer

    def publish_raw(self, message_type, topic, payload):
        self._transport.publish_raw(message_type, topic, payload)

    def subscribe_raw(self, message_type, topic, callback):
        self._transport.subscribe_raw(message_type, topic, callback)

    def subscribe_all_raw(self, topics, callback):
        self._transport.subscribe_all_raw(topics, callback)

    def publish(self, topic, message, timestamp_sim=None):
        if isinstance(message, dict):
            message = types.JsonData(message)

        self._transport.publish(topic, message, timestamp_sim)

    def subscribe(self, message_type, topic, callback):

        def _preprocess_data(data):
            if isinstance(data, types.JsonData):
                return data.get_data()
            return data

        _callback = lambda data, metadata: callback(_preprocess_data(data), metadata)
        self._transport.subscribe(message_type, topic, _callback)

    def subscribe_all(self, message_type, topic, callback):

        def _preprocess_data(data):
            if isinstance(data, types.JsonData):
                return data.get_data()
            return data

        _callback = lambda data, metadata: callback(_preprocess_data(data), metadata)
        self._transport.subscribe_all(message_type, topic, _callback)


class KafkaMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__(middleware.KafkaMiddleware(), middleware.KafkaSerializer())


class DDSMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__(middleware.DDSMiddleware(), middleware.DDSSerializer())
