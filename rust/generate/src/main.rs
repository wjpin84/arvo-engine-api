//! Regenerates the Rust bindings from the protos.
//!
//! Run from `rust/`: `cargo run -p generate`. The output is committed under
//! `arvo-api/src/generated` and `arvo-client/src/generated`, so a consumer of
//! the published crates needs neither `protoc` nor a build script, docs.rs
//! builds them as it builds anything else, and a reader can open the types
//! without generating anything. A release checks that running this leaves
//! the tree unchanged.
//!
//! Messages go to `arvo-api`, services to `arvo-client`, and the services'
//! signatures name `arvo-api`'s types through `extern_path` rather than
//! carrying a second copy. Messages only in `arvo-api` because it has to
//! build for WebAssembly, where a gRPC transport does not.

use std::path::{Path, PathBuf};

/// The message packages, in the order the module tree lists them.
const DOMAINS: [&str; 6] = ["common", "market", "platform", "portfolio", "research", "session"];

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let rust = Path::new(env!("CARGO_MANIFEST_DIR")).parent().ok_or("no parent")?.to_path_buf();
    let protos = rust.parent().ok_or("no repository root")?.join("protos");
    std::env::set_var("PROTOC", protoc_bin_vendored::protoc_bin_path()?);

    let mut all: Vec<PathBuf> = walk(&protos).filter(|p| p.extension().is_some_and(|e| e == "proto")).collect();
    all.sort();
    let (services, messages): (Vec<PathBuf>, Vec<PathBuf>) =
        all.into_iter().partition(|p| p.components().any(|c| c.as_os_str() == "services"));
    if messages.is_empty() || services.is_empty() {
        return Err(format!("no protos under {}", protos.display()).into());
    }

    // Messages: one file per package, and a module tree that mirrors the
    // package names so a type in one package can name a type in another.
    let api = rust.join("arvo-api/src/generated");
    reset(&api)?;
    prost_build::Config::new()
        .out_dir(&api)
        // The shapes cross JSON bridges as well as gRPC.
        .type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]")
        .compile_protos(&messages, std::slice::from_ref(&protos))?;
    let mut tree = String::from(
        "//! Generated from the protos by `cargo run -p generate`. Do not edit.\n\
         //!\n\
         //! One module per package, named as the package is, because that is how\n\
         //! prost spells a reference from one package to another.\n\
         #![allow(missing_docs, rustdoc::all, clippy::all, clippy::pedantic, clippy::nursery)]\n\n\
         pub mod arvo {\n",
    );
    for domain in DOMAINS {
        let file = api.join(format!("arvo.{domain}.v1.rs"));
        if !file.is_file() {
            return Err(format!("prost did not write {}", file.display()).into());
        }
        tree.push_str(&format!(
            "    pub mod {domain} {{\n        pub mod v1 {{\n            include!(\"arvo.{domain}.v1.rs\");\n        }}\n    }}\n"
        ));
    }
    tree.push_str("}\n");
    std::fs::write(api.join("mod.rs"), tree)?;

    // Services: the stubs, client and server, over the types above.
    let client = rust.join("arvo-client/src/generated");
    reset(&client)?;
    let mut config = tonic_prost_build::configure().out_dir(&client).build_client(true).build_server(true);
    for domain in DOMAINS {
        config = config.extern_path(format!(".arvo.{domain}.v1"), format!("::arvo_api::{domain}"));
    }
    config.compile_protos(&services, &[protos])?;
    if !client.join("arvo.services.v1.rs").is_file() {
        return Err("tonic did not write arvo.services.v1.rs".into());
    }
    std::fs::write(
        client.join("mod.rs"),
        "//! Generated from the protos by `cargo run -p generate`. Do not edit.\n\
         #![allow(missing_docs, rustdoc::all, clippy::all, clippy::pedantic, clippy::nursery)]\n\n\
         /// The stubs, client and server, from `arvo/services/v1`.\n\
         pub mod services {\n    include!(\"arvo.services.v1.rs\");\n}\n",
    )?;

    println!("generated {} message packages and {} service files", DOMAINS.len(), services.len());
    Ok(())
}

/// An empty output directory.
fn reset(dir: &Path) -> std::io::Result<()> {
    if dir.exists() {
        std::fs::remove_dir_all(dir)?;
    }
    std::fs::create_dir_all(dir)
}

/// Every file under `dir`, depth first.
fn walk(dir: &Path) -> Box<dyn Iterator<Item = PathBuf>> {
    let Ok(entries) = std::fs::read_dir(dir) else { return Box::new(std::iter::empty()) };
    Box::new(entries.flatten().flat_map(|entry| {
        let path = entry.path();
        if path.is_dir() { walk(&path) } else { Box::new(std::iter::once(path)) }
    }))
}
