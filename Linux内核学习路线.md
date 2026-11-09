# Linux 内核源码学习路线与清单

> 源码版本：**Linux 6.6.161**（LTS 长期支持版）
> 学习方式：源码阅读为主，构建/调试/实验为辅，坚持"读—改—跑—验证"循环。

---

## 0. 前置知识自查（第 0 周）

在深入源码之前，确认以下基础是否扎实，缺什么补什么：

- [ ] C 语言：指针、结构体、函数指针、链表、宏、GCC 扩展（`__attribute__`、内联汇编）
- [ ] 数据结构：链表（内核用侵入式 `list_head`）、红黑树、哈希表、基数树
- [ ] 操作系统原理：进程/线程、虚拟内存、中断、文件系统、并发与死锁
- [ ] 计算机组成：CPU 寄存器、MMU、页表、TLB、CPU 特权级（Ring0/Ring3）、缓存
- [ ] x86 汇编基础：能读懂 AT&T 汇编（启动代码、上下文切换会用到）
- [ ] 基本工具：gcc / make / git / gdb

> 推荐补课：《深入理解计算机系统》(CSAPP) 第 1~9 章。

---

## 1. 环境搭建（第 1 周）

### 1.1 源码阅读环境

- [ ] 配置 VSCode + clangd（在源码根目录 `make defconfig` 后生成 `compile_commands.json`：
      `make LLVM=1 defconfig && make LLVM=1 compile_commands.json`，或者直接使用内核自带的 `scripts/clang-tools/gen_compile_commands.py`）
- [ ] 安装 ctags/cscope（或 universial-ctags）用于函数跳转
- [ ] 收藏在线交叉引用站：[Bootlin Elixir](https://elixir.bootlin.com/linux/v6.6.161/source)（按版本号浏览，与本地源码同步对照）

### 1.2 实验/调试环境（重要！只看不跑容易忘）

- [ ] 安装 QEMU（`qemu-system-x86_64`）
- [ ] 用 Buildroot 或 BusyBox 制作最小根文件系统（initramfs）
- [ ] 完成第一次"构建 → QEMU 启动 → 进入 shell"全流程
- [ ] 配置内核 + GDB 远程调试（`nokaslr` 启动参数、`-s -S` 断点调试）
- [ ] 熟悉 trace 工具三件套：`ftrace` / `perf` / `bpftrace`（验证理解的金钥匙）

```bash
# 最小可行调试流程示例（x86_64）
make defconfig                 # 生成默认配置
make -j$(nproc)                # 构建
qemu-system-x86_64 -kernel arch/x86/boot/bzImage \
    -initrd rootfs.cpio.gz -append "console=ttyS0 nokaslr" -nographic
```

---

## 2. 全局总览（第 1~2 周）

目标：建立内核地图，不求看懂细节，只求知道"什么在哪里"。

- [ ] 通读 [README](linux-6.6.161/README) 和 [Documentation](linux-6.6.161/Documentation)
- [ ] 理解顶层目录结构：`arch/`（CPU 相关）、`kernel/`（核心机制）、`mm/`（内存）、`fs/`（文件系统）、`drivers/`（驱动，占代码量 60%+）、`net/`（网络）、`include/`（头文件）、`init/`（启动）、`ipc/`（进程间通信）、`block/`（块层）、`lib/`（通用库）
- [ ] 看懂 [Makefile](linux-6.6.161/Makefile) 和 [Kconfig](linux-6.6.161/Kconfig) 工作机制：
      配置如何通过 Kconfig → `.config` → 编译选项，`obj-y / obj-m` 的含义
- [ ] 了解内核编码风格：[Documentation/process/coding-style.rst](linux-6.6.161/Documentation/process/coding-style.rst)
- [ ] 第一次动手：写一个最小内核模块（hello module），`insmod/rmmod` 跑通，理解模块加载机制

---

## 3. 主线一：启动流程（第 3~4 周）

目标：从按下电源键到第一个用户进程 `init`，打通"开机全景图"。

- [ ] x86 实模式 → 保护模式：[arch/x86/boot/](linux-6.6.161/arch/x86/boot/)（`header.S`、`main.c`）
- [ ] 解压与重定位：[arch/x86/boot/compressed/](linux-6.6.161/arch/x86/boot/compressed/)（`head_64.S`、`misc.c`）
- [ ] 内核入口：`arch/x86/kernel/head_64.S` → `x86_64_start_kernel()` → `start_kernel()`
- [ ] [init/main.c](linux-6.6.161/init/main.c) 的 `start_kernel()` 逐行精读：
      - [ ] `setup_arch()` —— 架构初始化
      - [ ] `mm_init()` —— 内存子系统初始化
      - [ ] `sched_init()` —— 调度器初始化
      - [ ] `rest_init()` → `kernel_init` → 挂载根文件系统 → 启动 `init` 进程
- [ ] 实验：在 `start_kernel()` 各关键点加 `printk` 重新编译，观察启动日志顺序
- [ ] 实验：GDB 断点跟踪 `start_kernel()` 的执行流

---

## 4. 主线二：进程管理与调度（第 5~8 周）

目标：理解进程的一生——创建、运行、调度、切换、消亡。

> 📌 详细分站路线见 **[Linux进程调度学习路线.md](Linux进程调度学习路线.md)**（九站式：task_struct → sched_class 框架 → schedule() 主路径 → 触发时机与抢占 → CFS → 实时调度 → 多核负载均衡 → 进程生命周期 → 综合验证）

- [ ] 核心数据结构：[include/linux/sched.h](linux-6.6.161/include/linux/sched.h) 的 `task_struct`（打印 `pahole` 结构体布局）
- [ ] 进程描述符与内核栈：`thread_info` 与 `task_struct` 的关系、`current` 宏的实现
- [ ] 进程生命周期：[kernel/fork.c](linux-6.6.161/kernel/fork.c) 的 `copy_process()`（`fork/vfork/clone` 三合一，按 `clone_flags` 分流）
- [ ] 进程终结：[kernel/exit.c](linux-6.6.161/kernel/exit.c)（`do_exit()`、僵尸进程与 `wait` 的配合）
- [ ] 调度器：
      - [ ] [kernel/sched/core.c](linux-6.6.161/kernel/sched/core.c) —— 调度入口 `schedule()`、上下文切换 `context_switch()`
      - [ ] [kernel/sched/fair.c](linux-6.6.161/kernel/sched/fair.c) —— CFS 调度类（红黑树、虚拟运行时间 vruntime、`pick_next_task`）
      - [ ] 实时调度类 RT、`sched_class` 抽象层
      - [ ] 调度域与负载均衡（`load_balance`）
- [ ] 上下文切换汇编：`arch/x86/kernel/process_64.S` 的 `__switch_to`
- [ ] 同步原语：[kernel/locking/](linux-6.6.161/kernel/locking/) —— `spinlock`、`mutex`、`rwsem`、`seqlock`、`RCU`
- [ ] 实验：写内核模块遍历 `task_struct` 双向链表，打印所有进程状态（对应 `ps` 命令的实现）
- [ ] 实验：`perf sched` 观察调度行为；用两个死循环进程验证 CFS 时间片分配

---

## 5. 主线三：内存管理（第 9~13 周）

目标：从物理内存探测到用户态 malloc，打通内存全景。这是内核最复杂的子系统，值得投入最多时间。

- [ ] 物理内存管理：
      - [ ] 内存模型：NUMA / UMA、node / zone / page 三级结构
      - [ ] [mm/bootmem.c](linux-6.6.161/mm/bootmem.c) 引导期分配器 → 伙伴系统 [mm/page_alloc.c](linux-6.6.161/mm/page_alloc.c)（`alloc_pages`、`__free_pages`）
      - [ ] 页分配流程：`get_free_pages` → `zone_watermark` 水位检查 → `rmqueue`
- [ ] slab 分配器：[mm/slub.c](linux-6.6.161/mm/slub.c)（`kmalloc`、`kmem_cache`，`/proc/slabinfo` 验证）
- [ ] 虚拟内存：
      - [ ] `struct mm_struct` / `vm_area_struct`（`/proc/PID/maps` 验证）
      - [ ] `mmap` / `brk` 的完整调用链：系统调用 → `do_mmap` → `get_unmapped_area` → 页表建立
      - [ ] x86 四级页表（PGD→P4D→PUD→PMD→PTE），`mm/gup.c` 页表遍历
- [ ] 缺页异常：[mm/memory.c](linux-6.6.161/mm/memory.c) 的 `do_page_fault()` / `handle_mm_fault()`：
      - [ ] 匿名页缺页（首次写触发零页映射 → 写时复制）
      - [ ] 文件映射缺页（page cache 读入）
      - [ ] 写时复制 COW（`do_wp_page`）
- [ ] 页回收与交换：[mm/vmscan.c](linux-6.6.161/mm/vmscan.c)（LRU 链表、`kswapd`、水位触发回收）
- [ ] 反向映射 rmap（页 → 所有映射它的页表项）
- [ ] 实验：`/proc/meminfo`、`/proc/buddyinfo`、`/proc/pagetypeinfo` 对照源码理解每个字段
- [ ] 实验：写内核模块调用 `alloc_pages` 观察伙伴系统分裂/合并；用 `ftrace` 追踪 `handle_mm_fault`

---

## 6. 主线四：中断、异常与系统调用（第 14~15 周）

目标：理解用户态到内核态的全部通道。

- [ ] 中断描述符表 IDT：[arch/x86/kernel/idt.c](linux-6.6.161/arch/x86/kernel/idt.c)（门描述符、中断向量表布局）
- [ ] 中断处理框架：
      - [ ] `request_irq` / `free_irq`、`irq_desc` 数据结构、中断线程化
      - [ ] 上半部与下半部：softirq、tasklet、workqueue（[kernel/softirq.c](linux-6.6.161/kernel/softirq.c)、[kernel/workqueue.c](linux-6.6.161/kernel/workqueue.c)）
- [ ] 系统调用全流程：
      - [ ] x86-64 快速系统调用 `syscall` 指令 → `entry_SYSCALL_64`（[arch/x86/entry/entry_64.S](linux-6.6.161/arch/x86/entry/entry_64.S)）
      - [ ] 系统调用表 [arch/x86/entry/syscalls/syscall_64.tbl](linux-6.6.161/arch/x86/entry/syscalls/syscall_64.tbl)
      - [ ] 追踪一个具体调用：`read()` → `SYSCALL_DEFINE3(read, ...)` → `ksys_read` → VFS
- [ ] 实验：GDB 在 `entry_SYSCALL_64` 下断点，观察用户态 `read()` 触发中断进入内核
- [ ] 实验：编写自己的系统调用（可选，涉及修改 syscall 表和重新编译）

---

## 7. 主线五：文件系统与块设备（第 16~19 周）

目标：从 VFS 抽象层到磁盘扇区，打通 I/O 全景。

- [ ] VFS 四大对象：`super_block`、`inode`、`dentry`、`file`（[include/linux/fs.h](linux-6.6.161/include/linux/fs.h)）
- [ ] 文件打开全流程：[fs/open.c](linux-6.6.161/fs/open.c) 的 `do_sys_open` → `path_lookup` 路径解析 → `dentry cache`（dcache）
- [ ] 文件读写：[fs/read_write.c](linux-6.6.161/fs/read_write.c) 的 `vfs_read/vfs_write` → `file->f_op`
- [ ] 页缓存 page cache：[mm/filemap.c](linux-6.6.161/mm/filemap.c)（`find_get_page`、脏页回写 `writeback`）
- [ ] 块设备层：
      - [ ] `bio` 结构、请求队列 `request_queue`（[block/blk-mq.c](linux-6.6.161/block/blk-mq.c) 多队列框架）
      - [ ] I/O 调度器：mq-deadline、kyber、bfq
- [ ] 具体文件系统二选一精读：
      - [ ] ext4（[fs/ext4/](linux-6.6.161/fs/ext4/)，成熟、文档多）
      - [ ] 或 btrfs（更现代但复杂）
- [ ] 实验：`strace cat file` 逐条对照内核调用链；用 `fio` + `blktrace` 观察 I/O 落盘路径
- [ ] 实验：注册一个简单的内存文件系统（参考 ramfs），实现 `open/read/write` 接口

---

## 8. 主线六：网络子系统（第 20~22 周）

- [ ] 网络协议栈分层：socket 层 → 传输层 → 网络层 → 邻居子系统 → 设备层
- [ ] socket 系统调用：[net/socket.c](linux-6.6.161/net/socket.c)（`socket()` → `sock` → 协议族分派）
- [ ] TCP 实现：[net/ipv4/tcp_input.c](linux-6.6.161/net/ipv4/tcp_input.c)（接收路径、拥塞控制 [net/ipv4/tcp_cong.c](linux-6.6.161/net/ipv4/tcp_cong.c)）、[net/ipv4/tcp_output.c](linux-6.6.161/net/ipv4/tcp_output.c)（发送路径）
- [ ] UDP 实现：[net/ipv4/udp.c](linux-6.6.161/net/ipv4/udp.c)（简单，建议作为第一个精读的协议）
- [ ] IP 层：[net/ipv4/ip_input.c](linux-6.6.161/net/ipv4/ip_input.c)、[net/ipv4/ip_output.c](linux-6.6.161/net/ipv4/ip_output.c)（路由查找）
- [ ] 网卡驱动与 NAPI：[drivers/net/](linux-6.6.161/drivers/net/) 中选一个简单网卡驱动（如 virtio_net）
- [ ] 实验：`tcpdump` 抓包 + `dropwatch`/`ftrace` 定位丢包点；写一个内核态 TCP 回显服务

---

## 9. 主线七：设备驱动（第 23~24 周）

驱动占内核代码量一半以上，但学习重点是"框架"而非具体硬件。

- [ ] 设备模型：`kobject` / `kset` / `device` / `driver` / `bus`（[drivers/base/](linux-6.6.161/drivers/base/)）
- [ ] 字符设备驱动：[fs/char_dev.c](linux-6.6.161/fs/char_dev.c)（`register_chrdev`、`file_operations`）
- [ ] `procfs` / `sysfs` 接口
- [ ] platform 总线与设备树（DT）
- [ ] 实验项目：写一个完整字符设备驱动（如虚拟内存设备 /dev/mychardev），支持 read/write/ioctl/mmap
- [ ] 阅读一个真实驱动：如 [drivers/char/mem.c](linux-6.6.161/drivers/char/mem.c)（/dev/null、/dev/zero 的实现，短小精悍）

---

## 10. 进阶专题（第 25 周起，按兴趣选择）

- [ ] RCU 机制深入（[Documentation/RCU/](linux-6.6.161/Documentation/RCU/)）
- [ ] io_uring（[io_uring/](linux-6.6.161/io_uring/)，6.x 热点）
- [ ] eBPF 与内核观测（[kernel/bpf/](linux-6.6.161/kernel/bpf/)，配合 bpftrace 实践）
- [ ] cgroup 与容器资源隔离（[kernel/cgroup/](linux-6.6.161/kernel/cgroup/)）
- [ ] 内核 Rust 支持（[rust/](linux-6.6.161/rust/)，6.6 已含初步支持，了解即可）
- [ ] 虚拟化：KVM（[virt/kvm/](linux-6.6.161/virt/kvm/)、[arch/x86/kvm/](linux-6.6.161/arch/x86/kvm/)）
- [ ] 内核调试与故障定位：kdump/crash、KASAN、lockdep、ftrace 函数图
- [ ] 安全机制：LSM、seccomp、namespaces
- [ ] 实时内核 PREEMPT_RT（6.6 已合入主线）

---

## 11. 综合实践项目（贯穿全程，强烈建议至少完成 3 个）

- [ ] 项目 1：hello 内核模块 + 模块参数 + procfs 接口
- [ ] 项目 2：遍历并打印所有进程的 PID/状态/父进程（模块版 `ps`）
- [ ] 项目 3：字符设备驱动（read/write/ioctl/mmap 全接口）
- [ ] 项目 4：hook 系统调用 `open`，记录文件访问日志（学习 ftrace/kprobe 的替代方案）
- [ ] 项目 5：基于 workqueue 的定时任务模块
- [ ] 项目 6：用 eBPF/bpftrace 追踪 `malloc/free` 或调度延迟
- [ ] 项目 7：自己 build 一个定制内核（裁剪不需要的功能），在 QEMU 中运行并调优

---

## 12. 推荐学习资料

### 书籍（按推荐顺序）

1. 《Linux 内核设计与实现》(Robert Love, 第 3 版) —— 入门首选，薄而精
2. 《深入理解 Linux 内核》(第 3 版) —— 经典，基于 2.6 但原理不过时
3. 《Professional Linux Kernel Architecture》(Wolfgang Mauerer) —— 大部头进阶
4. 《奔跑吧 Linux 内核》 —— 中文，配合实验场景
5. 《Understanding the Linux Kernel》 —— 与 2 类似，互补阅读

### 在线资源

- [Linux Kernel Documentation](https://www.kernel.org/doc/html/latest/) —— 内核自带文档（对应本地 [Documentation](linux-6.6.161/Documentation)）
- [Bootlin Elixir](https://elixir.bootlin.com/linux/v6.6.161/source) —— 代码交叉引用
- [Linux Weekly News (LWN)](https://lwn.net/Kernel/Index/) —— 内核最新动态与深度技术文章
- [kernelnewbies](https://kernelnewbies.org/) —— 初学者社区，内核版本变更摘要
- [x86 手册：Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html) —— 系统编程卷，中断/页表/特权级权威参考
- 内核邮件列表（LKML）—— 感受真实开发流程

### 视频课程

- Linux 内核源码剖析系列（B 站可搜，选讲 4.x/5.x/6.x 的较新课程）

---

## 13. 学习方法论（血泪经验）

1. **先主干后枝叶**：优先读 `include/linux/` 头文件理解数据结构，再看实现；数据结构是内核代码的骨架。
2. **自顶向下 + 自底向上结合**：读大函数先看注释和调用关系图（`make cscope` 生成索引），再从最底层的小函数逐层向上拼装理解。
3. **以问题驱动阅读**：不要顺序读代码。每阶段带一个问题（"malloc 是怎么拿到内存的？"、"read 一个文件发生了什么？"），沿调用链追踪答案。
4. **每看懂一块就做笔记**：画调用链图、数据结构关系图（推荐 draw.io / mermaid），笔记目录建议放在本仓库 `notes/` 下，按主线分文件。
5. **动手验证 > 死记硬背**：printk 打日志、ftrace 看调用栈、GDB 单步、bpftrace 统计，验证一次胜过读十遍。
6. **先 2.6/4.x 资料后 6.x 源码**：老书讲原理，新源码看实现。遇到对不上的地方（如 slab 由 SLAB 变 SLUB、调度器由 O(1) 变 CFS），先查 LWN 或内核提交记录了解演变原因。
7. **学会用 git 考古**：`git log -L` 追一个函数的修改历史，`git blame` 看代码为什么这么写，commit message 是最好的教材。
8. **不求甚解也要继续**：内核有 3000 万+ 行代码，没有人全懂。卡住超过 2~3 天就跳过，带着问题继续，回来看往往豁然开朗。
9. **节奏建议**：每周保证 10~15 小时，约半年走完主线，一年形成系统认知。不要中断超过两周，内核知识衰减很快。

---

## 14. 进度记录模板

每周学习结束，在 `notes/progress.md` 中记录：

```markdown
## 第 N 周（日期范围）
- 学习内容：（主线/章节）
- 读懂的关键点：
- 卡住的问题：
- 做的实验：
- 下周计划：
```

---

## 附：核心源文件速查表

| 子系统 | 核心文件 | 说明 |
|--------|----------|------|
| 启动 | [init/main.c](linux-6.6.161/init/main.c) | `start_kernel()` |
| 进程 | [include/linux/sched.h](linux-6.6.161/include/linux/sched.h) | `task_struct` |
| 进程创建 | [kernel/fork.c](linux-6.6.161/kernel/fork.c) | `copy_process` |
| 调度 | [kernel/sched/fair.c](linux-6.6.161/kernel/sched/fair.c) | CFS |
| 内存分配 | [mm/page_alloc.c](linux-6.6.161/mm/page_alloc.c) | 伙伴系统 |
| slab | [mm/slub.c](linux-6.6.161/mm/slub.c) | SLUB 分配器 |
| 缺页 | [mm/memory.c](linux-6.6.161/mm/memory.c) | `handle_mm_fault` |
| 中断 | [kernel/irq/](linux-6.6.161/kernel/irq/) | 中断框架 |
| 系统调用 | [arch/x86/entry/syscalls/syscall_64.tbl](linux-6.6.161/arch/x86/entry/syscalls/syscall_64.tbl) | 调用表 |
| 下半部 | [kernel/softirq.c](linux-6.6.161/kernel/softirq.c) | softirq |
| 同步 | [kernel/locking/](linux-6.6.161/kernel/locking/) | 各种锁 |
| VFS | [include/linux/fs.h](linux-6.6.161/include/linux/fs.h) | 四大对象 |
| 页缓存 | [mm/filemap.c](linux-6.6.161/mm/filemap.c) | page cache |
| 块层 | [block/blk-mq.c](linux-6.6.161/block/blk-mq.c) | 多队列 |
| 网络 | [net/socket.c](linux-6.6.161/net/socket.c) | socket 层 |
| 驱动模型 | [drivers/base/](linux-6.6.161/drivers/base/) | kobject 等 |

---

*开始日期：______　预计周期：6~12 个月　祝你内核之旅顺利！*
