import os
import shutil
import threading

from dotty_dictionary import dotty

import fmpy
from fmpy.fmi3 import FMU3Slave
from fmpy.fmi2 import FMU2Slave

from aerosim_data import types as aerosim_types
from aerosim_data import middleware
from aerosim_data import flatten_to_dict
from aerosim_sensors import adsb_functions


class FmuDriver:
    def __init__(self, fmu_id: str, working_dir: str = "") -> None:
        self.fmu_id = fmu_id
        self.working_dir = working_dir
        self.unzipped_temp_dir = None
        self.fmu_config_json = {}
        self.aerosim_root_path = os.getenv("AEROSIM_ROOT")

        self._is_sim_config_loaded = False
        self._is_sim_started = False
        self.sim_start_time = aerosim_types.TimeStamp(0, 0)

        self._running = True
        self._processing_callback_lock = threading.Lock()

        self.transport = middleware.get_transport("kafka")
        self.serializer = self.transport.get_serializer()

        self.transport.subscribe(
            aerosim_types.JsonData,
            "aerosim.orchestrator.commands",
            self.orchestator_commands_callback,
        )
        self.transport.subscribe(
            aerosim_types.JsonData, "aerosim.clock", self.clock_callback
        )

        self.reset_data()

    def __del__(self):
        # Delete temporary folder where FMU was unzipped
        dir_to_delete = self.unzipped_temp_dir
        if dir_to_delete is not None:
            try:
                print(
                    f"{self.fmudriver_name} Deleting extracted FMU at: {dir_to_delete}"
                )
                shutil.rmtree(dir_to_delete)
                print(
                    f"{self.fmudriver_name} Successfully deleted extracted FMU at: {dir_to_delete}"
                )
            except OSError as e:
                print(f"{self.fmudriver_name} Error deleting extracted FMU: {e}")

    def reset_data(self):
        # FMU model data
        self.fmu_filename = ""
        self.fmudriver_name = f"[aerosim.fmudriver.{self.fmu_id}]"
        self.model_description = None
        self.fmu_var_refs = {}
        self.fmu_var_types = {}
        self.fmu_var_causality = {}
        self.fmu_var_dims = {}
        self.fmu_instance: FMU3Slave | FMU2Slave | None = None

        # FMU instance data
        self.start_time = 0.0  # TODO Need to get the actual start time from sim clock
        self.fmu_time = 0.0
        self.fmu_data = {}  # {"fmu var": value}
        self.in_topic_data = {}  # {"topic": {"topic var": value, ...}}
        self.out_topic_data = {}  # {"topic": {"topic var": value, ...}}

        # Track all topics that need to be subscribed to
        # Each element is a tuple representing the (msg_type, topic_name)
        self.all_topics_to_subscribe = set()

        # Track a set of which topics are aux inputs that need variable remapping
        self.aux_topics_to_subscribe = set()

        # Track a set of which topics are aux outputs that need variable remapping
        self.aux_topics_to_publish = set()

    def load_config(self):
        self.all_topics_to_subscribe.clear()
        self.aux_topics_to_subscribe.clear()
        self.aux_topics_to_publish.clear()

        if "component_input_topics" in self.fmu_config_json:
            in_topics = self.fmu_config_json["component_input_topics"]
            for in_topic_info in in_topics:
                in_topic = in_topic_info["topic"]
                msg_type = in_topic_info["msg_type"]
                self.all_topics_to_subscribe.add((msg_type, in_topic))
                self.in_topic_data[in_topic] = {}

        if "fmu_aux_input_mapping" in self.fmu_config_json:
            for in_topic_root, _ in self.fmu_config_json[
                "fmu_aux_input_mapping"
            ].items():
                # We treat auxiliary topics as JsonData because they are not tied to any specific data type.
                self.all_topics_to_subscribe.add(
                    ("aerosim::types::JsonData", in_topic_root)
                )
                self.aux_topics_to_subscribe.add(in_topic_root)
                self.in_topic_data[in_topic_root] = {}
            # print(f"topics_to_subscribe = {self.topics_to_subscribe}")

        if "fmu_aux_output_mapping" in self.fmu_config_json:
            for out_topic_root, _ in self.fmu_config_json[
                "fmu_aux_output_mapping"
            ].items():
                self.aux_topics_to_publish.add(out_topic_root)
                self.out_topic_data[out_topic_root] = {}
            # print(f"topics_to_publish = {self.topics_to_publish}")

    def load_fmu(self):
        fmu_model_path = self.fmu_config_json["fmu_model_path"]
        if not os.path.isfile(fmu_model_path) and self.aerosim_root_path is not None:
            # If the FMU model path is not found, check if it is relative to the AeroSim root dir
            fmu_model_path = os.path.join(self.aerosim_root_path, fmu_model_path)
        if not os.path.isfile(fmu_model_path):
            # If the FMU model path is still not found, check if it is relative to
            # the working directory
            fmu_model_path = os.path.join(self.working_dir, fmu_model_path)

        self.fmu_filename = os.path.abspath(fmu_model_path)
        print(f"{self.fmudriver_name} Loading FMU file: {self.fmu_filename}")

        # Read the model description
        # fmpy.dump(self.fmu_filename)
        self.model_description = fmpy.read_model_description(self.fmu_filename)

        # Collect the value references
        for var in self.model_description.modelVariables:
            self.fmu_var_refs[var.name] = var.valueReference
            self.fmu_var_types[var.name] = var.type
            self.fmu_var_dims[var.name] = [dim.start for dim in var.dimensions]
            self.fmu_var_causality[var.name] = var.causality
            print(
                f"{self.fmudriver_name} "
                f"FMU ref={self.fmu_var_refs[var.name]} "
                f"var='{var.name}', "
                f"type={self.fmu_var_types[var.name]}, "
                f"dims={self.fmu_var_dims[var.name]}, "
                f"causality={self.fmu_var_causality[var.name]}"
            )

        # Extract the FMU
        self.unzipped_temp_dir = fmpy.extract(
            filename=self.fmu_filename,
            unzipdir=os.path.join(self.working_dir, "temp_fmu_extract", self.fmu_id),
        )  # Note: this moves CWD to the temp dir
        os.chdir(self.working_dir)  # Set CWD back to the original working dir
        print(f"{self.fmudriver_name} Extracted FMU to: {self.unzipped_temp_dir}")
        print(f"{self.fmudriver_name} CWD set back to: {os.getcwd()}")

        if self.model_description.fmiVersion == "3.0":
            self.fmu_instance = FMU3Slave(
                guid=self.model_description.guid,
                unzipDirectory=self.unzipped_temp_dir,
                modelIdentifier=self.model_description.coSimulation.modelIdentifier,
                instanceName="instance1",
            )
        elif self.model_description.fmiVersion == "2.0":
            self.fmu_instance = FMU2Slave(
                guid=self.model_description.guid,
                unzipDirectory=self.unzipped_temp_dir,
                modelIdentifier=self.model_description.coSimulation.modelIdentifier,
                instanceName="instance1",
            )
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")
            return

    def set_fmu_float(self, fmu_var: str, value: float | list[float]):
        if type(value) is float:
            value = [value]
        if self.model_description.fmiVersion == "3.0":
            self.fmu_instance.setFloat64([self.fmu_var_refs[fmu_var]], value)
        elif self.model_description.fmiVersion == "2.0":
            self.fmu_instance.setReal([self.fmu_var_refs[fmu_var]], value)
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")

    def get_fmu_float(
        self, fmu_var: str, array_dim: int | None = None
    ) -> float | list[float]:
        if self.model_description.fmiVersion == "3.0":
            out_vals = self.fmu_instance.getFloat64(
                vr=[self.fmu_var_refs[fmu_var]], nValues=array_dim
            )
            if not array_dim:
                out_vals = out_vals[0]
        elif self.model_description.fmiVersion == "2.0":
            if array_dim:
                print("FMU 2.0 does not support array dimensions, ignoring array_dim.")
            out_vals = self.fmu_instance.getReal([self.fmu_var_refs[fmu_var]])[0]
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")
            out_vals = 0.0
        return out_vals

    def set_fmu_int(self, fmu_var: str, value: int | list[int]):
        if type(value) is int:
            value = [value]
        if self.model_description.fmiVersion == "3.0":
            self.fmu_instance.setInt64([self.fmu_var_refs[fmu_var]], value)
        elif self.model_description.fmiVersion == "2.0":
            self.fmu_instance.setInteger([self.fmu_var_refs[fmu_var]], value)
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")

    def get_fmu_int(
        self, fmu_var: str, array_dim: int | None = None
    ) -> int | list[int]:
        if self.model_description.fmiVersion == "3.0":
            out_vals = self.fmu_instance.getInt64(
                vr=[self.fmu_var_refs[fmu_var]], nValues=array_dim
            )
            if not array_dim:
                out_vals = out_vals[0]

        elif self.model_description.fmiVersion == "2.0":
            if array_dim:
                print("FMU 2.0 does not support array dimensions, ignoring array_dim.")
            out_vals = self.fmu_instance.getInteger([self.fmu_var_refs[fmu_var]])[0]
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")
            out_vals = 0
        return out_vals

    def set_fmu_string(self, fmu_var: str, value: str | list[str]):
        if type(value) is str:
            value = [value]
        self.fmu_instance.setString([self.fmu_var_refs[fmu_var]], value)

    def get_fmu_string(
        self, fmu_var: str, array_dim: int | None = None
    ) -> str | list[str]:
        if self.model_description.fmiVersion == "3.0":
            out_vals = self.fmu_instance.getString(
                vr=[self.fmu_var_refs[fmu_var]], nValues=array_dim
            )
            if not array_dim:
                out_vals = out_vals[0]

        elif self.model_description.fmiVersion == "2.0":
            if array_dim:
                print("FMU 2.0 does not support array dimensions, ignoring array_dim.")
            out_vals = self.fmu_instance.getString([self.fmu_var_refs[fmu_var]])[0]
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")
            out_vals = ""
        return out_vals

    def set_fmu_bool(self, fmu_var: str, value: bool | list[bool]):
        if type(value) is bool:
            value = [value]
        self.fmu_instance.setBoolean([self.fmu_var_refs[fmu_var]], value)

    def get_fmu_bool(
        self, fmu_var: str, array_dim: int | None = None
    ) -> bool | list[bool]:
        if self.model_description.fmiVersion == "3.0":
            out_vals = self.fmu_instance.getBoolean(
                vr=[self.fmu_var_refs[fmu_var]], nValues=array_dim
            )
            if not array_dim:
                out_vals = out_vals[0]

        elif self.model_description.fmiVersion == "2.0":
            if array_dim:
                print("FMU 2.0 does not support array dimensions, ignoring array_dim.")
            out_vals = self.fmu_instance.getBoolean([self.fmu_var_refs[fmu_var]])[0]
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")
            out_vals = False
        return out_vals

    def start(self):
        print(f"{self.fmudriver_name} Start FMU driver...")
        print(f"{self.fmudriver_name} FMU driver is started.")

    def init_fmu(self):
        # Instantiate the FMU
        self.fmu_instance.instantiate()

        # Set some base default values for all FMU input/output variables (these are
        # used in initial published output at t=0 for any variables set below by
        # values specified in the "fmu_initial_vals" config)
        for fmu_var, fmu_var_type in self.fmu_var_types.items():
            var_dim = None  # default var_dim to None for scalar variables
            if len(self.fmu_var_dims[fmu_var]) > 0:
                # var_dim is the total number of elements in the n-dimensional array
                var_dim = 1
                for dim in self.fmu_var_dims[fmu_var]:
                    var_dim *= dim
            if fmu_var_type == "Real" or fmu_var_type == "Float64":
                self.fmu_data[fmu_var] = 0.0 if not var_dim else [0.0] * var_dim
            elif fmu_var_type == "Integer" or fmu_var_type == "Int64":
                self.fmu_data[fmu_var] = 0 if not var_dim else [0] * var_dim
            elif fmu_var_type == "String":
                self.fmu_data[fmu_var] = ""
            elif fmu_var_type == "Boolean":
                self.fmu_data[fmu_var] = False
            else:
                # TODO Handle other FMI 3.0 types
                print(
                    f"{self.fmudriver_name} WARNING: Unsupported FMU variable type '{fmu_var_type}'"
                )
                continue

        # Set initial values for FMU variables set in the "fmu_initial_vals" config
        for init_var, init_value in self.fmu_config_json["fmu_initial_vals"].items():
            print(
                f"{self.fmudriver_name} Setting initial value {init_var} = {init_value}"
            )
            # Handle the case where the initial value is a list of values
            init_value_type = (
                type(init_value[0]) if type(init_value) is list else type(init_value)
            )

            # Set initial values for the specified FMU variables
            if init_value_type is float:
                self.set_fmu_float(init_var, init_value)
            elif init_value_type is int:
                self.set_fmu_int(init_var, init_value)
            elif init_value_type is str:
                self.set_fmu_string(init_var, init_value)
            elif init_value_type is bool:
                self.set_fmu_bool(init_var, init_value)
            else:
                print(f"{self.fmudriver_name} Error: Unsupported initial value type.")
                continue
            self.fmu_data[init_var] = init_value

        # Initialize the FMU states
        if self.model_description.fmiVersion == "3.0":
            self.fmu_instance.enterInitializationMode(startTime=self.start_time)
        elif self.model_description.fmiVersion == "2.0":
            self.fmu_instance.setupExperiment(startTime=self.start_time)
            self.fmu_instance.enterInitializationMode()
        else:
            print(f"{self.fmudriver_name} Error: Unsupported FMI version.")
            return

        # Exit initialization mode to be ready to start stepping
        self.fmu_instance.exitInitializationMode()
        self.fmu_time = self.start_time

    def step_fmu(self, simtime_sec):
        if not self.fmu_instance:
            return

        # ------------------------------------------------------------
        # Write inputs to the FMU from self.in_topic_data and fmu_aux_input_mapping

        # Process every input topic that has been received and stored in self.in_topic_data
        for in_topic, in_var_map in self.in_topic_data.items():
            # print(f"{self.fmudriver_name} Processing input topic '{in_topic}'")
            is_aux_in_topic = in_topic in self.aux_topics_to_subscribe

            # Process each of this topic's variables and values
            for topic_var, in_value in in_var_map.items():
                if (
                    is_aux_in_topic
                    and topic_var
                    not in self.fmu_config_json["fmu_aux_input_mapping"][in_topic]
                ):
                    # Skip if the topic var is an aux topic that's not mapped to an FMU var
                    continue

                if is_aux_in_topic:
                    # Topics in aux_topics_to_subscribe are remapped to FMU var names from the config
                    fmu_var = self.fmu_config_json["fmu_aux_input_mapping"][in_topic][
                        topic_var
                    ]
                else:
                    # Otherwise, component input topics are assumed to match FMU var names
                    fmu_var = topic_var

                fmu_var_type = self.fmu_var_types[fmu_var]
                if fmu_var_type == "Real" or fmu_var_type == "Float64":
                    self.set_fmu_float(fmu_var, in_value)
                elif fmu_var_type == "Integer" or fmu_var_type == "Int64":
                    self.set_fmu_int(fmu_var, in_value)
                elif fmu_var_type == "String":
                    self.set_fmu_string(fmu_var, in_value)
                elif fmu_var_type == "Boolean":
                    self.set_fmu_bool(fmu_var, in_value)
                else:
                    # TODO Handle other FMI 3.0 types
                    print(
                        f"{self.fmudriver_name} WARNING: Unsupported FMU variable type '{fmu_var_type}'"
                    )
                    continue

        # ------------------------------------------------------------
        # Do one step of the FMU

        cur_step_sec = simtime_sec - self.fmu_time
        if cur_step_sec < 0:
            print(
                f"{self.fmudriver_name} WARNING: Negative time step for simtime_sec='{simtime_sec}' fmu_time='{self.fmu_time}'"
            )
            return

        try:
            if self.model_description.fmiVersion == "3.0":
                (
                    _eventEncountered,
                    _terminate_simulation,
                    _early_return,
                    last_successful_time,
                ) = self.fmu_instance.doStep(
                    currentCommunicationPoint=self.fmu_time,
                    communicationStepSize=cur_step_sec,
                )

            elif self.model_description.fmiVersion == "2.0":
                self.fmu_instance.doStep(
                    currentCommunicationPoint=self.fmu_time,
                    communicationStepSize=cur_step_sec,
                )
                _event_encountered = False  # N/A for FMI 2.0
                _terminate_simulation = False  # N/A for FMI 2.0
                _early_return = False  # N/A for FMI 2.0
            last_successful_time = self.fmu_time + cur_step_sec
        except Exception as e:
            print(f"{self.fmudriver_name} ERROR: {e}")
            self._running = False
            return

        # print(f"{self.fmudriver_name} Stepped FMU from {self.fmu_time} to {last_successful_time}")

        # Advance the time
        self.fmu_time = last_successful_time

        # ------------------------------------------------------------
        # Read outputs from the FMU to update self.fmu_data

        # Store latest values for all FMU in/output variables
        for fmu_var, fmu_var_type in self.fmu_var_types.items():
            var_dim = None  # default var_dim to None for scalar variables
            if len(self.fmu_var_dims[fmu_var]) > 0:
                # var_dim is the total number of elements in the n-dimensional array
                var_dim = 1
                for dim in self.fmu_var_dims[fmu_var]:
                    var_dim *= dim
            if fmu_var_type == "Real" or fmu_var_type == "Float64":
                self.fmu_data[fmu_var] = self.get_fmu_float(fmu_var, var_dim)
            elif fmu_var_type == "Integer" or fmu_var_type == "Int64":
                self.fmu_data[fmu_var] = self.get_fmu_int(fmu_var, var_dim)
            elif fmu_var_type == "String":
                self.fmu_data[fmu_var] = self.get_fmu_string(fmu_var, var_dim)
            elif fmu_var_type == "Boolean":
                self.fmu_data[fmu_var] = self.get_fmu_bool(fmu_var, var_dim)
            else:
                # TODO Handle other FMI 3.0 types
                print(
                    f"{self.fmudriver_name} WARNING: Unsupported FMU variable type '{fmu_var_type}'"
                )
                continue

        # Process auxiliary FMU outputs to topics
        if "fmu_aux_output_mapping" in self.fmu_config_json:
            for out_topic, out_var_map in self.fmu_config_json[
                "fmu_aux_output_mapping"
            ].items():
                for out_topic_var, out_fmu_var in out_var_map.items():
                    if out_fmu_var in self.fmu_data:
                        out_val = self.fmu_data[out_fmu_var]
                        self.out_topic_data[out_topic][out_topic_var] = out_val
                    else:
                        # print(
                        #     f"{self.fmudriver_name} WARNING: FMU variable '{out_fmu_var}' not found."
                        # )
                        pass

    def publish_output_data(self, timestamp):
        if "component_output_topics" in self.fmu_config_json:
            output_topics = self.fmu_config_json["component_output_topics"]
            if len(output_topics) > 0:
                for out_topic_info in output_topics:
                    msg_type = out_topic_info["msg_type"]
                    out_topic = out_topic_info["topic"]
                    out_data = {}
                    if msg_type == "aerosim::types::FlightControlCommand":
                        out_data = aerosim_types.FlightControlCommand().to_dict()
                        var_prefix = "flight_control_command"
                    elif msg_type == "aerosim::types::AircraftEffectorCommand":
                        out_data = aerosim_types.AircraftEffectorCommand().to_dict()
                        var_prefix = "aircraft_effector_command"
                    elif msg_type == "aerosim::types::VehicleState":
                        out_data = aerosim_types.VehicleState().to_dict()
                        var_prefix = "vehicle_state"
                    elif msg_type == "aerosim::types::EffectorState":
                        out_data = aerosim_types.EffectorState().to_dict()
                        var_prefix = "effector_state"
                    elif msg_type == "aerosim::types::PrimaryFlightDisplayData":
                        out_data = aerosim_types.PrimaryFlightDisplayData().to_dict()
                        var_prefix = "primary_flight_display_data"
                    elif msg_type == "aerosim::types::TrajectoryVisualization":
                        out_data = aerosim_types.TrajectoryVisualization().to_dict()
                        var_prefix = "trajectory_visualization"
                    elif msg_type == "aerosim::types::GNSS":
                        out_data = aerosim_types.GNSS().to_dict()
                        var_prefix = "gnss"
                    elif msg_type == "aerosim::types::ADSB":
                        out_data = adsb_functions.adsb_from_gnss_data(
                            0.0,
                            0.0,
                            0.0,
                            0.0,
                            0.0,
                            0.0,
                            0.0
                        ).to_dict()
                        var_prefix = "adsb"
                    elif msg_type == "aerosim::types::IMU":
                        out_data = aerosim_types.IMU().to_dict()
                        var_prefix = "imu"
                    else:
                        print(
                            f"{self.fmudriver_name} Warning: Unsupported output message type '{msg_type}'"
                        )
                        continue

                    # print(f"Data to publish: {self.fmu_data}")

                    # Override var_prefix if one is provided
                    if "var_prefix" in out_topic_info:
                        var_prefix = out_topic_info["var_prefix"]

                    # Pack data from FMU into output message dictionary
                    out_data_dotty = dotty(out_data)
                    out_data_flat = flatten_to_dict(out_data)
                    for out_topic_var, _ in out_data_flat.items():
                        fmu_var = var_prefix + "." + out_topic_var
                        if fmu_var in self.fmu_data:
                            out_data_dotty[out_topic_var] = self.fmu_data[fmu_var]
                        else:
                            print(
                                f"{self.fmudriver_name} WARNING: Variable '{out_topic_var}' not found in self.fmu_data."
                            )
                            print(f"Variables are: {self.fmu_data.keys()}")

                    metadata = middleware.Metadata(
                        out_topic, msg_type, timestamp_sim=timestamp
                    )
                    payload = self.serializer.from_json(
                        msg_type, metadata, out_data_dotty.to_dict()
                    )
                    self.transport.publish_raw(msg_type, out_topic, payload)

        if "fmu_aux_output_mapping" in self.fmu_config_json:
            # Publish auxiliary FMU outputs to topics
            for out_topic in self.aux_topics_to_publish:
                data_dict = {}
                # Populate topic dict with latest data
                # fmu_aux_output_mapping is {"topic": {"topic var": "FMU var"}}
                out_var_map = self.fmu_config_json["fmu_aux_output_mapping"][out_topic]
                for out_topic_var, out_fmu_var in out_var_map.items():
                    if out_fmu_var in self.fmu_data:
                        data_dict[out_topic_var] = self.fmu_data[out_fmu_var]
                    else:
                        print(
                            f"WARNING: Aux output FMU variable '{out_fmu_var}' not found self.fmu_data."
                        )

                # We treat auxiliary topics as JsonData because they are not tied to any specific data type.
                msg_type = "aerosim::types::JsonData"
                metadata = middleware.Metadata(
                    out_topic, msg_type, timestamp_sim=timestamp
                )
                payload = self.serializer.serialize_message(
                    metadata, aerosim_types.JsonData(data_dict)
                )
                self.transport.publish_raw(msg_type, out_topic, payload)

    def orchestator_commands_callback(self, data, metadata):
        msg_data = data
        msg_topic = metadata.topic

        with self._processing_callback_lock:
            if not self._running:
                return

            if msg_data["command"] == ("stop"):
                print(f"{self.fmudriver_name} Received orchestrator stop command.")
                self._running = False
                return

            if (
                not self._is_sim_config_loaded
                and msg_topic == "aerosim.orchestrator.commands"
            ):
                # If the sim config hasn't been loaded yet, wait for the orchestrator load command
                if msg_data["command"] == ("load_config"):
                    print(f"{self.fmudriver_name} Received orchestrator load command.")
                    # Load the FMU config into self.fmu_config_json
                    self.fmu_config_json = {}
                    sim_config = msg_data["parameters"]["sim_config"]
                    for fmu_config in sim_config["fmu_models"]:
                        if fmu_config["id"] == self.fmu_id:
                            self.fmu_config_json = fmu_config
                            break
                    if not self.fmu_config_json:
                        print(
                            f"{self.fmudriver_name} Error: FMU ID '{self.fmu_id}' not found in sim config."
                        )
                        return

                    # Process self.fmu_config_json
                    self.load_config()

                    # Subscribe to all of the topics specified in the sim config
                    self.transport.subscribe_all_raw(
                        list(self.all_topics_to_subscribe),
                        self.input_data_callback,
                    )

                    # Load the FMU model file
                    self.load_fmu()

                    # After loading FMU model file to populate self.fmu_var_refs, pass
                    # through the world origin values if the FMU has variables for it
                    if (
                        "world_origin_latitude" in self.fmu_var_refs
                        and "world_origin_longitude" in self.fmu_var_refs
                        and "world_origin_altitude" in self.fmu_var_refs
                    ):
                        self.fmu_config_json["fmu_initial_vals"][
                            "world_origin_latitude"
                        ] = sim_config["world"]["origin"]["latitude"]

                        self.fmu_config_json["fmu_initial_vals"][
                            "world_origin_longitude"
                        ] = sim_config["world"]["origin"]["longitude"]

                        self.fmu_config_json["fmu_initial_vals"][
                            "world_origin_altitude"
                        ] = sim_config["world"]["origin"]["altitude"]

                    self._is_sim_config_loaded = True
                else:
                    print(
                        f"{self.fmudriver_name} Waiting for orchestrator load command..."
                    )
                return

            if (
                not self._is_sim_started
                and msg_topic == "aerosim.orchestrator.commands"
            ):
                # If the sim hasn't started yet, wait for the orchestrator start command
                if msg_data["command"] == "start":
                    print(f"{self.fmudriver_name} Received orchestrator start command.")

                    # Save sim start time from the orchestrator
                    self.sim_start_time = aerosim_types.TimeStamp(
                        msg_data["parameters"]["sim_start_time"]["sec"],
                        msg_data["parameters"]["sim_start_time"]["nanosec"],
                    )

                    initial_timestamp = metadata.timestamp_sim

                    # Initialize the FMU model instance to be ready to start stepping
                    self.init_fmu()

                    # Publish initial value output topics for initial timestamp
                    self.publish_output_data(initial_timestamp)

                    self._is_sim_started = True
                else:
                    print(
                        f"{self.fmudriver_name} Waiting for orchestrator start command..."
                    )
                return

    def clock_callback(self, data, _):
        msg_data = data

        with self._processing_callback_lock:
            if not self._running or not self._is_sim_started:
                return

            timestamp = aerosim_types.TimeStamp(
                msg_data["timestamp_sim"]["sec"],
                msg_data["timestamp_sim"]["nanosec"],
            )
            simtime_as_sec = timestamp.sec + timestamp.nanosec / 1.0e9

            # print(
            #     f"{self.fmudriver_name} Received aerosim.clock message with "
            #     f"t={simtime_sec}"
            # )

            # t1 = time.time()
            self.step_fmu(simtime_as_sec)
            # t2 = time.time()
            # print(f"{self.fmudriver_name} step_fmu t={(t2-t1)*1000:.1f} ms")

            self.publish_output_data(timestamp)

    def input_data_callback(self, payload):
        metadata = self.serializer.deserialize_metadata(payload)
        if metadata.type_name == "aerosim::types::JsonData":
            data = self.serializer.deserialize_data(
                aerosim_types.JsonData, payload
            ).get_data()
        else:
            data = self.serializer.to_json(metadata.type_name, payload)

        with self._processing_callback_lock:
            if not self._running:
                return

            var_prefix = ""
            if metadata.topic not in self.aux_topics_to_subscribe:
                if metadata.type_name == "aerosim::types::VehicleState":
                    var_prefix = "vehicle_state."
                elif metadata.type_name == "aerosim::types::EffectorState":
                    var_prefix = "effector_state."
                elif metadata.type_name == "aerosim::types::AutopilotCommand":
                    var_prefix = "autopilot_command."
                elif metadata.type_name == "aerosim::types::FlightControlCommand":
                    var_prefix = "flight_control_command."
                elif metadata.type_name == "aerosim::types::AircraftEffectorCommand":
                    var_prefix = "aircraft_effector_command."
                elif metadata.type_name == "aerosim::types::PrimaryFlightDisplayData":
                    var_prefix = "primary_flight_display_data."

            # Save data from input topic as flattened dict
            msg_data_flattened = flatten_to_dict(data)
            for in_topic_var, in_val in msg_data_flattened.items():
                self.in_topic_data[metadata.topic][var_prefix + in_topic_var] = in_val

    def stop(self):
        print(f"{self.fmudriver_name} Stop fmu driver")
        self._is_sim_started = False

        with self._processing_callback_lock:
            self._running = False

        # Stop kafka thread first to stop stepping FMU before terminating it
        if self.fmu_instance is not None:
            try:
                self.fmu_instance.terminate()
                self.fmu_instance.freeInstance()
            except Exception as e:
                print(f"Warning: Error when terminating FMU instance: {e}")
        self.fmu_instance = None

        self.reset_data()

        print(f"{self.fmudriver_name} Fmu driver is stopped")
