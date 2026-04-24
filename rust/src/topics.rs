//! Topic name constants and ROS↔DDS conversion helpers.
//!
//! Mirrors the Python `lite_sdk2.topics` module so both sides agree on
//! topic naming (ROS names with a `/` prefix get a `rt/` prefix on the wire).

pub const LOWCOMMAND: &str = "/lowcommand";
pub const LOWSTATE: &str = "/lowstate";

pub fn ros_topic_to_dds(name: &str) -> String {
    if name.starts_with("rt/") {
        return name.to_string();
    }
    if name.starts_with('/') {
        return format!("rt{name}");
    }
    format!("rt/{name}")
}

pub fn dds_topic_to_ros(name: &str) -> &str {
    // Matches Python: `rt/lowstate` → `/lowstate` (keeps the leading slash).
    name.strip_prefix("rt").unwrap_or(name)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ros_absolute_to_dds() {
        assert_eq!(ros_topic_to_dds("/lowcommand"), "rt/lowcommand");
    }

    #[test]
    fn ros_relative_to_dds() {
        assert_eq!(ros_topic_to_dds("lowcommand"), "rt/lowcommand");
    }

    #[test]
    fn already_dds_passes_through() {
        assert_eq!(ros_topic_to_dds("rt/lowcommand"), "rt/lowcommand");
    }

    #[test]
    fn dds_to_ros_strips_prefix() {
        assert_eq!(dds_topic_to_ros("rt/lowstate"), "/lowstate");
    }
}
