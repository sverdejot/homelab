{ pkgs, ... }:
{
  environment.systemPackages = [ pkgs.k3s ];

  networking.firewall.allowedTCPPorts = [ 6443 ];

  services.k3s = {
    enable = true;
    role = "server";
    tokenFile = "/etc/k3s/token"; # place token at this path before first boot
    extraFlags = toString [
      "--tls-san=homelab-0.local"
      "--disable=traefik"
      "--disable=servicelb"
      "--disable=local-storage" # Since you are using Longhorn
      "--write-kubeconfig-mode=644"
    ];
  };
}
