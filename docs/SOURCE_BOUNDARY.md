# Source and data boundary

This release extracts and adapts a bounded temporal/turn-consistency guard
from a larger private local-agent implementation. It starts a new repository
history. The public package is not a copy of the private application tree.

Included:

- Three bounded Japanese checks: outdated bedtime sendoffs, supported
  immediate-reply chronology conflicts, and unsupported persistent-memory
  mutation claims.
- Immutable evidence and receipt structures, one text-correction callback,
  repeated validation, and a delivery result that withholds unresolved text.
- Packaging metadata, licensing, installation/integration documentation,
  and wholly synthetic tests and examples.

Excluded:

- Private identities, persona prompts, dialogue, memory databases, logs,
  device paths, credentials, model weights, and original Git history.
- Unfinished-message classification, reflection, memory retrieval and
  evidence-search mechanisms, or the wider application's runtime.

Public-source adaptations remove application-specific identity and timezone
dependencies, fixed elapsed-time wording, and direct store access. The host
supplies an explicit local reference time and turn-bound execution receipts.
The actual elapsed duration of an event is never invented by a repair template.

Importing this package or running its CLI and offline example makes no
network requests and writes no conversation state. Passing private inputs
to a host-owned model callback or saving results is the host's responsibility.

The copyright identifier in NOTICE and public repository URL are intentional
attribution. They are not runtime personal data.
