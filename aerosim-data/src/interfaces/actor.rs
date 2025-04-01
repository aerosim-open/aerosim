use crate::types::{TimeStamp, ActorType, ActorState, ActorModel};

pub trait Actor {
    fn get_uid(&self) -> u64;
    fn get_type(&self) -> ActorType;
    fn get_model(&self) -> &ActorModel;
    fn set_model(&mut self, model: ActorModel);
    fn get_state(&self) -> &ActorState;
    fn set_state(&mut self, state: ActorState);
    fn update(&mut self, time: TimeStamp);
}