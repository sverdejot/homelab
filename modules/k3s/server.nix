{ config, pkgs, lib, ... }:
let
  ip = (builtins.head config.networking.interfaces.end0.ipv4.addresses).address;
in {
  imports = [ ./default.nix ];

  environment.systemPackages = [ pkgs.k3s ];

  networking.firewall.allowedTCPPorts = [ 6443 ];

  services.k3s = {
    enable = true;
    role = "server";
    tokenFile = "/run/secrets/k3s-token";
    extraFlags = lib.concatStringsSep " " [
      "--tls-san=${config.networking.hostName}.local"
      "--tls-san=${ip}"
      "--disable=traefik"
      "--disable=servicelb"
      "--disable=local-storage"
      "--write-kubeconfig-mode=644"
    ];
  };
}
