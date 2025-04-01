from pythonfmu3 import (
    Fmi3Causality,
    Fmi3Variability,
    Fmi3Slave,
    Float64,
    Int64,
    String,
    Boolean,
    Dimension,
)

import numpy as np
from types import SimpleNamespace

from aerosim_data import flatten_to_dict


def register_fmu3_var(fmi_obj: Fmi3Slave, var_name: str, causality: str):
    registered_vars = []

    if causality == "input":
        caus = Fmi3Causality.input
    elif causality == "output":
        caus = Fmi3Causality.output
    elif causality == "independent":
        caus = Fmi3Causality.independent
    else:
        raise ValueError(f"Unsupported causality: {causality}")

    var = getattr(fmi_obj, var_name)

    if type(var) is SimpleNamespace or type(var) is dict:
        var = flatten_to_dict(var)

    if type(var) is dict:
        for local_var_name, var_value in var.items():
            if type(var_value) is np.ndarray:
                if (var_value.dtype == np.float64) or (var_value.dtype == np.float32):
                    fmi_obj.register_variable(
                        Float64(
                            var_name + "." + local_var_name,
                            causality=caus,
                            dimensions=[Dimension(start=f"{var_value.shape[0]}")],
                        ),
                        nested=True,
                    )
                    registered_vars.append(
                        var_name + "." + local_var_name + " as Float64"
                    )
                else:
                    raise ValueError(f"Unsupported array data type: {var_value.dtype}")
            else:  # var_value is not an array
                if type(var_value) is float:
                    fmi_obj.register_variable(
                        Float64(
                            var_name + "." + local_var_name,
                            causality=caus,
                        ),
                        nested=True,
                    )
                    registered_vars.append(
                        var_name + "." + local_var_name + " as Float64"
                    )
                elif type(var_value) is int:
                    fmi_obj.register_variable(
                        Int64(
                            var_name + "." + local_var_name,
                            causality=caus,
                            variability=Fmi3Variability.discrete,
                        ),
                        nested=True,
                    )
                    registered_vars.append(
                        var_name + "." + local_var_name + " as Int64"
                    )
                elif type(var_value) is str:
                    fmi_obj.register_variable(
                        String(
                            var_name + "." + local_var_name,
                            causality=caus,
                        ),
                        nested=True,
                    )
                    registered_vars.append(
                        var_name + "." + local_var_name + " as String"
                    )
                elif type(var_value) is bool:
                    fmi_obj.register_variable(
                        Boolean(
                            var_name + "." + local_var_name,
                            causality=caus,
                        ),
                        nested=True,
                    )
                    registered_vars.append(
                        var_name + "." + local_var_name + " as Boolean"
                    )
                else:
                    raise ValueError(
                        f"'{var_name}' variable '{local_var_name}' has an unsupported data type: {type(var)}"
                    )
    else:  # var is a single element
        if type(var) is float:
            fmi_obj.register_variable(Float64(var_name, causality=caus), nested=False)
            registered_vars.append(var_name + " as Float64")
        elif type(var) is int:
            fmi_obj.register_variable(
                Int64(
                    var_name,
                    causality=caus,
                    variability=Fmi3Variability.discrete,
                ),
                nested=False,
            )
            registered_vars.append(var_name + " as Int64")
        elif type(var) is str:
            fmi_obj.register_variable(String(var_name, causality=caus), nested=False)
            registered_vars.append(var_name + " as String")
        elif type(var) is bool:
            fmi_obj.register_variable(Boolean(var_name, causality=caus), nested=False)
            registered_vars.append(var_name + " as Boolean")
        else:
            raise ValueError(f"Unsupported data type: {type(var)}")

    if len(registered_vars) == 1:
        print(f"Registered FMU {causality} variable: {registered_vars[0]}")
    elif len(registered_vars) > 1:
        print(f"Registered FMU {causality} variables:")
        for var in registered_vars:
            print(f"  {var}")


def register_fmu3_param(fmi_obj: Fmi3Slave, param_name: str):
    param = getattr(fmi_obj, param_name)

    if type(param) is float:
        fmi_obj.register_variable(
            Float64(
                param_name,
                causality=Fmi3Causality.parameter,
                variability=Fmi3Variability.tunable,
            ),
            nested=False,
        )
    elif type(param) is int:
        fmi_obj.register_variable(
            Int64(
                param_name,
                causality=Fmi3Causality.parameter,
                variability=Fmi3Variability.tunable,
            ),
            nested=False,
        )
    elif type(param) is str:
        fmi_obj.register_variable(
            String(
                param_name,
                causality=Fmi3Causality.parameter,
                variability=Fmi3Variability.tunable,
            ),
            nested=False,
        )
    elif type(param) is bool:
        fmi_obj.register_variable(
            Boolean(
                param_name,
                causality=Fmi3Causality.parameter,
                variability=Fmi3Variability.tunable,
            ),
            nested=False,
        )
    else:
        raise ValueError(f"Unsupported data type: {type(param)}")

    print(f"Registered FMU tunable parameter: {param_name}")
