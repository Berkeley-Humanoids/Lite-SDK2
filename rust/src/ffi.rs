//! CycloneDDS C bindings and `#[repr(C)]` shadow structs for our messages.
//!
//! Kept tightly scoped to what `channel` needs. Struct layouts must match
//! `native/descriptors.c` byte-for-byte.

#![allow(non_camel_case_types)]

use core::ffi::{c_char, c_void};

pub type dds_domainid_t = u32;
pub type dds_entity_t = i32;
pub type dds_instance_handle_t = u64;
pub type dds_return_t = i32;
pub type dds_sample_state_t = i32;
pub type dds_view_state_t = i32;
pub type dds_instance_state_t = i32;
pub type dds_time_t = i64;

#[repr(C)]
pub struct dds_qos_t {
    _private: [u8; 0],
}

#[repr(C)]
pub struct dds_listener_t {
    _private: [u8; 0],
}

#[repr(C)]
pub struct dds_topic_descriptor_t {
    pub m_size: u32,
    pub m_align: u32,
    pub m_flagset: u32,
    pub m_nkeys: u32,
    pub m_typename: *const c_char,
    pub m_keys: *const c_void,
    pub m_nops: u32,
    pub m_ops: *const u32,
    pub m_meta: *const c_char,
}

#[repr(C)]
pub struct dds_sequence_float {
    pub maximum: u32,
    pub length: u32,
    pub buffer: *mut f32,
    pub release: bool,
}

#[repr(C)]
#[derive(Clone, Copy, Default)]
pub struct ActuatorCommand {
    pub mode: u32,
    pub position: f32,
    pub velocity: f32,
    pub torque: f32,
    pub kp: f32,
    pub kd: f32,
}

#[repr(C)]
#[derive(Clone, Copy, Default)]
pub struct ActuatorState {
    pub mode: u32,
    pub position: f32,
    pub velocity: f32,
    pub torque: f32,
    pub acceleration: f32,
    pub temperature: f32,
}

#[repr(C)]
pub struct ImuState {
    pub quaternion: dds_sequence_float,
    pub gyroscope: dds_sequence_float,
    pub accelerometer: dds_sequence_float,
    pub rpy: dds_sequence_float,
    pub temperature: f32,
}

#[repr(C)]
pub struct dds_sequence_ActuatorCommand {
    pub maximum: u32,
    pub length: u32,
    pub buffer: *mut ActuatorCommand,
    pub release: bool,
}

#[repr(C)]
pub struct dds_sequence_ActuatorState {
    pub maximum: u32,
    pub length: u32,
    pub buffer: *mut ActuatorState,
    pub release: bool,
}

#[repr(C)]
pub struct LowCommand {
    pub configuration: u32,
    pub actuator_commands: dds_sequence_ActuatorCommand,
}

#[repr(C)]
pub struct LowState {
    pub version: u32,
    pub tick: u32,
    pub configuration: u32,
    pub imu_state: ImuState,
    pub actuator_states: dds_sequence_ActuatorState,
}

#[repr(C)]
pub struct dds_sample_info_t {
    pub sample_state: dds_sample_state_t,
    pub view_state: dds_view_state_t,
    pub instance_state: dds_instance_state_t,
    pub valid_data: bool,
    pub source_timestamp: dds_time_t,
    pub instance_handle: dds_instance_handle_t,
    pub publication_handle: dds_instance_handle_t,
    pub disposed_generation_count: u32,
    pub no_writers_generation_count: u32,
    pub sample_rank: u32,
    pub generation_rank: u32,
    pub absolute_generation_rank: u32,
}

impl Default for dds_sample_info_t {
    fn default() -> Self {
        Self {
            sample_state: 0,
            view_state: 0,
            instance_state: 0,
            valid_data: false,
            source_timestamp: 0,
            instance_handle: 0,
            publication_handle: 0,
            disposed_generation_count: 0,
            no_writers_generation_count: 0,
            sample_rank: 0,
            generation_rank: 0,
            absolute_generation_rank: 0,
        }
    }
}

unsafe extern "C" {
    pub static lite_sdk2_msg__LowCommand__desc: dds_topic_descriptor_t;
    pub static lite_sdk2_msg__LowState__desc: dds_topic_descriptor_t;

    pub fn dds_create_participant(
        domain: dds_domainid_t,
        qos: *const dds_qos_t,
        listener: *const dds_listener_t,
    ) -> dds_entity_t;
    pub fn dds_create_topic(
        participant: dds_entity_t,
        descriptor: *const dds_topic_descriptor_t,
        name: *const c_char,
        qos: *const dds_qos_t,
        listener: *const dds_listener_t,
    ) -> dds_entity_t;
    pub fn dds_create_reader(
        subscriber_or_participant: dds_entity_t,
        topic: dds_entity_t,
        qos: *const dds_qos_t,
        listener: *const dds_listener_t,
    ) -> dds_entity_t;
    pub fn dds_create_writer(
        publisher_or_participant: dds_entity_t,
        topic: dds_entity_t,
        qos: *const dds_qos_t,
        listener: *const dds_listener_t,
    ) -> dds_entity_t;
    pub fn dds_take_next_wl(
        reader: dds_entity_t,
        buf: *mut *mut c_void,
        si: *mut dds_sample_info_t,
    ) -> dds_return_t;
    pub fn dds_return_loan(
        entity: dds_entity_t,
        buf: *mut *mut c_void,
        bufsz: i32,
    ) -> dds_return_t;
    pub fn dds_write(writer: dds_entity_t, data: *const c_void) -> dds_return_t;
    pub fn dds_delete(entity: dds_entity_t) -> dds_return_t;
    pub fn dds_strretcode(ret: dds_return_t) -> *const c_char;
}
