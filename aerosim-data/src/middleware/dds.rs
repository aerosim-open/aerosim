use std::{
    collections::HashMap,
    error::Error,
    mem::ManuallyDrop,
    sync::{Arc, Mutex},
};

use async_trait::async_trait;
use cdr::{CdrLe, Infinite};
use pyo3::{exceptions::PyRuntimeError, prelude::*};
use serde::{Deserialize, Serialize};

use crate::{
    middleware::{
        CallbackClosureRaw, Metadata, Middleware, MiddlewareRaw, PyMiddleware, PySerializer,
        Serializer, SerializerEnum,
    },
    types::TimeStamp,
};

// Safe abstraction for cyclonedds and cyclors.
mod cyclonedds {

    use std::{
        ffi::CString,
        mem::MaybeUninit,
        slice,
        sync::{Arc, Mutex},
    };

    use cyclors::*;

    use crate::middleware::CallbackClosureRaw;

    pub type DDSParticipant = i32;
    pub type DDSTopic = i32;

    pub struct DDSWriter {
        pub entity: dds_entity_t,
        topic: dds_entity_t,
        qos: *mut dds_qos_t,
    }
    unsafe impl Sync for DDSWriter {}
    unsafe impl Send for DDSWriter {}
    impl Drop for DDSWriter {
        fn drop(&mut self) {
            unsafe {
                dds_delete(self.entity);
                dds_delete(self.topic);
                dds_delete_qos(self.qos);
            }
        }
    }

    pub struct DDSReader {
        pub entity: dds_entity_t,
        topic: dds_entity_t,
        qos: *mut dds_qos_t,
        listener: *mut dds_listener_t,
        callback: *mut std::os::raw::c_void,
    }
    unsafe impl Sync for DDSReader {}
    unsafe impl Send for DDSReader {}
    impl Drop for DDSReader {
        fn drop(&mut self) {
            unsafe {
                dds_delete(self.entity);
                dds_delete(self.topic);
                dds_delete_qos(self.qos);
                dds_delete_listener(self.listener);
                Arc::new(Arc::from_raw(self.callback));
            }
        }
    }

    pub struct DDSSample {
        serdata: *mut ddsi_serdata,
        iovec: ddsrt_iovec_t,
    }

    impl DDSSample {
        pub fn payload(&self) -> &[u8] {
            unsafe {
                slice::from_raw_parts(
                    self.iovec.iov_base as *const u8,
                    self.iovec.iov_len.try_into().unwrap(),
                )
            }
        }
    }

    impl Drop for DDSSample {
        fn drop(&mut self) {
            unsafe {
                // Unlock serialized data (ref previously filled by ddsi_serdata_to_ref) and release it.
                ddsi_serdata_to_ser_unref(self.serdata, &self.iovec);
                ddsi_serdata_unref(self.serdata);
            }
        }
    }

    pub fn create_participant(domain: u32) -> Option<DDSParticipant> {
        let participant =
            unsafe { dds_create_participant(domain, std::ptr::null(), std::ptr::null()) };
        match participant > 0 {
            true => Some(participant),
            false => None,
        }
    }

    pub fn create_topic(
        participant: i32,
        topic_name: &str,
        type_name: &str,
        is_keyless: bool,
    ) -> Option<DDSTopic> {
        let ctopic = CString::new(topic_name.to_owned()).unwrap().into_raw();
        let ctype = CString::new(type_name.to_owned()).unwrap().into_raw();

        let topic = unsafe {
            cdds_create_blob_topic(
                participant,
                ctopic,
                ctype,
                is_keyless, // TODO: Keyless topic. Revisit.
            )
        };

        // Explicitly drop `ctopic` and `ctype` to prevent memory leaks,
        // since CycloneDDS does not does not appear to manage the memory of these strings.
        unsafe {
            drop(CString::from_raw(ctopic));
            drop(CString::from_raw(ctype));
        }

        match topic >= 0 {
            true => Some(topic),
            false => None,
        }
    }

    fn create_qos() -> Option<*mut dds_qos> {
        let qos = cyclors::qos::Qos::default();
        let qos_ptr = unsafe { qos.to_qos_native() };
        match !qos_ptr.is_null() {
            true => Some(qos_ptr),
            false => None,
        }
    }

    pub fn create_writer(participant: DDSParticipant, topic: DDSTopic) -> Option<DDSWriter> {
        let qos_ptr = create_qos()?;
        let writer =
            unsafe { dds_create_writer(participant, topic, qos_ptr, std::ptr::null_mut()) };
        match writer > 0 {
            true => Some(DDSWriter {
                entity: writer,
                topic: topic,
                qos: qos_ptr,
            }),
            false => None,
        }
    }

    pub fn create_reader(
        participant: DDSParticipant,
        topic: DDSTopic,
        callback: CallbackClosureRaw,
    ) -> Option<DDSReader> {
        let qos_ptr = create_qos()?;
        let args = Arc::into_raw(Arc::new(Mutex::new(callback))) as *mut std::os::raw::c_void;
        let listener_ptr = create_listener(args)?;

        let reader = unsafe { dds_create_reader(participant, topic, qos_ptr, listener_ptr) };
        match reader > 0 {
            true => Some(DDSReader {
                entity: reader,
                topic: topic,
                qos: qos_ptr,
                listener: listener_ptr,
                callback: args,
            }),
            false => None,
        }
    }

    fn create_listener(callback: *mut std::os::raw::c_void) -> Option<*mut dds_listener> {
        let listener = unsafe {
            let listener = dds_create_listener(callback);
            dds_lset_data_available(listener, Some(super::listener_callback));
            listener
        };
        match !listener.is_null() {
            true => Some(listener),
            false => None,
        }
    }

    fn get_entity_sertype(entity: i32) -> Option<*const ddsi_sertype> {
        let mut sertype_ptr: *const ddsi_sertype = std::ptr::null_mut();
        let ret = unsafe { dds_get_entity_sertype(entity, &mut sertype_ptr) };
        match ret >= 0 && !sertype_ptr.is_null() {
            true => Some(sertype_ptr),
            false => None,
        }
    }

    fn serdata_from_ser_iov(
        sertype_ptr: *const ddsi_sertype,
        data: &ddsrt_iovec_t,
        len: usize,
    ) -> Option<*mut ddsi_serdata> {
        let serdata_ptr = unsafe {
            ddsi_serdata_from_ser_iov(sertype_ptr, ddsi_serdata_kind_SDK_DATA, 1, data, len)
        };
        match !serdata_ptr.is_null() {
            true => Some(serdata_ptr),
            false => None,
        }
    }

    fn ser_iov_from_serdata(serdata: *mut ddsi_serdata) -> Option<ddsrt_iovec_t> {
        let mut data = ddsrt_iovec_t {
            iov_base: std::ptr::null_mut(),
            iov_len: 0,
        };

        unsafe {
            let size = ddsi_serdata_size(serdata);
            ddsi_serdata_to_ser_ref(serdata, 0, size as usize, &mut data);
        };
        match !data.iov_base.is_null() | !data.iov_base.is_aligned() {
            true => Some(data),
            false => None,
        }
    }

    pub fn write(writer: i32, encoded: &[u8]) -> Result<(), String> {
        let data = ddsrt_iovec_t {
            iov_base: encoded.as_ptr() as *mut std::ffi::c_void,
            iov_len: encoded.len().try_into().unwrap(),
        };

        let sertype_ptr = get_entity_sertype(writer).ok_or("Could not get entity sertype")?;
        let serdata_ptr = serdata_from_ser_iov(sertype_ptr, &data, encoded.len())
            .ok_or("Could not create serdata from iovec")?;
        let ret = unsafe { dds_writecdr(writer, serdata_ptr) };
        match ret == 0 {
            true => Ok(()),
            false => Err(format!("Could not write CDR data")),
        }
    }

    pub fn read(reader: i32) -> Result<DDSSample, String> {
        let mut serdata: *mut ddsi_serdata = std::ptr::null_mut();
        let mut si = MaybeUninit::<[dds_sample_info_t; 1]>::uninit();

        let ret = unsafe {
            dds_takecdr(
                reader,
                &mut serdata,
                1,
                si.as_mut_ptr() as *mut dds_sample_info_t,
                DDS_ANY_STATE,
            )
        };
        if ret != 1 {
            return Err(format!("Could not read CDR data"));
        };

        let iovec = ser_iov_from_serdata(serdata).ok_or("Could not create iovec from serdata")?;
        Ok(DDSSample { serdata, iovec })
    }

    pub fn delete_dds_entity(entity: dds_entity_t) -> Result<(), String> {
        unsafe {
            let r = dds_delete(entity);
            match r {
                0 | DDS_RETCODE_ALREADY_DELETED => Ok(()),
                e => Err(format!("Error deleting DDS entity - retcode={e}")),
            }
        }
    }
}

#[pyclass]
pub struct DDSSerializer;

impl Serializer for DDSSerializer {
    fn serializer(&self) -> SerializerEnum {
        SerializerEnum::from(Self {})
    }

    fn serialize<T: Serialize>(&self, data: &T) -> Option<Vec<u8>> {
        cdr::serialize::<_, _, CdrLe>(data, Infinite).ok()
    }

    fn deserialize<T: for<'de> Deserialize<'de>>(&self, payload: &[u8]) -> Option<T> {
        cdr::deserialize_from::<_, T, _>(payload, Infinite).ok()
    }
}

#[pyclass]
pub struct DDSMiddleware {
    participant: cyclonedds::DDSParticipant,
    writers: Mutex<HashMap<String, Arc<cyclonedds::DDSWriter>>>,
    readers: Mutex<HashMap<String, Arc<cyclonedds::DDSReader>>>,
}

impl DDSMiddleware {
    pub fn new() -> Self {
        // TODO: domain hardcoded to 0.
        let participant = cyclonedds::create_participant(0).unwrap();
        DDSMiddleware {
            participant,
            writers: Mutex::new(HashMap::new()),
            readers: Mutex::new(HashMap::new()),
        }
    }
}

#[async_trait]
impl MiddlewareRaw for DDSMiddleware {
    async fn publish_raw(
        &self,
        message_type: &str,
        topic: &str,
        payload: &[u8],
    ) -> Result<(), Box<dyn Error>> {
        let writer: Arc<cyclonedds::DDSWriter> = {
            let mut writers = self.writers.lock().unwrap();

            if !writers.contains_key(topic) {
                let dds_topic =
                    cyclonedds::create_topic(self.participant, topic, message_type, true)
                        .ok_or("Could not create DDS topic")?;

                // Create writer.
                let _writer = cyclonedds::create_writer(self.participant, dds_topic)
                    .ok_or("Could not create DDS writer")?;

                writers.insert(topic.to_string(), Arc::new(_writer));
            }

            match writers.get(topic).cloned() {
                Some(writer) => Some(writer),
                None => None,
            }
        }
        .ok_or("Could not retrieve DDS writer")?;

        // Write message.
        cyclonedds::write(writer.entity, payload)?;

        Ok(())
    }

    async fn subscribe_raw(
        &self,
        message_type: &str,
        topic: &str,
        callback: CallbackClosureRaw,
    ) -> Result<(), Box<dyn Error>> {
        let dds_topic = cyclonedds::create_topic(self.participant, topic, message_type, true)
            .ok_or("Could not create DDS topic")?;

        let reader = cyclonedds::create_reader(self.participant, dds_topic, callback)
            .ok_or("Could not create DDS reader")?;

        {
            let mut readers = self.readers.lock().unwrap();
            readers.insert(topic.to_string(), Arc::new(reader));
        }
        Ok(())
    }

    async fn subscribe_all_raw(
        &self,
        _topics: Vec<(String, String)>,
        _callback: CallbackClosureRaw,
    ) -> Result<(), Box<dyn Error>> {
        Ok(())
    }

    fn shutdown_raw(&self) {
        // Clear and drop any created writer.
        {
            let mut writers = self.writers.lock().unwrap();
            writers.clear();
        }
        // Clear and drop any created reader.
        {
            let mut readers = self.readers.lock().unwrap();
            readers.clear();
        }
        cyclonedds::delete_dds_entity(self.participant).ok();
    }
}

pub extern "C" fn listener_callback(entity: i32, arg: *mut std::os::raw::c_void) {
    // Read message.
    let sample = match cyclonedds::read(entity) {
        Ok(sample) => sample,
        Err(err) => {
            eprintln!("{}", err);
            return;
        }
    };

    let payload = sample.payload();

    // Wrapping the callback in ManuallyDrop to avoid prematurely dropping it.
    let arguments: ManuallyDrop<Arc<Mutex<CallbackClosureRaw>>> =
        unsafe { ManuallyDrop::new(Arc::from_raw(arg as *mut _)) };
    match arguments.lock() {
        Ok(lock) => {
            let callback = &*lock;
            match callback(payload) {
                Ok(_) => return,
                Err(err) => {
                    eprintln!("{}", err);
                    return;
                }
            }
        }
        Err(err) => {
            eprintln!("{}", err);
            return;
        }
    };
}

#[async_trait]
impl Middleware for DDSMiddleware {
    fn get_serializer(&self) -> SerializerEnum {
        SerializerEnum::from(DDSSerializer {})
    }
}

impl PyMiddleware for DDSMiddleware {}

#[pymethods]
impl DDSMiddleware {
    #[new]
    fn pynew(_py: Python) -> PyResult<Self> {
        Ok(Self::new())
    }

    #[pyo3(name = "publish")]
    #[pyo3(signature = (topic, message, timestamp_sim=None))]
    fn pypublish(
        &self,
        py: Python,
        topic: &str,
        message: PyObject,
        timestamp_sim: Option<TimeStamp>,
    ) -> PyResult<()> {
        futures::executor::block_on(self.pypublish_impl(py, topic, message, timestamp_sim))
    }

    #[pyo3(name = "subscribe")]
    fn pysubscribe(
        &self,
        py: Python,
        message_type: PyObject,
        topic: &str,
        callback: PyObject,
    ) -> PyResult<()> {
        futures::executor::block_on(self.pysubscribe_impl(py, message_type, topic, callback))
    }

    #[pyo3(name = "subscribe_all")]
    fn pysubscribe_all(
        &self,
        _py: Python,
        _message_type: PyObject,
        _topics: PyObject,
        _callback: PyObject,
    ) -> PyResult<()> {
        Err(PyRuntimeError::new_err(format!(
            "'subscribe_all' not implemented for DDS middleware"
        )))
    }

    #[pyo3(name = "publish_raw")]
    fn pypublish_raw(
        &self,
        py: Python,
        message_type: &str,
        topic: &str,
        payload: Py<pyo3::types::PyBytes>,
    ) -> PyResult<()> {
        futures::executor::block_on(self.pypublish_raw_impl(py, message_type, topic, payload))
    }

    #[pyo3(name = "subscribe_raw")]
    fn pysubscribe_raw(
        &self,
        py: Python<'_>,
        message_type: &str,
        topic: &str,
        callback: PyObject,
    ) -> PyResult<()> {
        futures::executor::block_on(self.pysubscribe_raw_impl(py, message_type, topic, callback))
    }

    #[pyo3(name = "subscribe_all_raw")]
    fn pysubscribe_all_raw(
        &self,
        _py: Python,
        _topics: Vec<(String, String)>,
        _callback: PyObject,
    ) -> PyResult<()> {
        Err(PyRuntimeError::new_err(format!(
            "'subscribe_all' not implemented for DDS middleware"
        )))
    }
}

impl PySerializer for DDSSerializer {}

#[pymethods]
impl DDSSerializer {
    #[new]
    fn pynew(_py: Python) -> PyResult<Self> {
        Ok(Self {})
    }

    #[pyo3(name = "serialize_message")]
    fn pyserialize_message(
        &self,
        py: Python<'_>,
        metadata: Metadata,
        data: PyObject,
    ) -> Option<Vec<u8>> {
        let serializer = SerializerEnum::from(DDSSerializer {});
        self.pyserialize_message_impl(py, &serializer, metadata, data)
    }

    #[pyo3(name = "deserialize_message")]
    fn pydeserialize_message(
        &self,
        py: Python<'_>,
        message_type: PyObject,
        payload: &[u8],
    ) -> Option<(Metadata, PyObject)> {
        let serializer = SerializerEnum::from(DDSSerializer {});
        self.pydeserialize_message_impl(py, &serializer, message_type, payload)
    }

    #[pyo3(name = "deserialize_metadata")]
    fn pydeserialize_metadata(
        &self,
        py: Python<'_>,
        payload: &[u8],
    ) -> Option<Metadata> {
        let serializer = SerializerEnum::from(DDSSerializer {});
        self.pydeserialize_metadata_impl(py, &serializer, payload)
    }

    #[pyo3(name = "deserialize_data")]
    fn pydeserialize_data(
        &self,
        py: Python<'_>,
        message_type: PyObject,
        payload: &[u8],
    ) -> Option<PyObject> {
        let serializer = SerializerEnum::from(DDSSerializer {});
        self.pydeserialize_data_impl(py, &serializer, message_type, payload)
    }

    #[pyo3(name = "from_json")]
    fn pyserialize_from_json(
        &self,
        py: Python<'_>,
        type_name: &str,
        metadata: &Metadata,
        data: PyObject,
    ) -> Option<Vec<u8>> {
        let serializer = SerializerEnum::from(DDSSerializer {});
        self.pyserialize_from_json_impl(py, &serializer, type_name, metadata, data)
    }

    #[pyo3(name = "to_json")]
    fn pydeserialize_to_json(
        &self,
        py: Python<'_>,
        type_name: &str,
        payload: &[u8],
    ) -> Option<PyObject> {
        let serializer = SerializerEnum::from(DDSSerializer {});
        self.pydeserialize_to_json_impl(py, &serializer, type_name, payload)
    }

}
