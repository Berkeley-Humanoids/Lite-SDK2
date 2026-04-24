//! Cross-lang test harness.
//!
//! Subscribes to `/lowcommand` and echoes each command back as a `/lowstate`
//! sample, copying every ActuatorCommand field into the matching ActuatorState
//! slot (temperature = 42.0 for each). Exits when it receives SIGINT or after
//! `--duration-s` seconds.
//!
//! Driven by `python/tests/test_crosslang.py` as a subprocess.

use std::env;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use lite_sdk2::{ActuatorState, ImuState, LowCommand, LowState, Participant, initialize};

fn main() {
    let args: Args = parse_args();

    initialize(args.domain_id, args.nic.as_deref()).expect("initialize DDS");
    let participant = Participant::new(args.domain_id).expect("create participant");
    let command_sub = participant
        .subscriber::<LowCommand>("/lowcommand")
        .expect("subscribe to /lowcommand");
    let state_pub = participant
        .publisher::<LowState>("/lowstate")
        .expect("publish to /lowstate");

    let stop = Arc::new(AtomicBool::new(false));
    {
        let stop = Arc::clone(&stop);
        ctrlc::set_handler(move || stop.store(true, Ordering::SeqCst)).ok();
    }

    eprintln!(
        "responder ready: domain={} nic={:?} duration={}s",
        args.domain_id, args.nic, args.duration_s,
    );

    let deadline = Instant::now() + Duration::from_secs_f64(args.duration_s);
    let mut tick: u32 = 0;
    while !stop.load(Ordering::SeqCst) && Instant::now() < deadline {
        match command_sub.take_latest() {
            Ok(Some(command)) => {
                tick = tick.wrapping_add(1);
                let state = LowState {
                    version: 1,
                    tick,
                    configuration: command.configuration,
                    imu_state: ImuState::default(),
                    actuator_states: command
                        .actuator_commands
                        .iter()
                        .map(|c| ActuatorState {
                            mode: c.mode,
                            position: c.position,
                            velocity: c.velocity,
                            torque: c.torque,
                            acceleration: c.kp,
                            temperature: 42.0,
                        })
                        .collect(),
                };
                if let Err(error) = state_pub.write(state) {
                    eprintln!("responder: write_state failed: {error}");
                }
            }
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(error) => {
                eprintln!("responder: take_latest failed: {error}");
                thread::sleep(Duration::from_millis(20));
            }
        }
    }

    eprintln!("responder exiting (ticks={tick})");
}

struct Args {
    domain_id: u16,
    nic: Option<String>,
    duration_s: f64,
}

fn parse_args() -> Args {
    let mut iter = env::args().skip(1);
    let mut domain_id = 0u16;
    let mut nic = None;
    let mut duration_s = 30.0;

    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--domain-id" => {
                domain_id = iter
                    .next()
                    .expect("--domain-id requires a value")
                    .parse()
                    .expect("domain id must parse as u16");
            }
            "--nic" => nic = Some(iter.next().expect("--nic requires a value")),
            "--duration-s" => {
                duration_s = iter
                    .next()
                    .expect("--duration-s requires a value")
                    .parse()
                    .expect("duration must parse as f64");
            }
            "--help" | "-h" => {
                eprintln!(
                    "usage: responder [--domain-id N] [--nic IFACE] [--duration-s SECS]"
                );
                std::process::exit(0);
            }
            other => panic!("unknown argument: {other}"),
        }
    }

    Args {
        domain_id,
        nic,
        duration_s,
    }
}
