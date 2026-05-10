{ lib, ... }:
{
  disko.devices.disk.main = lib.mkForce {
    device = "/dev/nvme0n1";
    type = "disk";
    content = {
      type = "gpt";
      partitions = {
        boot = {
          size = "512M";
          type = "EF00";
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot/firmware";
          };
        };
        root = {
          size = "50G";
          content = {
            type = "filesystem";
            format = "ext4";
            mountpoint = "/";
          };
        };
        longhorn = {
          size = "100%";
          content = {
            type = "filesystem";
            format = "ext4";
            mountpoint = "/var/lib/longhorn";
          };
        };
      };
    };
  };
}
