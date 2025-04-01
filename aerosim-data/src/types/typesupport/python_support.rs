use pyo3::{prelude::*, types::PyCapsule, FromPyObject, IntoPyObjectExt};
use std::ffi::CString;

use crate::{
    middleware::{Metadata, Serializer, SerializerEnum},
    types::AerosimMessage,
};

fn pyserialize_message<T: AerosimMessage + for<'a> FromPyObject<'a>>(
    serializer: &SerializerEnum,
    metadata: &Metadata,
    data: &PyObject,
) -> Option<Vec<u8>> {
    let data = Python::with_gil(|py| data.extract::<T>(py)).ok()?;
    serializer.serialize_message::<T>(metadata, &data)
}

fn pydeserialize_message<T: AerosimMessage + for<'a> IntoPyObject<'a>>(
    serializer: &SerializerEnum,
    payload: &[u8],
) -> Option<(Metadata, PyObject)> {
    let (metadata, data) = serializer.deserialize_message::<T>(payload)?;
    let pyobject = Python::with_gil(|py| data.into_py_any(py)).ok()?;
    Some((metadata, pyobject))
}

fn pydeserialize_metadata(serializer: &SerializerEnum, payload: &[u8]) -> Option<Metadata> {
    serializer.deserialize_metadata(payload)
}

fn pydeserialize_data<T: AerosimMessage + for<'a> IntoPyObject<'a>>(
    serializer: &SerializerEnum,
    payload: &[u8],
) -> Option<PyObject> {
    let data = serializer.deserialize_data::<T>(payload)?;
    let pyobject = Python::with_gil(|py| data.into_py_any(py)).ok()?;
    Some(pyobject)
}

#[derive(Clone)]
pub struct PyTypeSupport {
    pub type_name: String,
    /// Function to serialize a message (metadata and its data) using a specified serializer.
    pub serialize_fn: fn(&SerializerEnum, &Metadata, &PyObject) -> Option<Vec<u8>>,
    /// Function to deserialize bytes into a metadata and its data (PyObject).
    pub deserialize_fn: fn(&SerializerEnum, &[u8]) -> Option<(Metadata, PyObject)>,
    pub deserialize_metadata_fn: fn(&SerializerEnum, &[u8]) -> Option<Metadata>,
    pub deserialize_data_fn: fn(&SerializerEnum, &[u8]) -> Option<PyObject>,
}

impl PyTypeSupport {
    pub fn create<T: AerosimMessage + for<'a> FromPyObject<'a> + for<'a> IntoPyObject<'a>>(
    ) -> Py<PyCapsule> {
        let type_support = PyTypeSupport {
            type_name: T::get_type_name(),
            serialize_fn: pyserialize_message::<T>,
            deserialize_fn: pydeserialize_message::<T>,
            deserialize_metadata_fn: pydeserialize_metadata,
            deserialize_data_fn: pydeserialize_data::<T>,
        };

        Python::with_gil(|py| {
            let name = CString::new("TYPE_SUPPORT").unwrap();
            let cap = PyCapsule::new(py, type_support as PyTypeSupport, Some(name)).unwrap();
            cap.into()
        })
    }

    pub fn extract<'a>(py: Python<'a>, message: &'a PyObject) -> Option<&'a Self> {
        let type_support_pyattr = message.getattr(py, "__type_support__").ok()?;
        let type_support_pycapsule = type_support_pyattr.downcast_bound::<PyCapsule>(py).ok()?;
        Some(unsafe { type_support_pycapsule.reference::<PyTypeSupport>() })
    }

    pub fn serialize_message(
        &self,
        serializer: &SerializerEnum,
        metadata: &Metadata,
        data: &PyObject,
    ) -> Option<Vec<u8>> {
        (self.serialize_fn)(serializer, metadata, data)
    }

    pub fn deserialize_message(
        &self,
        serializer: &SerializerEnum,
        payload: &[u8],
    ) -> Option<(Metadata, PyObject)> {
        (self.deserialize_fn)(serializer, payload)
    }

    pub fn deserialize_metadata(
        &self,
        serializer: &SerializerEnum,
        payload: &[u8],
    ) -> Option<Metadata> {
        (self.deserialize_metadata_fn)(serializer, payload)
    }

    pub fn deserialize_data(
        &self,
        serializer: &SerializerEnum,
        payload: &[u8],
    ) -> Option<PyObject> {
        (self.deserialize_data_fn)(serializer, payload)
    }
}
