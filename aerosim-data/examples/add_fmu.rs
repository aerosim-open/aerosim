use aerosim_data::interfaces::fmi::{FMI, FMU};

struct BouncingBallFMU {
    height: f64,
    velocity: f64,
}

impl FMI for BouncingBallFMU {
    fn initialize(&mut self) -> Result<(), String> {
        self.height = 1.0;
        self.velocity = 0.0;
        Ok(())
    }

    fn step(&mut self, step_size: f64) -> Result<(), String> {
        let g = 9.81;
        self.height += self.velocity * step_size - 0.5 * g * step_size * step_size;
        self.velocity -= g * step_size;

        if self.height < 0.0 {
            self.height = 0.0;
            self.velocity = -self.velocity * 0.8; // Coefficient of restitution
        }

        Ok(())
    }

    fn terminate(&mut self) -> Result<(), String> {
        Ok(())
    }
}

impl FMU for BouncingBallFMU {
    fn get_variable(&self, name: &str) -> Result<f64, String> {
        match name {
            "height" => Ok(self.height),
            "velocity" => Ok(self.velocity),
            _ => Err(format!("Unknown variable: {}", name)),
        }
    }

    fn set_variable(&mut self, name: &str, value: f64) -> Result<(), String> {
        match name {
            "height" => {
                self.height = value;
                Ok(())
            },
            "velocity" => {
                self.velocity = value;
                Ok(())
            },
            _ => Err(format!("Unknown variable: {}", name)),
        }
    }
}

fn main() {
    let mut fmu = BouncingBallFMU { height: 0.0, velocity: 0.0 };
    fmu.initialize().unwrap();

    println!("Initial height: {}", fmu.get_variable("height").unwrap());

    for _ in 0..100 {
        fmu.step(0.01).unwrap();
        println!("Height: {}, Velocity: {}", 
                 fmu.get_variable("height").unwrap(),
                 fmu.get_variable("velocity").unwrap());
    }

    fmu.terminate().unwrap();
}