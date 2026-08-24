<img src="docs/icon.svg" width="72" height="72" alt="">

# Agenxy Homebrew tap

Formulae for Agenxy projects. Remap and Supgang are updated by hand from that
project's release; the Dibs cask is written by GoReleaser when Dibs tags one.

```sh
brew install --cask agenxy/tap/dibs
brew install agenxy/tap/remap
brew install agenxy/tap/supgang
```

[Dibs](https://github.com/agenxy/dibs) installs as a cask, from prebuilt
binaries rather than from source: the `dibs` and `dibd` commands and the `dibs`
man page. They are cosign-signed for provenance but not Apple-notarised, so
macOS quarantines them and refuses to run them; the cask clears the flag on
install, which is the main thing it exists to absorb. Homebrew casks are macOS
only — on Linux, take the binaries from
[releases](https://github.com/agenxy/dibs/releases), which cover both
architectures.

[Remap](https://github.com/agenxy/remap) installs the cross-platform `remap`
CLI. Its foundation release validates name-to-address and name-to-service
mappings without changing DNS or system trust; privileged integration follows
in explicitly proof-gated releases.

[Supgang](https://github.com/agenxy/supgang) installs the macOS and Linux
`supgang` CLI. Its first alpha supports direct, authenticated peer contact;
automatic rendezvous, NAT traversal, and owned relay mode remain later work.

Dibs was called Lanes until August 2026, and this tap was `homebrew-lanes`
before that. Both still resolve. `agenxy/lanes/lanes` reaches the tap through
GitHub's redirect, and `tap_migrations.json` sends `lanes` to `dibs`, so an
existing install moves across on the next `brew update` rather than sitting on a
version that no longer gets releases.

Apache 2.0, like everything else here.
