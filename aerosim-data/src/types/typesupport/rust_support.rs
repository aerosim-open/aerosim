use schemars::{gen::SchemaSettings, schema::RootSchema, JsonSchema};
use serde_json;

use crate::{
    middleware::{Message, Metadata, Serializer, SerializerEnum},
    AerosimMessage,
};

fn from_json<T: AerosimMessage>(
    serializer: &SerializerEnum,
    metadata: &Metadata,
    data: serde_json::Value,
) -> Option<Vec<u8>> {
    let data = serde_json::from_value::<T>(data).ok()?;
    serializer.serialize_message::<T>(metadata, &data)
}

fn to_json<T: AerosimMessage>(
    serializer: &SerializerEnum,
    payload: &[u8],
) -> Option<serde_json::Value> {
    // TODO: Investigate how we can deserialize only the data field for CDR.
    let (_, data) = serializer.deserialize_message::<T>(payload)?;
    serde_json::to_value::<T>(data).ok()
}

pub struct TypeSupport {
    schema: RootSchema,
    from_json_fn: fn(&SerializerEnum, &Metadata, serde_json::Value) -> Option<Vec<u8>>,
    to_json_fn: fn(&SerializerEnum, &[u8]) -> Option<serde_json::Value>,
}

impl TypeSupport {
    pub fn create<T: AerosimMessage + JsonSchema>() -> Self {
        let schema_settings = SchemaSettings::default().with(|s| {
            // Inline all subschemas instead of using references as MCAP does not support them.
            s.inline_subschemas = true;
        });
        let schema_generator = schema_settings.into_generator();

        TypeSupport {
            schema: schema_generator.into_root_schema_for::<Message<T>>(),
            from_json_fn: from_json::<T>,
            to_json_fn: to_json::<T>,
        }
    }

    pub fn from_json(
        &self,
        serializer: &SerializerEnum,
        metadata: &Metadata,
        data: serde_json::Value,
    ) -> Option<Vec<u8>> {
        (self.from_json_fn)(serializer, metadata, data)
    }

    pub fn to_json(
        &self,
        serializer: &SerializerEnum,
        payload: &[u8],
    ) -> Option<serde_json::Value> {
        (self.to_json_fn)(serializer, payload)
    }

    pub fn schema(&self) -> &RootSchema {
        &self.schema
    }

    pub fn schema_as_bytes(&self) -> Option<Vec<u8>> {
        serde_json::to_vec(&self.schema).ok()
    }
}
