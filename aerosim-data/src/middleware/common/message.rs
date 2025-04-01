use std::borrow::Cow;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use super::Metadata;

#[derive(Serialize, Deserialize, JsonSchema)]
pub struct Message<'a, T: Clone> {
    pub metadata: Cow<'a, Metadata>,
    pub data: Cow<'a, T>,
}

impl<'a, T: Clone> Message<'a, T> {
    pub fn new(metadata: Cow<'a, Metadata>, data: Cow<'a, T>) -> Self {
        Message::<T> { metadata, data }
    }
}

#[derive(Serialize, Deserialize)]
pub struct PartialMessageMetadata {
    pub metadata: Metadata,
}

#[derive(Serialize, Deserialize)]
pub struct PartialMessageData<T> {
    #[serde(skip_deserializing)]
    pub metadata: Option<Metadata>,
    pub data: T,
}
