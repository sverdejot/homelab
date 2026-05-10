{
  systemd.services.k3s = {
    after = [ "sops-nix.service" ];
    wants = [ "sops-nix.service" ];
  };
}
