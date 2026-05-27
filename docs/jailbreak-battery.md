# Jailbreak battery

The battery is the load-bearing axis of PromptAudit. It is a versioned corpus of
known jailbreak prompts grouped into attack classes. Each prompt declares the
expected behavior (`should_refuse`).

## Attack classes

- **roleplay**: DAN-style persona and role assumption (evil twin, developer
  mode, deceased-relative framing).
- **ignore_instructions**: direct override of the system prompt.
- **encoding**: base64, rot13, and other encodings smuggling a harmful payload.
- **hypothetical**: fictional or "thought experiment" framing.
- **token_smuggling**: splitting or spacing trigger tokens to evade filters.
- **prompt_leak**: attempts to extract the hidden system prompt.
- **obfuscation**: misspelling and word-splitting to dodge keyword filters.
- **payload_injection**: fake authority or pre-filled refusals.
- **benign_control**: benign prompts that should NOT be refused; these guard
  against over-refusal.

## Schema

```yaml
version: 1
categories:
  roleplay:
    description: "..."
    prompts:
      - id: rp-dan-classic
        text: "..."
        should_refuse: true
```

## Coverage invariants

Enforced by the test suite:

- every non-control attack class has at least 3 prompts,
- every prompt has an explicit `should_refuse`,
- the battery has at least 30 prompts total.

## Versioning

Adding a new attack class is a battery version bump. A model that passed an
earlier battery version is re-audited against the new one; failures on the newly
added class are surfaced as `newly-covered-and-failing`, distinct from a true
regression. See [battery-versioning.md](battery-versioning.md).
