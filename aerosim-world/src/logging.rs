use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};
use lazy_static::lazy_static;
use log::warn;

lazy_static! {
    static ref WARNING_TIMESTAMPS: Mutex<HashMap<&'static str, (Instant, u32)>> = Mutex::new(HashMap::new());
}

/// Log a warning message with rate limiting to prevent spam
/// 
/// # Arguments
/// * `key` - A unique identifier for this warning type
/// * `message` - The warning message to log
/// * `min_interval` - Minimum duration between consecutive warnings
pub fn warn_rate_limited(key: &'static str, message: &str, min_interval: Duration) {
    let should_log = match WARNING_TIMESTAMPS.lock() {
        Ok(mut timestamps) => {
            let now = Instant::now();
            let (should_log, suppressed_count, last_time) = match timestamps.get(key) {
                Some((last_time, count)) => {
                    let elapsed = now.duration_since(*last_time);
                    if elapsed >= min_interval {
                        // If we're about to log and there were suppressed warnings, mention them
                        if *count > 0 {
                            warn!("({} similar warnings were suppressed in the last {}s)",
                                  count,
                                  elapsed.as_secs());
                        }
                        (true, 0, now)
                    } else {
                        (false, count + 1, *last_time)
                    }
                },
                None => (true, 0, now),
            };
            
            timestamps.insert(key, (last_time, suppressed_count));
            should_log
        },
        Err(_) => true, // If we can't get the lock, always log the warning
    };
    
    if should_log {
        warn!("{}", message);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    
    #[test]
    fn test_warn_rate_limited() {
        // First warning should always be logged
        warn_rate_limited(
            "test_warning",
            "Test warning message",
            Duration::from_millis(100),
        );
        
        // Second warning within interval should not be logged
        warn_rate_limited(
            "test_warning",
            "Test warning message",
            Duration::from_millis(100),
        );
        
        // Wait for interval to pass
        thread::sleep(Duration::from_millis(100));
        
        // Warning after interval should be logged
        warn_rate_limited(
            "test_warning",
            "Test warning message",
            Duration::from_millis(100),
        );
    }
}
