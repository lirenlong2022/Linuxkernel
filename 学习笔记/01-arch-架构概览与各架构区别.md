# 第一节：arch —— Linux 支持哪些架构，区别在哪

> 源码版本：Linux 6.6.161
> 本节回答三个问题：内核支持哪些 CPU 架构？它们底层有什么区别？这些区别如何体现在源码里？

---

## 1. arch/ 目录里有什么

6.6 内核的 [arch/](../linux-6.6.161/arch/) 下共有 **22 个架构**（`Kconfig` 不是架构，是配置入口）：

```
alpha        arc          arm          arm64        csky
hexagon      ia64         loongarch    m68k         microblaze
mips         nios2        openrisc     parisc       powerpc
riscv        s390         sh           sparc        um
x86          xtensa
```

### 1.1 各架构一句话定位

| 架构            | 指令集风格       | 位宽  | 字节序                | 典型应用场景                                                          | 状态                     |
| --------------- | ---------------- | ----- | --------------------- | --------------------------------------------------------------------- | ------------------------ |
| **x86**   | CISC（变长指令） | 32/64 | 小端                  | **PC、笔记本、服务器**，绝对主流                                | 活跃，Intel/AMD/众多公司 |
| **arm64** | RISC（定长）     | 64    | 小端                  | **手机（垄断）、ARM 服务器、树莓派**，最热门的非 x86 架构       | 活跃，Arm 及众多公司     |
| **arm**   | RISC             | 32    | 小端（支持 BE8 大端） | 传统嵌入式、IoT（很多 MCU 跑 RTOS 而非 Linux）                        | 活跃但重心转向 arm64     |
| **riscv** | RISC（开源 ISA） | 32/64 | 小端为主              | 嵌入式、AI 加速器、教学科研，服务器起步                               | 活跃，社区高速成长       |
| powerpc         | RISC             | 32/64 | 双端（ppc64le 主流）  | IBM Power 服务器、部分网络/工业设备                                   | 维护中                   |
| s390            | CISC             | 64    | **大端**        | IBM 大型机（银行、证券核心系统）                                      | IBM 支持                 |
| mips            | RISC             | 32/64 | 双端                  | 路由器、机顶盒（OpenWrt 时代的主力），**衰落中**                | 维护中                   |
| loongarch       | RISC（国产自主） | 64    | 小端                  | 龙芯 CPU（信创/国产化）                                               | 活跃（龙芯主导）         |
| sparc           | RISC             | 32/64 | 大端                  | Sun 服务器遗产（Oracle 已停止开发），衰落                             | 维护中                   |
| parisc          | RISC             | 32/64 | 大端                  | HP PA-RISC 服务器遗产                                                 | 社区维护                 |
| ia64            | EPIC（VLIW 类）  | 64    | 小端                  | 英特尔安腾（Itanium），**商业失败，6.7 已移除**                 | Orphan（无维护者）       |
| alpha           | RISC             | 64    | 小端                  | DEC Alpha 遗产（64 位计算先驱）                                       | 社区维护                 |
| m68k            | CISC             | 32    | 大端                  | 摩托罗拉 68K 遗产；ColdFire 用于工业控制（支持无 MMU）                | 社区维护                 |
| sh              | RISC             | 32    | 双端                  | 工业控制、J-Core 开源 SoC                                             | 社区维护                 |
| csky            | RISC             | 32    | 小端                  | 国产 C-SKY（物联网芯片）                                              | 活跃                     |
| hexagon         | VLIW             | 32    | 小端                  | 高通 Hexagon DSP（数字信号处理器）                                    | 维护中                   |
| xtensa          | RISC（可配置）   | 32    | 可配置                | 定制 SoC（如 ESP32 的 LX 系列）                                       | 维护中                   |
| arc             | RISC（可配置）   | 32    | 小端                  | Synopsys 嵌入式 IP 核                                                 | 维护中                   |
| microblaze      | RISC（软核）     | 32    | 大端                  | Xilinx FPGA 软核 CPU                                                  | 维护中                   |
| nios2           | RISC（软核）     | 32    | 小端                  | Intel/Altera FPGA 软核 CPU                                            | 维护中                   |
| openrisc        | RISC（开源软核） | 32    | 大端                  | FPGA 开源软核                                                         | 社区维护                 |
| **um**    | （宿主机的）     | 32/64 | 随宿主                | **User-Mode Linux**：内核编译成用户态程序，教学/沙盒/开发调试用 | 维护中                   |

> 备注：`arm`/`riscv`/`mips` 同时支持 32/64 位两种内核（目录合一）；x86 从 2.6.24 起 32 位与 64 位合并为同一个 arch 目录。各架构维护状态以 [MAINTAINERS](../linux-6.6.161/MAINTAINERS) 为准（搜索 `S:` 字段：Supported / Maintained / Orphan）。

### 1.2 一句话总结

**x86 统治 PC 与服务器，arm64 统治移动端并进军服务器，riscv 是开源的未来之星，其余 19 个架构大多服务于特定硬件或作为历史遗产存在。**

---

## 2. 区分架构的六个维度

理解架构差异，先看六个"坐标系"：

### 2.1 CISC vs RISC

|              | CISC（x86、s390）                            | RISC（arm64、riscv、mips 等）                                 |
| ------------ | -------------------------------------------- | ------------------------------------------------------------- |
| 指令长度     | **变长**（1~15 字节，解码复杂）        | **定长**（arm64 4 字节，riscv 基础 4 字节/压缩 2 字节） |
| 访存方式     | 算术指令可直接操作内存（`add eax, [mem]`） | **Load/Store 架构**：必须先取到寄存器再运算             |
| 寄存器数量   | 少（x86-64 仅 16 个通用寄存器）              | 多（arm64/riscv 有 31 个通用寄存器）                          |
| 对内核的影响 | 解码器复杂、功耗高；内核要处理大量特殊指令   | 指令规整，内核的汇编代码更好读                                |

### 2.2 位宽：32 位 vs 64 位

- 64 位架构（x86_64、arm64、riscv64、s390x、ppc64）内核地址空间巨大（见第 5 节），**没有 32 位时代的 highmem 问题**
- 32 位架构（arm、m68k、sh、i386）内核只能映射 3G/1G 或 2G/2G 的用户/内核地址空间，需要 **highmem**（高端内存）机制来访问超过 1G 的物理内存——这是理解老式内存管理绕不开的概念

### 2.3 字节序（大小端）

- 小端主流：x86、arm64、riscv（默认）、alpha、ia64、loongarch、csky、hexagon、arc、nios2
- 大端阵营：s390、sparc、parisc、m68k、microblaze、openrisc
- 双端（内核可配置）：powerpc（ppc64le 主流）、mips（mipsel 主流）、sh、arm（BE8 模式）、xtensa
- 对内核的影响：网络字节序是大端，大端 CPU 处理报文头时省去转换；小端 CPU 要用 `ntohs/htonl` 宏（[include/linux/byteorder/](../linux-6.6.161/include/linux/byteorder/)）

### 2.4 有无 MMU（内存管理单元）

绝大多数 Linux 设备有 MMU（虚拟内存的前提）。但 **uClinux** 场景下，部分架构支持 `CONFIG_MMU=n` 编译出**无 MMU 内核**：

- 支持无 MMU 的架构：arm、m68k（ColdFire）、microblaze、riscv、sh、xtensa、csky
- 无 MMU 内核没有虚拟内存、没有进程隔离（所有进程共享地址空间）、`fork` 只能用 `vfork` 语义（mm/nommu.c 实现）

### 2.5 内存序：强内存序 vs 弱内存序

|              | 强内存序（x86 的 TSO）                                          | 弱内存序（arm64、powerpc、riscv）                                                                                                                                 |
| ------------ | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 特点         | 硬件保证绝大多数访存顺序                                        | 硬件允许更多乱序，编译器/CPU 都可能重排                                                                                                                           |
| 内核中的体现 | `arch/x86/include/asm/barrier.h` 里大多屏障近乎空操作         | `arch/arm64/include/asm/barrier.h` 大量使用 `dmb`/`ldar`/`stlr` 指令                                                                                      |
| 编程影响     | x86 上"碰巧能跑"的无锁代码，**移植到 arm64 上就会出 bug** | 内核用 `READ_ONCE/WRITE_ONCE`、`smp_mb()` 等抽象屏蔽差异（[Documentation/memory-barriers.txt](../linux-6.6.161/Documentation/memory-barriers.txt) 是必读文档） |

#### 2.5.1 为什么会乱序

乱序有两个来源，内存屏障要分别对付它们：

1. **编译器重排（编译期）**：编译器在"单线程语义不变"（as-if 规则）的前提下自由重排指令。它不知道变量被其他 CPU/设备并发访问，所以会把你的访问顺序改掉。
2. **CPU 硬件重排（运行期）**：现代 CPU 有**写缓冲（store buffer）**、乱序执行引擎；写操作进入写缓冲后按自己的节奏刷到缓存，不同地址的写可能以不同顺序被其他 CPU 观察到；缓存一致性协议的传播本身也有延迟。

典型场景：CPU0 依次写 `A=1; B=2`，CPU1 可能**先看到 B=2，后看到 A=1**——两件事看起来"因果颠倒"了。

> **内存屏障的本质**：在指令流上划一条线，告诉编译器/CPU"这条线两边的访存不允许跨线重排"。

#### 2.5.2 屏障的两个层次

| 层次 | 防谁 | 内核实现 |
|------|------|----------|
| **编译屏障** `barrier()` | 禁止**编译器**跨屏障重排 | 一条空 asm 语句 + `"memory"` clobber，零运行时开销 |
| **CPU 屏障** | 禁止 **CPU 硬件**跨屏障重排 | 各架构 `barrier.h` 里的 `mb/rmb/wmb` 等，生成真正的 fence 指令 |

一个 CPU 屏障同时蕴含编译屏障的作用（fence 指令本身是 volatile asm，带 memory clobber）。

#### 2.5.3 内核屏障 API 一览

| API | 语义 | 说明 |
|-----|------|------|
| `barrier()` | 编译屏障 | 防编译器重排，不生成指令 |
| `smp_rmb()` | 读-读屏障 | 屏障**前**的读先于屏障**后**的读完成 |
| `smp_wmb()` | 写-写屏障 | 屏障**前**的写先于屏障**后**的写被其他 CPU 看见 |
| `smp_mb()` | 全屏障 | 两侧的读写都不允许跨线 |
| `dma_rmb()/dma_wmb()/dma_mb()` | 与设备 DMA 相关的屏障 | 比 `smp_*` 更强（保证对**设备**的可见性，不只是 CPU 之间） |
| `smp_load_acquire()` | **单边**屏障：这次读之后的所有访存不许提前 | 读到某值后，之后的代码一定看到"发布者"之前写的所有数据 |
| `smp_store_release()` | **单边**屏障：这次写之前的所有访存不许落后 | 之前写的数据全部可见后，才发布这个"标志"写 |
| `READ_ONCE()/WRITE_ONCE()` | **单次访问的原子性** | 防编译器撕裂/合并访问、防"读两次"优化；定义在 [include/asm-generic/rwonce.h](../linux-6.6.161/include/asm-generic/rwonce.h) |

几个关键理解：

- **屏障必须成对使用**：写者一侧用 `smp_wmb()`，读者一侧用 `smp_rmb()`，单边屏障毫无意义。
- **`smp_*` 只在 SMP 下生效**，UP 系统退化为编译屏障；`dma_*` 还保证与设备的一致性，常用于驱动代码。
- **单边屏障比全屏障便宜**：arm64 上 `smp_load_acquire/smp_store_release` 用 `ldar/stlr` 指令，比 `dmb` 全屏障开销小得多。现代无锁代码（RCU、per-cpu、wake_up 机制）大量使用 acquire/release 语义。
- **锁本身自带屏障**：`spin_lock()` 隐含 acquire 语义、`spin_unlock()` 隐含 release 语义。**拿到锁的代码一定看到上个持锁者写的数据**——这正是锁能保护共享数据的原因，也是"优先用锁"的理由：你不用自己管屏障。
- **内核不用 `volatile` 做并发同步**：`volatile` 只防编译器优化不防 CPU 乱序，且不保证原子性。并发访问共享变量一律用 `READ_ONCE/WRITE_ONCE`。

#### 2.5.4 各架构的实现对比（源码验证）

| 架构 | `smp_wmb()` | `smp_mb()` | 实现说明 |
|------|-------------|-----------|----------|
| **x86-64** | **`barrier()`（纯编译屏障！）** | `lock; addl $0,-4(%rsp)` | TSO 内存序已保证"写写有序"，所以写屏障**零成本**；但 TSO 允许"读越过先前的写"，全屏障需要真指令——用带 `lock` 前缀的空操作（lock 前缀指令天然是全屏障，比 `mfence` 便宜） |
| **arm64** | `dmb(ishst)` | `dmb(ish)` | 弱内存序，所有屏障都是真指令；`ish` = inner shareable（CPU 之间的共享域），dma 屏障用 `osh`（outer shareable，含设备）；全屏障还有更重的 `dsb(sy)` |
| **riscv** | `fence w,w` | `fence rw,rw` | `fence` 指令显式指定排序方向（前序集合→后序集合） |
| **powerpc** | `lwsync`（轻） | `sync`（重） | 弱内存序，重轻两级屏障 |

> 源码对照：[arch/x86/include/asm/barrier.h](../linux-6.6.161/arch/x86/include/asm/barrier.h)（`__smp_wmb()` 就是 `barrier()`）；[arch/arm64/include/asm/barrier.h](../linux-6.6.161/arch/arm64/include/asm/barrier.h)（`__mb()=dsb(sy)`、`__smp_mb()=dmb(ish)`）。
>
> **一句话总结**：同样的 `smp_wmb()`，在 x86 上编译完"什么都没有"，在 arm64 上是一条 `dmb ishst` 指令——这就是"强/弱内存序"最直观的体现。

#### 2.5.5 经典示例：消息传递模式（message passing）

```c
/* CPU 0 —— 写者 */
data = 42;
smp_wmb();                    /* 保证 data 的写先于 flag 被其他 CPU 看见 */
WRITE_ONCE(flag, 1);

/* CPU 1 —— 读者 */
if (READ_ONCE(flag) == 1) {
        smp_rmb();            /* 保证读到 flag 后，data 读到的必是新值 */
        printk(KERN_INFO "%d\n", data);   /* 一定是 42 */
}
```

- 没有屏障时：CPU1 可能先观察到 `flag=1`（后执行的写先到），此时读 `data` 得到的还是旧值
- 屏障成对出现：写者保证"数据先于标志发布"，读者保证"看到标志后再读数据"
- 这就是内核中 `wake_up()/wait_event()`、`smp_store_release/smp_load_acquire` 通信用例的共同原型

#### 2.5.6 使用原则（工程经验）

1. 并发访问的共享变量，**一律**用 `READ_ONCE/WRITE_ONCE` 读写
2. **优先用锁**（spinlock/mutex/RCU），锁自带的屏障语义覆盖了绝大多数场景；只有锁开销不可接受时才手写屏障
3. 手写屏障**必须成对**，并在注释里写清楚配对的另一侧在哪、保护什么数据
4. 拿不准就查 [Documentation/memory-barriers.txt](../linux-6.6.161/Documentation/memory-barriers.txt)（权威长文，可作工具书）
5. 用工具验证：**KCSAN**（[kernel/kcsan/](../linux-6.6.161/kernel/kcsan/)，内核数据竞争检测器）；**LKMM**（[tools/memory-model/](../linux-6.6.161/tools/memory-model/)，Linux 内核内存模型，可形式化验证屏障代码的正确性）
6. 在 x86 上测试通过 ≠ 在 arm64 上正确（x86 的强内存序会掩盖屏障缺失的 bug）

### 2.6 外围体系（中断控制器、定时器等）

x86 的 PC 平台是"全家桶"（APIC 中断控制器、TSC 时间戳计数器、HPET 定时器、PCI），而 ARM/RISC-V 是"乐高"（SoC 厂商自由搭配 IP），所以：

- 中断控制器：x86 用 **APIC/LAPIC**；arm64 用 **GIC**（ARM 通用中断控制器，drivers/irqchip/irq-gic*.c）；riscv 用 **PLIC** 或新一代 AIA
- 系统定时器：x86 用 TSC/HPET/APIC timer；arm64 用 **arch timer**（每核一个，通过 MMIO 访问）；riscv 用 **SBI timer**
- 设备枚举：x86 靠 ACPI/PCI 自动发现；嵌入式 arm/riscv 靠**设备树**（Device Tree）描述硬件

---

## 3. 底层区别：内核代码怎么体现

### 3.1 系统调用机制对比

|            | x86-64                                                                             | arm64                                                                      | riscv              |
| ---------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------ |
| 触发指令   | `syscall`（快速路径，也保留 `int 0x80` 兼容 32 位）                            | `svc #0`                                                                 | `ecall`          |
| 系统调用号 | 独立的表：[syscall_64.tbl](../linux-6.6.161/arch/x86/entry/syscalls/syscall_64.tbl) | 直接用**通用表** `include/uapi/asm-generic/unistd.h`               | 同左，也用通用表   |
| 内核入口   | `arch/x86/entry/entry_64.S` 的 `entry_SYSCALL_64`                              | [arch/arm64/kernel/syscall.c](../linux-6.6.161/arch/arm64/kernel/syscall.c) | arch/riscv/kernel/ |
| 差异原因   | x86 有 40 年历史包袱（i386 时代自定调用号）                                        | arm64 是全新设计，直接复用通用表，**新增系统调用无需改 arm64 代码**  | 同 arm64           |

> 这就是为什么你改 x86 内核加系统调用要动 `.tbl` 文件，而 arm64/riscv 只需要在 asm-generic 里加一行。

### 3.2 中断与异常机制

- **x86**：中断描述符表 **IDT**（[arch/x86/kernel/idt.c](../linux-6.6.161/arch/x86/kernel/idt.c)，256 个门描述符，前 32 个固定为异常），设备中断经 LAPIC → IOAPIC 路由
- **arm64**：**异常级别 EL0~EL3**（用户态 EL0、内核 EL1、hypervisor EL2），异常向量表在 entry.S；设备中断统一走 **GIC**
- **riscv**：异常委托机制（M/S/U 三级权限），中断控制器 PLIC/AIA

### 3.3 页表结构对比（关键！）

|                   | x86-64                                                        | arm64                                                                          | riscv                                                                            |
| ----------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| 页表级数          | **4 级**（默认）/ 5 级（LA57 选项，支持 57 位虚拟地址） | 由**页大小**决定：4K 页→4 级；16K 页→4 级；**64K 页→3 级**      | 3 种模式：**Sv39**（3 级）/ **Sv48**（4 级）/ **Sv57**（5 级） |
| 页大小            | 固定 4K（+2M/1G 大页）                                        | **编译期三选一**：4K / 16K / 64K                                         | 4K（+2M/1G 大页）                                                                |
| 页表基址寄存器    | CR3                                                           | TTBR0_EL1（用户页表）/ **TTBR1_EL1（内核页表）——用户和内核用两套页表** | satp                                                                             |
| TLB 标签          | **PCID**（进程上下文 ID）                               | **ASID**（地址空间 ID）                                                  | ASID                                                                             |
| accessed/dirty 位 | 硬件自动置位                                                  | ARMv8.0 硬件**不**自动置位，缺页路径软件模拟；ARMv8.1+ 可选硬件管理      | 软件管理                                                                         |
| 特点              | 页表项格式最复杂（NX、PAT 等）                                | 两级 TTBR 让内核态/用户态切换不用换页表                                        | 三种模式按需裁剪，嵌入式常用 Sv39                                                |

> 学习提示：对比 [arch/x86/include/asm/pgtable_types.h](../linux-6.6.161/arch/x86/include/asm/pgtable_types.h) 和 [arch/arm64/include/asm/pgtable.h](../linux-6.6.161/arch/arm64/include/asm/pgtable.h) 的 PTE 格式定义，是理解"架构差异如何内聚在头文件"的最好案例。

### 3.4 DMA 与缓存一致性

- **x86**：硬件保证缓存一致（cache-coherent），DMA 前后几乎不需要软件干预
- **arm/arm64 等**：DMA 区域可能不一致，内核需要**显式 cache 维护操作**（clean/invalidate），通过 `dma_map_ops` 抽象；物理内存不足 32 位寻址时用 **swiotlb** 反弹缓冲
- 统一 API：驱动只调 `dma_map_single/dma_unmap_single`（[include/linux/dma-mapping.h](../linux-6.6.161/include/linux/dma-mapping.h)），架构差异被隐藏

---

## 4. 启动流程区别

### 4.1 三种典型启动路径

**x86（最曲折）**：有 40 年历史包袱，要经过三代 CPU 模式

```
BIOS/UEFI → 实模式(16位, boot/ 目录的 header.S、main.c)
  → 保护模式(32位) → 长模式(64位)
  → 自解压(boot/compressed/) → start_kernel()
```

**arm64（最简洁）**：现代架构没有历史包袱

```
固件/bootloader（U-Boot 等）直接把 Image 加载进内存
  → 内核在 EL2/EL1 特权级启动（已是 64 位模式，无需模式切换）
  → 通过设备树（嵌入式）或 ACPI（服务器）获取硬件信息
  → start_kernel()
```

**riscv（最新潮）**：依赖 SBI 固件接口

```
固件（OpenSBI，运行在 M 态）→ 内核在 S 态启动
  → SBI 提供定时器、IPI、远程 fence 等"特权服务"（类似 BIOS 调用）
  → 设备树传递硬件信息 → start_kernel()
```

> **注意：U-Boot 不在内核源码树里！** U-Boot（Das U-Boot）、GRUB 是**独立的 bootloader 项目**（独立 git 仓库），BIOS/UEFI/OpenSBI 属于固件。本内核源码树里只有：
>
> - 内核**自己**的启动代码（`arch/*/boot/`：x86 的实模式代码、arm64 的 `head.S` 等）——即"拿到控制权之后"的部分
> - 与 bootloader 的**交接协议文档**（[Documentation/arch/arm64/booting.rst](../linux-6.6.161/Documentation/arch/arm64/booting.rst)、[Documentation/arch/x86/boot.rst](../linux-6.6.161/Documentation/arch/x86/boot.rst)）——规定 bootloader 交权时必须满足的条件（寄存器状态、内存布局、设备树指针放哪个寄存器等）
>
> 学习时**不需要单独编译 U-Boot**：QEMU 的 `-kernel` 参数自带简易 bootloader 功能，会直接按 boot protocol 把内核加载进内存并启动。

### 4.2 关键差异点

| 差异点         | x86                                                                                     | arm64                                                                                      | riscv                |
| -------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------- |
| 进入内核时状态 | 16 位实模式，**内核自己完成模式切换**                                             | 已是最终模式，固件完成一切                                                                 | 已是最终模式（S 态） |
| 硬件信息获取   | ACPI 表为主（UEFI 时代）                                                                | **设备树为主**（服务器也用 ACPI）                                                    | 设备树               |
| 引导协议       | 内核自己的 boot protocol（[boot.rst](../linux-6.6.161/Documentation/arch/x86/boot.rst)） | 严格的 booting 规范（[booting.rst](../linux-6.6.161/Documentation/arch/arm64/booting.rst)） | SBI 规范             |
| 内核镜像       | bzImage（含引导扇区）                                                                   | Image（裸 ELF，bootloader 直接加载）                                                       | Image（类似）        |
| 启动代码量     | 大（boot/ + compressed/ 几千行）                                                        | 小（head.S 几百行）                                                                        | 小                   |

### 4.3 汇聚点：start_kernel()

**无论哪个架构，最终都会进入 [init/main.c](../linux-6.6.161/init/main.c) 的 `start_kernel()`**。在此之前的启动代码（几百到几千行）是架构相关的，之后的初始化流程 90% 是架构无关的——这也是为什么学内核要先读 `start_kernel()`：它是所有架构的"合流点"。

---

## 5. 内存管理区别

### 5.1 内核虚拟地址空间布局（64 位架构对比）

|                                            | x86-64                                                     | arm64                                                         | riscv                                                             |
| ------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| 线性映射区（direct map，物理内存直接映射） | `0xffff888000000000`（L4）/ `0xff11000000000000`（L5） | 默认 48 位 VA 时 `0xffff000000000000`（随 VA_BITS 变）      | **动态计算** `kernel_map.page_offset`（随 Sv39/48/57 变） |
| 内核代码/模块区                            | `0xffffffff80000000` 起                                  | `0xffff8000...` 起（48 位 VA 时）                           | 线性映射区内                                                      |
| 特点                                       | 布局**编译期固定**，有 L4/L5 两套方案                | 布局随 `CONFIG_ARM64_VA_BITS`（48/52 位）**自动伸缩** | 布局最灵活，启动时按模式动态确定                                  |

> 以上常量可直接在源码验证：
>
> - x86：`arch/x86/include/asm/page_64_types.h` 的 `__PAGE_OFFSET_BASE_L4` / `__START_KERNEL_map`
> - arm64：`arch/arm64/include/asm/memory.h` 的 `PAGE_OFFSET`（由 `_PAGE_OFFSET(VA_BITS)` 宏算出）
> - riscv：`arch/riscv/include/asm/page.h` 的 `PAGE_OFFSET = kernel_map.page_offset`

### 5.2 32 位与 64 位的本质区别

- 32 位架构：内核只占 1G（或 2G）地址空间，物理内存 > 内核映射能力时出现 **highmem**——需要临时映射（kmap）才能访问，这是 32 位特有的复杂度
- 64 位架构：地址空间巨大（48 位 = 256TB），**物理内存全量直接映射**，没有 highmem

### 5.3 页表与 TLB 差异（回顾 3.3）

- arm64 的 TTBR0/TTBR1 双页表设计：用户态用 TTBR0、内核态用 TTBR1，**进程切换只换 TTBR0**，内核页表全局共享
- x86 单 CR3 页表：每个进程页表里都**复制一份内核映射**（内核区域在页表中固定不变）
- TLB 优化标签：x86 用 PCID、arm64 用 ASID，目的相同（切换进程时不用全刷 TLB）

### 5.4 其他

- 大页支持：x86 固定 2M/1G；arm64 因页大小可变（4K/16K/64K），大页组合更灵活
- KASLR（内核地址随机化）：x86_64、arm64 成熟支持；riscv 较晚加入
- 内存保护：arm64 有 BTI/PAC（指针认证、分支目标识别）等硬件安全特性，x86 有 CET

---

## 6. 应用场景区别（谁在用哪个架构）

| 场景              | 主力架构                                    | 说明                                                     |
| ----------------- | ------------------------------------------- | -------------------------------------------------------- |
| 桌面 / 笔记本     | **x86**（arm64 崛起中）               | Windows/macOS/Linux 桌面；苹果 M 系列（arm64）改变了格局 |
| 服务器 / 云       | **x86**，arm64 快速增长               | AWS Graviton、Ampere 等 arm64 服务器芯片主打性价比       |
| 移动设备          | **arm64（垄断）**                     | 几乎所有智能手机                                         |
| 嵌入式 / IoT      | arm（32 位）、riscv                         | riscv 因开源免授权费高速渗透                             |
| 路由器 / 网络设备 | mips（存量）、arm                           | OpenWrt 时代 mips 是王者，新设备转向 arm                 |
| 大型机 / 金融     | **s390**                              | IBM z 系列，银行核心系统                                 |
| 高性能计算        | x86、powerpc、arm64                         | 富岳超算（arm64）、Summit（powerpc）                     |
| 国产化            | **loongarch**、csky、x86/arm 国产授权 | 龙芯（loongarch）是自主指令集的代表                      |
| FPGA 软核         | microblaze、nios2、openrisc                 | 芯片设计验证、定制硬件                                   |
| DSP               | hexagon                                     | 高通芯片内的专用处理器                                   |
| 教学 / 沙盒       | **um**（User-Mode Linux）、riscv      | um 把内核当普通程序跑，调试零成本                        |

---

## 7. 架构在内核源码中的组织方式

### 7.1 每个 arch/xxx/ 的标准结构

```
arch/x86/
├── Kconfig          # 架构的配置选项（页表级数、CPU 类型等）
├── boot/            # 启动第一阶段代码
├── kernel/          # 架构核心：head.S、中断、信号、上下文切换
├── mm/              # 架构内存管理：页表建立、缺页异常的架构部分
├── entry/           # 系统调用/异常入口（部分架构）
├── include/         # 架构头文件（内有一级子目录 asm/）
├── lib/             # 架构优化的库函数（memcpy 汇编版等）
├── crypto/          # 架构优化的加密实现（AES-NI 等）
└── ...              # 各架构不尽相同（kvm/、platform/、power/ 等）
```

### 7.2 include/asm 的符号链接机制

编译时 `include/asm` 会**符号链接**到当前架构的 asm 目录（如 `arch/x86/include/asm`）。所以内核代码里写 `#include <asm/pgtable.h>` 时，x86 和 arm64 编译会包含**完全不同的文件**——这就是"架构无关代码"与"架构相关代码"的分界点。

### 7.3 交叉编译如何选择架构

```bash
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig   # 编译 arm64 内核
make ARCH=x86 defconfig                                       # 本机 x86 无需 CROSS_COMPILE
```

`ARCH=` 决定用哪个 `arch/xxx/` 目录（注意：32 位 x86 也是 `ARCH=x86`，通过配置选 32/64）。

### 7.4 架构代码占比

内核 3000 万+ 行代码中，架构相关代码约占 **10% 左右**（其余在 drivers/、fs/、net/、mm/ 等架构无关部分）。这意味着：**学好一个架构的内核机制，90% 的知识可以平移到其他架构。**

---

## 8. 小结与学习建议

### 8.1 本节要点回顾

1. **22 个架构**中，真正值得投入精力的只有 3 个：**x86**（PC/服务器）、**arm64**（移动/服务器）、**riscv**（开源未来）
2. 架构差异集中在六个维度：**指令集风格、位宽、字节序、有无 MMU、内存序、外围体系**
3. 内核层面差异体现在：**系统调用机制、中断机制、页表结构、DMA 一致性、启动流程**
4. 所有架构殊途同归于 **`start_kernel()`**，之后 90% 代码架构无关
5. 64 位 vs 32 位的最本质差异：**highmem 问题**（32 位内核映射能力不足）

### 8.2 学习建议

1. **只深入一个架构**：推荐 x86（资料最多、PC 上调试方便、QEMU 支持成熟）或 arm64（就业市场更热）。不要同时学两个。
2. **对照阅读法**：理解一个概念（如 `switch_mm` 切换页表）时，同时打开 x86 和 arm64 两个实现对比，架构差异一目了然。
3. **重点吃透页表**：第 3.3 节的页表对比是架构差异最浓缩的体现，也是内存管理学习（后续章节）的前置知识。
4. **知道去哪查**：[Documentation/arch/](../linux-6.6.161/Documentation/arch/) 下每个架构有独立的文档（booting.rst 等）；[MAINTAINERS](../linux-6.6.161/MAINTAINERS) 可查每个架构的维护状态。

### 8.3 延伸思考（给自己留的作业）

- [ ] x86 为什么保留了实模式启动路径，而 arm64 不需要？（提示：历史兼容）
- [ ] 弱内存序下，为什么 x86 上"跑得好好的"无锁代码在 arm64 上会出错？
- [ ] arm64 为什么要把用户态和内核态页表分开（TTBR0/TTBR1），x86 为什么不？
- [ ] 无 MMU 内核（uClinux）为什么 fork 只能退化为 vfork？

---

*笔记日期：2026-11-07　对应源码：linux-6.6.161*
