pub trait FMI {
    fn initialize(&mut self) -> Result<(), String>;
    fn step(&mut self, step_size: f64) -> Result<(), String>;
    fn terminate(&mut self) -> Result<(), String>;
}

pub trait FMU: FMI {
    fn get_variable(&self, name: &str) -> Result<f64, String>;
    fn set_variable(&mut self, name: &str, value: f64) -> Result<(), String>;
}