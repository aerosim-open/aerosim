use pyo3::prelude::*;

use std::env;
use std::fs;
use std::io::{self, Read};
use std::path::Path;

pub fn read_config_file_internal(file_name: &str) -> io::Result<String> {
    // Get the current working directory (usually the root of the project)
    let binding = env::current_dir().expect("Failed to get current directory");
    let current_dir = binding.to_str().unwrap();

    // Join the current directory with "src/lib.rs" to get the absolute path
    let base_path = current_dir.to_string() + ("/../aerosim-core/config/");
    let full_path_str = base_path.to_string() + file_name;
    let full_path = &fs::canonicalize(&Path::new(&full_path_str)).unwrap();

    if !full_path.exists() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!(
                "The file does not exist in config files in path: {}",
                full_path.display()
            ),
        ));
    }

    // Read file content
    let mut file = fs::File::open(full_path)?;
    let mut content = String::new();
    file.read_to_string(&mut content)?;

    Ok(content)
}

#[pyfunction]
pub fn read_config_file(file_name: &str) -> PyResult<String> {
    match read_config_file_internal(file_name) {
        Ok(content) => Ok(content),
        Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_read_config_file() {
        let config_dir = "config";
        let test_file = "test_file.json";
        let test_path = Path::new(config_dir).join(test_file);

        // Create the file
        fs::create_dir_all(config_dir).unwrap();
        fs::write(&test_path, "Test Config").unwrap();

        // Read the file
        let content = read_config_file(test_file).unwrap();
        assert_eq!(content, "Test Config");

        // Clean up
        fs::remove_file(test_path).unwrap();
    }
}
