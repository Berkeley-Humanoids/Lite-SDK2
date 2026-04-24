//! Minimal XCDR1 (PLAIN_CDR) encoder/decoder, little-endian only.
//!
//! Handles the 4-byte encapsulation header plus primitive alignment rules.
//! Scope is limited to the types used by `lite_sdk2`: `u32`, `f32`, and
//! `sequence<T>` over structs of aligned primitives.

use core::mem::size_of;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CdrError {
    UnexpectedEof { need: usize, have: usize },
    UnsupportedEncapsulation { id: [u8; 2] },
    InvalidLength(u32),
}

impl core::fmt::Display for CdrError {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            Self::UnexpectedEof { need, have } => {
                write!(f, "unexpected EOF: need {need} bytes, have {have}")
            }
            Self::UnsupportedEncapsulation { id } => {
                write!(f, "unsupported CDR encapsulation {:#04x}{:02x}", id[0], id[1])
            }
            Self::InvalidLength(len) => write!(f, "invalid sequence length {len}"),
        }
    }
}

impl core::error::Error for CdrError {}

/// A type whose wire representation is a fixed CDR struct body (no header).
pub trait CdrBody: Sized {
    fn write(&self, w: &mut Writer);
    fn read(r: &mut Reader<'_>) -> Result<Self, CdrError>;
}

/// Encode a top-level message: 4-byte LE PLAIN_CDR header + body.
pub fn encode<T: CdrBody>(value: &T) -> Vec<u8> {
    let mut w = Writer::new();
    w.buf.extend_from_slice(&[0x00, 0x01, 0x00, 0x00]);
    w.mark_header();
    value.write(&mut w);
    w.buf
}

/// Decode a top-level message from bytes, validating the header.
pub fn decode<T: CdrBody>(bytes: &[u8]) -> Result<T, CdrError> {
    if bytes.len() < 4 {
        return Err(CdrError::UnexpectedEof { need: 4, have: bytes.len() });
    }
    if bytes[0] != 0x00 || bytes[1] != 0x01 {
        return Err(CdrError::UnsupportedEncapsulation { id: [bytes[0], bytes[1]] });
    }
    let mut r = Reader::new(&bytes[4..]);
    T::read(&mut r)
}

pub struct Writer {
    buf: Vec<u8>,
    body_start: usize,
}

impl Writer {
    fn new() -> Self {
        Self { buf: Vec::with_capacity(64), body_start: 0 }
    }

    fn mark_header(&mut self) {
        self.body_start = self.buf.len();
    }

    fn align(&mut self, to: usize) {
        let pad = (to - (self.buf.len() - self.body_start) % to) % to;
        self.buf.extend(core::iter::repeat(0).take(pad));
    }

    pub fn write_u32(&mut self, value: u32) {
        self.align(size_of::<u32>());
        self.buf.extend_from_slice(&value.to_le_bytes());
    }

    pub fn write_f32(&mut self, value: f32) {
        self.align(size_of::<f32>());
        self.buf.extend_from_slice(&value.to_le_bytes());
    }

    pub fn write_sequence<T: CdrBody>(&mut self, items: &[T]) {
        self.write_u32(items.len() as u32);
        for item in items {
            item.write(self);
        }
    }

    pub fn write_float_array(&mut self, values: &[f32]) {
        self.write_u32(values.len() as u32);
        for v in values {
            self.write_f32(*v);
        }
    }
}

pub struct Reader<'a> {
    buf: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    fn new(buf: &'a [u8]) -> Self {
        Self { buf, pos: 0 }
    }

    fn align(&mut self, to: usize) {
        let pad = (to - self.pos % to) % to;
        self.pos += pad;
    }

    fn take(&mut self, n: usize) -> Result<&'a [u8], CdrError> {
        if self.pos + n > self.buf.len() {
            return Err(CdrError::UnexpectedEof {
                need: n,
                have: self.buf.len() - self.pos,
            });
        }
        let slice = &self.buf[self.pos..self.pos + n];
        self.pos += n;
        Ok(slice)
    }

    pub fn read_u32(&mut self) -> Result<u32, CdrError> {
        self.align(size_of::<u32>());
        let bytes = self.take(size_of::<u32>())?;
        Ok(u32::from_le_bytes(bytes.try_into().unwrap()))
    }

    pub fn read_f32(&mut self) -> Result<f32, CdrError> {
        self.align(size_of::<f32>());
        let bytes = self.take(size_of::<f32>())?;
        Ok(f32::from_le_bytes(bytes.try_into().unwrap()))
    }

    pub fn read_sequence<T: CdrBody>(&mut self) -> Result<Vec<T>, CdrError> {
        let len = self.read_u32()? as usize;
        let mut out = Vec::with_capacity(len);
        for _ in 0..len {
            out.push(T::read(self)?);
        }
        Ok(out)
    }

    pub fn read_float_array(&mut self, expected: usize) -> Result<Vec<f32>, CdrError> {
        let len = self.read_u32()? as usize;
        if len != expected {
            return Err(CdrError::InvalidLength(len as u32));
        }
        let mut out = Vec::with_capacity(len);
        for _ in 0..len {
            out.push(self.read_f32()?);
        }
        Ok(out)
    }
}
