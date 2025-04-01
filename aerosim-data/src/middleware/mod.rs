use std::{
    borrow::Cow,
    collections::HashMap,
    error::Error,
    sync::{Arc, RwLock},
};

use async_trait::async_trait;
use ctor::ctor;
use enum_dispatch::enum_dispatch;
use pyo3::{exceptions::PyRuntimeError, prelude::*};
use pythonize::{depythonize, pythonize};
use serde::{Deserialize, Serialize};

use crate::types::{AerosimMessage, PyTypeSupport, TimeStamp, TypeRegistry};

pub mod common;
#[cfg(feature = "dds")]
pub mod dds;
#[cfg(feature = "kafka")]
pub mod kafka;

use common::message;
pub use common::{Message, Metadata};

pub use aerosim_macros::AerosimDeserializeEnum;

#[cfg(feature = "dds")]
pub use dds::{DDSMiddleware, DDSSerializer};
#[cfg(feature = "kafka")]
pub use kafka::{BincodeSerializer, KafkaMiddleware, KafkaSerializer};

pub type CallbackClosureRaw = Box<dyn Fn(&[u8]) -> Result<(), Box<dyn Error>> + Send + Sync>;
pub type CallbackClosure<T> = Box<dyn Fn(T, Metadata) -> Result<(), Box<dyn Error>> + Send + Sync>;

#[enum_dispatch(SerializerEnum)]
pub trait Serializer {
    fn serializer(&self) -> SerializerEnum;

    fn serialize<T: Serialize>(&self, data: &T) -> Option<Vec<u8>>;
    fn deserialize<T: for<'de> Deserialize<'de>>(&self, payload: &[u8]) -> Option<T>;

    fn from_json<T: AerosimMessage>(
        &self,
        metadata: &Metadata,
        data: serde_json::Value,
    ) -> Option<Vec<u8>> {
        let typesupport = TypeRegistry::new().get(&T::get_type_name())?;
        typesupport.from_json(&self.serializer(), metadata, data)
    }
    fn to_json<T: AerosimMessage>(&self, payload: &[u8]) -> Option<serde_json::Value> {
        let typesupport = TypeRegistry::new().get(&T::get_type_name())?;
        typesupport.to_json(&self.serializer(), payload)
    }

    fn serialize_message<T: Clone + Serialize>(
        &self,
        metadata: &Metadata,
        data: &T,
    ) -> Option<Vec<u8>> {
        let message = Message::<T>::new(Cow::Borrowed(metadata), Cow::Borrowed(data));
        self.serialize::<Message<T>>(&message)
    }
    fn deserialize_message<T: Clone + for<'de> Deserialize<'de>>(
        &self,
        payload: &[u8],
    ) -> Option<(Metadata, T)> {
        match self.deserialize::<Message<T>>(payload) {
            Some(message) => Some((message.metadata.into_owned(), message.data.into_owned())),
            None => None,
        }
    }

    fn deserialize_metadata(&self, payload: &[u8]) -> Option<Metadata> {
        match self.deserialize::<message::PartialMessageMetadata>(payload) {
            Some(partial) => Some(partial.metadata),
            None => None,
        }
    }
    // TODO: Investigate how we can deserialize only the data field for CDR.
    // fn deserialize_data<T: for<'de> Deserialize<'de>>(&self, payload: &[u8]) -> Option<T> {
    //     match self.deserialize::<message::PartialMessageData<T>>(payload) {
    //         Some(partial) => Some(partial.data),
    //         None => None,
    //     }
    // }
    fn deserialize_data<T: Clone + for<'de> Deserialize<'de>>(&self, payload: &[u8]) -> Option<T> {
        match self.deserialize::<Message<T>>(payload) {
            Some(message) => Some(message.data.into_owned()),
            None => None,
        }
    }
}

pub trait PySerializer: Serializer {
    fn pyserialize_message_impl(
        &self,
        py: Python<'_>,
        serializer: &SerializerEnum,
        metadata: Metadata,
        data: PyObject,
    ) -> Option<Vec<u8>> {
        let type_support = PyTypeSupport::extract(py, &data)?;
        type_support.serialize_message(serializer, &metadata, &data)
    }

    fn pydeserialize_message_impl(
        &self,
        py: Python<'_>,
        serializer: &SerializerEnum,
        message_type: PyObject,
        payload: &[u8],
    ) -> Option<(Metadata, PyObject)> {
        let type_support = PyTypeSupport::extract(py, &message_type)?;
        type_support.deserialize_message(serializer, payload)
    }

    fn pydeserialize_metadata_impl(
        &self,
        _py: Python<'_>,
        _serializer: &SerializerEnum,
        payload: &[u8],
    ) -> Option<Metadata> {
        self.deserialize_metadata(payload)
    }

    fn pydeserialize_data_impl(
        &self,
        py: Python<'_>,
        serializer: &SerializerEnum,
        message_type: PyObject,
        payload: &[u8],
    ) -> Option<PyObject> {
        let type_support = PyTypeSupport::extract(py, &message_type)?;
        type_support.deserialize_data(serializer, payload)
    }

    fn pyserialize_from_json_impl(
        &self,
        py: Python<'_>,
        serializer: &SerializerEnum,
        type_name: &str,
        metadata: &Metadata,
        data: PyObject,
    ) -> Option<Vec<u8>> {
        let data = depythonize::<serde_json::Value>(&data.into_bound(py)).ok()?;
        let typesupport = TypeRegistry::new().get(type_name)?;
        typesupport.from_json(serializer, metadata, data)
    }

    fn pydeserialize_to_json_impl(
        &self,
        py: Python<'_>,
        serializer: &SerializerEnum,
        type_name: &str,
        payload: &[u8],
    ) -> Option<PyObject> {
        let typesupport = TypeRegistry::new().get(type_name)?;
        let data = typesupport.to_json(serializer, payload)?;
        let pyobject = pythonize(py, &data).ok()?;
        Some(pyobject.into())
    }
}

#[async_trait]
#[enum_dispatch(MiddlewareEnum)]
pub trait MiddlewareRaw: Send + Sync {
    async fn publish_raw(
        &self,
        message_type: &str,
        topic: &str,
        payload: &[u8],
    ) -> Result<(), Box<dyn Error>>;
    async fn subscribe_raw(
        &self,
        message_type: &str,
        topic: &str,
        callback: CallbackClosureRaw,
    ) -> Result<(), Box<dyn Error>>;
    async fn subscribe_all_raw(
        &self,
        topics: Vec<(String, String)>,
        callback: CallbackClosureRaw,
    ) -> Result<(), Box<dyn Error>>;
    fn shutdown_raw(&self) {}
}

#[async_trait]
#[enum_dispatch(MiddlewareEnum)]
pub trait Middleware: MiddlewareRaw {
    fn get_serializer(&self) -> SerializerEnum;

    async fn publish<T: AerosimMessage + 'static>(
        &self,
        topic: &str,
        message: &T,
        timestamp_sim: Option<TimeStamp>,
    ) -> Result<(), Box<dyn Error>> {
        let metadata = Metadata::new(
            topic,
            &T::get_type_name(),
            timestamp_sim,
            Some(TimeStamp::now()),
        );
        let payload = self
            .get_serializer()
            .serialize_message::<T>(&metadata, &message)
            .ok_or(format!(
                "Could not serialize topic data '{}'",
                &T::get_type_name()
            ))?;
        self.publish_raw(&T::get_type_name(), topic, &payload).await
    }

    async fn subscribe<T: AerosimMessage + 'static>(
        &self,
        topic: &str,
        callback: CallbackClosure<T>,
    ) -> Result<(), Box<dyn Error>> {
        let serializer = self.get_serializer();
        let raw_callback = Box::new(move |payload: &[u8]| {
            let (metadata, data) = serializer.deserialize_message::<T>(payload).ok_or(format!(
                "Could not deserialize topic data '{}'",
                &T::get_type_name()
            ))?;
            callback(data, metadata)
        });
        self.subscribe_raw(&T::get_type_name(), topic, raw_callback)
            .await
    }

    async fn subscribe_all<T: AerosimMessage + 'static>(
        &self,
        topics: Vec<String>,
        callback: CallbackClosure<T>,
    ) -> Result<(), Box<dyn Error>> {
        let serializer = self.get_serializer();
        let raw_callback = Box::new(move |payload: &[u8]| {
            let (metadata, data) = serializer.deserialize_message::<T>(payload).ok_or(format!(
                "Could not deserialize topic data '{}'",
                &T::get_type_name()
            ))?;
            callback(data, metadata)
        });
        let topics: Vec<(String, String)> = topics
            .into_iter()
            .map(|topic| (T::get_type_name(), topic))
            .collect();
        self.subscribe_all_raw(topics, raw_callback).await
    }

    fn shutdown(&self) {
        self.shutdown_raw();
    }
}

trait PyMiddleware: Middleware {
    async fn pypublish_impl(
        &self,
        py: Python<'_>,
        topic: &str,
        message: PyObject,
        timestamp_sim: Option<TimeStamp>,
    ) -> PyResult<()> {
        let type_support = PyTypeSupport::extract(py, &message).ok_or(PyRuntimeError::new_err(
            format!("Failed to extract PyTypeSupport from python object"),
        ))?;
        let metadata = Metadata::new(
            topic,
            &type_support.type_name,
            timestamp_sim,
            Some(TimeStamp::now()),
        );
        let payload = type_support
            .serialize_message(&self.get_serializer(), &metadata, &message)
            .ok_or(PyRuntimeError::new_err(format!(
                "Failed to serialize python object"
            )))?;
        self.publish_raw(&type_support.type_name, topic, &payload)
            .await
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to publish topic data: {}", e)))
    }

    async fn pysubscribe_impl(
        &self,
        py: Python<'_>,
        message_type: PyObject,
        topic: &str,
        callback: PyObject,
    ) -> PyResult<()> {
        let type_support = PyTypeSupport::extract(py, &message_type)
            .ok_or(PyRuntimeError::new_err(format!(
                "Failed to extract PyTypeSupport from python object"
            )))?
            .clone();
        let message_type = type_support.type_name.clone();

        let serializer = self.get_serializer();
        let rust_callback = Box::new(move |data: &[u8]| {
            let _ = Python::with_gil(|py| {
                let (metadata, pyobject) = match type_support.deserialize_message(&serializer, data)
                {
                    Some((metadata, pyobject)) => (metadata, pyobject),
                    None => {
                        eprintln!("Could not deserialize data to {}", &type_support.type_name);
                        return Err(format!("Failed to deserialize data to: {}", &type_support.type_name));
                    }
                };
                if let Err(e) = callback.call(py, (pyobject, metadata), None) {
                    eprintln!("Error calling Python callback: {:?}", e);
                    return Err(format!("Python callback failed: {:?}", e));
                }
                Ok(())
            });
            Ok(())
        });

        self.subscribe_raw(&message_type, topic, rust_callback)
            .await
            .map_err(|e| {
                PyRuntimeError::new_err(format!("Failed to deserialize from Python object: {}", e))
            })
    }

    async fn pysubscribe_all_impl(
        &self,
        py: Python<'_>,
        message_type: PyObject,
        topics: Vec<String>,
        callback: PyObject,
    ) -> PyResult<()> {
        let type_support = PyTypeSupport::extract(py, &message_type)
            .ok_or(PyRuntimeError::new_err(format!(
                "Failed to extract PyTypeSupport from python object"
            )))?
            .clone();
        let message_type = type_support.type_name.clone();

        let serializer = self.get_serializer();
        let rust_callback = Box::new(move |data: &[u8]| {
            let _ = Python::with_gil(|py| {
                let (metadata, pyobject) = match type_support.deserialize_message(&serializer, data)
                {
                    Some((metadata, pyobject)) => (metadata, pyobject),
                    None => {
                        eprintln!("Could not deserialize data to {}", &type_support.type_name);
                        return Err(format!("Failed to deserialize data to: {}", &type_support.type_name));
                    }
                };
                if let Err(e) = callback.call(py, (pyobject, metadata), None) {
                    eprintln!("Error calling Python callback: {:?}", e);
                    return Err(format!("Python callback failed: {:?}", e));
                }
                Ok(())
            });
            Ok(())
        });
        let topics: Vec<(String, String)> = topics
            .into_iter()
            .map(|topic| (message_type.clone(), topic))
            .collect();
        self.subscribe_all_raw(topics, rust_callback)
            .await
            .map_err(|e| {
                PyRuntimeError::new_err(format!("Failed to deserialize from Python object: {}", e))
            })
    }

    async fn pypublish_raw_impl(
        &self,
        py: Python<'_>,
        message_type: &str,
        topic: &str,
        payload: Py<pyo3::types::PyBytes>,
    ) -> PyResult<()> {
        self.publish_raw(message_type, topic, payload.as_bytes(py))
            .await
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to publish topic data: {}", e)))
    }

    async fn pysubscribe_raw_impl(
        &self,
        _py: Python<'_>,
        message_type: &str,
        topic: &str,
        callback: PyObject,
    ) -> PyResult<()> {
        let rust_callback = Box::new(move |data: &[u8]| {
            Python::with_gil(|py| match callback.call(py, (data,), None) {
                Ok(_) => {}
                Err(e) => eprintln!("Error calling Python callback: {:?}", e),
            });
            Ok(())
        });

        self.subscribe_raw(&message_type, topic, rust_callback)
            .await
            .map_err(|e| {
                PyRuntimeError::new_err(format!("Failed to deserialize from Python object: {}", e))
            })
    }

    async fn pysubscribe_all_raw_impl(
        &self,
        _py: Python<'_>,
        topics: Vec<(String, String)>,
        callback: PyObject,
    ) -> PyResult<()> {
        let rust_callback = Box::new(move |data: &[u8]| {
            Python::with_gil(|py| match callback.call(py, (data,), None) {
                Ok(_) => {}
                Err(e) => eprintln!("Error calling Python callback: {:?}", e),
            });
            Ok(())
        });
        self.subscribe_all_raw(topics, rust_callback)
            .await
            .map_err(|e| {
                PyRuntimeError::new_err(format!("Failed to deserialize from Python object: {}", e))
            })
    }
}

#[enum_dispatch]
pub enum MiddlewareEnum {
    #[cfg(feature = "dds")]
    DDSMiddleware,
    #[cfg(feature = "kafka")]
    KafkaMiddleware,
}

#[enum_dispatch]
pub enum SerializerEnum {
    #[cfg(feature = "dds")]
    DDSSerializer,
    #[cfg(feature = "kafka")]
    KafkaSerializer,
    #[cfg(feature = "kafka")]
    BincodeSerializer,
}

pub struct MiddlewareRegistry {
    middlewares: RwLock<HashMap<String, Arc<MiddlewareEnum>>>,
}

impl MiddlewareRegistry {
    fn create() -> Self {
        MiddlewareRegistry {
            middlewares: RwLock::new(HashMap::new()),
        }
    }

    pub fn new() -> &'static Self {
        &MIDDLEWARE_REGISTRY
    }

    pub fn register(&self, name: &str, middleware: MiddlewareEnum) -> Result<(), String> {
        let mut middlewares = self.middlewares.write().unwrap();
        match middlewares.insert(name.to_string(), Arc::new(middleware)) {
            Some(_) => Err(format!(
                "A middleware named `{}` is already registered",
                name
            )),
            None => Ok(()),
        }
    }

    pub fn get(&self, name: &str) -> Option<Arc<MiddlewareEnum>> {
        let middlewares = self.middlewares.read().unwrap();
        middlewares.get(name).map(|m| Arc::clone(m))
    }
}

#[ctor]
static MIDDLEWARE_REGISTRY: MiddlewareRegistry = {
    let registry = MiddlewareRegistry::create();
    #[cfg(feature = "dds")]
    registry
        .register("dds", MiddlewareEnum::from(DDSMiddleware::new()))
        .ok();
    #[cfg(feature = "kafka")]
    registry
        .register("kafka", MiddlewareEnum::from(KafkaMiddleware::new()))
        .ok();
    registry
};
