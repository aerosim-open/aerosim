use proc_macro::TokenStream;
use quote::quote;
use syn::{parse_macro_input, Data, DeriveInput};

#[proc_macro_derive(AerosimMessage)]
pub fn derive_aerosim_type(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    impl_derive_aerosim_type(&input)
}

fn impl_derive_aerosim_type(ast: &syn::DeriveInput) -> TokenStream {
    let name = &ast.ident;
    let gen = quote! {
        impl AerosimMessage for #name {
            fn get_type_name() -> String {
                format!("aerosim::types::{}", stringify!(#name))
            }
        }
    };
    gen.into()
}

/// Derive macro for enums that generates a `deserialize` method.
/// It simplifies deserialization by mapping a given `type_name` to the corresponding enum variant.
/// 
/// The macro compares the `type_name` and deserializes the data into the matching variant if found.
#[proc_macro_derive(AerosimDeserializeEnum)]
pub fn derive_aerosim_deserialize(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    impl_derive_aerosim_deserialize(&input)
}

fn impl_derive_aerosim_deserialize(ast: &syn::DeriveInput) -> TokenStream {
    let name = &ast.ident;
    let data = match &ast.data {
        Data::Enum(data_enum) => data_enum,
        _ => panic!("AerosimDeserializeEnum can only be derived for enums"),
    };

    let deserialize_cases = data.variants.iter().map(|variant| {
        let variant_name = &variant.ident;
        let variant_type = &variant
            .fields
            .iter()
            .next()
            .expect("Expecting one variant with exactly one field representing the data type")
            .ty;

        quote! {
            if type_name == #variant_type::get_type_name() {
                return match serializer.deserialize_data::<#variant_type>(payload) {
                    Some(data) => Some(#name::#variant_name(data)),
                    None => None,
                }
            }
        }
    });

    let gen = quote! {
        impl #name {
            pub fn deserialize(serializer: &SerializerEnum, type_name: &str, payload: &[u8]) -> Option<#name> {
                #(#deserialize_cases)*
                None
            }
        }
    };

    gen.into()
}
