# VPS Swap Setup (Cheap Server)

Run these commands on the VPS host over SSH (not inside a container).

## 1) Check current memory + swap
```bash
free -h
swapon --show
```

Why:
- `free -h` shows current RAM and swap usage.
- `swapon --show` confirms if swap is already active.

## 2) Create a 2GB swap file
```bash
sudo fallocate -l 2G /swapfile
```

If `fallocate` is unavailable/fails:
```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
```

Why:
- Creates disk-backed emergency memory space.

## 3) Restrict file permissions
```bash
sudo chmod 600 /swapfile
```

Why:
- Swap can contain sensitive memory data; root-only access is required.

## 4) Format the file as swap
```bash
sudo mkswap /swapfile
```

Why:
- Marks the file in the format the kernel expects for swap.

## 5) Enable swap immediately
```bash
sudo swapon /swapfile
```

Why:
- Activates swap now without rebooting.

## 6) Verify it is active
```bash
swapon --show
free -h
```

Expected:
- `swapon --show` should list `/swapfile`.
- `free -h` should show non-zero Swap total.

## 7) Persist swap across reboots
```bash
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Why:
- Ensures swap automatically comes back after reboot.

## 8) Tune swappiness (recommended)
```bash
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.d/99-swappiness.conf
sudo sysctl --system
```

Why:
- `swappiness=10` keeps swap as a safety net instead of primary memory.
- `vfs_cache_pressure=50` preserves useful filesystem cache longer.

## 9) Final validation
```bash
free -h
swapon --show
cat /proc/sys/vm/swappiness
grep -n '/swapfile' /etc/fstab
```

Expected:
- Swap is active.
- Swappiness reads `10`.
- `/etc/fstab` contains a `/swapfile` entry.

## Optional: 1GB swap instead of 2GB
```bash
sudo fallocate -l 1G /swapfile
# or: sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
```
