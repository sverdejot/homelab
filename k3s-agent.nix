{ pkgs, ... }:
{
  environment.systemPackages = [ pkgs.k3s ];

  services.k3s = {
    enable = true;
    role = "agent";
    serverAddr = "https://homelab-0.local:6443";
    tokenFile = "/etc/k3s/token"; # same token as server
    extraFlags = toString [
      "--kubelet-arg=v=2"
    ];
  };
}
