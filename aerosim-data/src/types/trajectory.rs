use pyo3::prelude::*;
use pyo3::types::{PyCapsule, PyDict};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::AerosimMessage;

use super::PyTypeSupport;

// ----------------------------------------------------------------------------
// Aircraft Trajectory Visualization Command
//

#[derive(
    Debug, Clone, Serialize, Deserialize, aerosim_macros::AerosimMessage, JsonSchema, Default,
)]
#[pyclass(get_all)]
pub struct TrajectoryVisualization {
    pub settings: TrajectoryVisualizationSettings,
    pub user_defined_waypoints: TrajectoryWaypoints,
    pub future_trajectory: TrajectoryWaypoints,
}

#[pymethods]
impl TrajectoryVisualization {
    #[new]
    #[pyo3(signature = (settings = TrajectoryVisualizationSettings::default(),
    user_defined_waypoints = None,
    future_trajectory = None))]
    pub fn new(
        settings: TrajectoryVisualizationSettings,
        user_defined_waypoints: Option<TrajectoryWaypoints>,
        future_trajectory: Option<TrajectoryWaypoints>,
    ) -> Self {
        let user_defined_waypoints = user_defined_waypoints.unwrap_or_default();
        let future_trajectory = future_trajectory.unwrap_or_default();
        Self {
            settings,
            user_defined_waypoints,
            future_trajectory,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("settings", self.settings.to_dict(py)?)?;
        dict.set_item(
            "user_defined_waypoints",
            self.user_defined_waypoints.to_dict(py)?,
        )?;
        dict.set_item("future_trajectory", self.future_trajectory.to_dict(py)?)?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, aerosim_macros::AerosimMessage, JsonSchema)]
#[pyclass(get_all)]
pub struct TrajectoryVisualizationSettings {
    pub display_future_trajectory: bool,
    pub display_past_trajectory: bool,
    pub highlight_user_defined_waypoints: bool,
    pub number_of_future_waypoints: u64,
}

impl Default for TrajectoryVisualizationSettings {
    fn default() -> TrajectoryVisualizationSettings {
        TrajectoryVisualizationSettings {
            display_future_trajectory: false,
            display_past_trajectory: false,
            highlight_user_defined_waypoints: false,
            number_of_future_waypoints: 1,
        }
    }
}

#[pymethods]
impl TrajectoryVisualizationSettings {
    #[new]
    #[pyo3(signature = (
        display_future_trajectory=TrajectoryVisualizationSettings::default().display_future_trajectory,
        display_past_trajectory=TrajectoryVisualizationSettings::default().display_past_trajectory,
        highlight_user_defined_waypoints=TrajectoryVisualizationSettings::default().highlight_user_defined_waypoints,
        number_of_future_waypoints=TrajectoryVisualizationSettings::default().number_of_future_waypoints
    ))]
    pub fn new(
        display_future_trajectory: bool,
        display_past_trajectory: bool,
        highlight_user_defined_waypoints: bool,
        number_of_future_waypoints: u64,
    ) -> Self {
        TrajectoryVisualizationSettings {
            display_future_trajectory,
            display_past_trajectory,
            highlight_user_defined_waypoints,
            number_of_future_waypoints,
        }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("display_future_trajectory", self.display_future_trajectory)?;
        dict.set_item("display_past_trajectory", self.display_past_trajectory)?;
        dict.set_item(
            "highlight_user_defined_waypoints",
            self.highlight_user_defined_waypoints,
        )?;
        dict.set_item(
            "number_of_future_waypoints",
            self.number_of_future_waypoints,
        )?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}

#[derive(
    Debug, Clone, Serialize, Deserialize, aerosim_macros::AerosimMessage, JsonSchema, Default,
)]
#[pyclass(get_all, set_all)]
pub struct TrajectoryWaypoints {
    pub waypoints: String,
}

#[pymethods]
impl TrajectoryWaypoints {
    #[new]
    #[pyo3(signature = (waypoints="".to_string()))]
    pub fn new(waypoints: String) -> Self {
        Self { waypoints }
    }

    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("waypoints", self.waypoints.clone())?;
        Ok(dict.into())
    }

    #[classattr]
    fn __type_support__() -> Py<PyCapsule> {
        PyTypeSupport::create::<Self>()
    }
}
