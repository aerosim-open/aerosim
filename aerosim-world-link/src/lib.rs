mod logger;
mod message_handler;

use crate::logger::Logger;
use crate::message_handler::MessageHandler;
use aerosim_core::math::quaternion::{Quaternion, RotationSequence, RotationType};

use log::{error, info};
use std::borrow::Cow;
use std::ffi::c_void;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;
use std::slice;
use std::sync::Mutex;

use aerosim_data::types::sensor::Image;
use aerosim_data::types::sensor::ImageEncoding;
use aerosim_data::types::CameraInfo;

lazy_static::lazy_static! {
    static ref GLOBAL_HANDLER: Mutex<Option<MessageHandler>> = Mutex::new(None);
}

/// Convert an integer format to `ImageEncoding`
fn parse_encoding(format: i32) -> Option<ImageEncoding> {
    match format {
        0 => Some(ImageEncoding::RGB8),
        1 => Some(ImageEncoding::RGBA8),
        2 => Some(ImageEncoding::BGR8),
        3 => Some(ImageEncoding::BGRA8),
        4 => Some(ImageEncoding::MONO8),
        5 => Some(ImageEncoding::MONO16),
        6 => Some(ImageEncoding::YUV422),
        _ => None, // Invalid format
    }
}

#[no_mangle]
pub extern "C" fn initialize_logger(log_file: *const c_char) {
    // Convert the C string (log_file) to a Rust string
    let c_str = unsafe { CStr::from_ptr(log_file) };

    match c_str.to_str() {
        Ok(log_file_str) => {
            // Initialize the logger using the passed log file
            Logger::initialize(log_file_str);
            info!(
                "[aerosim.renderer] Logger initialized with file: {}",
                log_file_str
            );
        }
        Err(e) => {
            error!(
                "[aerosim.renderer] Failed to initialize logger: invalid UTF-8 string. Error: {:?}",
                e
            );
        }
    }
}

#[no_mangle]
pub extern "C" fn initialize_message_handler(instance_id: *const c_char) -> bool {
    info!("[aerosim.renderer] Initializing message handler.");

    // Convert the C string (instance_id) to a Rust string
    let c_str = unsafe {
        assert!(!instance_id.is_null());
        CStr::from_ptr(instance_id)
    };
    let instance_id_str = c_str.to_str().unwrap();

    let mut handler = match GLOBAL_HANDLER.lock() {
        Ok(handler) => handler,
        Err(_) => {
            error!("[aerosim.renderer] Failed to lock GLOBAL_HANDLER mutex.");
            return false; // Failed to lock mutex
        }
    };

    if let Some(ref mut handler) = *handler {
        info!("[aerosim.renderer] Message handler already exists. Stopping the previous one.");
        handler
            .stop()
            .expect("[aerosim.renderer] Failed to stop the previously running message handler.");
    }

    info!("[aerosim.renderer] Creating a new MessageHandler.");
    *handler = Some(MessageHandler::new(instance_id_str));

    true
}

#[no_mangle]
pub extern "C" fn start_message_handler() {
    info!("[aerosim.renderer] Starting message handler.");
    let mut handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(ref mut handler) = *handler {
        match handler.start() {
            Ok(_) => info!("[aerosim.renderer] Message handler started successfully."),
            Err(e) => error!(
                "[aerosim.renderer] Failed to start message handler: {:?}",
                e
            ),
        }
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
}

#[no_mangle]
pub extern "C" fn notify_scene_graph_loaded() {
    info!("[aerosim.renderer] Notifying that the scene graph has been loaded.");
    let mut handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(ref mut handler) = *handler {
        handler.notify_scene_graph_loaded();
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
}

#[no_mangle]
pub extern "C" fn publish_to_topic(topic: *const c_char, payload: *const c_char) {
    // Convert the C strings (topic and payload) to Rust strings
    let c_str_topic = unsafe { CStr::from_ptr(topic) };
    let c_str_payload = unsafe { CStr::from_ptr(payload) };

    match (c_str_topic.to_str(), c_str_payload.to_str()) {
        (Ok(topic_str), Ok(payload_str)) => {
            // info!(
            //     "[aerosim.renderer] Publishing message to topic: {}",
            //     topic_str
            // );
            let mut handler = GLOBAL_HANDLER.lock().unwrap();
            if let Some(ref mut handler) = *handler {
                handler.publish_to_topic(topic_str, payload_str);
            } else {
                error!("[aerosim.renderer] Message handler has not been initialized.");
            }
        }
        _ => {
            error!("[aerosim.renderer] Failed to publish message: invalid UTF-8 string.");
        }
    }
}

#[no_mangle]
pub extern "C" fn publish_image_to_topic(
    topic: *const c_char,
    width: i32,
    height: i32,
    format: i32,
    data: *const c_void,
    data_size: usize,
) {
    if topic.is_null() || data.is_null() {
        eprintln!("Invalid null pointer received.");
        return;
    }

    let c_str_topic = unsafe { CStr::from_ptr(topic) };
    let topic_str = match c_str_topic.to_str() {
        Ok(c_str_topic) => c_str_topic,
        Err(_) => {
            eprintln!("Invalid UTF-8 string received.");
            return;
        }
    };

    // info!(
    //     "[aerosim.renderer] Publishing message: {} to topic: ",
    //     topic_str
    // );

    let encoding = match parse_encoding(format) {
        Some(enc) => enc,
        None => {
            eprintln!("Invalid image format: {}", format);
            return;
        }
    };

    // info!(
    //     "[aerosim.renderer] Publishing format: {} to topic: ",
    //     format
    // );

    let image_data = unsafe { slice::from_raw_parts(data as *const u8, data_size) };

    let d: Vec<f64> = vec![0.0];
    let k: [f64; 9] = [0.0; 9];
    let r: [f64; 9] = [0.0; 9];
    let p: [f64; 12] = [0.0; 12];
    let image = Image {
        camera_info: CameraInfo::new(
            width.try_into().unwrap(),
            height.try_into().unwrap(),
            "none".to_string(),
            d,
            k,
            r,
            p,
        ),
        height: height as u32,
        width: width as u32,
        encoding,  // Hardcoded to BGRA on the renderer side.
        is_bigendian: 0,
        step: (width * 4) as u32, // Assuming there is no padding
        data: Cow::Borrowed(image_data),
    };

    info!("[aerosim.renderer] Publishing message: {} ", topic_str);

    let mut handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(ref mut handler) = *handler {
        handler.publish_image_to_topic(topic_str, image);
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
}

#[no_mangle]
pub extern "C" fn get_consumer_payload_queue_size() -> u32 {
    // info!("[aerosim.renderer] Getting consumer payload queue's size.");
    let handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(ref handler) = *handler {
        return handler.get_payload_queue_size();
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
    0
}

#[no_mangle]
pub extern "C" fn get_consumer_payload_queue_oldest_timestamp() -> f64 {
    // info!("[aerosim.renderer] Getting consumer payload queue's oldest timestamp.");
    let handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(ref handler) = *handler {
        return handler.get_payload_queue_oldest_timestamp();
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
    -1.0
}

#[no_mangle]
pub extern "C" fn get_consumer_payload_queue_newest_timestamp() -> f64 {
    // info!("[aerosim.renderer] Getting consumer payload queue's newest timestamp.");
    let handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(ref handler) = *handler {
        return handler.get_payload_queue_newest_timestamp();
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
    -1.0
}

#[no_mangle]
pub extern "C" fn get_consumer_payload_from_queue() -> *mut c_char {
    // info!("[aerosim.renderer] Getting consumer payload.");
    let handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(ref handler) = *handler {
        if let Some(payload) = handler.get_payload_from_queue() {
            // info!("[aerosim.renderer] Retrieved payload: {}", payload);
            let c_str_payload = CString::new(payload).unwrap();
            return c_str_payload.into_raw(); // Pass ownership to C code
        } else {
            // info!("[aerosim.renderer] No new payloads available.");
        }
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
    ptr::null_mut()
}

#[no_mangle]
pub extern "C" fn end_message_handler() {
    info!("[aerosim.renderer] Stopping message handler.");
    let mut handler = GLOBAL_HANDLER.lock().unwrap();
    if let Some(mut handler) = handler.take() {
        match handler.stop() {
            Ok(_) => info!("[aerosim.renderer] Message handler stopped successfully."),
            Err(e) => error!("[aerosim.renderer] Failed to stop message handler: {:?}", e),
        }
    } else {
        error!("[aerosim.renderer] Message handler has not been initialized.");
    }
}

#[no_mangle]
pub extern "C" fn aerosim_quat_wxyz_to_rpy(
    w: f64,
    x: f64,
    y: f64,
    z: f64,
    out_roll: *mut f64,
    out_pitch: *mut f64,
    out_yaw: *mut f64,
) {
    let quat_data = aerosim_data::types::Quaternion::new(w, x, y, z);
    let q = Quaternion::from_quaternion_data(quat_data);
    let [roll, pitch, yaw] = q.to_euler_angles(RotationType::Extrinsic, RotationSequence::ZYX);
    unsafe {
        *out_roll = roll;
        *out_pitch = pitch;
        *out_yaw = yaw;
    }
}

#[no_mangle]
pub extern "C" fn ned_to_unreal_esu(x: *mut f64, y: *mut f64, z: *mut f64) {
    unsafe {
        let (east, south, up) =
            aerosim_core::coordinate_system::conversion_utils::ned_to_unreal_esu(*x, *y, *z);
        *x = east;
        *y = south;
        *z = up;
    }
}

#[no_mangle]
pub extern "C" fn rpy_ned_to_unreal_esu(roll: *mut f64, pitch: *mut f64, yaw: *mut f64) {
    unsafe {
        let (roll_esu, pitch_esu, yaw_esu) =
            aerosim_core::coordinate_system::conversion_utils::rpy_ned_to_unreal_esu(
                *roll, *pitch, *yaw,
            );
        *roll = roll_esu.to_degrees();
        *pitch = pitch_esu.to_degrees();
        *yaw = yaw_esu.to_degrees();
    }
}

// Generalized conversion functions

#[no_mangle]
pub extern "C" fn to_degrees(radians: f64) -> f64 {
    radians.to_degrees()
}

#[no_mangle]
pub extern "C" fn to_radians(degrees: f64) -> f64 {
    degrees.to_radians()
}

#[no_mangle]
pub extern "C" fn ned_to_enu(x: *mut f64, y: *mut f64, z: *mut f64) {
    unsafe {
        let (east, north, up) =
            aerosim_core::coordinate_system::conversion_utils::ned_to_enu(*x, *y, *z);
        *x = east;
        *y = north;
        *z = up;
    }
}

#[no_mangle]
pub extern "C" fn frd_to_flu(x: *mut f64, y: *mut f64, z: *mut f64) {
    unsafe {
        let (front, left, up) =
            aerosim_core::coordinate_system::conversion_utils::frd_to_flu(*x, *y, *z);
        *x = front;
        *y = left;
        *z = up;
    }
}

#[no_mangle]
pub extern "C" fn rpy_frd_to_flu(roll: *mut f64, pitch: *mut f64, yaw: *mut f64) {
    unsafe {
        let (roll_flu, pitch_flu, yaw_flu) =
            aerosim_core::coordinate_system::conversion_utils::rpy_frd_to_flu(*roll, *pitch, *yaw);
        *roll = roll_flu;
        *pitch = pitch_flu;
        *yaw = yaw_flu;
    }
}

#[no_mangle]
pub extern "C" fn rpy_nwu_to_enu(roll: *mut f64, pitch: *mut f64, yaw: *mut f64) {
    unsafe {
        let (roll_enu, pitch_enu, yaw_enu) =
            aerosim_core::coordinate_system::conversion_utils::rpy_nwu_to_enu(*roll, *pitch, *yaw);
        *roll = roll_enu;
        *pitch = pitch_enu;
        *yaw = yaw_enu;
    }
}
