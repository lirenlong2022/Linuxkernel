# -*- coding: utf-8 -*-
"""给 include/linux/mm_types.h 的 struct mm_struct 成员添加中文注释。
规则自检：每个正则必须恰好命中 1 次；插入后花括号数量不变。
"""
import io
import re
import sys

PATH = r"D:\Linux_kernel_learn\linux-6.6.161\include\linux\mm_types.h"

INTRO = [
 "/* ═ 学习导读 ═══════════════════════════════════",
 " * struct mm_struct —— 进程的\"内存描述符\"：管理整个用户虚拟地址空间。",
 " * 【与 task_struct 的关系】task_struct 描述任务(调度视角)，mm_struct",
 " *   描述地址空间(内存视角)，task_struct.mm 指向它。线程共享同一份",
 " *   (clone 带 CLONE_VM)；fork 则 copy_mm() 复制一份。内核线程没有 mm，",
 " *   靠 active_mm 借用别的进程的地址空间。",
 " * 【两大引用计数·易混淆点】mm_users = 用户侧引用数(mmget()/mmput() 维护)，",
 " *   归零说明地址空间没人用了；mm_count = 内核侧引用数(mmgrab()/mmdrop()",
 " *   维护)，mm_users 归零时也会释放一次 mm_count；只有 mm_count 归零",
 " *   才真正释放本结构体。",
 " * 【地址空间怎么管】VMA(一段段映射)存在 maple tree 里 —— 6.1 起用一棵",
 " *   mm_mt 替代旧版\"红黑树 mmap_rb + 链表 mmap\"双结构；mmap_lock 读写锁",
 " *   保护整棵 VMA 树，page_table_lock 自旋锁保护页表本体。",
 " * 【页表】pgd 是进程页表树的根，进程切换时 CR3 指向它(内核部分全局",
 " *   共享、用户部分进程私有)；pgtables_bytes 统计页表占用的内存。",
 " * 【布局随机化】几乎全部成员包在匿名 struct 里，结尾 __randomize_layout",
 " *   让编译器按随机种子重排字段顺序(randstruct 安全加固)。",
 " * ══════════════════════════════════════════════",
 " */",
]

# (name, kind, regex, flags, payload)
# kind: trail    -> 注释追加到匹配起始行行尾
#       trail_end-> 注释追加到匹配结束行行尾
#       banner   -> 单行横幅插入匹配起始行上方(缩进对齐)
#       intro    -> 多行块插入匹配行下方(缩进 = 锚点缩进 + 1 tab)
RULES = [
    # ── 导读 ──
    ("intro",  "intro", r"^struct mm_struct \{", re.M, INTRO),

    # ── ① 内核侧引用计数 mm_count ──
    ("B1", "banner", r"^\tstruct \{\s*$\n^\t\t/\*$\n^\t\t \* Fields which are often written", re.M,
     "/* ===== 【① 引用计数·内核侧】mm_count —— mm_struct 自身的引用计数（独占 cache line 的热数据） ===== */"),
    ("mmcount-sub", "trail", r"^\t\tstruct \{\s*$\n^\t\t\t/\*\*$\n^\t\t\t \* @mm_count:", re.M,
     "/* 高频写字段的 cache line 子结构：目前只装 mm_count 一个成员 */"),
    ("mm_count", "trail", r"atomic_t mm_count;", 0,
     "/* mm_struct 自身的内核引用计数：mmgrab()/mmdrop() 维护；归零才真正释放本结构体（用户侧计数见下面 mm_users） */"),
    ("cacheline-close", "trail", r"\} ____cacheline_aligned_in_smp;", 0,
     "/* 结束 mm_count 子结构；独占一条 cache line，避免与其他热字段伪共享 */"),

    # ── ③ 地址空间：VMA 树与 mmap 布局 ──
    ("B3", "banner", r"struct maple_tree mm_mt;", 0,
     "/* ===== 【③ 地址空间】VMA 树 + mmap 布局 —— 进程地址空间的组织核心 ===== */"),
    ("mm_mt", "trail", r"struct maple_tree mm_mt;", 0,
     "/* VMA 管理核心：一棵 maple tree 存进程全部 VMA（按地址有序）；6.1 起替代旧版\"红黑树 mmap_rb + 链表 mmap\"双结构；查找/增删都受 mmap_lock 保护 */"),
    ("get_unmapped_area", "trail", r"^\s*unsigned long pgoff, unsigned long flags\);", re.M,
     "/* 函数指针：为新映射找一段空闲虚拟地址（arch_get_unmapped_area_topdown() 等，见 mm/mmap.c）；mmap() 调用它选址 */"),
    ("mmap_base", "trail", r"unsigned long mmap_base;", 0,
     "/* mmap 区域起始基址：top-down 模式下从 task_size 附近向下分配，ASLR 随机化后写入 */"),
    ("mmap_legacy_base", "trail", r"unsigned long mmap_legacy_base;", 0,
     "/* bottom-up 分配模式（老程序/禁用 ASLR）的 mmap 基址 */"),
    ("mmap_compat_base", "trail", r"unsigned long mmap_compat_base;", 0,
     "/* 32 位兼容模式（IA32 模拟进程）的 mmap 基址 */"),
    ("mmap_compat_legacy_base", "trail", r"unsigned long mmap_compat_legacy_base;", 0,
     "/* 兼容模式的 bottom-up 基址 */"),

    # ── ④ 地址空间边界与页表根 ──
    ("B4", "banner", r"unsigned long task_size;", 0,
     "/* ===== 【④ 地址空间边界与页表根】task_size / pgd ===== */"),
    ("task_size", "trail", r"unsigned long task_size;", 0,
     "/* 用户地址空间总大小（如 47 位虚拟地址 = 128TB）；用户能用的最高虚拟地址 */"),
    ("pgd", "trail", r"pgd_t \* pgd;", 0,
     "/* 进程页表树根：PGD 顶级页目录。内核空间部分所有进程共享、用户空间部分进程私有；进程切换时写 CR3 指向它 */"),
    ("membarrier_state", "trail", r"atomic_t membarrier_state;", 0,
     "/* membarrier() 系统调用标志位；特意紧挨 pgd 共享 cache line——switch_mm() 时都会被触达 */"),

    # ── ② 用户侧引用计数 mm_users ──
    ("B2", "banner", r"^\t\t/\*\*\s*$\n^\t\t \* @mm_users: The number of users", re.M,
     "/* ===== 【② 引用计数·用户侧】mm_users —— 使用本地址空间的任务数 ===== */"),
    ("mm_users", "trail", r"atomic_t mm_users;", 0,
     "/* 用户侧引用计数：有多少任务（含临时持有者）在用本地址空间；mmget()/mmput() 维护。归零时也释放一次上面的 mm_count（即\"地址空间没人用了\"） */"),
    ("pcpu_cid", "trail", r"struct mm_cid __percpu \*pcpu_cid;", 0,
     "/* 每 CPU 的 mm context ID（CONFIG_SCHED_MM_CID）：记录每个 CPU 当前分配的 mm_cid（调度器识别各 CPU 上的 mm 使用情况） */"),
    ("mm_cid_next_scan", "trail", r"unsigned long mm_cid_next_scan;", 0,
     "/* 下次扫描/回收 mm_cid 的时间（jiffies） */"),

    # ── ⑤ 页表与地址空间锁 ──
    ("B5", "banner", r"atomic_long_t pgtables_bytes;", 0,
     "/* ===== 【⑤ 页表与地址空间锁】page_table_lock / mmap_lock —— 双锁分工 ===== */"),
    ("pgtables_bytes", "trail", r"atomic_long_t pgtables_bytes;", 0,
     "/* 本进程所有页表占用的内存字节数：页表页是内存大户，这里统计开销 */"),
    ("map_count", "trail", r"int map_count;", 0,
     "/* VMA 个数（/proc/PID/maps 的行数）；上限 sysctl_max_map_count（默认 65530）防恶意刷映射 */"),
    ("page_table_lock", "trail", r"spinlock_t page_table_lock;", 0,
     "/* 自旋锁：保护页表本体及部分计数；与下面 mmap_lock 分工——它管页表，mmap_lock 管地址空间树 */"),
    ("mmap_lock", "trail", r"struct rw_semaphore mmap_lock;", 0,
     "/* 地址空间大锁（rw_semaphore）：保护 VMA 树与布局。缺页路径拿读锁；mmap/munmap/mprotect/brk 拿写锁；有写者等待时新读者也会排队 */"),
    ("mmlist", "trail", r"struct list_head mmlist;", 0,
     "/* 全局链表节点：所有\"可能被换出\"的 mm 挂到 init_mm.mmlist 上（mmlist_lock 保护），页面回收(kswapd)遍历它找换出对象 */"),
    ("mm_lock_seq", "trail", r"int mm_lock_seq;", 0,
     "/* 每-VMA 锁（CONFIG_PER_VMA_LOCK）序列号：递增 = 释放所有 VMA 写锁；读它 ≈ 取得 VMA 读锁快照，缺页路径用它快速上锁 */"),
    ("futex_unique_id", "trail", r"atomic64_t futex_unique_id;", 0,
     "/* futex 唯一 ID 分配器（CONFIG_FUTEX）：给进程内 futex 生成递增标识 */"),

    # ── ⑥ 内存统计与水位 ──
    ("B6", "banner", r"unsigned long hiwater_rss;", 0,
     "/* ===== 【⑥ 内存统计与水位】RSS / VM 统计 —— /proc 展示的数据来源 ===== */"),
    ("hiwater_rss", "trail", r"unsigned long hiwater_rss;", 0,
     "/* RSS 历史峰值：VmHWM（/proc/PID/status），update_hiwater_rss() 维护 */"),
    ("hiwater_vm", "trail", r"unsigned long hiwater_vm;", 0,
     "/* 虚拟内存历史峰值：VmPeak */"),
    ("total_vm", "trail", r"unsigned long total_vm;", 0,
     "/* 已映射虚拟内存总页数：VmSize（所有 VMA 页数之和） */"),
    ("locked_vm", "trail", r"unsigned long locked_vm;", 0,
     "/* mlock 锁住的页数（不可换出），受 RLIMIT_MEMLOCK 限额 */"),
    ("pinned_vm", "trail", r"atomic64_t\s+pinned_vm;", 0,
     "/* 永久 pin 的页数（get_user_pages() 长期持有，RDMA/VFIO 等用），需 CAP_IPC_LOCK */"),
    ("data_vm", "trail", r"unsigned long data_vm;", 0,
     "/* 数据映射页数（可写、非共享、非栈）：VmData */"),
    ("exec_vm", "trail", r"unsigned long exec_vm;", 0,
     "/* 可执行映射页数（可执行、非写、非栈）：VmExe */"),
    ("stack_vm", "trail", r"unsigned long stack_vm;", 0,
     "/* 栈映射页数（VM_STACK）：VmStk */"),
    ("def_flags", "trail", r"unsigned long def_flags;", 0,
     "/* 新建 VMA 的默认 VM_* 标志（如 VM_NOHUGEPAGE）；mmap() 创建 VMA 时继承 */"),

    # ── ⑦ 进程映像布局 ──
    ("B7", "banner", r"seqcount_t write_protect_seq;", 0,
     "/* ===== 【⑦ 进程映像布局】代码/数据/堆/栈/参数 —— exec 时填充 ===== */"),
    ("write_protect_seq", "trail", r"seqcount_t write_protect_seq;", 0,
     "/* seqcount 写保护序号：fork() 复制页表等场景先给页加写保护（制造 COW）；配合 mmap_lock 保证写保护期间无并发修改 */"),
    ("arg_lock", "trail", r"spinlock_t arg_lock;", 0,
     "/* 自旋锁：保护下面 start/end 一串映像布局字段（exec 与读 /proc/PID/stat 并发时不撕裂） */"),
    ("start_code", "trail", r"unsigned long start_code, end_code, start_data, end_data;", 0,
     "/* 代码段（ELF .text）起止地址 */"),
    ("start_brk", "trail", r"unsigned long start_brk, brk, start_stack;", 0,
     "/* start_brk 堆起点 / brk 堆顶（brk() 移动） / start_stack 初始栈顶（参数压栈后） */"),
    ("arg_env", "trail", r"unsigned long arg_start, arg_end, env_start, env_end;", 0,
     "/* 命令行参数(argv)/环境变量(envp)在栈上的起止地址 */"),
    ("saved_auxv", "trail", r"unsigned long saved_auxv\[AT_VECTOR_SIZE\];", 0,
     "/* auxv 辅助向量快照：供 /proc/PID/auxv 读（AT_PHDR/AT_ENTRY 等） */"),
    ("rss_stat", "trail", r"struct percpu_counter rss_stat\[NR_MM_COUNTERS\];", 0,
     "/* 每 CPU RSS 计数器数组（MM_FILEPAGES/MM_ANONPAGES/MM_SHMEMPAGES/MM_SWAPENTS）：get_mm_counter() 汇总出 VmRSS（属 ⑥ 统计类） */"),
    ("binfmt", "trail", r"struct linux_binfmt \*binfmt;", 0,
     "/* 加载本进程的二进制格式处理器（ELF→elf_format，脚本→script_format）；exec 和 core dump 都走它 */"),

    # ── ⑧ 体系结构上下文与内核特性 ──
    ("B8", "banner", r"mm_context_t context;", 0,
     "/* ===== 【⑧ 体系结构上下文与内核特性】context / flags / AIO / memcg / exe ===== */"),
    ("context", "trail", r"mm_context_t context;", 0,
     "/* 体系结构私有内存上下文（x86 是 ldt/ctx_id 等，见 arch/x86/include/asm/mmu.h）；switch_mm() 切换它 */"),
    ("flags", "trail_end", r"mm_context_t context;\n\n\s*unsigned long flags;", 0,
     "/* mm 状态位 MMF_*（MMF_DUMPABLE、MMF_OOM_VICTIM 等，见 sched.h），必须用原子位操作访问 */"),
    ("ioctx_lock", "trail", r"spinlock_t\s+ioctx_lock;", 0,
     "/* 保护 ioctx_table 的自旋锁（AIO 上下文） */"),
    ("ioctx_table", "trail", r"struct kioctx_table __rcu\s+\*ioctx_table;", 0,
     "/* AIO 上下文表：进程所有异步 IO 上下文（io_context）的 RCU 哈希表 */"),
    ("owner", "trail", r"struct task_struct __rcu \*owner;", 0,
     "/* 该 mm 的\"规范属主\"任务：memcg 内存记账挂到它的 cgroup；改属主需满足 current==owner、新属主->mm==mm 等条件 */"),
    ("user_ns", "trail", r"struct user_namespace \*user_ns;", 0,
     "/* 拥有本 mm 的用户命名空间（权限检查与记账） */"),
    ("exe_file", "trail", r"struct file __rcu \*exe_file;", 0,
     "/* /proc/PID/exe 符号链接指向的可执行文件（持有引用防 inode 被删）；execve 时更新 */"),
    ("notifier_subscriptions", "trail", r"struct mmu_notifier_subscriptions \*notifier_subscriptions;", 0,
     "/* MMU notifier 订阅表：KVM/GPU 等外部组件注册回调，页表变化/页回收时被通知（同步 EPT 等） */"),
    ("pmd_huge_pte", "trail", r"pgtable_t pmd_huge_pte; /\* protected by page_table_lock \*/", 0,
     "/* THP 的 PMD 巨型页表项（不拆 PMD 锁的配置下） */"),

    # ── ⑨ 高级内存特性 ──
    ("B9", "banner", r"^\t\t/\*\s*$\n^\t\t \* numa_next_scan is the next time", re.M,
     "/* ===== 【⑨ 高级内存特性】NUMA 均衡 / TLB 冲刷 / uprobe / 大页 / KSM / 设备 ===== */"),
    ("numa_next_scan", "trail", r"unsigned long numa_next_scan;", 0,
     "/* NUMA 均衡：下次把 PTE 改 PROT_NONE 触发 hint fault 的时间（收集统计并迁移页） */"),
    ("numa_scan_offset", "trail", r"unsigned long numa_scan_offset;", 0,
     "/* 地址扫描游标：接着上次位置继续扫 */"),
    ("numa_scan_seq", "trail", r"int numa_scan_seq;", 0,
     "/* 防止两个线程同时做 PTE 重映射 */"),
    ("tlb_flush_pending", "trail", r"atomic_t tlb_flush_pending;", 0,
     "/* 有批量 TLB 冲刷正在进行：移动 PROT_NONE 页的路径必须冲刷 TLB；归零才可安全回收页表 */"),
    ("tlb_flush_batched", "trail", r"atomic_t tlb_flush_batched;", 0,
     "/* 有挂起的批量 unmap TLB 冲刷（flush_tlb_batched_pending()） */"),
    ("uprobes_state", "trail", r"struct uprobes_state uprobes_state;", 0,
     "/* 用户态探针（uprobe）状态：本进程插入的探针点信息 */"),
    ("delayed_drop", "trail", r"struct rcu_head delayed_drop;", 0,
     "/* PREEMPT_RT 专用：mmdrop 延迟到 RCU 回调执行（实时内核不能在原子上下文释放页表） */"),
    ("hugetlb_usage", "trail", r"atomic_long_t hugetlb_usage;", 0,
     "/* 本进程使用的大页（hugetlb）数量 */"),
    ("async_put_work", "trail", r"struct work_struct async_put_work;", 0,
     "/* workqueue 工作项：mmput 在原子上下文时把释放收尾推迟到这里异步执行 */"),
    ("pasid", "trail", r"u32 pasid;", 0,
     "/* 进程地址空间 ID（IOMMU SVA 共享虚拟地址）：设备用它做 DMA 地址翻译 */"),
    ("ksm_merging_pages", "trail", r"unsigned long ksm_merging_pages;", 0,
     "/* KSM 已合并的页数（不含零页） */"),
    ("ksm_rmap_items", "trail", r"unsigned long ksm_rmap_items;", 0,
     "/* KSM 检查过的反向映射项数（含未合并的） */"),
    ("ksm_zero_pages", "trail", r"atomic_long_t ksm_zero_pages;", 0,
     "/* 启用 use_zero_pages 时用内核零页合并的空页数 */"),

    # ── ⑩ 多代 LRU 与结尾 ──
    ("B10", "banner", r"^#ifdef CONFIG_LRU_GEN$\n^\t\tstruct \{\s*$\n^\t\t\t/\* this mm_struct is on lru_gen_mm_list", re.M,
     "/* ===== 【⑩ 多代 LRU 与结构结尾】lru_gen / __randomize_layout / cpu_bitmap ===== */"),
    ("lrugen-struct", "trail", r"^\t\tstruct \{\s*$\n^\t\t\t/\* this mm_struct is on lru_gen_mm_list \*/", re.M,
     "/* 多代 LRU（CONFIG_LRU_GEN）的 mm 级状态：按代管理页回收 */"),
    ("lrugen-list", "trail", r"^\t\t\tstruct list_head list;", re.M,
     "/* 挂到全局 lru_gen_mm_list 链表（页表遍历者遍历用） */"),
    ("lrugen-bitmap", "trail", r"^\t\t\tunsigned long bitmap;", re.M,
     "/* 位图提示：自上次逐节点页表遍历后本 mm 是否被使用过 */"),
    ("lrugen-memcg", "trail", r"^\t\t\tstruct mem_cgroup \*memcg;", re.M,
     "/* 指向上面 owner 所属的 memcg */"),
    ("lrugen-close", "trail", r"\} lru_gen;", 0,
     "/* 结束多代 LRU 子结构 */"),
    ("randomize-close", "trail", r"^\t\} __randomize_layout;", re.M,
     "/* 结束外层匿名 struct：randstruct 插件按随机种子重排内部成员布局（安全加固） */"),
    ("cpu_bitmap", "trail", r"unsigned long cpu_bitmap\[\];", 0,
     "/* 柔性数组 cpu_vm_mask：哪些 CPU 的 TLB 里缓存了本进程的映射（mm_cpumask() 访问）；必须放结构体末尾，按 nr_cpu_ids 动态定长 */"),
]


def main():
    with io.open(PATH, encoding="utf-8") as f:
        text = f.read()
    if "\r" in text:
        print("FAIL: CRLF line endings found, abort")
        return 1

    edits = []
    for name, kind, pat, flags, payload in RULES:
        ms = list(re.finditer(pat, text, flags))
        if len(ms) != 1:
            print("FAIL rule %-20s matches=%d" % (name, len(ms)))
            return 1
        m = ms[0]
        lineno = text.count("\n", 0, m.start()) + 1
        ls = text.rfind("\n", 0, m.start()) + 1
        le = text.find("\n", m.start())
        if le == -1:
            le = len(text)
        if kind == "trail":
            edits.append((ls, 0, "trail", payload, name))
        elif kind == "trail_end":
            edits.append((text.rfind("\n", 0, m.end() - 1) + 1, 0, "trail", payload, name))
        elif kind == "banner":
            edits.append((ls, 1, "banner", payload, name))
        elif kind == "intro":
            edits.append((le, 2, "intro", payload, name))
        print("OK  %-22s line %d" % (name, lineno))

    # 从文件底部向上应用，避免位置失效；同一位置先 trail 后 banner
    edits.sort(key=lambda e: (-e[0], e[1]))
    out = text
    for pos, _prio, kind, payload, name in edits:
        if kind == "trail":
            le2 = out.find("\n", pos)
            if le2 == -1:
                le2 = len(out)
            out = out[:le2] + "\t" + payload + out[le2:]
        elif kind == "banner":
            le2 = out.find("\n", pos)
            if le2 == -1:
                le2 = len(out)
            anchor = out[pos:le2]
            indent = re.match(r"\s*", anchor).group(0)
            out = out[:pos] + indent + payload + "\n" + out[pos:]
        elif kind == "intro":
            ls2 = out.rfind("\n", 0, pos) + 1
            anchor = out[ls2:pos]
            indent = re.match(r"\s*", anchor).group(0) + "\t"
            block = "".join(indent + l + "\n" for l in payload)
            out = out[:pos] + "\n" + block + out[pos:]

    if out.count("{") != text.count("{") or out.count("}") != text.count("}"):
        print("FAIL: brace balance changed")
        return 1

    with io.open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("DONE: %d rules applied, braces balanced" % len(RULES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
