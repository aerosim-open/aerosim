use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

pub mod scenario;
use crate::scenario::read_scenario_json;
use crate::scenario::write_scenario_json;
use crate::scenario::Scenario;
use crate::scenario::WeatherScenarioData;
use crate::scenario::ActorScenarioData;
use crate::scenario::TrajectoryScenarioData;
use crate::scenario::SensorScenarioData;

pub mod scenario_translator;
use crate::scenario_translator::ConfigGenerator;
// PyO3 Module Definition
#[pymodule]
fn _scenarios(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Scenario>()?;
    m.add_class::<WeatherScenarioData>()?;
    m.add_class::<ActorScenarioData>()?;
    m.add_class::<TrajectoryScenarioData>()?;
    m.add_class::<SensorScenarioData>()?;
    m.add_class::<ConfigGenerator>()?;
    m.add_function(wrap_pyfunction!(read_scenario_json, m)?)?;
    m.add_function(wrap_pyfunction!(write_scenario_json, m)?)?;
    Ok(())
}
