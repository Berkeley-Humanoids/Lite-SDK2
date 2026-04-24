// Compiles the CycloneDDS topic descriptors for our message set and links
// against the system-installed CycloneDDS C library (ddsc).
//
// Locates CycloneDDS in this order:
//   1. `CYCLONEDDS_HOME` env var (the convention from install_cyclonedds.sh)
//   2. `pkg-config --cflags --libs CycloneDDS` (honors `PKG_CONFIG_PATH`)
//   3. System include/lib paths (fails with a helpful message if not found)

use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=../idl");

    if env::var_os("CARGO_FEATURE_TRANSPORT").is_none() {
        // Codec-only build; skip C compilation and ddsc linkage.
        return;
    }

    println!("cargo:rerun-if-changed=native/descriptors.c");
    println!("cargo:rerun-if-env-changed=CC");
    println!("cargo:rerun-if-env-changed=AR");
    println!("cargo:rerun-if-env-changed=CYCLONEDDS_HOME");
    println!("cargo:rerun-if-env-changed=PKG_CONFIG_PATH");

    let cyclonedds = locate_cyclonedds();

    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("missing manifest dir"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("missing OUT_DIR"));
    let source = manifest_dir.join("native/descriptors.c");
    let object = out_dir.join("lite_sdk2_descriptors.o");
    let archive = out_dir.join("liblite_sdk2_descriptors.a");

    let cc = env::var("CC").unwrap_or_else(|_| "cc".to_string());
    let ar = env::var("AR").unwrap_or_else(|_| "ar".to_string());

    let mut compile = Command::new(&cc);
    compile.arg("-fPIC").arg("-std=c11").arg("-c").arg(&source);
    for dir in &cyclonedds.include_dirs {
        compile.arg(format!("-I{}", dir.display()));
    }
    compile.arg("-o").arg(&object);
    run(&mut compile);

    run(Command::new(&ar).arg("crus").arg(&archive).arg(&object));

    println!("cargo:rustc-link-search=native={}", out_dir.display());
    println!("cargo:rustc-link-lib=static=lite_sdk2_descriptors");
    for dir in &cyclonedds.lib_dirs {
        println!("cargo:rustc-link-search=native={}", dir.display());
        // Emit an rpath so the resulting binary can find libddsc at runtime
        // without needing LD_LIBRARY_PATH. Harmless when ddsc is on the system
        // linker path already.
        println!("cargo:rustc-link-arg=-Wl,-rpath,{}", dir.display());
    }
    println!("cargo:rustc-link-lib=ddsc");
}

struct CycloneDds {
    include_dirs: Vec<PathBuf>,
    lib_dirs: Vec<PathBuf>,
}

fn locate_cyclonedds() -> CycloneDds {
    if let Some(home) = env::var_os("CYCLONEDDS_HOME") {
        let home = PathBuf::from(home);
        let include = home.join("include");
        let lib = home.join("lib");
        if include.join("dds/ddsc/dds_public_impl.h").exists() {
            return CycloneDds {
                include_dirs: vec![include],
                lib_dirs: vec![lib].into_iter().filter(|p| p.exists()).collect(),
            };
        }
        eprintln!(
            "warning: CYCLONEDDS_HOME={} does not contain include/dds/ddsc/dds_public_impl.h; \
             trying pkg-config next",
            home.display()
        );
    }

    if let Some(info) = query_pkg_config() {
        return info;
    }

    // Last-ditch: trust that `cc` will find ddsc's headers on the system
    // default path. If not, the compile fails with a clear -I error below.
    if Path::new("/usr/include/dds/ddsc/dds_public_impl.h").exists()
        || Path::new("/usr/local/include/dds/ddsc/dds_public_impl.h").exists()
    {
        return CycloneDds {
            include_dirs: Vec::new(),
            lib_dirs: Vec::new(),
        };
    }

    panic!(
        "CycloneDDS not found.\n\
         \n\
         Tried in order: CYCLONEDDS_HOME, pkg-config CycloneDDS, /usr(/local)/include/dds.\n\
         \n\
         Fix one of these:\n\
         - export CYCLONEDDS_HOME=/path/to/cyclonedds/install\n\
         - export PKG_CONFIG_PATH=/path/to/cyclonedds/install/lib/pkgconfig\n\
         - install CycloneDDS system-wide so headers land in /usr/include/dds/\n\
         \n\
         See Lite-SDK2/install_cyclonedds.sh for a from-source install."
    );
}

fn query_pkg_config() -> Option<CycloneDds> {
    let output = Command::new("pkg-config")
        .args(["--cflags", "--libs", "CycloneDDS"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8(output.stdout).ok()?;
    let mut include_dirs = Vec::new();
    let mut lib_dirs = Vec::new();
    for token in text.split_whitespace() {
        if let Some(path) = token.strip_prefix("-I") {
            include_dirs.push(PathBuf::from(path));
        } else if let Some(path) = token.strip_prefix("-L") {
            lib_dirs.push(PathBuf::from(path));
        }
    }
    if include_dirs.is_empty() && lib_dirs.is_empty() {
        return None;
    }
    Some(CycloneDds {
        include_dirs,
        lib_dirs,
    })
}

fn run(command: &mut Command) {
    let debug = format!("{command:?}");
    let status = command
        .status()
        .unwrap_or_else(|error| panic!("failed to run {debug}: {error}"));
    if !status.success() {
        panic!("command failed: {debug}");
    }
}
