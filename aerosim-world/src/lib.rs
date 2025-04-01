pub mod data_manager;
pub mod logging;
pub mod orchestrator;
pub mod scene_graph;
pub mod sim_clock;
pub mod components;

use pyo3::prelude::*;

// -------------------------------------------------------------------------
// Python module exports
#[pymodule]
fn _aerosim_world(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<orchestrator::Orchestrator>()?;
    Ok(())
}
