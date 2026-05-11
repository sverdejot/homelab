{
  # harcoded until I find a proper way of handling secrets using sops-nix
  systemd.tmpfiles.rules = [
    "f /etc/k3s/token 0400 root root - ttNUyfWrYgpRIxU9JTFRlt8bFpUfbTBn1K0SH2NWRYA="
  ];
}
