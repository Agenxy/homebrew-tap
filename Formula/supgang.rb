class Supgang < Formula
  desc "Peer address discovery for computers whose addresses change"
  homepage "https://github.com/Agenxy/supgang"
  url "https://github.com/Agenxy/supgang/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "496f775fc07d2b4052bc675b140457a802affc4168f01104f4330958e8d126f6"
  license "Apache-2.0"

  depends_on "rust" => :build

  def install
    system "cargo", "install", *std_cargo_args(path: "crates/supgang-cli")
  end

  test do
    assert_match "supgang #{version}", shell_output("#{bin}/supgang --version")

    # The usage line and a subcommand name, not the summary sentence.
    #
    # This asserted "Sovereign peer address discovery" until upstream reworded
    # it, which would have broken the tap on the next release for a copy edit.
    # `Usage:` and the subcommand names come from the CLI structure, which the
    # crate documents as stable; the summary is prose and is not.
    help = shell_output("#{bin}/supgang --help")
    assert_match "Usage: supgang", help
    assert_match(/^\s+doctor\s/, help)
  end
end
