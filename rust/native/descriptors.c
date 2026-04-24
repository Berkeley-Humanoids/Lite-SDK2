/* CycloneDDS topic descriptors for the lite_sdk2 message set.
 *
 * These mirror the IDL in ../../idl/lite_sdk2/msg/*.idl exactly. If you change
 * a struct layout there, update:
 *   - this file (fields + ops array)
 *   - rust/src/ffi.rs (the #[repr(C)] shadow structs)
 *   - rust/src/messages.rs (the high-level types and their CdrBody impls)
 *   - python/lite_sdk2/messages/*.py (IdlStruct field order + typename)
 *   - rust/tests/data/low_command.cdr (regenerate via scripts/refresh_fixtures.py)
 */
#include <stddef.h>

#include "dds/ddsc/dds_public_impl.h"

typedef struct dds_sequence_float
{
  uint32_t _maximum;
  uint32_t _length;
  float *_buffer;
  bool _release;
} dds_sequence_float;

typedef struct lite_sdk2_msg__ActuatorCommand
{
  uint32_t mode;
  float position;
  float velocity;
  float torque;
  float kp;
  float kd;
} lite_sdk2_msg__ActuatorCommand;

typedef struct lite_sdk2_msg__ActuatorState
{
  uint32_t mode;
  float position;
  float velocity;
  float torque;
  float acceleration;
  float temperature;
} lite_sdk2_msg__ActuatorState;

typedef struct lite_sdk2_msg__ImuState
{
  dds_sequence_float quaternion;
  dds_sequence_float gyroscope;
  dds_sequence_float accelerometer;
  dds_sequence_float rpy;
  float temperature;
} lite_sdk2_msg__ImuState;

typedef struct dds_sequence_lite_sdk2_msg__ActuatorCommand
{
  uint32_t _maximum;
  uint32_t _length;
  lite_sdk2_msg__ActuatorCommand *_buffer;
  bool _release;
} dds_sequence_lite_sdk2_msg__ActuatorCommand;

typedef struct dds_sequence_lite_sdk2_msg__ActuatorState
{
  uint32_t _maximum;
  uint32_t _length;
  lite_sdk2_msg__ActuatorState *_buffer;
  bool _release;
} dds_sequence_lite_sdk2_msg__ActuatorState;

typedef struct lite_sdk2_msg__LowCommand
{
  uint32_t configuration;
  dds_sequence_lite_sdk2_msg__ActuatorCommand actuator_commands;
} lite_sdk2_msg__LowCommand;

typedef struct lite_sdk2_msg__LowState
{
  uint32_t version;
  uint32_t tick;
  uint32_t configuration;
  lite_sdk2_msg__ImuState imu_state;
  dds_sequence_lite_sdk2_msg__ActuatorState actuator_states;
} lite_sdk2_msg__LowState;

static const uint32_t lite_sdk2_msg__LowCommand__ops[] =
{
  DDS_OP_ADR | DDS_OP_TYPE_4BY, offsetof(lite_sdk2_msg__LowCommand, configuration),
  DDS_OP_ADR | DDS_OP_TYPE_SEQ | DDS_OP_SUBTYPE_STU, offsetof(lite_sdk2_msg__LowCommand, actuator_commands),
  sizeof(lite_sdk2_msg__ActuatorCommand), (17u << 16u) + 4u,
  DDS_OP_ADR | DDS_OP_TYPE_4BY, offsetof(lite_sdk2_msg__ActuatorCommand, mode),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorCommand, position),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorCommand, velocity),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorCommand, torque),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorCommand, kp),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorCommand, kd),
  DDS_OP_RTS,
  DDS_OP_RTS
};

const dds_topic_descriptor_t lite_sdk2_msg__LowCommand__desc =
{
  sizeof(lite_sdk2_msg__LowCommand),
  sizeof(char *),
  DDS_TOPIC_NO_OPTIMIZE,
  0u,
  "lite_sdk2::msg::LowCommand",
  NULL,
  10,
  lite_sdk2_msg__LowCommand__ops,
  ""
};

static const uint32_t lite_sdk2_msg__LowState__ops[] =
{
  DDS_OP_ADR | DDS_OP_TYPE_4BY, offsetof(lite_sdk2_msg__LowState, version),
  DDS_OP_ADR | DDS_OP_TYPE_4BY, offsetof(lite_sdk2_msg__LowState, tick),
  DDS_OP_ADR | DDS_OP_TYPE_4BY, offsetof(lite_sdk2_msg__LowState, configuration),
  DDS_OP_ADR | DDS_OP_TYPE_SEQ | DDS_OP_SUBTYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__LowState, imu_state.quaternion),
  DDS_OP_ADR | DDS_OP_TYPE_SEQ | DDS_OP_SUBTYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__LowState, imu_state.gyroscope),
  DDS_OP_ADR | DDS_OP_TYPE_SEQ | DDS_OP_SUBTYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__LowState, imu_state.accelerometer),
  DDS_OP_ADR | DDS_OP_TYPE_SEQ | DDS_OP_SUBTYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__LowState, imu_state.rpy),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__LowState, imu_state.temperature),
  DDS_OP_ADR | DDS_OP_TYPE_SEQ | DDS_OP_SUBTYPE_STU, offsetof(lite_sdk2_msg__LowState, actuator_states),
  sizeof(lite_sdk2_msg__ActuatorState), (17u << 16u) + 4u,
  DDS_OP_ADR | DDS_OP_TYPE_4BY, offsetof(lite_sdk2_msg__ActuatorState, mode),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorState, position),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorState, velocity),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorState, torque),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorState, acceleration),
  DDS_OP_ADR | DDS_OP_TYPE_4BY | DDS_OP_FLAG_FP, offsetof(lite_sdk2_msg__ActuatorState, temperature),
  DDS_OP_RTS,
  DDS_OP_RTS
};

const dds_topic_descriptor_t lite_sdk2_msg__LowState__desc =
{
  sizeof(lite_sdk2_msg__LowState),
  sizeof(char *),
  DDS_TOPIC_NO_OPTIMIZE,
  0u,
  "lite_sdk2::msg::LowState",
  NULL,
  17,
  lite_sdk2_msg__LowState__ops,
  ""
};
