use serde::{Serialize, Serializer};

/// What a front end shows when a call did not do what was asked.
///
/// One variant, carrying the engine's own words: the status message from a
/// refused call, or what went wrong before one could be made. Serialises as
/// a plain string, because that is what a front end can render.
#[derive(Debug, thiserror::Error)]
pub enum CommandError {
    /// What went wrong, in the engine's words or this side's.
    #[error("{0}")]
    Failed(String),
}

impl Serialize for CommandError {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&self.to_string())
    }
}
