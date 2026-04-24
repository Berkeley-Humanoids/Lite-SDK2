//! CycloneDDS-backed publisher/subscriber for `lite_sdk2` messages.
//!
//! Mirrors the Python `lite_sdk2.channel` API: call [`initialize`] once per
//! process to bind the DDS participant to a domain + NIC, then construct
//! [`Publisher`]/[`Subscriber`] for each message type.

use core::ffi::{CStr, c_void};
use core::marker::PhantomData;
use core::ptr;
use std::env;
use std::ffi::CString;
use std::sync::OnceLock;

use crate::ffi;
use crate::messages::{ActuatorCommand, ActuatorState, ImuState, LowCommand, LowState};
use crate::topics::ros_topic_to_dds;

#[derive(Debug)]
pub enum Error {
    Dds { context: String, code: ffi::dds_return_t },
    InvalidInterface(String),
}

impl core::fmt::Display for Error {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            Self::Dds { context, code } => write!(f, "{context}: {}", describe_retcode(*code)),
            Self::InvalidInterface(name) => write!(f, "invalid network interface {name:?}"),
        }
    }
}

impl core::error::Error for Error {}

pub type Result<T> = core::result::Result<T, Error>;

/// Bind the process-wide CycloneDDS configuration to a domain and NIC.
///
/// Writes a `CYCLONEDDS_URI` XML config fragment before any DDS entities are
/// created. Call once at startup. `network_interface = None` lets CycloneDDS
/// auto-select.
pub fn initialize(domain_id: u16, network_interface: Option<&str>) -> Result<()> {
    if INITIALIZED.get().is_some() {
        return Ok(());
    }

    if let Some(nic) = network_interface {
        if nic.is_empty() {
            return Err(Error::InvalidInterface(nic.to_string()));
        }
        // Same XML shape as the Python side's `channel._build_domain_config` so
        // both processes bind to the same NIC on the same domain.
        let config = format!(
            "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\
             <CycloneDDS><Domain Id=\"{domain_id}\"><General><Interfaces>\
             <NetworkInterface name=\"{nic}\" priority=\"default\" multicast=\"default\" />\
             </Interfaces></General></Domain></CycloneDDS>",
        );
        // SAFETY: documented one-time init before any DDS thread starts.
        unsafe { env::set_var("CYCLONEDDS_URI", config) };
    }

    INITIALIZED.set(()).ok();
    Ok(())
}

static INITIALIZED: OnceLock<()> = OnceLock::new();

/// A DDS-wire-compatible message type backed by a CycloneDDS topic descriptor.
///
/// # Safety
///
/// `FFI_LAYOUT` must exactly match the C struct declared in
/// `native/descriptors.c` (same field order, same types, `#[repr(C)]`).
/// `descriptor()` must return a pointer to the matching descriptor.
/// `into_ffi` / `from_ffi` must preserve field values byte-identically.
pub unsafe trait Message: Sized {
    /// The `#[repr(C)]` shadow struct passed to CycloneDDS.
    type Ffi;

    /// Owned storage that backs any sequences inside [`Ffi`]. Dropped after
    /// the synchronous call to `dds_write` returns.
    type WriteStorage: Default;

    /// Default ROS topic for this message type.
    fn default_topic() -> &'static str;

    /// Pointer to the statically-linked topic descriptor.
    fn descriptor() -> *const ffi::dds_topic_descriptor_t;

    /// Fill in `storage` and return an FFI struct whose sequence pointers
    /// borrow from it. The caller must keep `storage` alive for as long as
    /// the returned FFI struct is used.
    fn into_ffi(self, storage: &mut Self::WriteStorage) -> Self::Ffi;

    /// Copy out of a CycloneDDS loan. The sample buffer outlives the call.
    ///
    /// # Safety
    ///
    /// `sample` must be a valid pointer to a `Self::Ffi` produced by CycloneDDS.
    unsafe fn from_ffi(sample: &Self::Ffi) -> Result<Self>;
}

#[derive(Default)]
pub struct LowCommandStorage {
    actuator_commands: Vec<ffi::ActuatorCommand>,
}

unsafe impl Message for LowCommand {
    type Ffi = ffi::LowCommand;
    type WriteStorage = LowCommandStorage;

    fn default_topic() -> &'static str {
        crate::topics::LOWCOMMAND
    }

    fn descriptor() -> *const ffi::dds_topic_descriptor_t {
        unsafe { &ffi::lite_sdk2_msg__LowCommand__desc }
    }

    fn into_ffi(self, storage: &mut Self::WriteStorage) -> Self::Ffi {
        storage.actuator_commands = self
            .actuator_commands
            .into_iter()
            .map(|c| ffi::ActuatorCommand {
                mode: c.mode,
                position: c.position,
                velocity: c.velocity,
                torque: c.torque,
                kp: c.kp,
                kd: c.kd,
            })
            .collect();
        ffi::LowCommand {
            configuration: self.configuration,
            actuator_commands: borrow_actuator_commands(&storage.actuator_commands),
        }
    }

    unsafe fn from_ffi(sample: &Self::Ffi) -> Result<Self> {
        Ok(LowCommand {
            configuration: sample.configuration,
            actuator_commands: unsafe { sequence_slice(&sample.actuator_commands)? }
                .iter()
                .map(|c| ActuatorCommand {
                    mode: c.mode,
                    position: c.position,
                    velocity: c.velocity,
                    torque: c.torque,
                    kp: c.kp,
                    kd: c.kd,
                })
                .collect(),
        })
    }
}

#[derive(Default)]
pub struct LowStateStorage {
    quaternion: Vec<f32>,
    gyroscope: Vec<f32>,
    accelerometer: Vec<f32>,
    rpy: Vec<f32>,
    actuator_states: Vec<ffi::ActuatorState>,
}

unsafe impl Message for LowState {
    type Ffi = ffi::LowState;
    type WriteStorage = LowStateStorage;

    fn default_topic() -> &'static str {
        crate::topics::LOWSTATE
    }

    fn descriptor() -> *const ffi::dds_topic_descriptor_t {
        unsafe { &ffi::lite_sdk2_msg__LowState__desc }
    }

    fn into_ffi(self, storage: &mut Self::WriteStorage) -> Self::Ffi {
        storage.quaternion = self.imu_state.quaternion.to_vec();
        storage.gyroscope = self.imu_state.gyroscope.to_vec();
        storage.accelerometer = self.imu_state.accelerometer.to_vec();
        storage.rpy = self.imu_state.rpy.to_vec();
        storage.actuator_states = self
            .actuator_states
            .into_iter()
            .map(|s| ffi::ActuatorState {
                mode: s.mode,
                position: s.position,
                velocity: s.velocity,
                torque: s.torque,
                acceleration: s.acceleration,
                temperature: s.temperature,
            })
            .collect();
        ffi::LowState {
            version: self.version,
            tick: self.tick,
            configuration: self.configuration,
            imu_state: ffi::ImuState {
                quaternion: borrow_floats(&storage.quaternion),
                gyroscope: borrow_floats(&storage.gyroscope),
                accelerometer: borrow_floats(&storage.accelerometer),
                rpy: borrow_floats(&storage.rpy),
                temperature: self.imu_state.temperature,
            },
            actuator_states: borrow_actuator_states(&storage.actuator_states),
        }
    }

    unsafe fn from_ffi(sample: &Self::Ffi) -> Result<Self> {
        unsafe {
            Ok(LowState {
                version: sample.version,
                tick: sample.tick,
                configuration: sample.configuration,
                imu_state: ImuState {
                    quaternion: float_array::<4>(&sample.imu_state.quaternion)?,
                    gyroscope: float_array::<3>(&sample.imu_state.gyroscope)?,
                    accelerometer: float_array::<3>(&sample.imu_state.accelerometer)?,
                    rpy: float_array::<3>(&sample.imu_state.rpy)?,
                    temperature: sample.imu_state.temperature,
                },
                actuator_states: actuator_state_slice(&sample.actuator_states)?
                    .iter()
                    .map(|s| ActuatorState {
                        mode: s.mode,
                        position: s.position,
                        velocity: s.velocity,
                        torque: s.torque,
                        acceleration: s.acceleration,
                        temperature: s.temperature,
                    })
                    .collect(),
            })
        }
    }
}

pub struct Participant {
    entity: ffi::dds_entity_t,
}

impl Participant {
    pub fn new(domain_id: u16) -> Result<Self> {
        let entity = unsafe {
            ffi::dds_create_participant(u32::from(domain_id), ptr::null(), ptr::null())
        };
        check_entity(entity, "failed to create CycloneDDS participant")?;
        Ok(Self { entity })
    }

    pub fn publisher<T: Message>(&self, topic: &str) -> Result<Publisher<T>> {
        let topic_entity = create_topic::<T>(self.entity, topic)?;
        let writer = unsafe {
            ffi::dds_create_writer(self.entity, topic_entity, ptr::null(), ptr::null())
        };
        check_entity(writer, "failed to create DDS writer")?;
        Ok(Publisher {
            writer,
            _marker: PhantomData,
        })
    }

    pub fn subscriber<T: Message>(&self, topic: &str) -> Result<Subscriber<T>> {
        let topic_entity = create_topic::<T>(self.entity, topic)?;
        let reader = unsafe {
            ffi::dds_create_reader(self.entity, topic_entity, ptr::null(), ptr::null())
        };
        check_entity(reader, "failed to create DDS reader")?;
        Ok(Subscriber {
            reader,
            _marker: PhantomData,
        })
    }
}

impl Drop for Participant {
    fn drop(&mut self) {
        if self.entity > 0 {
            unsafe { ffi::dds_delete(self.entity) };
        }
    }
}

pub struct Publisher<T: Message> {
    writer: ffi::dds_entity_t,
    _marker: PhantomData<fn(T)>,
}

impl<T: Message> Publisher<T> {
    /// Realtime-safe write. Non-blocking; returns immediately after handing
    /// the sample to CycloneDDS.
    pub fn write(&self, message: T) -> Result<()> {
        let mut storage = T::WriteStorage::default();
        let ffi_struct = message.into_ffi(&mut storage);
        check_retcode(
            unsafe { ffi::dds_write(self.writer, &ffi_struct as *const _ as *const c_void) },
            "failed to publish DDS sample",
        )
    }
}

pub struct Subscriber<T: Message> {
    reader: ffi::dds_entity_t,
    _marker: PhantomData<fn() -> T>,
}

impl<T: Message> Subscriber<T> {
    /// Drain the reader queue and return the most recent sample, if any.
    pub fn take_latest(&self) -> Result<Option<T>> {
        let mut latest = None;
        loop {
            let mut raw: *mut c_void = ptr::null_mut();
            let mut info = ffi::dds_sample_info_t::default();
            let ret = unsafe { ffi::dds_take_next_wl(self.reader, &mut raw, &mut info) };
            match ret {
                1 => {
                    if info.valid_data {
                        let sample = unsafe { &*(raw as *const T::Ffi) };
                        latest = Some(unsafe { T::from_ffi(sample)? });
                    }
                    let mut loan = raw;
                    check_retcode(
                        unsafe { ffi::dds_return_loan(self.reader, &mut loan, 1) },
                        "failed to return DDS loan",
                    )?;
                }
                0 => break,
                code => {
                    return Err(Error::Dds {
                        context: "failed to take DDS sample".to_string(),
                        code,
                    });
                }
            }
        }
        Ok(latest)
    }
}

fn create_topic<T: Message>(
    participant: ffi::dds_entity_t,
    ros_topic: &str,
) -> Result<ffi::dds_entity_t> {
    let dds_name = CString::new(ros_topic_to_dds(ros_topic))
        .expect("DDS topic names never contain NUL bytes");
    let topic = unsafe {
        ffi::dds_create_topic(
            participant,
            T::descriptor(),
            dds_name.as_ptr(),
            ptr::null(),
            ptr::null(),
        )
    };
    check_entity(topic, "failed to create DDS topic")?;
    Ok(topic)
}

fn check_entity(entity: ffi::dds_entity_t, context: &str) -> Result<()> {
    if entity > 0 {
        Ok(())
    } else {
        Err(Error::Dds {
            context: context.to_string(),
            code: entity,
        })
    }
}

fn check_retcode(code: ffi::dds_return_t, context: &str) -> Result<()> {
    if code >= 0 {
        Ok(())
    } else {
        Err(Error::Dds {
            context: context.to_string(),
            code,
        })
    }
}

fn describe_retcode(code: ffi::dds_return_t) -> String {
    let raw = unsafe { ffi::dds_strretcode(code) };
    if raw.is_null() {
        return format!("DDS error {code}");
    }
    let text = unsafe { CStr::from_ptr(raw) }.to_string_lossy();
    format!("{text} ({code})")
}

fn borrow_floats(values: &[f32]) -> ffi::dds_sequence_float {
    ffi::dds_sequence_float {
        maximum: values.len() as u32,
        length: values.len() as u32,
        buffer: if values.is_empty() {
            ptr::null_mut()
        } else {
            values.as_ptr() as *mut f32
        },
        release: false,
    }
}

fn borrow_actuator_commands(values: &[ffi::ActuatorCommand]) -> ffi::dds_sequence_ActuatorCommand {
    ffi::dds_sequence_ActuatorCommand {
        maximum: values.len() as u32,
        length: values.len() as u32,
        buffer: if values.is_empty() {
            ptr::null_mut()
        } else {
            values.as_ptr() as *mut ffi::ActuatorCommand
        },
        release: false,
    }
}

fn borrow_actuator_states(values: &[ffi::ActuatorState]) -> ffi::dds_sequence_ActuatorState {
    ffi::dds_sequence_ActuatorState {
        maximum: values.len() as u32,
        length: values.len() as u32,
        buffer: if values.is_empty() {
            ptr::null_mut()
        } else {
            values.as_ptr() as *mut ffi::ActuatorState
        },
        release: false,
    }
}

unsafe fn sequence_slice(
    seq: &ffi::dds_sequence_ActuatorCommand,
) -> Result<&[ffi::ActuatorCommand]> {
    if seq.length == 0 {
        return Ok(&[]);
    }
    if seq.buffer.is_null() {
        return Err(Error::Dds {
            context: "received ActuatorCommand sequence with null buffer".to_string(),
            code: 0,
        });
    }
    Ok(unsafe { core::slice::from_raw_parts(seq.buffer, seq.length as usize) })
}

unsafe fn actuator_state_slice(
    seq: &ffi::dds_sequence_ActuatorState,
) -> Result<&[ffi::ActuatorState]> {
    if seq.length == 0 {
        return Ok(&[]);
    }
    if seq.buffer.is_null() {
        return Err(Error::Dds {
            context: "received ActuatorState sequence with null buffer".to_string(),
            code: 0,
        });
    }
    Ok(unsafe { core::slice::from_raw_parts(seq.buffer, seq.length as usize) })
}

unsafe fn float_array<const N: usize>(seq: &ffi::dds_sequence_float) -> Result<[f32; N]> {
    if seq.length as usize != N {
        return Err(Error::Dds {
            context: format!("expected float sequence of length {N}, got {}", seq.length),
            code: 0,
        });
    }
    if seq.buffer.is_null() {
        return Err(Error::Dds {
            context: "received float sequence with null buffer".to_string(),
            code: 0,
        });
    }
    let slice = unsafe { core::slice::from_raw_parts(seq.buffer, N) };
    let mut out = [0.0_f32; N];
    out.copy_from_slice(slice);
    Ok(out)
}
