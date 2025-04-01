# import os
# import sys
# import argparse
# from shutil import copytree
# import importlib.resources

# """
# Entrypoint for user is:
# > pip/uv install aerosim
# > python -m aerosim.install

# usage: install.py [-h] [-dev] [-unreal] [-omniverse] [-assets] [-simulink] [-all]

# options:
#   -h, --help  show this help message and exit
#   -dev        Install the developer environment
#   -unreal     Install the Unreal renderer environment
#   -omniverse  Install the Omniverse renderer environment
#   -assets     Install the asset library
#   -simulink   Install the Simulink integration
#   -all        Install all AeroSim components

# Creates env vars:
#   AEROSIM_ROOT,
#   AEROSIM_UNREAL_PROJECT_ROOT
#   AEROSIM_OMNIVERSE_ROOT
#   AEROSIM_ASSETS_ROOT

# User sets env vars:
#   AEROSIM_UNREAL_ENGINE_ROOT
#   OMNIVERSE_ROOT (?) - not sure if this is needed

# Alternatively, this function could just download and call an installer shell script.
# """


# def set_env_var(var_name, var_path, env_var_set=None | dict):
#     print(f"Setting env var {var_name} to '{var_path}'")
#     if os.name == "nt":
#         os.system("setx " + var_name + " " + var_path)
#     elif os.name == "posix":
#         os.system("export " + var_name + "=" + var_path)
#     if env_var_set is not None:
#         env_var_set[var_name] = var_path


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "-dev", help="Install the developer environment", action="store_true"
#     )
#     parser.add_argument(
#         "-unreal", help="Install the Unreal renderer environment", action="store_true"
#     )
#     parser.add_argument(
#         "-omniverse",
#         help="Install the Omniverse renderer environment",
#         action="store_true",
#     )
#     parser.add_argument(
#         "-assets", help="Install the asset library", action="store_true"
#     )
#     parser.add_argument(
#         "-simulink", help="Install the Simulink integration", action="store_true"
#     )
#     parser.add_argument(
#         "-all", help="Install all AeroSim components", action="store_true"
#     )
#     args, unknown = parser.parse_known_args()

#     # If no args are provided, install the default environment
#     if not len(sys.argv) > 1:
#         print("\n----- Installing AeroSim default environment -----")
#         # Manually set the default args for clarity
#         args.dev = False
#         args.unreal = False
#         args.omniverse = False
#         args.assets = False
#         args.simulink = False
#     elif args.all:
#         args.dev = True
#         args.unreal = True
#         args.omniverse = True
#         args.assets = True
#         args.simulink = True

#     cwd = os.getcwd()
#     env_var_set = {}

#     print("\n----- Installing AeroSim prerequisites -----")
#     # Install the required system prereqs
#     # TODO - Add system prereqs

#     # Check if AEROSIM_UNREAL_ENGINE_ROOT env var is set
#     if args.unreal:
#         AEROSIM_UNREAL_ENGINE_ROOT = os.environ.get("AEROSIM_UNREAL_ENGINE_ROOT")
#         if AEROSIM_UNREAL_ENGINE_ROOT:
#             print(f"AEROSIM_UNREAL_ENGINE_ROOT is set to '{AEROSIM_UNREAL_ENGINE_ROOT}'")
#         else:
#             print(
#                 "ERROR: Please set the AEROSIM_UNREAL_ENGINE_ROOT environment variable to the path of your Unreal Engine installation."
#             )
#             sys.exit(1)

#     if args.dev:
#         print("\n----- Installing AeroSim developer environment -----")
#         # Clone 'aerosim' repo
#         os.system("git clone git@github.com:aerosim-open/aerosim.git")
#         # Set AEROSIM_ROOT env var path to the cloned aerosim repo
#         aerosim_root = os.path.join(cwd, "aerosim")
#     else:
#         print("\n----- Installing AeroSim user environment -----")
#         # Copy example demo scripts and configs from aerosim package resources to user's working dir
#         # Set AEROSIM_ROOT env var path to the user's working dir
#         aerosim_root = cwd

#         data_path = importlib.resources.files("aerosim.examples")
#         print(f"Copy examples from aerosim package: {data_path}")
#         copytree(data_path._paths[0], os.path.join(cwd, "aerosim-examples"))

#     set_env_var("AEROSIM_ROOT", aerosim_root, env_var_set)

#     if args.unreal:
#         print("\n----- Installing Unreal renderer environment -----")
#         # Clone AeroSim Unreal project repo
#         os.system(
#             "git clone git@github.com:aerosim-open/aerosim-unreal.git"
#         )
#         # Set AEROSIM_UNREAL_PROJECT_ROOT env var path to the cloned aerosim-unreal repo
#         AEROSIM_UNREAL_PROJECT_ROOT = os.path.join(cwd, "aerosim-unreal")
#         set_env_var("AEROSIM_UNREAL_PROJECT_ROOT", AEROSIM_UNREAL_PROJECT_ROOT, env_var_set)

#     if args.omniverse:
#         print("\n----- Installing Omniverse renderer environment -----")
#         # Clone AeroSim Omniverse Kit app project repo
#         os.system(
#             "git clone git@github.com:aerosim-open/aerosim-omniverse.git"
#         )
#         # Set AEROSIM_OMNIVERSE_ROOT env var path to the cloned aerosim-omniverse repo
#         aerosim_omniverse_root = os.path.join(cwd, "aerosim-omniverse")
#         set_env_var("AEROSIM_OMNIVERSE_ROOT", aerosim_omniverse_root, env_var_set)

#     if args.assets:
#         print("\n----- Installing asset library -----")
#         # Clone AeroSim asset library repo
#         os.system(
#             "git clone git@github.com:aerosim-open/aerosim-assets.git"
#         )
#         # Set AEROSIM_ASSETS_ROOT env var path to the cloned aerosim-assets repo
#         aerosim_assets_root = os.path.join(cwd, "aerosim-assets")
#         set_env_var("AEROSIM_ASSETS_ROOT", aerosim_assets_root, env_var_set)

#         # If Unreal is installed, create a symlink from the Unreal assets to the Unreal project
#         if args.unreal:
#             unreal_content_path = os.path.join(aerosim_assets_root, "Unreal", "Aerosim")
#             unreal_project_content_path = os.path.join(
#                 AEROSIM_UNREAL_PROJECT_ROOT,
#                 "AerosimUE5",
#                 "Content",
#                 "Aerosim",
#             )
#             if os.name == "nt":
#                 # Make a junction link of the Unreal content plugin to the Unreal project
#                 print(
#                     f"Running: mklink /j {unreal_project_content_path} {unreal_content_path}"
#                 )
#                 os.system(
#                     "mklink /j "
#                     + unreal_project_content_path
#                     + " "
#                     + unreal_content_path
#                 )
#             elif os.name == "posix":
#                 # Make a symlink of the Unreal content plugin to the Unreal project
#                 print(
#                     f"Running: ln -s {unreal_content_path} {unreal_project_content_path}"
#                 )
#                 os.system(
#                     "ln -s " + unreal_content_path + " " + unreal_project_content_path
#                 )

#     print("\nAeroSim environment variables were set.")
#     if os.name == "nt":
#         for key, value in env_var_set.items():
#             print(f"{key}={value}")
#         print("IMPORTANT: Restart your terminal to refresh them:")
#     elif os.name == "posix":
#         print("IMPORTANT: Add these to your shell profile to persist them:")
#         print("'''")
#         for key, value in env_var_set.items():
#             print(f"export {key}={value}")
#         print("'''")
