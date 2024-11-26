# Homelab: Kubernetes Cluster with K3s on NixOS

Lightweight, reproducible and easy-to-scale homelab K8s cluster built using [**Raspberry Pi** devices](https://www.raspberrypi.com/products/raspberry-pi-5/).

## Features

- NixOS-based: fully-reproducible, declarative and deterministic system configuration
- K3s: lightweight container orchestration using K8s
- Raspberry Pi: cost-wise setup

## Getting Started

I'm currently testing the setup locally on my Macbook Air M2, using OrbStack built-in support for NixOS (see `virtualiation.nix`). To reproduce this setup in a similar way:

1. Clone the repository:
   ```bash
   git clone https://github.com/sverdejot/homelab.git
   ```
2. Change user's configuration settings with your own hashed password and SSH key
    ```bash
    mkpasswd -m sha512
    ssh-keygen -t ed25519
    ```
3. Copy the contents of the repo into `/etc/nixos`
    ```bash
    cd
    git clone git@github.com:sverdejot/homelab.git
    sudo cp homelab/* /etc/nixos
    ```
4. Rebuild the Nix configuration
    ```
    sudo nixos-rebuild switch
    ```

Now you should be able to run `sudo kubectl get pods`

