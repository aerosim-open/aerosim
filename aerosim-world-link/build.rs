use std::env;
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    if env::consts::OS == "linux" {
        println!("cargo:rustc-link-lib=pthread");
    }

    let crate_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let mut config: cbindgen::Config = Default::default();
    config.language = cbindgen::Language::C;
    cbindgen::Builder::new()
        .with_crate(crate_dir)
        .with_config(config)
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file("lib/aerosim_world_link.h");
    Ok(())
}
