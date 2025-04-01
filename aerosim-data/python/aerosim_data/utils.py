from types import SimpleNamespace


def dict_to_namespace(d):
    """Convert a dictionary to a SimpleNamespace, handling nested dictionaries."""
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = dict_to_namespace(value)
    return SimpleNamespace(**d)


def flatten_to_dict(dict_or_namespace: dict | SimpleNamespace):
    flat_dict = {}

    def flatten(d, parent_key=""):
        if not isinstance(d, (dict, SimpleNamespace)):
            raise ValueError("Input must be a dictionary or SimpleNamespace")

        if isinstance(d, SimpleNamespace):
            d = d.__dict__

        for k, v in d.items():
            if isinstance(v, SimpleNamespace):
                v = v.__dict__

            if isinstance(v, dict):
                flatten(v, parent_key + k + ".")
            else:
                flat_dict[parent_key + k] = v

    flatten(dict_or_namespace)

    return flat_dict
