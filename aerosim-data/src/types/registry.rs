use std::{
    collections::HashMap,
    sync::{Arc, OnceLock, RwLock},
};

use schemars::JsonSchema;

use crate::{
    types::{register_types, TypeSupport},
    AerosimMessage,
};

/// Generates a function to simplify and unify the registration of essential types.
///
/// The generated function is used by the TypeRegistry to automatically
/// register the initial set of core types.
#[macro_export]
macro_rules! register_types {
    ($($type:ty)+) => {
        pub fn register_types() -> $crate::types::registry::TypeRegistry {
            let registry = $crate::types::registry::TypeRegistry::create();
            $(
                let _ = registry.register::<$type>();
            )+
            registry
        }
    };
}

static TYPE_REGISTRY: OnceLock<TypeRegistry> = OnceLock::new();

pub struct TypeRegistry {
    types: RwLock<HashMap<String, Arc<TypeSupport>>>,
}

impl TypeRegistry {
    pub fn create() -> Self {
        TypeRegistry {
            types: RwLock::new(HashMap::new()),
        }
    }

    pub fn new() -> &'static TypeRegistry {
        TYPE_REGISTRY.get_or_init(|| register_types())
    }

    pub fn register<T: AerosimMessage + JsonSchema>(&self) -> Result<(), String> {
        match self.types.write() {
            Ok(mut wtypes) => wtypes
                .insert(T::get_type_name(), Arc::new(TypeSupport::create::<T>()))
                .map_or(Ok(()), |_| {
                    Err(format!(
                        "A type named `{}` is already registered",
                        T::get_type_name()
                    ))
                }),
            Err(_) => Err(format!("Failed to acquire write lock")),
        }
    }

    pub fn get(&self, type_name: &str) -> Option<Arc<TypeSupport>> {
        match self.types.read() {
            Ok(rtypes) => rtypes.get(type_name).map(|ts| Arc::clone(ts)),
            Err(_) => None,
        }
    }
}
