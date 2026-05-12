{ pkgs, ... }:
{
  imports = [ ./default.nix ];

  environment.systemPackages = [ pkgs.k3s ];

  services.k3s = {
    enable = true;
    role = "agent";
    serverAddr = "https://192.168.1.2:6443";
    tokenFile = "/etc/k3s/token";
  };
}
