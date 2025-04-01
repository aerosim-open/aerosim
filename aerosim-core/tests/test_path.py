# We are going to test the read_trajectory_json function from aerosim_core
from aerosim_core import read_trajectory_json


def main():
    jsoncontent = read_trajectory_json("topics_needed.json")
    print(jsoncontent)

if __name__ == "__main__":
    main()
