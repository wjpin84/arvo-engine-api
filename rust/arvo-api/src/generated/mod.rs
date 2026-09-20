//! Generated from the protos by `cargo run -p generate`. Do not edit.
//!
//! One module per package, named as the package is, because that is how
//! prost spells a reference from one package to another.
#![allow(missing_docs, rustdoc::all, clippy::all, clippy::pedantic, clippy::nursery)]

pub mod arvo {
    pub mod common {
        pub mod v1 {
            include!("arvo.common.v1.rs");
        }
    }
    pub mod market {
        pub mod v1 {
            include!("arvo.market.v1.rs");
        }
    }
    pub mod platform {
        pub mod v1 {
            include!("arvo.platform.v1.rs");
        }
    }
    pub mod portfolio {
        pub mod v1 {
            include!("arvo.portfolio.v1.rs");
        }
    }
    pub mod research {
        pub mod v1 {
            include!("arvo.research.v1.rs");
        }
    }
    pub mod session {
        pub mod v1 {
            include!("arvo.session.v1.rs");
        }
    }
}
