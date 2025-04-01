pub mod decode;

/// Computes a 24-bit CRC (parity) for a Mode S (ADS‑B) message.
/// It is applied over the first 88 bits (11 bytes) using the polynomial 0xFFF409.
///
/// This function iterates over each bit in the `data` slice.
#[allow(dead_code)]
fn compute_crc24(data: &[u8]) -> u32 {
    let poly: u32 = 0xFFF409;
    let mut crc: u32 = 0;
    let bit_len = data.len() * 8;
    for i in 0..bit_len {
        let byte_index = i / 8;
        let bit_index = 7 - (i % 8);
        let bit = (data[byte_index] >> bit_index) & 1;
        let crc_msb = (crc >> 23) & 1;
        crc = (crc << 1) & 0xFFFFFF;
        if ((bit as u32) ^ crc_msb) != 0 {
            crc ^= poly;
        }
    }
    crc
}
