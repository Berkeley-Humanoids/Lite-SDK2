//! Hand-maintained Rust mirrors of `../idl/lite_sdk2/msg/*.idl`.
//!
//! DDS typenames (used for topic discovery) are the constants on each impl.

use crate::cdr::{CdrBody, CdrError, Reader, Writer};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum Configuration {
    None = 0x00,
    FullBody = 0x01,
    FullBodyWithFingers = 0x02,
    ArmsAndLegs = 0x03,
    BimanualArms = 0x04,
    LeftArm = 0x05,
    RightArm = 0x06,
}

impl Configuration {
    pub fn from_u32(value: u32) -> Option<Self> {
        match value {
            0x00 => Some(Self::None),
            0x01 => Some(Self::FullBody),
            0x02 => Some(Self::FullBodyWithFingers),
            0x03 => Some(Self::ArmsAndLegs),
            0x04 => Some(Self::BimanualArms),
            0x05 => Some(Self::LeftArm),
            0x06 => Some(Self::RightArm),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct ActuatorCommand {
    pub mode: u32,
    pub position: f32,
    pub velocity: f32,
    pub torque: f32,
    pub kp: f32,
    pub kd: f32,
}

impl ActuatorCommand {
    pub const TYPENAME: &'static str = "lite_sdk2::msg::ActuatorCommand";
}

impl CdrBody for ActuatorCommand {
    fn write(&self, w: &mut Writer) {
        w.write_u32(self.mode);
        w.write_f32(self.position);
        w.write_f32(self.velocity);
        w.write_f32(self.torque);
        w.write_f32(self.kp);
        w.write_f32(self.kd);
    }

    fn read(r: &mut Reader<'_>) -> Result<Self, CdrError> {
        Ok(Self {
            mode: r.read_u32()?,
            position: r.read_f32()?,
            velocity: r.read_f32()?,
            torque: r.read_f32()?,
            kp: r.read_f32()?,
            kd: r.read_f32()?,
        })
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct ActuatorState {
    pub mode: u32,
    pub position: f32,
    pub velocity: f32,
    pub torque: f32,
    pub acceleration: f32,
    pub temperature: f32,
}

impl ActuatorState {
    pub const TYPENAME: &'static str = "lite_sdk2::msg::ActuatorState";
}

impl CdrBody for ActuatorState {
    fn write(&self, w: &mut Writer) {
        w.write_u32(self.mode);
        w.write_f32(self.position);
        w.write_f32(self.velocity);
        w.write_f32(self.torque);
        w.write_f32(self.acceleration);
        w.write_f32(self.temperature);
    }

    fn read(r: &mut Reader<'_>) -> Result<Self, CdrError> {
        Ok(Self {
            mode: r.read_u32()?,
            position: r.read_f32()?,
            velocity: r.read_f32()?,
            torque: r.read_f32()?,
            acceleration: r.read_f32()?,
            temperature: r.read_f32()?,
        })
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct ImuState {
    pub quaternion: [f32; 4],
    pub gyroscope: [f32; 3],
    pub accelerometer: [f32; 3],
    pub rpy: [f32; 3],
    pub temperature: f32,
}

impl ImuState {
    pub const TYPENAME: &'static str = "lite_sdk2::msg::ImuState";
}

impl Default for ImuState {
    fn default() -> Self {
        Self {
            quaternion: [0.0; 4],
            gyroscope: [0.0; 3],
            accelerometer: [0.0; 3],
            rpy: [0.0; 3],
            temperature: 0.0,
        }
    }
}

impl CdrBody for ImuState {
    fn write(&self, w: &mut Writer) {
        w.write_float_array(&self.quaternion);
        w.write_float_array(&self.gyroscope);
        w.write_float_array(&self.accelerometer);
        w.write_float_array(&self.rpy);
        w.write_f32(self.temperature);
    }

    fn read(r: &mut Reader<'_>) -> Result<Self, CdrError> {
        let quaternion = r.read_float_array(4)?;
        let gyroscope = r.read_float_array(3)?;
        let accelerometer = r.read_float_array(3)?;
        let rpy = r.read_float_array(3)?;
        let temperature = r.read_f32()?;
        Ok(Self {
            quaternion: quaternion.try_into().unwrap(),
            gyroscope: gyroscope.try_into().unwrap(),
            accelerometer: accelerometer.try_into().unwrap(),
            rpy: rpy.try_into().unwrap(),
            temperature,
        })
    }
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct LowCommand {
    pub configuration: u32,
    pub actuator_commands: Vec<ActuatorCommand>,
}

impl LowCommand {
    pub const TYPENAME: &'static str = "lite_sdk2::msg::LowCommand";
}

impl CdrBody for LowCommand {
    fn write(&self, w: &mut Writer) {
        w.write_u32(self.configuration);
        w.write_sequence(&self.actuator_commands);
    }

    fn read(r: &mut Reader<'_>) -> Result<Self, CdrError> {
        Ok(Self {
            configuration: r.read_u32()?,
            actuator_commands: r.read_sequence()?,
        })
    }
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct LowState {
    pub version: u32,
    pub tick: u32,
    pub configuration: u32,
    pub imu_state: ImuState,
    pub actuator_states: Vec<ActuatorState>,
}

impl LowState {
    pub const TYPENAME: &'static str = "lite_sdk2::msg::LowState";
}

impl CdrBody for LowState {
    fn write(&self, w: &mut Writer) {
        w.write_u32(self.version);
        w.write_u32(self.tick);
        w.write_u32(self.configuration);
        self.imu_state.write(w);
        w.write_sequence(&self.actuator_states);
    }

    fn read(r: &mut Reader<'_>) -> Result<Self, CdrError> {
        Ok(Self {
            version: r.read_u32()?,
            tick: r.read_u32()?,
            configuration: r.read_u32()?,
            imu_state: ImuState::read(r)?,
            actuator_states: r.read_sequence()?,
        })
    }
}
