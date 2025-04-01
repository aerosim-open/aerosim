# Simulink integration

AeroSim provides a native Simulink integration to enable Simulink models to issue control inputs to the simulation directly from the Simulink runtime environment.

Compatible Simulink models can also be exported as FMUs through [Simulink's FMU export tool](https://www.mathworks.com/help/slcompiler/ug/simulinkfmuexample.html) and these can be used as FMUs equally to standard FMUs. Refer to the [FMU reference](fmu_reference.md) for details on how to use a standard FMU in AeroSim.

The Simulink runtime is integrated into AeroSim through the data middleware layer. Your Simulink model can communicate with AeroSim through topics pubhished by Kafka.

Clone the aerosim-simulink repository into a new folder:

```sh
git clone https://github.com/aerosim-open/aerosim-simulink.git
```

Enter the repo and run the `init_submodules.sh/bat` script:

```sh
./init_submodules.sh # init_submodules.bat on Windows
```

Set up an environment variable to identify the aerosim-simulink repository root. You may want to add this to `.bashrc` in Ubuntu:

```sh
export AEROSIM_SIMULINK_ROOT=/path/to/aerosim-simulink/
```

Then run the `build.sh/bat` script:

```sh
./build.sh # build.bat on Windows
```





