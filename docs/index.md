# AeroSim documentation

Welcome to the AeroSim documentation! 

AeroSim is a scalable, performant flight simulator for use in aerospace engineering and software development. It is designed to integrate seemlessly with standard tools widely used in the AeroSpace industry through standardized interfaces and data formats. A modular design supports configuration, modification and 3rd party integration making it adaptable to an extensive range of use cases. 

Through the standardized Functional Mockup Interface (FMI), AeroSim supports straighforward integration of custom dynamics models, sensor models and controllers made with any tools complying to the FMI standard. AeroSim's components communicate using standardized data formats through a data middleware layer (Kafka or DDS), coordinated by a performant and configurable orchestrator and globally synchronized simulation state data-store. This enables the simulator to interface with multiple high-fidelity sensor renderers and allows switching or modifying individual components without the need for system-wide modification. 

AeroSim is provided with an easy-to-use Python API, allowing extensive control over the simulation without sacrificing accessibility. This means that simple simulations can be set up in minutes while deeper control is available for more complex scenarios. The source code is provided for developers interested in extensive adjustment for custom deployments while packaged versions are also available for users looking to bootstrap simulation projects rapidly. 

## Getting started

* [__AeroSim overview__](overview.md)
* [__Build AeroSim in Linux__](build_linux.md)
* [__Build AeroSim in Windows__](build_windows.md)
* [__First steps tutorial__](first_steps.md)

## Resources

* [__Messages reference__](messages.md)
* [__Simulation configuration reference__](sim_config.md)
