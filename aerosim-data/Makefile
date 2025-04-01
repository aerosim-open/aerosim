.PHONY: all clean rust python cpp

all: rust python cpp

rust:
	cargo build --release

python:
	python3 -m pip install .

cpp:
	mkdir -p build && cd build && cmake .. && make

clean:
	cargo clean
	rm -rf build
	rm -rf *.egg-info