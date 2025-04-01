use ::log::{error, info, warn};
use std::sync::Mutex;
use std::time::Duration;

use aerosim_data::types::TimeStamp;
use crate::logging::warn_rate_limited;

pub struct SimClock {
    pub step_size: Duration,
    pub pace_1x_scale: bool,
    sim_time: Mutex<TimeStamp>,
    sim_start_time: Mutex<TimeStamp>,
    real_to_sim_time: Mutex<Vec<(TimeStamp, TimeStamp)>>,
}

impl Default for SimClock {
    fn default() -> SimClock {
        SimClock {
            step_size: Duration::from_millis(10),
            pace_1x_scale: true,
            sim_time: Mutex::new(TimeStamp::new(0, 0)),
            sim_start_time: Mutex::new(TimeStamp::new(0, 0)),
            real_to_sim_time: Mutex::new(Vec::new()),
        }
    }
}

impl SimClock {
    pub fn new(step_size: Duration, pace_1x_scale: bool) -> Self {
        SimClock {
            step_size,
            pace_1x_scale,
            ..Default::default()
        }
    }

    pub fn start(&self) -> TimeStamp {
        info!("Starting sim clock.");
        let mut sim_start_time = self
            .sim_start_time
            .lock()
            .expect("Failed to acquire lock for sim clock");
        *sim_start_time = TimeStamp::now();
        *sim_start_time
    }

    pub fn stop(&self) -> TimeStamp {
        info!("Stopping sim clock.");
        self.sim_time()
            .expect("Failed to acquire lock for sim clock")
    }

    pub fn step(&self) -> TimeStamp {
        let mut sim_time = self
            .sim_time
            .lock()
            .expect("Failed to acquire lock for sim clock");

        let mut cur_sim_time = Duration::new(sim_time.sec as u64, sim_time.nanosec as u32);
        cur_sim_time += self.step_size;

        sim_time.sec = cur_sim_time.as_secs() as i32;
        sim_time.nanosec = cur_sim_time.subsec_nanos() as u32;

        let now_real = TimeStamp::now();

        {
            let mut real_to_sim_time = self
                .real_to_sim_time
                .lock()
                .expect("Failed to acquire lock for sim clock");
            real_to_sim_time.push((now_real, *sim_time));
        }

        *sim_time
    }

    pub fn sim_time(&self) -> Option<TimeStamp> {
        match self.sim_time.lock() {
            Ok(sim_time) => Some(*sim_time),
            Err(_) => {
                warn!("Failed to acquire lock for sim clock");
                None
            }
        }
    }

    pub fn sim_start_time(&self) -> Option<TimeStamp> {
        match self.sim_start_time.lock() {
            Ok(sim_start_time) => Some(*sim_start_time),
            Err(_) => {
                warn!("Failed to acquire lock for sim clock");
                None
            }
        }
    }

    pub fn get_sim_time_from_real_time(&self, real_time: TimeStamp) -> TimeStamp {
        let real_to_sim_time = match self.real_to_sim_time.lock() {
            Ok(guard) => guard,
            Err(_) => {
                error!("Failed to acquire lock for sim clock");
                return TimeStamp::new(0, 0);
            }
        };

        if real_to_sim_time.is_empty() {
            warn_rate_limited(
                "no_time_mapping",
                "No real-to-sim time mapping available.",
                Duration::from_secs(1)
            );
            return TimeStamp::new(0, 0);
        }

        let sim_time = match real_to_sim_time.binary_search_by(|(real, _)| real.cmp(&real_time)) {
            Ok(idx) => real_to_sim_time[idx].1,
            Err(idx) => {
                if idx == 0 {
                    // real_time is before the first sim_time, so return sim_time=0
                    TimeStamp::new(0, 0)
                } else {
                    // real_time is between two real-to-sim time mappings, so return
                    // the sim_time step that happened right before real_time
                    real_to_sim_time[idx - 1].1
                }
            }
        };

        sim_time
    }
}

// Unit tests
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simclock_real_to_sim_time() {
        let simclock = SimClock::new(Duration::from_millis(10), true);
        simclock.start(); // sim_time = 0

        let real_time_1 = TimeStamp::now();
        simclock.step(); // sim_time = 10 ms
        let real_time_2 = TimeStamp::now();
        simclock.step(); // sim_time = 20 ms
        let real_time_3 = TimeStamp::now();

        let sim_time_1 = simclock.get_sim_time_from_real_time(real_time_1);
        let sim_time_2 = simclock.get_sim_time_from_real_time(real_time_2);
        let sim_time_3 = simclock.get_sim_time_from_real_time(real_time_3);

        assert_eq!(sim_time_1, TimeStamp::new(0, 0));
        assert_eq!(sim_time_2, TimeStamp::from_millis(10));
        assert_eq!(sim_time_3, TimeStamp::from_millis(20));
    }
}
