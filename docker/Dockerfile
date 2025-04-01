FROM ubuntu:22.04

# Set noninteractive frontend to avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    cmake \
    git-lfs \
    openjdk-21-jdk \
    software-properties-common && \
    rm -rf /var/lib/apt/lists/*

# Install Python 3.12 and development headers
RUN	add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y python3.12 python3.12-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Verify Python 3.12 installation
RUN python3.12 --version

# Create a non-root user
RUN useradd -m -s /bin/bash aerosimuser

# Switch to non-root user
USER aerosimuser
WORKDIR /home/aerosimuser
ENV HOME=/home/aerosimuser

# Ensure Cargo has the right permissions
RUN mkdir -p /home/aerosimuser/.cargo && chown -R aerosimuser:aerosimuser /home/aerosimuser/.cargo
ENV CARGO_HOME="/home/aerosimuser/.cargo"

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="${HOME}/.cargo/bin:${PATH}"


# Install Rye
RUN curl -sSf https://rye.astral.sh/get | RYE_INSTALL_OPTION="--yes" bash
ENV PATH="${HOME}/.rye/shims:${PATH}"

# Create cache directory
RUN mkdir -p /home/aerosimuser/.cache/buildx

# Copy project files
COPY --chown=aerosimuser:aerosimuser . /home/aerosimuser/app

# Set working directory
WORKDIR /home/aerosimuser/app

# Initialize submodules
# RUN ./init_submodules.sh

# Set up Python environment
RUN rye sync --no-dev && \
    rye sync && \
    . .venv/bin/activate && \
    # Verify maturin was installed by rye based on pyproject.toml
    maturin --version

# Set .venv/bin/python as the default Python interpreter
RUN echo "source /home/aerosimuser/app/.venv/bin/activate" >> ~/.bashrc
# Add .venv/bin to PATH
ENV PATH="/home/aerosimuser/app/.venv/bin:${PATH}"

# Build all projects; This will help cache dependencies and raise build errors early
# RUN rye build -a

## Build AeroSim Rust packages/libraries
#RUN rust_packages="aerosim-core \
#aerosim-data \
#aerosim-orchestrator \
#aerosim-renderer-adapter-rtx \
#aerosim-renderer-adapter-ue5 \
#aerosim-sensors" && \
#	for package in ${rust_packages}; do \
#        cd "$package" && \
#        cargo build --verbose && \
#        cd ../; \
#    done
#
## Set the default command to run tests
# CMD ["bash", "-c", "echo 'Run tests using GitHub Actions'"]

# Entry point
CMD ["/bin/bash"]
