# Linux 内核源码目录结构详解

> 源码版本：**Linux 6.6.161**（LTS）
> 本目录树为「目录级」展示（深度 2 层），配合每个目录的作用说明。
> 配套阅读：[Linux内核学习路线.md](Linux内核学习路线.md)

---

## 1. 顶层目录总览

| 目录 | 作用 | 学习优先级 |
|------|------|-----------|
| [kernel/](linux-6.6.161/kernel/) | **核心机制**：调度、进程、中断、锁、RCU、时间、模块、cgroup、bpf | ★★★★★ |
| [mm/](linux-6.6.161/mm/) | **内存管理**：伙伴系统、slab、页表、缺页、回收 | ★★★★★ |
| [fs/](linux-6.6.161/fs/) | **文件系统**：VFS 层 + 各类具体文件系统 | ★★★★★ |
| [include/](linux-6.6.161/include/) | **头文件**：内核数据结构的"字典"，读源码的入口 | ★★★★★ |
| [arch/](linux-6.6.161/arch/) | 架构相关代码（x86/ARM/RISC-V...，与硬件打交道的部分） | ★★★★☆ |
| [net/](linux-6.6.161/net/) | 网络协议栈（TCP/IP、socket、netfilter） | ★★★★☆ |
| [block/](linux-6.6.161/block/) | 块设备 I/O 层（bio、请求队列、I/O 调度器） | ★★★★☆ |
| [init/](linux-6.6.161/init/) | 内核启动初始化（`start_kernel` 所在地） | ★★★★☆ |
| [ipc/](linux-6.6.161/ipc/) | System V 进程间通信（消息队列、信号量、共享内存） | ★★★☆☆ |
| [drivers/](linux-6.6.161/drivers/) | **设备驱动**（占内核代码量约 60%，学习以框架为主） | ★★★☆☆ |
| [lib/](linux-6.6.161/lib/) | 通用库函数（链表、红黑树、字符串、压缩算法等） | ★★★☆☆ |
| [scripts/](linux-6.6.161/scripts/) | 构建辅助脚本（Kconfig、模块处理等） | ★★★☆☆ |
| [crypto/](linux-6.6.161/crypto/) | 内核加密 API 与算法实现 | ★★☆☆☆ |
| [io_uring/](linux-6.6.161/io_uring/) | io_uring 高性能异步 I/O（6.x 热点） | ★★☆☆☆ |
| [security/](linux-6.6.161/security/) | 安全模块 LSM（SELinux、AppArmor 等） | ★★☆☆☆ |
| [virt/](linux-6.6.161/virt/) | 虚拟化（KVM 通用部分） | ★★☆☆☆ |
| [sound/](linux-6.6.161/sound/) | 音频子系统（ALSA） | ★☆☆☆☆ |
| [tools/](linux-6.6.161/tools/) | 用户态工具源码（perf、bpftool、objtool...） | ★★☆☆☆ |
| [samples/](linux-6.6.161/samples/) | 各子系统的示例代码（入门练习的宝库） | ★★☆☆☆ |
| [usr/](linux-6.6.161/usr/) | initramfs 构建（gen_init_cpio） | ★☆☆☆☆ |
| [rust/](linux-6.6.161/rust/) | 内核 Rust 语言支持（6.6 引入的试验特性） | ★☆☆☆☆ |
| [certs/](linux-6.6.161/certs/) | 内核模块签名证书 | ★☆☆☆☆ |
| [Documentation/](linux-6.6.161/Documentation/) | **官方文档**（质量极高，遇到问题先查这里） | ★★★★★ |
| [LICENSES/](linux-6.6.161/LICENSES/) | SPDX 许可证文本（GPL-2.0 等） | ☆☆☆☆☆ |

---

## 2. 完整目录树（深度 2 层）

<details>
<summary>点击展开：linux-6.6.161/ 完整目录树（仅目录，约 700 项）</summary>

```
linux-6.6.161/
├── Documentation/
│   ├── ABI/
│   ├── PCI/
│   ├── RCU/
│   ├── accel/
│   ├── accounting/
│   ├── admin-guide/
│   ├── arch/
│   ├── block/
│   ├── bpf/
│   ├── cdrom/
│   ├── core-api/
│   ├── cpu-freq/
│   ├── crypto/
│   ├── dev-tools/
│   ├── devicetree/
│   ├── doc-guide/
│   ├── driver-api/
│   ├── fault-injection/
│   ├── fb/
│   ├── features/
│   ├── filesystems/
│   ├── firmware-guide/
│   ├── firmware_class/
│   ├── fpga/
│   ├── gpu/
│   ├── hid/
│   ├── hwmon/
│   ├── i2c/
│   ├── iio/
│   ├── images/
│   ├── infiniband/
│   ├── input/
│   ├── isdn/
│   ├── kbuild/
│   ├── kernel-hacking/
│   ├── leds/
│   ├── litmus-tests/
│   ├── livepatch/
│   ├── locking/
│   ├── maintainer/
│   ├── mhi/
│   ├── misc-devices/
│   ├── mm/
│   ├── netlabel/
│   ├── netlink/
│   ├── networking/
│   ├── nvdimm/
│   ├── nvme/
│   ├── pcmcia/
│   ├── peci/
│   ├── power/
│   ├── powerpc/
│   ├── process/
│   ├── riscv/
│   ├── rust/
│   ├── scheduler/
│   ├── scsi/
│   ├── security/
│   ├── sound/
│   ├── sphinx/
│   ├── sphinx-static/
│   ├── spi/
│   ├── staging/
│   ├── target/
│   ├── timers/
│   ├── tools/
│   ├── trace/
│   ├── translations/
│   ├── usb/
│   ├── userspace-api/
│   ├── virt/
│   ├── w1/
│   ├── watchdog/
│   └── wmi/
├── LICENSES/
│   ├── deprecated/
│   ├── dual/
│   ├── exceptions/
│   └── preferred/
├── arch/
│   ├── alpha/
│   ├── arc/
│   ├── arm/
│   ├── arm64/
│   ├── csky/
│   ├── hexagon/
│   ├── ia64/
│   ├── loongarch/
│   ├── m68k/
│   ├── microblaze/
│   ├── mips/
│   ├── nios2/
│   ├── openrisc/
│   ├── parisc/
│   ├── powerpc/
│   ├── riscv/
│   ├── s390/
│   ├── sh/
│   ├── sparc/
│   ├── um/
│   ├── x86/
│   └── xtensa/
├── block/
│   └── partitions/
├── certs/
├── crypto/
│   ├── asymmetric_keys/
│   └── async_tx/
├── drivers/
│   ├── accel/
│   ├── accessibility/
│   ├── acpi/
│   ├── amba/
│   ├── android/
│   ├── ata/
│   ├── atm/
│   ├── auxdisplay/
│   ├── base/
│   ├── bcma/
│   ├── block/
│   ├── bluetooth/
│   ├── bus/
│   ├── cache/
│   ├── cdrom/
│   ├── cdx/
│   ├── char/
│   ├── clk/
│   ├── clocksource/
│   ├── comedi/
│   ├── connector/
│   ├── counter/
│   ├── cpufreq/
│   ├── cpuidle/
│   ├── crypto/
│   ├── cxl/
│   ├── dax/
│   ├── dca/
│   ├── devfreq/
│   ├── dio/
│   ├── dma/
│   ├── dma-buf/
│   ├── edac/
│   ├── eisa/
│   ├── extcon/
│   ├── firewire/
│   ├── firmware/
│   ├── fpga/
│   ├── fsi/
│   ├── gnss/
│   ├── gpio/
│   ├── gpu/
│   ├── greybus/
│   ├── hid/
│   ├── hsi/
│   ├── hte/
│   ├── hv/
│   ├── hwmon/
│   ├── hwspinlock/
│   ├── hwtracing/
│   ├── i2c/
│   ├── i3c/
│   ├── idle/
│   ├── iio/
│   ├── infiniband/
│   ├── input/
│   ├── interconnect/
│   ├── iommu/
│   ├── ipack/
│   ├── irqchip/
│   ├── isdn/
│   ├── leds/
│   ├── macintosh/
│   ├── mailbox/
│   ├── mcb/
│   ├── md/
│   ├── media/
│   ├── memory/
│   ├── memstick/
│   ├── message/
│   ├── mfd/
│   ├── misc/
│   ├── mmc/
│   ├── most/
│   ├── mtd/
│   ├── mux/
│   ├── net/
│   ├── nfc/
│   ├── ntb/
│   ├── nubus/
│   ├── nvdimm/
│   ├── nvme/
│   ├── nvmem/
│   ├── of/
│   ├── opp/
│   ├── parisc/
│   ├── parport/
│   ├── pci/
│   ├── pcmcia/
│   ├── peci/
│   ├── perf/
│   ├── phy/
│   ├── pinctrl/
│   ├── platform/
│   ├── pmdomain/
│   ├── pnp/
│   ├── power/
│   ├── powercap/
│   ├── pps/
│   ├── ps3/
│   ├── ptp/
│   ├── pwm/
│   ├── rapidio/
│   ├── ras/
│   ├── regulator/
│   ├── remoteproc/
│   ├── reset/
│   ├── rpmsg/
│   ├── rtc/
│   ├── s390/
│   ├── sbus/
│   ├── scsi/
│   ├── sh/
│   ├── siox/
│   ├── slimbus/
│   ├── soc/
│   ├── soundwire/
│   ├── spi/
│   ├── spmi/
│   ├── ssb/
│   ├── staging/
│   ├── target/
│   ├── tc/
│   ├── tee/
│   ├── thermal/
│   ├── thunderbolt/
│   ├── tty/
│   ├── ufs/
│   ├── uio/
│   ├── usb/
│   ├── vdpa/
│   ├── vfio/
│   ├── vhost/
│   ├── video/
│   ├── virt/
│   ├── virtio/
│   ├── vlynq/
│   ├── w1/
│   ├── watchdog/
│   ├── xen/
│   └── zorro/
├── fs/
│   ├── 9p/
│   ├── adfs/
│   ├── affs/
│   ├── afs/
│   ├── autofs/
│   ├── befs/
│   ├── bfs/
│   ├── btrfs/
│   ├── cachefiles/
│   ├── ceph/
│   ├── coda/
│   ├── configfs/
│   ├── cramfs/
│   ├── crypto/
│   ├── debugfs/
│   ├── devpts/
│   ├── dlm/
│   ├── ecryptfs/
│   ├── efivarfs/
│   ├── efs/
│   ├── erofs/
│   ├── exfat/
│   ├── exportfs/
│   ├── ext2/
│   ├── ext4/
│   ├── f2fs/
│   ├── fat/
│   ├── freevxfs/
│   ├── fscache/
│   ├── fuse/
│   ├── gfs2/
│   ├── hfs/
│   ├── hfsplus/
│   ├── hostfs/
│   ├── hpfs/
│   ├── hugetlbfs/
│   ├── iomap/
│   ├── isofs/
│   ├── jbd2/
│   ├── jffs2/
│   ├── jfs/
│   ├── kernfs/
│   ├── lockd/
│   ├── minix/
│   ├── netfs/
│   ├── nfs/
│   ├── nfs_common/
│   ├── nfsd/
│   ├── nilfs2/
│   ├── nls/
│   ├── notify/
│   ├── ntfs3/
│   ├── ocfs2/
│   ├── omfs/
│   ├── openpromfs/
│   ├── orangefs/
│   ├── overlayfs/
│   ├── proc/
│   ├── pstore/
│   ├── qnx4/
│   ├── qnx6/
│   ├── quota/
│   ├── ramfs/
│   ├── reiserfs/
│   ├── romfs/
│   ├── smb/
│   ├── squashfs/
│   ├── sysfs/
│   ├── sysv/
│   ├── tracefs/
│   ├── ubifs/
│   ├── udf/
│   ├── ufs/
│   ├── unicode/
│   ├── vboxsf/
│   ├── verity/
│   ├── xfs/
│   └── zonefs/
├── include/
│   ├── acpi/
│   ├── asm-generic/
│   ├── clocksource/
│   ├── crypto/
│   ├── drm/
│   ├── dt-bindings/
│   ├── keys/
│   ├── kunit/
│   ├── kvm/
│   ├── linux/
│   ├── math-emu/
│   ├── media/
│   ├── memory/
│   ├── misc/
│   ├── net/
│   ├── pcmcia/
│   ├── ras/
│   ├── rdma/
│   ├── rv/
│   ├── scsi/
│   ├── soc/
│   ├── sound/
│   ├── target/
│   ├── trace/
│   ├── uapi/
│   ├── ufs/
│   ├── vdso/
│   ├── video/
│   └── xen/
├── init/
├── io_uring/
├── ipc/
├── kernel/
│   ├── bpf/
│   ├── cgroup/
│   ├── configs/
│   ├── debug/
│   ├── dma/
│   ├── entry/
│   ├── events/
│   ├── futex/
│   ├── gcov/
│   ├── irq/
│   ├── kcsan/
│   ├── livepatch/
│   ├── locking/
│   ├── module/
│   ├── power/
│   ├── printk/
│   ├── rcu/
│   ├── sched/
│   ├── time/
│   └── trace/
├── lib/
│   ├── 842/
│   ├── crypto/
│   ├── dim/
│   ├── fonts/
│   ├── kunit/
│   ├── livepatch/
│   ├── lz4/
│   ├── lzo/
│   ├── math/
│   ├── pldmfw/
│   ├── raid6/
│   ├── reed_solomon/
│   ├── test_fortify/
│   ├── vdso/
│   ├── xz/
│   ├── zlib_deflate/
│   ├── zlib_dfltcc/
│   ├── zlib_inflate/
│   └── zstd/
├── mm/
│   ├── damon/
│   ├── kasan/
│   ├── kfence/
│   └── kmsan/
├── net/
│   ├── 6lowpan/
│   ├── 802/
│   ├── 8021q/
│   ├── 9p/
│   ├── appletalk/
│   ├── atm/
│   ├── ax25/
│   ├── batman-adv/
│   ├── bluetooth/
│   ├── bpf/
│   ├── bpfilter/
│   ├── bridge/
│   ├── caif/
│   ├── can/
│   ├── ceph/
│   ├── core/
│   ├── dcb/
│   ├── dccp/
│   ├── devlink/
│   ├── dns_resolver/
│   ├── dsa/
│   ├── ethernet/
│   ├── ethtool/
│   ├── handshake/
│   ├── hsr/
│   ├── ieee802154/
│   ├── ife/
│   ├── ipv4/
│   ├── ipv6/
│   ├── iucv/
│   ├── kcm/
│   ├── key/
│   ├── l2tp/
│   ├── l3mdev/
│   ├── lapb/
│   ├── llc/
│   ├── mac80211/
│   ├── mac802154/
│   ├── mctp/
│   ├── mpls/
│   ├── mptcp/
│   ├── ncsi/
│   ├── netfilter/
│   ├── netlabel/
│   ├── netlink/
│   ├── netrom/
│   ├── nfc/
│   ├── nsh/
│   ├── openvswitch/
│   ├── packet/
│   ├── phonet/
│   ├── psample/
│   ├── qrtr/
│   ├── rds/
│   ├── rfkill/
│   ├── rose/
│   ├── rxrpc/
│   ├── sched/
│   ├── sctp/
│   ├── smc/
│   ├── strparser/
│   ├── sunrpc/
│   ├── switchdev/
│   ├── tipc/
│   ├── tls/
│   ├── unix/
│   ├── vmw_vsock/
│   ├── wireless/
│   ├── x25/
│   ├── xdp/
│   └── xfrm/
├── rust/
│   ├── alloc/
│   ├── bindings/
│   ├── kernel/
│   ├── macros/
│   └── uapi/
├── samples/
│   ├── acrn/
│   ├── auxdisplay/
│   ├── binderfs/
│   ├── bpf/
│   ├── configfs/
│   ├── connector/
│   ├── coresight/
│   ├── fanotify/
│   ├── fprobe/
│   ├── ftrace/
│   ├── hid/
│   ├── hidraw/
│   ├── hw_breakpoint/
│   ├── kdb/
│   ├── kfifo/
│   ├── kmemleak/
│   ├── kobject/
│   ├── kprobes/
│   ├── landlock/
│   ├── livepatch/
│   ├── mei/
│   ├── nitro_enclaves/
│   ├── pfsm/
│   ├── pidfd/
│   ├── pktgen/
│   ├── qmi/
│   ├── rpmsg/
│   ├── rust/
│   ├── seccomp/
│   ├── timers/
│   ├── trace_events/
│   ├── trace_printk/
│   ├── uhid/
│   ├── user_events/
│   ├── v4l/
│   ├── vfio-mdev/
│   ├── vfs/
│   ├── watch_queue/
│   └── watchdog/
├── scripts/
│   ├── atomic/
│   ├── basic/
│   ├── clang-tools/
│   ├── coccinelle/
│   ├── dtc/
│   ├── dummy-tools/
│   ├── gcc-plugins/
│   ├── gdb/
│   ├── genksyms/
│   ├── kconfig/
│   ├── ksymoops/
│   ├── mod/
│   ├── package/
│   ├── selinux/
│   └── tracing/
├── security/
│   ├── apparmor/
│   ├── bpf/
│   ├── integrity/
│   ├── keys/
│   ├── landlock/
│   ├── loadpin/
│   ├── lockdown/
│   ├── safesetid/
│   ├── selinux/
│   ├── smack/
│   ├── tomoyo/
│   └── yama/
├── sound/
│   ├── ac97/
│   ├── aoa/
│   ├── arm/
│   ├── atmel/
│   ├── core/
│   ├── drivers/
│   ├── firewire/
│   ├── hda/
│   ├── i2c/
│   ├── isa/
│   ├── mips/
│   ├── oss/
│   ├── parisc/
│   ├── pci/
│   ├── pcmcia/
│   ├── ppc/
│   ├── sh/
│   ├── soc/
│   ├── sparc/
│   ├── spi/
│   ├── synth/
│   ├── usb/
│   ├── virtio/
│   ├── x86/
│   └── xen/
├── tools/
│   ├── accounting/
│   ├── arch/
│   ├── bootconfig/
│   ├── bpf/
│   ├── build/
│   ├── certs/
│   ├── cgroup/
│   ├── counter/
│   ├── crypto/
│   ├── debugging/
│   ├── edid/
│   ├── firewire/
│   ├── firmware/
│   ├── gpio/
│   ├── hv/
│   ├── iio/
│   ├── include/
│   ├── kvm/
│   ├── laptop/
│   ├── leds/
│   ├── lib/
│   ├── memory-model/
│   ├── mm/
│   ├── net/
│   ├── objtool/
│   ├── pci/
│   ├── pcmcia/
│   ├── perf/
│   ├── power/
│   ├── rcu/
│   ├── scripts/
│   ├── spi/
│   ├── testing/
│   ├── thermal/
│   ├── time/
│   ├── tracing/
│   ├── usb/
│   ├── verification/
│   ├── virtio/
│   ├── wmi/
│   └── workqueue/
├── usr/
│   ├── dummy-include/
│   └── include/
└── virt/
    ├── kvm/
    └── lib/
```

</details>

---

## 3. 核心子系统详解

### 3.1 kernel/ —— 内核的心脏

```
kernel/
├── sched/        # 调度器
├── irq/          # 中断框架
├── locking/      # 锁与同步原语
├── rcu/          # RCU 实现
├── time/         # 时间与定时器
├── power/        # 电源管理
├── printk/       # 内核日志
├── module/       # 模块机制
├── bpf/          # eBPF 虚拟机
├── cgroup/       # 控制组
├── trace/        # ftrace 框架
├── events/       # perf 事件
├── futex/        # 用户态快速锁
├── dma/          # DMA 映射 API
├── entry/        # 系统调用进入/退出（架构无关部分）
├── debug/        # 调试支持（kdb 等）
├── livepatch/    # 内核热补丁
├── kcsan/        # 并发数据竞争检测
└── gcov/         # 代码覆盖率
```

| 目录 | 核心内容 |
|------|----------|
| [kernel/sched/](linux-6.6.161/kernel/sched/) | `core.c`（调度入口 `schedule()`、上下文切换）、`fair.c`（CFS 完全公平调度类）、`rt.c`（实时）、`deadline.c`（EDF）、负载均衡 |
| [kernel/irq/](linux-6.6.161/kernel/irq/) | `irqdesc` 中断描述符、`manage.c`（`request_irq` 实现）、`chip.c`（中断控制器抽象） |
| [kernel/locking/](linux-6.6.161/kernel/locking/) | `spinlock.c`、`mutex.c`、`rwsem.c`、`rtmutex.c`、`qspinlock`（锁的架构无关实现） |
| [kernel/rcu/](linux-6.6.161/kernel/rcu/) | `tree.c`（RCU 核心状态机）、宽限期、回调处理 |
| [kernel/time/](linux-6.6.161/kernel/time/) | `timer.c`（定时器）、`hrtimer.c`（高精度定时器）、`timekeeping.c`（系统时间）、`tick-*.c`（时钟节拍）、`clocksource` |
| [kernel/printk/](linux-6.6.161/kernel/printk/) | `printk.c` 内核日志核心（console、环形缓冲区、日志级别） |
| [kernel/module/](linux-6.6.161/kernel/module/) | `main.c`（`insmod` 的核心：加载 ELF、重定位、符号解析）、`kmod.c`（用户态辅助程序） |
| [kernel/bpf/](linux-6.6.161/kernel/bpf/) | eBPF 虚拟机、验证器（verifier）、JIT、map、辅助函数 |
| [kernel/cgroup/](linux-6.6.161/kernel/cgroup/) | 控制组 v1/v2（CPU、内存、I/O 资源限制——容器技术的基石） |
| [kernel/trace/](linux-6.6.161/kernel/trace/) | ftrace 核心（函数跟踪、tracepoint、环形缓冲） |
| [kernel/events/](linux-6.6.161/kernel/events/) | perf_event 子系统（硬件性能计数器、软件事件） |
| [kernel/entry/](linux-6.6.161/kernel/entry/) | 系统调用/中断的公共进入退出路径（`common.c`），与 `arch/*/entry` 配合 |
| [kernel/futex.c](linux-6.6.161/kernel/futex.c) | futex 快速用户态锁（pthread 同步原语的内核支撑） |
| [kernel/fork.c](linux-6.6.161/kernel/fork.c) | 进程创建 `copy_process`（**必读文件**） |
| [kernel/exit.c](linux-6.6.161/kernel/exit.c) | 进程退出、僵尸进程 |
| [kernel/signal.c](linux-6.6.161/kernel/signal.c) | 信号处理 |
| [kernel/sys.c](linux-6.6.161/kernel/sys.c) | 大量杂项系统调用（`sys_getpid`、`sys_reboot` 等） |
| [kernel/pid.c](linux-6.6.161/kernel/pid.c) | PID 命名空间与 pid 分配 |
| [kernel/workqueue.c](linux-6.6.161/kernel/workqueue.c) | 工作队列（下半部机制之一，**必读**） |
| [kernel/softirq.c](linux-6.6.161/kernel/softirq.c) | 软中断（下半部机制之一） |
| [kernel/kthread.c](linux-6.6.161/kernel/kthread.c) | 内核线程基础设施 |

### 3.2 mm/ —— 内存管理

```
mm/
├── damon/   # DAMON 数据访问监测框架
├── kasan/   # KASAN 内存错误检测（调试用）
├── kfence/  # KFENCE 低开销越界检测
└── kmsan/   # KMSAN 未初始化内存检测
```

| 文件/目录 | 核心内容 |
|-----------|----------|
| [mm/page_alloc.c](linux-6.6.161/mm/page_alloc.c) | **伙伴系统**：物理页分配/释放（`alloc_pages`、水位检查、node/zone 管理） |
| [mm/slub.c](linux-6.6.161/mm/slub.c) | **SLUB 分配器**（`kmalloc`/`kmem_cache` 的实现，取代了旧的 SLAB） |
| [mm/vmalloc.c](linux-6.6.161/mm/vmalloc.c) | 非连续虚拟内存分配 |
| [mm/memory.c](linux-6.6.161/mm/memory.c) | **缺页异常处理** `handle_mm_fault`、COW（**必读**） |
| [mm/mmap.c](linux-6.6.161/mm/mmap.c) | `mmap`/`brk`/`munmap` 实现、VMA 管理 |
| [mm/filemap.c](linux-6.6.161/mm/filemap.c) | **页缓存 page cache**（**必读**） |
| [mm/shmem.c](linux-6.6.161/mm/shmem.c) | tmpfs 与共享内存的实现 |
| [mm/vmscan.c](linux-6.6.161/mm/vmscan.c) | 页回收（kswapd、LRU、水位触发） |
| [mm/swapfile.c](linux-6.6.161/mm/swapfile.c) | 交换分区 |
| [mm/compaction.c](linux-6.6.161/mm/compaction.c) | 内存碎片整理 |
| [mm/migrate.c](linux-6.6.161/mm/migrate.c) | 页迁移（NUMA 平衡） |
| [mm/hugetlb.c](linux-6.6.161/mm/hugetlb.c) | 大页内存 |
| [mm/memcontrol.c](linux-6.6.161/mm/memcontrol.c) | cgroup 内存控制器 |
| [mm/memblock.c](linux-6.6.161/mm/memblock.c) | 启动早期内存分配器（伙伴系统运行之前使用） |
| [mm/kmemleak.c](linux-6.6.161/mm/kmemleak.c) | 内核内存泄漏检测 |

### 3.3 fs/ —— 文件系统

| 类别 | 目录 | 说明 |
|------|------|------|
| **VFS 核心**（文件都在 [fs/](linux-6.6.161/fs/) 根目录） | `open.c` `read_write.c` `namei.c` `inode.c` `dentry.c` `super.c` `dcache.c` `file.c` | **最高优先级**：`open` 路径解析（namei）、读写、四大对象 |
| 伪文件系统 | [fs/proc/](linux-6.6.161/fs/proc/)、[fs/sysfs/](linux-6.6.161/fs/sysfs/)、[fs/debugfs/](linux-6.6.161/fs/debugfs/)、[fs/tracefs/](linux-6.6.161/fs/tracefs/)、[fs/kernfs/](linux-6.6.161/fs/kernfs/)、[fs/ramfs/](linux-6.6.161/fs/ramfs/)、[fs/hugetlbfs/](linux-6.6.161/fs/hugetlbfs/)、[fs/devpts/](linux-6.6.161/fs/devpts/) | 无磁盘的文件系统；kernfs 是 sysfs 等的公共基座 |
| 主流磁盘文件系统 | [fs/ext4/](linux-6.6.161/fs/ext4/)、[fs/xfs/](linux-6.6.161/fs/xfs/)、[fs/btrfs/](linux-6.6.161/fs/btrfs/)、[fs/f2fs/](linux-6.6.161/fs/f2fs/)、[fs/fat/](linux-6.6.161/fs/fat/)、[fs/exfat/](linux-6.6.161/fs/exfat/)、[fs/ntfs3/](linux-6.6.161/fs/ntfs3/)、[fs/udf/](linux-6.6.161/fs/udf/) | ext4 代码成熟、文档多，适合精读 |
| 网络/分布式文件系统 | [fs/nfs/](linux-6.6.161/fs/nfs/)、[fs/smb/](linux-6.6.161/fs/smb/)、[fs/ceph/](linux-6.6.161/fs/ceph/)、[fs/gfs2/](linux-6.6.161/fs/gfs2/)、[fs/ocfs2/](linux-6.6.161/fs/ocfs2/)、[fs/9p/](linux-6.6.161/fs/9p/) | 客户端实现；`nfsd/` 是内核里的 NFS 服务器 |
| 用户态/堆叠式 | [fs/fuse/](linux-6.6.161/fs/fuse/)、[fs/overlayfs/](linux-6.6.161/fs/overlayfs/)、[fs/autofs/](linux-6.6.161/fs/autofs/)、[fs/fscache/](linux-6.6.161/fs/fscache/) | fuse 把文件系统搬到用户态；overlayfs 是容器镜像的基础 |
| 嵌入式/只读 | [fs/squashfs/](linux-6.6.161/fs/squashfs/)、[fs/erofs/](linux-6.6.161/fs/erofs/)、[fs/jffs2/](linux-6.6.161/fs/jffs2/)、[fs/ubifs/](linux-6.6.161/fs/ubifs/)、[fs/isofs/](linux-6.6.161/fs/isofs/) | 压缩只读/闪存文件系统 |
| 支撑组件 | [fs/jbd2/](linux-6.6.161/fs/jbd2/)、[fs/iomap/](linux-6.6.161/fs/iomap/)、[fs/crypto/](linux-6.6.161/fs/crypto/)、[fs/verity/](linux-6.6.161/fs/verity/)、[fs/notify/](linux-6.6.161/fs/notify/)、[fs/quota/](linux-6.6.161/fs/quota/)、[fs/lockd/](linux-6.6.161/fs/lockd/)、[fs/unicode/](linux-6.6.161/fs/unicode/) | jbd2 是 ext4 的日志层；notify 是 inotify/fanotify；quota 磁盘配额 |

### 3.4 net/ —— 网络协议栈

| 类别 | 目录 | 说明 |
|------|------|------|
| **核心框架** | [net/core/](linux-6.6.161/net/core/) | `skbuff.c`（sk_buff 报文结构）、`dev.c`（网络设备抽象）、`sock.c`、`datagram.c` —— **必读** |
| 套接字层 | [net/socket.c](linux-6.6.161/net/socket.c) | socket 系统调用入口（**必读**） |
| IP 协议 | [net/ipv4/](linux-6.6.161/net/ipv4/)、[net/ipv6/](linux-6.6.161/net/ipv6/) | TCP/UDP/IP 协议实现，`ipv4/tcp_input.c`（接收）、`tcp_output.c`（发送）、`tcp_cong.c`（拥塞控制） |
| 本地套接字 | [net/unix/](linux-6.6.161/net/unix/) | AF_UNIX（本机进程间通信，实现简单，**建议第一个精读的协议族**） |
| 过滤与流量控制 | [net/netfilter/](linux-6.6.161/net/netfilter/)、[net/sched/](linux-6.6.161/net/sched/)、[net/bpfilter/](linux-6.6.161/net/bpfilter/) | iptables/nftables 的内核实现；tc 流量控制（QoS） |
| 链路层 | [net/bridge/](linux-6.6.161/net/bridge/)、[net/8021q/](linux-6.6.161/net/8021q/)、[net/dsa/](linux-6.6.161/net/dsa/)、[net/switchdev/](linux-6.6.161/net/switchdev/) | 网桥、VLAN、交换机芯片框架 |
| 无线 | [net/wireless/](linux-6.6.161/net/wireless/)、[net/mac80211/](linux-6.6.161/net/mac80211/)、[net/rfkill/](linux-6.6.161/net/rfkill/) | Wi-Fi 协议栈（cfg80211 + mac80211） |
| 高性能数据面 | [net/xdp/](linux-6.6.161/net/xdp/)、[net/bpf/](linux-6.6.161/net/bpf/) | XDP/eBPF 数据面加速（现代内核热点） |
| 新兴协议 | [net/mptcp/](linux-6.6.161/net/mptcp/)、[net/tls/](linux-6.6.161/net/tls/)、[net/handshake/](linux-6.6.161/net/handshake/) | 多路径 TCP、内核 TLS |
| 用户态接口 | [net/netlink/](linux-6.6.161/net/netlink/)、[net/ethtool/](linux-6.6.161/net/ethtool/)、[net/devlink/](linux-6.6.161/net/devlink/) | 内核与用户态配置通道（ip 命令就是走 netlink） |
| 其他协议 | [net/bluetooth/](linux-6.6.161/net/bluetooth/)、[net/can/](linux-6.6.161/net/can/)、[net/sctp/](linux-6.6.161/net/sctp/)、[net/tipc/](linux-6.6.161/net/tipc/)、[net/xfrm/](linux-6.6.161/net/xfrm/)、[net/openvswitch/](linux-6.6.161/net/openvswitch/)、[net/sunrpc/](linux-6.6.161/net/sunrpc/) | 蓝牙、车载 CAN 总线、SCTP、IPsec、OVS、RPC |

### 3.5 block/、ipc/、init/、io_uring/

| 目录 | 说明 |
|------|------|
| [block/](linux-6.6.161/block/) | 块设备 I/O 层：`blk-mq.c`（多队列框架）、`bio.c`（I/O 请求描述）、`genhd.c`（磁盘分区）、I/O 调度器（mq-deadline、kyber、bfq）；[block/partitions/](linux-6.6.161/block/partitions/) 分区表解析（MBR/GPT） |
| [ipc/](linux-6.6.161/ipc/) | System V 进程间通信：`msg.c` 消息队列、`sem.c` 信号量、`shm.c` 共享内存（POSIX IPC 基于文件系统实现，不在这里） |
| [init/](linux-6.6.161/init/) | **内核启动**：`main.c` 的 `start_kernel()`、`version.c`、`initramfs.c`（**必读，很小**） |
| [io_uring/](linux-6.6.161/io_uring/) | io_uring 高性能异步 I/O 框架（用户态/内核态共享环形队列，绕过传统系统调用路径） |

### 3.6 include/ —— 头文件字典

| 目录 | 说明 |
|------|------|
| [include/linux/](linux-6.6.161/include/linux/) | **内核核心头文件**：`sched.h`（task_struct）、`fs.h`（VFS 四大对象）、`mm_types.h`、`list.h`（链表）、`rbtree.h`、`spinlock.h`... 读源码的**第一入口** |
| [include/uapi/](linux-6.6.161/include/uapi/) | 用户态 API 头文件（系统调用号、结构体定义），`make headers_install` 后安装到 `/usr/include`，是用户态与内核态的**接口契约** |
| [include/asm-generic/](linux-6.6.161/include/asm-generic/) | 架构无关的 asm 通用实现（各架构的 `asm/` 缺省时回退到这里） |
| [include/net/](linux-6.6.161/include/net/) | 网络子系统内部头文件（sock、sk_buff 等，不对用户态公开） |
| [include/trace/](linux-6.6.161/include/trace/) | tracepoint 事件定义（`TRACE_EVENT` 宏展开） |
| [include/vdso/](linux-6.6.161/include/vdso/) | vDSO 虚拟动态共享库（`gettimeofday` 免系统调用） |
| 其他 | [include/kvm/](linux-6.6.161/include/kvm/)、[include/drm/](linux-6.6.161/include/drm/)、[include/sound/](linux-6.6.161/include/sound/)、[include/media/](linux-6.6.161/include/media/)、[include/scsi/](linux-6.6.161/include/scsi/)、[include/rdma/](linux-6.6.161/include/rdma/) | 各子系统内部头文件 |

> **重要**：每个架构还有自己的头文件树，如 [arch/x86/include/](linux-6.6.161/arch/x86/include/)（内含 `asm/`）。编译时 `include/asm` 会符号链接到当前架构的 asm 目录。

---

## 4. arch/ —— 架构相关代码

### 4.1 arch/x86/ 详解（PC 学习者必看）

```
arch/x86/
├── boot/          # 启动第一段代码
├── kernel/        # x86 核心：head_64.S、中断、APIC、信号
├── mm/            # x86 内存：页表、fault.c
├── entry/         # 系统调用入口汇编
├── kvm/           # KVM 虚拟化 x86 部分
├── include/       # x86 头文件（asm/）
├── crypto/        # x86 加密指令优化（AES-NI 等汇编）
├── events/        # perf 硬件事件（Intel/AMD PMU）
├── pci/           # x86 PCI 总线
├── platform/      # x86 平台驱动（各笔记本厂商）
├── power/         # 电源管理
├── hyperv/ xen/   # 虚拟机监控程序支持
├── purgatory/     # kexec 内核热切换
├── realmode/      # 实模式代码
└── coco/          # 机密计算（TDX/SEV）
```

| 目录 | 说明 |
|------|------|
| [arch/x86/boot/](linux-6.6.161/arch/x86/boot/) | **开机第一段代码**：实模式 → 保护模式（`header.S`、`main.c`）；[boot/compressed/](linux-6.6.161/arch/x86/boot/compressed/) 内核自解压 |
| [arch/x86/kernel/](linux-6.6.161/arch/x86/kernel/) | `head_64.S`（内核入口汇编）、`traps.c`（异常）、`irq.c`（中断）、`apic/`（中断控制器）、`process_64.S`（上下文切换汇编）、`signal.c`、`ptrace.c`、`setup.c` |
| [arch/x86/mm/](linux-6.6.161/arch/x86/mm/) | 页表建立 `init_64.c`、缺页异常 x86 部分 `fault.c`、PAT/TLB 管理 |
| [arch/x86/entry/](linux-6.6.161/arch/x86/entry/) | **系统调用入口**：`entry_64.S`（`entry_SYSCALL_64`）、`syscall_64.tbl`（系统调用表）、`common.c` |
| [arch/x86/kvm/](linux-6.6.161/arch/x86/kvm/) | KVM 的 x86 实现（VMX/SVM 指令虚拟化） |

### 4.2 其他架构（了解即可）

`alpha`、`arc`、`arm`、`arm64`、`csky`、`hexagon`、`ia64`、`loongarch`（龙芯）、`m68k`、`microblaze`、`mips`、`nios2`、`openrisc`、`parisc`、`powerpc`、`riscv`（RISC-V）、`s390`、`sh`、`sparc`、`um`（User-Mode Linux）、`xtensa`

> 每个架构内部结构类似 x86：`boot/`、`kernel/`、`mm/`、`include/`。学习时**只看一个架构**（x86 或 arm64），其余架构仅在需要时查阅。

---

## 5. drivers/ —— 设备驱动（按类别分组）

驱动代码占内核总量约 60%，**不要逐个读**。学习重点是通用框架（设备模型、字符设备、总线），然后挑一两个简单驱动精读。

| 类别 | 代表目录 | 说明 |
|------|----------|------|
| **驱动模型核心** | [drivers/base/](linux-6.6.161/drivers/base/) | **必读**：`kobject`/`kset`、`device`/`driver`/`bus`、`platform` 设备模型、`devres` 资源管理 |
| 存储 | [drivers/block/](linux-6.6.161/drivers/block/)（loop 回环设备、zram）、[drivers/nvme/](linux-6.6.161/drivers/nvme/)、[drivers/ata/](linux-6.6.161/drivers/ata/)（SATA）、[drivers/scsi/](linux-6.6.161/drivers/scsi/)、[drivers/md/](linux-6.6.161/drivers/md/)（软 RAID/device-mapper）、[drivers/mtd/](linux-6.6.161/drivers/mtd/)、[drivers/mmc/](linux-6.6.161/drivers/mmc/)、[drivers/nvdimm/](linux-6.6.161/drivers/nvdimm/) | 块设备驱动与闪存 |
| 网络设备 | [drivers/net/](linux-6.6.161/drivers/net/)（ethernet 各厂商网卡、phy 物理层）、[drivers/infiniband/](linux-6.6.161/drivers/infiniband/) | 网卡驱动（**建议精读 virtio_net**，简单且能配合 QEMU 跑） |
| 显示与 GPU | [drivers/gpu/](linux-6.6.161/drivers/gpu/)（DRM：i915、amdgpu）、[drivers/video/](linux-6.6.161/drivers/video/)（fbdev 帧缓冲）、[drivers/accel/](linux-6.6.161/drivers/accel/) | 图形栈（复杂度极高，了解即可） |
| 输入输出 | [drivers/input/](linux-6.6.161/drivers/input/)（键盘鼠标触摸屏）、[drivers/hid/](linux-6.6.161/drivers/hid/)（USB HID）、[drivers/tty/](linux-6.6.161/drivers/tty/)（串口终端）、[drivers/char/](linux-6.6.161/drivers/char/)（字符设备杂项——`mem.c` 是 /dev/null、/dev/zero 的实现，**短小精悍适合入门**） | 输入子系统适合学习驱动框架 |
| 总线与 SoC 外设 | [drivers/pci/](linux-6.6.161/drivers/pci/)、[drivers/platform/](linux-6.6.161/drivers/platform/)、[drivers/pinctrl/](linux-6.6.161/drivers/pinctrl/)、[drivers/gpio/](linux-6.6.161/drivers/gpio/)、[drivers/clk/](linux-6.6.161/drivers/clk/)、[drivers/regulator/](linux-6.6.161/drivers/regulator/)、[drivers/i2c/](linux-6.6.161/drivers/i2c/)、[drivers/spi/](linux-6.6.161/drivers/spi/)、[drivers/irqchip/](linux-6.6.161/drivers/irqchip/)、[drivers/dma/](linux-6.6.161/drivers/dma/)、[drivers/iommu/](linux-6.6.161/drivers/iommu/)、[drivers/of/](linux-6.6.161/drivers/of/)（设备树） | 嵌入式 SoC 开发必备 |
| USB 与高速接口 | [drivers/usb/](linux-6.6.161/drivers/usb/)、[drivers/thunderbolt/](linux-6.6.161/drivers/thunderbolt/)、[drivers/firewire/](linux-6.6.161/drivers/firewire/)、[drivers/pcmcia/](linux-6.6.161/drivers/pcmcia/) | USB 框架复杂但经典 |
| 电源与热管理 | [drivers/cpufreq/](linux-6.6.161/drivers/cpufreq/)、[drivers/cpuidle/](linux-6.6.161/drivers/cpuidle/)、[drivers/thermal/](linux-6.6.161/drivers/thermal/)、[drivers/hwmon/](linux-6.6.161/drivers/hwmon/)、[drivers/power/](linux-6.6.161/drivers/power/)、[drivers/powercap/](linux-6.6.161/drivers/powercap/) | CPU 变频、温控、传感器 |
| 虚拟化 | [drivers/virtio/](linux-6.6.161/drivers/virtio/)（**QEMU 实验必用**）、[drivers/vhost/](linux-6.6.161/drivers/vhost/)、[drivers/vdpa/](linux-6.6.161/drivers/vdpa/)、[drivers/vfio/](linux-6.6.161/drivers/vfio/)（设备直通）、[drivers/virt/](linux-6.6.161/drivers/virt/)、[drivers/xen/](linux-6.6.161/drivers/xen/)、[drivers/hv/](linux-6.6.161/drivers/hv/)（Hyper-V） | 与 [virt/](linux-6.6.161/virt/)（KVM 核心）配套 |
| 安全与加密硬件 | [drivers/crypto/](linux-6.6.161/drivers/crypto/)（硬件加密引擎）、[drivers/tee/](linux-6.6.161/drivers/tee/)（可信执行环境） | |
| 嵌入式外设 | [drivers/leds/](linux-6.6.161/drivers/leds/)、[drivers/pwm/](linux-6.6.161/drivers/pwm/)、[drivers/iio/](linux-6.6.161/drivers/iio/)（传感器）、[drivers/rtc/](linux-6.6.161/drivers/rtc/)、[drivers/watchdog/](linux-6.6.161/drivers/watchdog/)、[drivers/w1/](linux-6.6.161/drivers/w1/)（单总线）、[drivers/gnss/](linux-6.6.161/drivers/gnss/)（卫星导航）、[drivers/nvmem/](linux-6.6.161/drivers/nvmem/)、[drivers/comedi/](linux-6.6.161/drivers/comedi/)（数据采集） | 小驱动适合练手 |
| 平台基础设施 | [drivers/acpi/](linux-6.6.161/drivers/acpi/)、[drivers/firmware/](linux-6.6.161/drivers/firmware/)（EFI/UEFI）、[drivers/dma-buf/](linux-6.6.161/drivers/dma-buf/)（跨设备内存共享）、[drivers/edac/](linux-6.6.161/drivers/edac/)（内存纠错）、[drivers/cxl/](linux-6.6.161/drivers/cxl/)、[drivers/rapidio/](linux-6.6.161/drivers/rapidio/)、[drivers/uio/](linux-6.6.161/drivers/uio/)（用户态驱动）、[drivers/staging/](linux-6.6.161/drivers/staging/)（**待清理的实验代码，不保证质量**） | staging 里的代码是反例教材 |

---

## 6. 构建与开发支持

### 6.1 scripts/ —— 构建辅助

| 目录 | 说明 |
|------|------|
| [scripts/kconfig/](linux-6.6.161/scripts/kconfig/) | 配置系统：`make menuconfig` 的底层（解析 Kconfig、生成 `.config`、生成 `autoconf.h`） |
| [scripts/mod/](linux-6.6.161/scripts/mod/) | modpost：模块符号校验、版本控制（CRC） |
| [scripts/gdb/](linux-6.6.161/scripts/gdb/) | GDB 内核调试辅助脚本（`lx-*` 命令：`lx-ps`、`lx-dmesg` 等） |
| [scripts/dtc/](linux-6.6.161/scripts/dtc/) | 设备树编译器（dts → dtb） |
| [scripts/clang-tools/](linux-6.6.161/scripts/clang-tools/) | 生成 `compile_commands.json`（clangd 代码跳转用） |
| [scripts/coccinelle/](linux-6.6.161/scripts/coccinelle/) | 语义补丁（大规模代码重构规则） |
| [scripts/package/](linux-6.6.161/scripts/package/) | 打包 deb/rpm/tar |
| [scripts/gcc-plugins/](linux-6.6.161/scripts/gcc-plugins/) | GCC 插件（加固编译选项） |

### 6.2 tools/ —— 用户态工具

| 目录 | 说明 |
|------|------|
| [tools/perf/](linux-6.6.161/tools/perf/) | **perf 性能分析工具**源码（与内核 perf_event 子系统配套，内核开发者的必备工具） |
| [tools/bpf/](linux-6.6.161/tools/bpf/) | bpftool（eBPF 程序管理工具） |
| [tools/objtool/](linux-6.6.161/tools/objtool/) | 栈布局校验工具（x86 内核编译的必要环节） |
| [tools/testing/](linux-6.6.161/tools/testing/) | kselftests 内核自测试（大量现成测试用例，可当学习材料） |
| [tools/kvm/](linux-6.6.161/tools/kvm/)、[tools/cgroup/](linux-6.6.161/tools/cgroup/)、[tools/power/](linux-6.6.161/tools/power/)、[tools/gpio/](linux-6.6.161/tools/gpio/)、[tools/usb/](linux-6.6.161/tools/usb/)、[tools/thermal/](linux-6.6.161/tools/thermal/)、[tools/tracing/](linux-6.6.161/tools/tracing/) | 各子系统配套工具 |
| [tools/memory-model/](linux-6.6.161/tools/memory-model/) | Linux 内核内存模型（LKMM，理解内存屏障的进阶资料） |
| [tools/lib/](linux-6.6.161/tools/lib/)、[tools/include/](linux-6.6.161/tools/include/) | 工具共享的用户态库与内核头文件拷贝 |

### 6.3 其他支持目录

| 目录 | 说明 |
|------|------|
| [samples/](linux-6.6.161/samples/) | **各子系统示例代码**：kprobes、ftrace、kobject、bpf、rust、vfs... 写第一个内核模块前先看这里 |
| [usr/](linux-6.6.161/usr/) | initramfs 构建：`gen_init_cpio.c` 生成启动用的 cpio 归档 |
| [rust/](linux-6.6.161/rust/) | 内核 Rust 支持：`bindings/`（自动生成的 C 绑定）、`kernel/`（Rust 封装的内核 API crate）、`macros/`（过程宏） |
| [certs/](linux-6.6.161/certs/) | 内核模块签名证书（`CONFIG_MODULE_SIG`） |
| [security/](linux-6.6.161/security/) | 安全模块 LSM 框架：`selinux/`、`apparmor/`、`landlock/`、`tomoyo/`、`smack/`、`yama/`、`integrity/`（IMA）、`keys/`（密钥环）、`lockdown/` |
| [virt/](linux-6.6.161/virt/) | 虚拟化通用部分：`kvm/`（KVM 核心，与 `arch/*/kvm` 分工）、`lib/`（irqbypass） |
| [sound/](linux-6.6.161/sound/) | ALSA 音频：`core/`（pcm、control 核心）、`soc/`（ASoC 嵌入式音频）、`pci/`、`usb/` 等声卡驱动 |
| [crypto/](linux-6.6.161/crypto/) | 内核加密 API（`skcipher`、`hash`、`aead` 算法框架 + 各算法实现，软件与硬件驱动对接） |
| [lib/](linux-6.6.161/lib/) | 通用库：`list_sort.c`、`rbtree.c`、`bitmap.c`、`string.c`、`kfifo.c`、`kobject.c`（设备模型基座）、压缩算法（`zstd/`、`lz4/`、`xz/`）、`raid6/`、校验算法 |

### 6.4 Documentation/ —— 官方文档

| 目录 | 内容 |
|------|------|
| [Documentation/process/](linux-6.6.161/Documentation/process/) | 开发流程：如何提交补丁、编码风格（`coding-style.rst`）、稳定内核规则 |
| [Documentation/core-api/](linux-6.6.161/Documentation/core-api/) | 内核核心 API 手册（链表、内存分配、中断...） |
| [Documentation/admin-guide/](linux-6.6.161/Documentation/admin-guide/) | 系统管理员指南（内核参数、sysfs 接口说明） |
| [Documentation/driver-api/](linux-6.6.161/Documentation/driver-api/) | 驱动开发 API |
| [Documentation/filesystems/](linux-6.6.161/Documentation/filesystems/)、[Documentation/networking/](linux-6.6.161/Documentation/networking/)、[Documentation/scheduler/](linux-6.6.161/Documentation/scheduler/)、[Documentation/mm/](linux-6.6.161/Documentation/mm/)、[Documentation/locking/](linux-6.6.161/Documentation/locking/)、[Documentation/RCU/](linux-6.6.161/Documentation/RCU/)、[Documentation/bpf/](linux-6.6.161/Documentation/bpf/)、[Documentation/kbuild/](linux-6.6.161/Documentation/kbuild/)、[Documentation/dev-tools/](linux-6.6.161/Documentation/dev-tools/) | 各子系统权威文档 |
| [Documentation/translations/zh_CN/](linux-6.6.161/Documentation/translations/zh_CN/) | **中文翻译**（虽然不全，但质量好） |
| [LICENSES/](linux-6.6.161/LICENSES/) | SPDX 许可证文本：`preferred/`（GPL-2.0 等）、`dual/`、`exceptions/` |

---

## 7. 顶层文件说明

| 文件 | 说明 |
|------|------|
| [Makefile](linux-6.6.161/Makefile) | **顶层构建入口**：定义版本号（`VERSION=6 PATCHLEVEL=6 SUBLEVEL=161`）、架构变量（ARCH）、遍历各子目录编译 |
| [Kconfig](linux-6.6.161/Kconfig) | 顶层配置入口：`source` 聚合所有子目录的 Kconfig，形成配置菜单树 |
| [Kbuild](linux-6.6.161/Kbuild) | 顶层 Kbuild 文件：定义 `head-y`（最先链接的目标文件）等 |
| [MAINTAINERS](linux-6.6.161/MAINTAINERS) | **子系统维护者名录**：每个文件属于哪个子系统、谁维护、邮件列表是什么 |
| [README](linux-6.6.161/README) | 内核简介与构建入门 |
| [CREDITS](linux-6.6.161/CREDITS) | 贡献者名单（历史情怀向） |
| [COPYING](linux-6.6.161/COPYING) | GPL v2 许可证全文 |
| [tags](linux-6.6.161/tags) | ctags 符号索引（`make tags` 生成，vim/emacs 跳转用；用 clangd 可忽略） |
| [.clang-format](linux-6.6.161/.clang-format) | 代码格式化规则 |
| [.mailmap](linux-6.6.161/.mailmap) | 邮件地址映射（同一作者多个邮箱归一） |
| [.get_maintainer.ignore](linux-6.6.161/.get_maintainer.ignore) | `get_maintainer.pl` 脚本忽略名单 |
| [.cocciconfig](linux-6.6.161/.cocciconfig) | coccinelle 语义补丁工具配置 |
| [.rustfmt.toml](linux-6.6.161/.rustfmt.toml) | Rust 代码格式化配置 |

---

## 8. 学习优先级路线图

```
第一梯队（核心机制，精读）
  include/linux  →  init/  →  kernel/  →  mm/  →  fs/(核心+VFS)  →  block/
  →  arch/x86/(boot, entry, kernel, mm)  →  net/(core, ipv4, unix)

第二梯队（框架理解，重点文件精读）
  drivers/base/（设备模型）  →  drivers/char/mem.c  →  drivers/virtio/
  →  ipc/  →  lib/  →  security/

第三梯队（按需查阅）
  sound/  →  drivers/ 其余  →  crypto/  →  virt/kvm/

第四梯队（工具与方法）
  Documentation/  →  scripts/kconfig  →  tools/perf  →  samples/  →  rust/
```

**学习顺序建议**（与 [Linux内核学习路线.md](Linux内核学习路线.md) 对应）：

1. 先读 `init/main.c` 的 `start_kernel()` —— 它是整个内核的初始化"节目单"，能帮你把上述所有目录串起来
2. 每个子系统先读 `include/linux/` 里的数据结构头文件，再读实现
3. `drivers/` 只看框架，不逐文件读；`sound/` 除非做音频否则跳过
4. 遇到不懂的配置项，`grep` 对应 Kconfig 的帮助文本（`make menuconfig` 里也能看）
