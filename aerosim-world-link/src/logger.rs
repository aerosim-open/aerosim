use log::LevelFilter;
use log4rs::{
    append::file::FileAppender,
    config::{Appender, Config, Root},
    encode::pattern::PatternEncoder,
    Handle,
};
use std::sync::Once;

static LOGGER_INIT: Once = Once::new();

pub struct Logger {
    _handle: Option<Handle>,
}

impl Logger {
    pub fn initialize(log_file: &str) -> Self {
        LOGGER_INIT.call_once(|| {
            let file_appender = FileAppender::builder()
                .encoder(Box::new(PatternEncoder::new("{d} - {l} - {m}\n")))
                .build(log_file)
                .expect("Failed to create file appender");

            let config = Config::builder()
                .appender(Appender::builder().build("file", Box::new(file_appender)))
                .build(Root::builder().appender("file").build(LevelFilter::Info))
                .expect("Failed to build logger configuration");

            log4rs::init_config(config).expect("Failed to initalize logger");
        });

        Logger { _handle: None }
    }
}
