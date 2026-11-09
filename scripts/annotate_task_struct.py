# -*- coding: utf-8 -*-
"""
给 include/linux/sched.h 中的 struct task_struct 成员添加中文学习注释。
- 原文件英文注释全部保留，只在成员行尾追加 / 行上方插入中文注释
- 只处理 task_struct 定义区域，文件其余部分不动
- 原文件备份: D:/Linux_kernel_learn/backup/sched.h.orig
"""
import re

PATH = r"d:/Linux_kernel_learn/linux-6.6.161/include/linux/sched.h"

# (正则, 注释文本, 模式)  模式: trail=行尾追加 / above=上方插块注释 / banner=上方插小节横幅
MEMBERS = [
    # ================= 结构体开头 =================
    (r"^struct task_struct \{", "进程描述符：一个 task_struct 描述一个任务(线程)。内核调度的基本单位是任务，不是进程。", "trail"),
    (r"^#ifdef CONFIG_THREAD_INFO_IN_TASK\s*$",
     "═ 学习导读 ═══════════════════════════════════\n"
     "· 每个 task_struct 对应一个「任务」= 用户态的一个线程；进程 = 线程组(thread group)。\n"
     "· 调度核心成员：__state(状态) / prio 系(优先级) / se、rt、dl(三类调度实体) / sched_class(调度类) / on_rq(是否在队列)。\n"
     "· 生命周期：usage 与 rcu_users 两个引用计数管理，最终经 RCU 延迟释放(见 rcu 成员)。\n"
     "· 内存布局：task_struct 紧贴内核栈顶，栈向低地址增长；thread 成员(架构状态)必须放最后。\n"
     "══════════════════════════════════════════════", "above_once"),

    # ================= ① 基础信息 =================
    (r"^\s*struct thread_info\s+thread_info;",
     "【① 每线程基础信息 · 不可随机化区】\n"
     "thread_info 已与 task_struct 合并(x86 标配)。它必须是第一个成员：current 宏靠「内核栈指针 & ~(THREAD_SIZE-1)」定位 task_struct 首地址，任何 current-> 访问都依赖此位置。", "above"),
    (r"^\s*unsigned int\s+__state;",
     "【进程状态位图】TASK_RUNNING(=0)/TASK_INTERRUPTIBLE/TASK_UNINTERRUPTIBLE/TASK_STOPPED/TASK_TRACED 等；\n"
     "多状态用 __TASK_* 位组合。只能通过 set_current_state() 写、READ_ONCE() 读，禁止直接赋值。", "above"),
    (r"^\s*unsigned int\s+saved_state;", "被「非自愿」状态改变(如 ptrace/信号踢醒睡眠任务)前暂存的旧状态", "trail"),
    (r"^\s*randomized_struct_fields_start", "可随机化区开始：以下字段会被结构体随机化(KASLR 加固)打乱顺序；上面的调度关键字段保持原位", "trail"),
    (r"^\s*void\s*\*\s*stack;",
     "【② 内核栈与引用计数】\n"
     "内核栈基址(THREAD_SIZE 对齐)。task_struct 紧贴栈顶存放，栈向低地址增长，栈底即 task_struct 起点(THREAD_INFO_IN_TASK 的前提)。", "above"),
    (r"^\s*refcount_t\s+usage;", "task_struct 引用计数：get_task_struct() 增 / put_task_struct() 减，归零才释放", "trail"),
    (r"^\s*unsigned int\s+flags;", "每任务标志 PF_*：PF_KTHREAD(内核线程) / PF_EXITING / PF_WQ_WORKER 等", "trail"),
    (r"^\s*unsigned int\s+ptrace;", "被 ptrace 跟踪状态：PT_PTRACED / PT_TRACESYSGOOD 等", "trail"),
    (r"^\s*int\s+on_cpu;", "正在哪个 CPU 上运行(-1 表示未运行)，SMP 调度核心状态", "trail"),
    (r"^\s*struct __call_single_node\s+wake_entry;", "唤醒链表节点：跨 CPU 唤醒时挂到目标 rq 的 wakelist", "trail"),
    (r"^\s*unsigned int\s+wakee_flips;", "「唤醒者-被唤醒者」关系翻转计数(唤醒亲和性启发式)", "trail"),
    (r"^\s*unsigned long\s+wakee_flip_decay_ts;", "翻转计数的衰减时间戳", "trail"),
    (r"^\s*struct task_struct\s*\*\s*last_wakee;", "最近一次唤醒本任务的任务(wake_affine 用)", "trail"),
    (r"^\s*int\s+recent_used_cpu;", "最近使用过的 CPU(唤醒时快速找空闲/热核)", "trail"),
    (r"^\s*int\s+wake_cpu;", "上次被唤醒时所在的 CPU", "trail"),

    # ================= ③ 调度核心 =================
    (r"^\s*int\s+on_rq;", "【③ 调度核心字段：优先级、调度实体、策略】", "是否在运行队列上(由调度器维护)", "btrail"),
    (r"^\s*int\s+prio;",
     "【优先级体系 0~139】RT 任务 0~99(数字越小优先级越高)；CFS 任务 100~139(nice -20~+19 映射)。\n"
     "prio 是动态/有效优先级：RT 任务可能因优先级继承(PI)被临时提升。三个字段关系：prio(有效) ← normal_prio(常规) ← static_prio(静态) / rt_priority(RT 专用)。", "above"),
    (r"^\s*int\s+static_prio;", "静态优先级 100~139(由 nice 换算，MAX_RT_PRIO+nice；RT 任务无效)", "trail"),
    (r"^\s*int\s+normal_prio;", "常规优先级：CFS=static_prio；RT=99-rt_priority", "trail"),
    (r"^\s*unsigned int\s+rt_priority;", "RT 优先级 0~99(仅 SCHED_FIFO/RR 有效)", "trail"),
    (r"^\s*struct sched_entity\s+se;", "CFS 调度实体(内含 vruntime、红黑树节点、PELT 负载跟踪)", "trail"),
    (r"^\s*struct sched_rt_entity\s+rt;", "RT 调度实体(优先级链表、时间片)", "trail"),
    (r"^\s*struct sched_dl_entity\s+dl;", "Deadline 调度实体(runtime/deadline/period，CBS 记账)", "trail"),
    (r"^\s*const struct sched_class\s*\*\s*sched_class;", "所属调度类指针(stop/dl/rt/fair/idle)——调度器多态的核心", "trail"),
    (r"^\s*struct rb_node\s+core_node;", "core scheduling 红黑树节点(SMT 同核互斥防护)", "trail"),
    (r"^\s*unsigned long\s+core_cookie;", "core 调度 cookie：同 cookie 的任务不会同时在 SMT 兄弟核上运行", "trail"),
    (r"^\s*unsigned int\s+core_occupation;", "core 调度占用状态", "trail"),
    (r"^\s*struct task_group\s*\*\s*sched_task_group;", "所属 task_group(cgroup 组调度 cpu.weight 的载体)", "trail"),
    (r"^\s*struct uclamp_se\s+uclamp_req\[UCLAMP_CNT\];", "请求的 util clamp 值(sched_setattr 设置)", "trail"),
    (r"^\s*struct uclamp_se\s+uclamp\[UCLAMP_CNT\];", "生效的 util clamp 值(可能被 cgroup 层级收紧)", "trail"),
    (r"^\s*struct sched_statistics\s+stats;", "调度统计(/proc/PID/sched：累计运行时间、唤醒次数等)", "trail"),
    (r"^\s*struct hlist_head\s+preempt_notifiers;", "抢占通知链：KVM 等订阅，任务被抢占时回调", "trail"),
    (r"^\s*unsigned int\s+btrace_seq;", "blktrace 每任务序号", "trail"),

    # ================= ④ CPU 亲和与迁移 =================
    (r"^\s*unsigned int\s+policy;", "【④ CPU 亲和性与迁移】", "调度策略：SCHED_NORMAL/BATCH/IDLE/FIFO/RR/DEADLINE", "btrail"),
    (r"^\s*int\s+nr_cpus_allowed;", "亲和掩码中允许的 CPU 数量", "trail"),
    (r"^\s*const cpumask_t\s*\*\s*cpus_ptr;", "当前生效的 CPU 亲和掩码(未自定义时 = &cpus_mask)", "trail"),
    (r"^\s*cpumask_t\s*\*\s*user_cpus_ptr;", "用户态 sched_setaffinity 设置的掩码(独立分配，默认 NULL)", "trail"),
    (r"^\s*cpumask_t\s+cpus_mask;", "内嵌亲和掩码实体(默认情况)", "trail"),
    (r"^\s*void\s*\*\s*migration_pending;", "待处理的迁移请求(migration 内核线程消费)", "trail"),
    (r"^\s*unsigned short\s+migration_disabled;", "禁止迁移的嵌套计数(每 CPU 上下文/热插拔期间)", "trail"),
    (r"^\s*unsigned short\s+migration_flags;", "迁移状态位 MDF_*", "trail"),

    # ================= ⑤ RCU =================
    (r"^\s*int\s+rcu_read_lock_nesting;", "【⑤ RCU 相关】", "rcu_read_lock() 嵌套计数(PREEMPT_RCU)", "btrail"),
    (r"^\s*union rcu_special\s+rcu_read_unlock_special;", "解锁时的特殊状态(阻塞过/需要 expedited 加速)", "trail"),
    (r"^\s*struct list_head\s+rcu_node_entry;", "阻塞在 rcu_node 上的链表节点", "trail"),
    (r"^\s*struct rcu_node\s*\*\s*rcu_blocked_node;", "阻塞所在的 rcu_node", "trail"),
    (r"^\s*unsigned long\s+rcu_tasks_nvcsw;", "Tasks RCU(睡眠 RCU)：宽限期观察所需的切换计数", "trail"),
    (r"^\s*u8\s+rcu_tasks_holdout;", "是否处于 holdout(拒绝退出宽限期)", "trail"),
    (r"^\s*u8\s+rcu_tasks_idx;", "当前宽限期阶段索引", "trail"),
    (r"^\s*int\s+rcu_tasks_idle_cpu;", "被观察的 idle CPU", "trail"),
    (r"^\s*struct list_head\s+rcu_tasks_holdout_list;", "holdout 链表节点", "trail"),
    (r"^\s*int\s+rcu_tasks_exit_cpu;", "退出阶段所在 CPU", "trail"),
    (r"^\s*struct list_head\s+rcu_tasks_exit_list;", "退出阶段链表节点", "trail"),
    (r"^\s*int\s+trc_reader_nesting;", "TASKS_TRACE_RCU 读者嵌套计数", "trail"),
    (r"^\s*int\s+trc_ipi_to_cpu;", "需发 IPI 查询的 CPU", "trail"),
    (r"^\s*union rcu_special\s+trc_reader_special;", "读者特殊状态", "trail"),
    (r"^\s*struct list_head\s+trc_holdout_list;", "holdout 链表节点", "trail"),
    (r"^\s*struct list_head\s+trc_blkd_node;", "阻塞节点", "trail"),
    (r"^\s*int\s+trc_blkd_cpu;", "阻塞所在 CPU", "trail"),

    # ================= ⑥ 调度统计与进程链表 =================
    (r"^\s*struct sched_info\s+sched_info;", "【⑥ 调度统计与全局进程链表】", "调度延迟统计(run_delay：在就绪队列上累计等待时间)", "btrail"),
    (r"^\s*struct list_head\s+tasks;", "全局任务链表节点(init_task.tasks 为头；ps / for_each_process 遍历的就是它)", "trail"),
    (r"^\s*struct plist_node\s+pushable_tasks;", "RT 任务可推送链表节点(按优先级排序，负载均衡 push/pull 用)", "trail"),
    (r"^\s*struct rb_node\s+pushable_dl_tasks;", "DL 任务可推送红黑树节点", "trail"),

    # ================= ⑦ 地址空间与退出 =================
    (r"^\s*struct mm_struct\s*\*\s*mm;", "【⑦ 地址空间与进程退出】",
     "用户地址空间(页表、vma 树)。内核线程为 NULL——内核线程借用前一个任务的 active_mm，省去刷 TLB。", "babove"),
    (r"^\s*struct mm_struct\s*\*\s*active_mm;", "实际使用的地址空间：内核线程借用上一个任务的 mm", "trail"),
    (r"^\s*struct address_space\s*\*\s*faults_disabled_mapping;", "缺页被禁用(pagefault_disabled)时正在访问的文件映射", "trail"),
    (r"^\s*int\s+exit_state;", "退出状态：EXIT_ZOMBIE(僵尸)/EXIT_DEAD", "trail"),
    (r"^\s*int\s+exit_code;", "退出码，父进程 wait() 取回", "trail"),
    (r"^\s*int\s+exit_signal;", "退出时发给父进程的信号", "trail"),
    (r"^\s*int\s+pdeath_signal;", "父进程死亡时发给本进程的信号(PR_SET_PDEATHSIG)", "trail"),
    (r"^\s*unsigned long\s+jobctl;", "作业控制位：JOBCTL_STOP_PENDING 等(siglock 保护)", "trail"),
    (r"^\s*unsigned int\s+personality;", "执行域/ABI 个性(PER_LINUX32 等，模拟旧 ABI)", "trail"),

    # ================= ⑧ 位域 =================
    (r"^\s*unsigned\s+sched_reset_on_fork:1;", "【⑧ 位域标志(按位打包节省内存)】", "fork 后重置调度属性(SCHED_FLAG_RESET_ON_FORK)", "btrail"),
    (r"^\s*unsigned\s+sched_contributes_to_load:1;", "是否计入系统负载", "trail"),
    (r"^\s*unsigned\s+sched_migrated:1;", "最近被负载均衡迁移过", "trail"),
    (r"^\s*unsigned\s+sched_task_hot:1;", "cache 仍热(倾向留在原 CPU 不迁移)", "trail"),
    (r"^\s*unsigned\s+:0;", "位域占位：强制后续位域对齐到下一个整型边界", "trail"),
    (r"^\s*unsigned\s+sched_remote_wakeup:1;", "由远程 CPU 通过 wakelist 唤醒", "trail"),
    (r"^\s*unsigned\s+user_dumpable:1;", "core dump 权限级别(SUID_DUMP_USER/ROOT)", "trail"),
    (r"^\s*unsigned\s+in_execve:1;", "正在 execve 中(LSM/审计使用)", "trail"),
    (r"^\s*unsigned\s+in_iowait:1;", "计入 iowait 统计(top 的 wa% 来源)", "trail"),
    (r"^\s*unsigned\s+restore_sigmask:1;", "返回用户态前恢复 saved_sigmask", "trail"),
    (r"^\s*unsigned\s+in_user_fault:1;", "正在处理用户态缺页", "trail"),
    (r"^\s*unsigned\s+in_lru_fault:1;", "本次缺页参与多代 LRU 判定", "trail"),
    (r"^\s*unsigned\s+brk_randomized:1;", "brk 地址已随机化", "trail"),
    (r"^\s*unsigned\s+no_cgroup_migration:1;", "禁止用户态发起的 cgroup 迁移", "trail"),
    (r"^\s*unsigned\s+frozen:1;", "被 cgroup freezer 冻结", "trail"),
    (r"^\s*unsigned\s+use_memdelay:1;", "blk-cgroup 统计内存延迟", "trail"),
    (r"^\s*unsigned\s+in_memstall:1;", "因缺内存而停顿(PSI 内存压力统计)", "trail"),
    (r"^\s*unsigned\s+in_page_owner:1;", "page_owner 递归保护", "trail"),
    (r"^\s*unsigned\s+in_eventfd:1;", "eventfd_signal 递归保护", "trail"),
    (r"^\s*unsigned\s+pasid_activated:1;", "IOMMU PASID 已激活", "trail"),
    (r"^\s*unsigned\s+reported_split_lock:1;", "已报告过 split lock(防止日志刷屏)", "trail"),
    (r"^\s*unsigned\s+in_thrashing:1;", "内存颠簸中(延迟统计)", "trail"),
    (r"^\s*unsigned long\s+atomic_flags;", "需原子访问的任务标志：PFA_NO_NEW_PRIVS 等", "trail"),

    # ================= ⑨ 身份标识 =================
    (r"^\s*struct restart_block\s+restart_block;", "【⑨ 身份标识与系统调用重启】",
     "系统调用重启块：被信号打断的系统调用(nanosleep/poll)从这里恢复(ERESTARTSYS 机制)", "btrail"),
    (r"^\s*pid_t\s+pid;", "内核任务 ID(用户态 gettid())：内核以任务为单位调度/收发信号", "trail"),
    (r"^\s*pid_t\s+tgid;", "线程组 ID(用户态 getpid())：同组线程共享", "trail"),
    (r"^\s*unsigned long\s+stack_canary;", "栈保护金丝雀(fork 时随机化，防栈溢出攻击)", "trail"),

    # ================= ⑩ 亲属关系 =================
    (r"^\s*struct task_struct __rcu\s*\*\s*real_parent;", "【⑩ 进程亲属关系(fork 树 / ptrace 树)】",
     "真实父进程(ptrace 不改变；孤儿进程 reparent 时更新)", "btrail"),
    (r"^\s*struct task_struct __rcu\s*\*\s*parent;", "逻辑父进程：接收 SIGCHLD / wait 的对象；被 ptrace 时是调试器", "trail"),
    (r"^\s*struct list_head\s+children;", "子进程链表头(父进程视角)", "trail"),
    (r"^\s*struct list_head\s+sibling;", "兄弟链表节点(挂在 parent->children 上)", "trail"),
    (r"^\s*struct task_struct\s*\*\s*group_leader;", "线程组组长(tgid 对应的那个任务)", "trail"),
    (r"^\s*struct list_head\s+ptraced;", "被我 ptrace 的任务链表头", "trail"),
    (r"^\s*struct list_head\s+ptrace_entry;", "挂到 tracer->ptraced 的链表节点", "trail"),
    (r"^\s*struct pid\s*\*\s*thread_pid;", "任务的 struct pid(pid 的引用对象，支持 pid 命名空间)", "trail"),
    (r"^\s*struct hlist_node\s+pid_links\[PIDTYPE_MAX\];", "各 PID 类型(PID/PGID/SID)的哈希链表节点(按 pid 查任务)", "trail"),
    (r"^\s*struct list_head\s+thread_group;", "线程组链表头(组长持有)", "trail"),
    (r"^\s*struct list_head\s+thread_node;", "同线程组链表节点", "trail"),
    (r"^\s*struct completion\s*\*\s*vfork_done;", "vfork 完成通知：子进程 exec/exit 时 complete 唤醒父进程", "trail"),
    (r"^\s*int __user\s*\*\s*set_child_tid;", "CLONE_CHILD_SETTID 的用户态地址(fork 返回前写入子 TID)", "trail"),
    (r"^\s*int __user\s*\*\s*clear_child_tid;", "CLONE_CHILD_CLEARTID：退出时清零并 futex 唤醒(pthread_join 依赖)", "trail"),
    (r"^\s*void\s*\*\s*worker_private;", "内核工作者私有数据(kworker / io_uring worker)", "trail"),

    # ================= ⑪ CPU 时间统计 =================
    (r"^\s*u64\s+utime;", "【⑪ CPU 时间统计与上下文切换计数】", "用户态 CPU 时间(/proc/PID/stat 第 14 项)", "btrail"),
    (r"^\s*u64\s+stime;", "内核态 CPU 时间(stat 第 15 项)", "trail"),
    (r"^\s*u64\s+utimescaled;", "按 CPU 频率缩放的用户态时间(cpufreq 统计)", "trail"),
    (r"^\s*u64\s+stimescaled;", "按 CPU 频率缩放的内核态时间", "trail"),
    (r"^\s*u64\s+gtime;", "运行虚拟机的 guest 时间(stat 第 43 项)", "trail"),
    (r"^\s*struct prev_cputime\s+prev_cputime;", "上次 CPU 时间记账快照", "trail"),
    (r"^\s*struct vtime\s+vtime;", "虚拟 CPU 时间记账(全 dynticks 系统)", "trail"),
    (r"^\s*atomic_t\s+tick_dep_mask;", "对 tick 的依赖掩码(NOHZ_FULL 下哪些子系统要求保留 tick)", "trail"),
    (r"^\s*unsigned long\s+nvcsw;", "自愿上下文切换次数(主动睡眠：wait/read 阻塞)", "trail"),
    (r"^\s*unsigned long\s+nivcsw;", "非自愿上下文切换次数(时间片耗尽/被抢占)", "trail"),
    (r"^\s*u64\s+start_time;", "进程启动时刻(单调时钟 ns；ps -o etime 的来源)", "trail"),
    (r"^\s*u64\s+start_boottime;", "启动时刻(CLOCK_BOOTTIME，含休眠时间)", "trail"),
    (r"^\s*unsigned long\s+min_flt;", "次缺页次数(页已在内存，无 IO)", "trail"),
    (r"^\s*unsigned long\s+maj_flt;", "主缺页次数(需要 IO 读盘/换入)", "trail"),
    (r"^\s*struct posix_cputimers\s+posix_cputimers;", "POSIX 每线程 CPU 定时器记账", "trail"),
    (r"^\s*struct posix_cputimers_work\s+posix_cputimers_work;", "POSIX 定时器的 task_work 回调", "trail"),

    # ================= ⑫ cred =================
    (r"^\s*const struct cred __rcu\s*\*\s*ptracer_cred;", "【⑫ 权限证书(cred)】", "被跟踪时的跟踪者证书快照", "btrail"),
    (r"^\s*const struct cred __rcu\s*\*\s*real_cred;", "真实证书(客观身份：是谁)", "trail"),
    (r"^\s*const struct cred __rcu\s*\*\s*cred;", "有效证书(主观身份：以谁的名义；setuid 后两者不同，COW 复制)", "trail"),
    (r"^\s*struct key\s*\*\s*cached_requested_key;", "缓存的请求密钥(keyrings)", "trail"),

    # ================= ⑬ 程序名 =================
    (r"^\s*char\s+comm\[TASK_COMM_LEN\];", "【⑬ 程序名与路径解析】", "程序名(不含路径，最长 16 字节；ps 的 CMD 前 15 字符)", "btrail"),
    (r"^\s*struct nameidata\s*\*\s*nameidata;", "当前路径解析状态(LOOKUP_ROOT 等)", "trail"),
    (r"^\s*struct sysv_sem\s+sysvsem;", "SysV 信号量撤销记录(exit 时 undo)", "trail"),
    (r"^\s*struct sysv_shm\s+sysvshm;", "SysV 共享内存撤销记录", "trail"),
    (r"^\s*unsigned long\s+last_switch_count;", "hung task 检测：上次切换计数", "trail"),
    (r"^\s*unsigned long\s+last_switch_time;", "hung task 检测：上次被调度的时间", "trail"),

    # ================= ⑭ 文件系统 =================
    (r"^\s*struct fs_struct\s*\*\s*fs;", "【⑭ 文件系统与打开文件】", "文件系统信息：根目录/当前目录/umask(线程组共享)", "btrail"),
    (r"^\s*struct files_struct\s*\*\s*files;", "打开文件表：fd → struct file(/proc/PID/fd)", "trail"),
    (r"^\s*struct io_uring_task\s*\*\s*io_uring;", "io_uring 任务级状态", "trail"),

    # ================= ⑮ 命名空间 =================
    (r"^\s*struct nsproxy\s*\*\s*nsproxy;", "【⑮ 命名空间】", "命名空间集合：mount/net/pid/uts/ipc/user…", "btrail"),

    # ================= ⑯ 信号 =================
    (r"^\s*struct signal_struct\s*\*\s*signal;", "【⑯ 信号处理】", "线程组共享的信号信息(挂起队列、资源限制、统计)", "btrail"),
    (r"^\s*struct sighand_struct __rcu\s*\*\s*sighand;", "信号处理器表(sigaction 设置，线程组共享，RCU 保护)", "trail"),
    (r"^\s*sigset_t\s+blocked;", "阻塞信号集(线程私有，sigprocmask)", "trail"),
    (r"^\s*sigset_t\s+real_blocked;", "临时阻塞集", "trail"),
    (r"^\s*sigset_t\s+saved_sigmask;", "保存的阻塞集(set_restore_sigmask 恢复)", "trail"),
    (r"^\s*struct sigpending\s+pending;", "待处理信号队列(线程私有；共享信号在 signal->shared_pending)", "trail"),
    (r"^\s*unsigned long\s+sas_ss_sp;", "信号备用栈地址(sigaltstack)", "trail"),
    (r"^\s*size_t\s+sas_ss_size;", "备用栈大小", "trail"),
    (r"^\s*unsigned int\s+sas_ss_flags;", "备用栈标志", "trail"),
    (r"^\s*struct callback_head\s*\*\s*task_works;", "task_work 延迟回调链表(exit 清理、RCU 回调、fd 关闭)", "trail"),
    (r"^\s*struct audit_context\s*\*\s*audit_context;", "审计上下文(auditsyscall)", "trail"),
    (r"^\s*kuid_t\s+loginuid;", "登录 UID(审计)", "trail"),
    (r"^\s*unsigned int\s+sessionid;", "审计会话 ID", "trail"),
    (r"^\s*struct seccomp\s+seccomp;", "seccomp 过滤器状态", "trail"),
    (r"^\s*struct syscall_user_dispatch\s+syscall_dispatch;", "syscall user dispatch：用户态自定义系统调用分发", "trail"),
    (r"^\s*u64\s+parent_exec_id;", "父进程 exec 计数(信号是否来自 exec 之前的检查)", "trail"),
    (r"^\s*u64\s+self_exec_id;", "本进程 exec 计数", "trail"),

    # ================= ⑰ 锁与 PI =================
    (r"^\s*spinlock_t\s+alloc_lock;", "【⑰ 锁与优先级继承(PI)】", "保护 mm/files/fs 等共享指针的分配与修改", "btrail"),
    (r"^\s*raw_spinlock_t\s+pi_lock;", "PI 数据结构锁(rt_mutex 优先级继承相关)", "trail"),
    (r"^\s*struct wake_q_node\s+wake_q;", "延迟唤醒队列节点(wake_q_add 攒批，最后统一唤醒，避免持锁唤醒)", "trail"),
    (r"^\s*struct rb_root_cached\s+pi_waiters;", "等待本任务持有的 rt_mutex 的任务集合(按优先级排序的红黑树)", "trail"),
    (r"^\s*struct task_struct\s*\*\s*pi_top_task;", "等待者中优先级最高的任务(决定本任务被提升到多高)", "trail"),
    (r"^\s*struct rt_mutex_waiter\s*\*\s*pi_blocked_on;", "本任务阻塞在哪个 rt_mutex 上(死锁检测 + PI 提升链)", "trail"),
    (r"^\s*struct mutex_waiter\s*\*\s*blocked_on;", "mutex 死锁检测：本任务阻塞的 mutex(DEBUG_MUTEXES)", "trail"),
    (r"^\s*int\s+non_block_count;", "原子上下文睡眠调试计数(DEBUG_ATOMIC_SLEEP)", "trail"),
    (r"^\s*struct irqtrace_events\s+irqtrace;", "中断标志跟踪(TRACE_IRQFLAGS，lockdep 依赖)", "trail"),
    (r"^\s*unsigned int\s+hardirq_threaded;", "硬中断是否线程化处理", "trail"),
    (r"^\s*u64\s+hardirq_chain_key;", "硬中断锁链哈希(lockdep)", "trail"),
    (r"^\s*int\s+softirqs_enabled;", "软中断开关状态", "trail"),
    (r"^\s*int\s+softirq_context;", "软中断嵌套计数", "trail"),
    (r"^\s*int\s+irq_config;", "中断配置状态", "trail"),
    (r"^\s*int\s+softirq_disable_cnt;", "PREEMPT_RT：软中断禁用计数", "trail"),
    (r"^\s*u64\s+curr_chain_key;", "当前锁链哈希值(lockdep)", "trail"),
    (r"^\s*int\s+lockdep_depth;", "持有锁的深度", "trail"),
    (r"^\s*unsigned int\s+lockdep_recursion;", "lockdep 递归保护计数", "trail"),
    (r"^\s*struct held_lock\s+held_locks\[MAX_LOCK_DEPTH\];", "已持有锁的数组(释放时校验顺序)", "trail"),
    (r"^\s*unsigned int\s+in_ubsan;", "UBSAN 报告递归保护", "trail"),

    # ================= ⑱ 块设备与回收 =================
    (r"^\s*void\s*\*\s*journal_info;", "【⑱ 块设备 IO 与内存回收】", "日志文件系统事务上下文(JBD2 挂在这里)", "btrail"),
    (r"^\s*struct bio_list\s*\*\s*bio_list;", "BIO 提交链表(栈式块设备递归提交)", "trail"),
    (r"^\s*struct blk_plug\s*\*\s*plug;", "块层蓄流(blk_start_plug：批量提交 IO，减少锁开销)", "trail"),
    (r"^\s*struct reclaim_state\s*\*\s*reclaim_state;", "页回收计数状态(direct reclaim 过程记录)", "trail"),
    (r"^\s*struct io_context\s*\*\s*io_context;", "IO 调度上下文(与电梯调度器关联)", "trail"),
    (r"^\s*struct capture_control\s*\*\s*capture_control;", "内存规整(compaction)捕获控制", "trail"),
    (r"^\s*unsigned long\s+ptrace_message;", "ptrace 事件消息(PTRACE_EVENT_*)", "trail"),
    (r"^\s*kernel_siginfo_t\s*\*\s*last_siginfo;", "最后收到的信号详细信息(等待队列消费)", "trail"),

    # ================= ⑲ IO 记账与资源控制 =================
    (r"^\s*struct task_io_accounting\s+ioac;", "【⑲ IO 记账与资源控制(cgroup/cpuset)】", "IO 记账(/proc/PID/io：rchar/wchar/syscr/syscw)", "btrail"),
    (r"^\s*unsigned int\s+psi_flags;", "PSI 压力停顿标志位", "trail"),
    (r"^\s*u64\s+acct_rss_mem1;", "BSD 记账：累计 RSS 内存", "trail"),
    (r"^\s*u64\s+acct_vm_mem1;", "BSD 记账：累计虚拟内存", "trail"),
    (r"^\s*u64\s+acct_timexpd;", "BSD 记账：上次更新以来的 CPU 时间", "trail"),
    (r"^\s*nodemask_t\s+mems_allowed;", "cpuset 允许的内存节点掩码", "trail"),
    (r"^\s*seqcount_spinlock_t\s+mems_allowed_seq;", "节点集合变更序号(seqcount，检测并发更新)", "trail"),
    (r"^\s*int\s+cpuset_mem_spread_rotor;", "内存分配轮转节点(散布策略)", "trail"),
    (r"^\s*int\s+cpuset_slab_spread_rotor;", "slab 分配轮转节点", "trail"),
    (r"^\s*struct css_set __rcu\s*\*\s*cgroups;", "所属 css_set(cgroup 集合，RCU 保护)", "trail"),
    (r"^\s*struct list_head\s+cg_list;", "css_set 上的任务链表节点", "trail"),
    (r"^\s*u32\s+closid;", "x86 resctrl：Cache 分配类 ID", "trail"),
    (r"^\s*u32\s+rmid;", "x86 resctrl：Cache 监控 ID", "trail"),

    # ================= ⑳ futex 与 perf =================
    (r"^\s*struct robust_list_head __user\s*\*\s*robust_list;", "【⑳ futex 与 perf】", "robust futex 链表：线程死亡时内核自动解锁并通知(pthread_mutex robust)", "btrail"),
    (r"^\s*struct compat_robust_list_head __user\s*\*\s*compat_robust_list;", "32 位兼容的 robust futex 链表", "trail"),
    (r"^\s*struct list_head\s+pi_state_list;", "futex PI 状态链表", "trail"),
    (r"^\s*struct futex_pi_state\s*\*\s*pi_state_cache;", "futex PI 状态缓存(空闲对象池)", "trail"),
    (r"^\s*struct mutex\s+futex_exit_mutex;", "futex 退出同步互斥锁", "trail"),
    (r"^\s*unsigned int\s+futex_state;", "futex 状态", "trail"),
    (r"^\s*struct perf_event_context\s*\*\s*perf_event_ctxp;", "perf 事件上下文指针", "trail"),
    (r"^\s*struct mutex\s+perf_event_mutex;", "perf 事件互斥锁", "trail"),
    (r"^\s*struct list_head\s+perf_event_list;", "本任务的 perf 事件链表", "trail"),
    (r"^\s*unsigned long\s+preempt_disable_ip;", "最后 preempt_disable 的地址(DEBUG_PREEMPT 报错打印)", "trail"),

    # ================= ㉑ NUMA =================
    (r"^\s*struct mempolicy\s*\*\s*mempolicy;", "【㉑ NUMA 内存策略与自动平衡】", "NUMA 内存策略(绑定/交错/优先节点)", "btrail"),
    (r"^\s*short\s+il_prev;", "交错(interleave)分配上次使用的节点", "trail"),
    (r"^\s*short\s+pref_node_fork;", "fork 时倾向分配的节点", "trail"),
    (r"^\s*int\s+numa_scan_seq;", "NUMA 扫描序列号", "trail"),
    (r"^\s*unsigned int\s+numa_scan_period;", "NUMA 扫描周期(页数，自适应调整)", "trail"),
    (r"^\s*unsigned int\s+numa_scan_period_max;", "扫描周期上限", "trail"),
    (r"^\s*int\s+numa_preferred_nid;", "首选 NUMA 节点(任务与内存的迁移目标)", "trail"),
    (r"^\s*unsigned long\s+numa_migrate_retry;", "迁移重试计数", "trail"),
    (r"^\s*u64\s+node_stamp;", "上次迁移时间戳", "trail"),
    (r"^\s*u64\s+last_task_numa_placement;", "上次任务放置时间", "trail"),
    (r"^\s*u64\s+last_sum_exec_runtime;", "上次放置时的累计运行时间", "trail"),
    (r"^\s*struct callback_head\s+numa_work;", "NUMA 扫描的 task_work 回调", "trail"),
    (r"^\s*struct numa_group __rcu\s*\*\s*numa_group;", "共享内存页的 NUMA 分组(多任务共享页一起迁移)", "trail"),
    (r"^\s*unsigned long\s*\*\s*numa_faults;", "四区数组：faults_memory/faults_cpu 及两个 buffer(放置决策依据)", "trail"),
    (r"^\s*unsigned long\s+total_numa_faults;", "NUMA 缺页总数", "trail"),
    (r"^\s*unsigned long\s+numa_faults_locality\[3\];", "本地/远端/迁移失败缺页统计(调整扫描周期用)", "trail"),
    (r"^\s*unsigned long\s+numa_pages_migrated;", "已迁移页数", "trail"),

    # ================= ㉒ 杂项与调试 =================
    (r"^\s*struct rseq __user\s*\*\s*rseq;", "【㉒ 杂项优化与调试设施(多数为 CONFIG_* 可选)】", "restartable sequences：用户态原子操作序列(每线程注册)", "btrail"),
    (r"^\s*u32\s+rseq_len;", "rseq 区域长度", "trail"),
    (r"^\s*u32\s+rseq_sig;", "rseq 签名(验证注册有效性)", "trail"),
    (r"^\s*unsigned long\s+rseq_event_mask;", "rseq 事件掩码(原子 RMW)", "trail"),
    (r"^\s*int\s+mm_cid;", "当前任务在 mm 中的 CID(per-mm per-cpu ID，优化 TLB 刷新)", "trail"),
    (r"^\s*int\s+last_mm_cid;", "最近使用的 mm CID", "trail"),
    (r"^\s*int\s+migrate_from_cpu;", "上次迁移来源 CPU", "trail"),
    (r"^\s*int\s+mm_cid_active;", "CID 位图是否活跃", "trail"),
    (r"^\s*struct callback_head\s+cid_work;", "CID 分配的 task_work 回调", "trail"),
    (r"^\s*struct tlbflush_unmap_batch\s+tlb_ubc;", "TLB 批量刷新批次", "trail"),
    (r"^\s*struct pipe_inode_info\s*\*\s*splice_pipe;", "splice 上次使用的管道(缓存优化)", "trail"),
    (r"^\s*struct page_frag\s+task_frag;", "页面碎片分配器缓存(小内存分配提速)", "trail"),
    (r"^\s*struct task_delay_info\s*\*\s*delays;", "延迟统计(blkio/swap/freepages，CONFIG_TASK_DELAY_ACCT)", "trail"),
    (r"^\s*int\s+make_it_fail;", "故障注入：本次分配是否强制失败", "trail"),
    (r"^\s*unsigned int\s+fail_nth;", "故障注入：每 N 次失败一次", "trail"),
    (r"^\s*int\s+nr_dirtied;", "累计写脏页数(超过 nr_dirtied_pause 就限速)", "trail"),
    (r"^\s*int\s+nr_dirtied_pause;", "触发脏页节流的阈值", "trail"),
    (r"^\s*unsigned long\s+dirty_paused_when;", "本次节流开始时间", "trail"),
    (r"^\s*int\s+latency_record_count;", "延迟记录计数(LatencyTOP)", "trail"),
    (r"^\s*struct latency_record\s+latency_record\[LT_SAVECOUNT\];", "延迟记录数组", "trail"),
    (r"^\s*u64\s+timer_slack_ns;", "定时器松弛：poll/select 超时向上取整(合批唤醒省电)", "trail"),
    (r"^\s*u64\s+default_timer_slack_ns;", "默认定时器松弛值", "trail"),
    (r"^\s*unsigned int\s+kasan_depth;", "KASAN 报告递归深度", "trail"),
    (r"^\s*struct kcsan_ctx\s+kcsan_ctx;", "KCSAN 数据竞争检测上下文", "trail"),
    (r"^\s*struct irqtrace_events\s+kcsan_save_irqtrace;", "KCSAN 保存的中断跟踪", "trail"),
    (r"^\s*int\s+kcsan_stack_depth;", "KCSAN 栈深度", "trail"),
    (r"^\s*struct kmsan_ctx\s+kmsan_ctx;", "KMSAN 未初始化内存检测上下文", "trail"),
    (r"^\s*struct kunit\s*\*\s*kunit_test;", "KUnit 测试上下文", "trail"),
    (r"^\s*int\s+curr_ret_stack;", "返回地址栈当前索引(函数图追踪)", "trail"),
    (r"^\s*int\s+curr_ret_depth;", "当前追踪深度", "trail"),
    (r"^\s*struct ftrace_ret_stack\s*\*\s*ret_stack;", "返回地址栈(记录函数调用图，function_graph tracer)", "trail"),
    (r"^\s*unsigned long long\s+ftrace_timestamp;", "上次调度的时间戳(函数图追踪)", "trail"),
    (r"^\s*atomic_t\s+trace_overrun;", "因深度溢出未追踪的函数计数", "trail"),
    (r"^\s*atomic_t\s+tracing_graph_pause;", "暂停追踪标志", "trail"),
    (r"^\s*unsigned long\s+trace_recursion;", "追踪递归保护位图", "trail"),
    (r"^\s*unsigned int\s+kcov_mode;", "kcov 收集模式(0=关闭)", "trail"),
    (r"^\s*unsigned int\s+kcov_size;", "kcov 缓冲区大小", "trail"),
    (r"^\s*void\s*\*\s*kcov_area;", "kcov 覆盖率缓冲区", "trail"),
    (r"^\s*struct kcov\s*\*\s*kcov;", "kcov 描述符", "trail"),
    (r"^\s*u64\s+kcov_handle;", "远程覆盖收集句柄", "trail"),
    (r"^\s*int\s+kcov_sequence;", "kcov 序号", "trail"),
    (r"^\s*unsigned int\s+kcov_softirq;", "软中断上下文收集覆盖", "trail"),
    (r"^\s*unsigned int\s+kcov_saved_mode;", "被抢占前暂存的 kcov 模式", "trail"),
    (r"^\s*unsigned int\s+kcov_saved_size;", "暂存的缓冲区大小", "trail"),
    (r"^\s*void\s*\*\s*kcov_saved_area;", "暂存的缓冲区", "trail"),
    (r"^\s*struct kcov\s*\*\s*kcov_saved_kcov;", "暂存的 kcov 描述符", "trail"),
    (r"^\s*int\s+kcov_saved_sequence;", "暂存的序号", "trail"),
    (r"^\s*struct mem_cgroup\s*\*\s*memcg_in_oom;", "本任务正在参与 OOM 的 memcg", "trail"),
    (r"^\s*gfp_t\s+memcg_oom_gfp_mask;", "触发 OOM 的分配标志", "trail"),
    (r"^\s*int\s+memcg_oom_order;", "触发 OOM 的分配阶", "trail"),
    (r"^\s*unsigned int\s+memcg_nr_pages_over_high;", "超过 high 水位、返回用户态前需回收的页数", "trail"),
    (r"^\s*struct mem_cgroup\s*\*\s*active_memcg;", "记账目标 memcg(可被临时覆盖)", "trail"),
    (r"^\s*struct gendisk\s*\*\s*throttle_disk;", "blk-cgroup 限流的磁盘", "trail"),
    (r"^\s*struct uprobe_task\s*\*\s*utask;", "uprobe 任务级数据", "trail"),
    (r"^\s*unsigned int\s+sequential_io;", "bcache 顺序 IO 检测计数", "trail"),
    (r"^\s*unsigned int\s+sequential_io_avg;", "顺序 IO 平均计数", "trail"),
    (r"^\s*struct kmap_ctrl\s+kmap_ctrl;", "临时映射控制(kmap_local)", "trail"),
    (r"^\s*unsigned long\s+task_state_change;", "任务状态变化计数(原子睡眠调试)", "trail"),
    (r"^\s*unsigned long\s+saved_state_change;", "PREEMPT_RT：暂存的状态变化计数", "trail"),
    (r"^\s*struct rcu_head\s+rcu;", "任务销毁时的 RCU 延迟释放头(task_struct 最终通过 RCU 释放)", "trail"),
    (r"^\s*refcount_t\s+rcu_users;", "RCU 引用计数(与 usage 共同决定释放时机)", "trail"),
    (r"^\s*int\s+pagefault_disabled;", "禁用缺页处理的嵌套计数", "trail"),
    (r"^\s*struct task_struct\s*\*\s*oom_reaper_list;", "OOM reaper 链表(收割被 OOM 杀死进程的内存)", "trail"),
    (r"^\s*struct timer_list\s+oom_reaper_timer;", "OOM reaper 定时器", "trail"),
    (r"^\s*struct vm_struct\s*\*\s*stack_vm_area;", "内核栈的 vmalloc 映射描述(VMAP_STACK：栈与 task_struct 分离)", "trail"),
    (r"^\s*refcount_t\s+stack_refcount;", "栈引用计数(栈可先于 task_struct 释放)", "trail"),
    (r"^\s*int\s+patch_state;", "livepatch 状态", "trail"),
    (r"^\s*void\s*\*\s*security;", "LSM 安全 blob(各 LSM 模块的私有数据)", "trail"),
    (r"^\s*struct bpf_local_storage __rcu\s*\*\s*bpf_storage;", "BPF 任务本地存储", "trail"),
    (r"^\s*struct bpf_run_ctx\s*\*\s*bpf_ctx;", "BPF 运行上下文", "trail"),
    (r"^\s*unsigned long\s+lowest_stack;", "栈最低使用位置(STACKLEAK 擦除栈用)", "trail"),
    (r"^\s*unsigned long\s+prev_lowest_stack;", "上次的栈最低位置", "trail"),
    (r"^\s*u32\s+kstack_offset;", "内核栈起始随机偏移(防栈地址泄露)", "trail"),
    (r"^\s*void __user\s*\*\s*mce_vaddr;", "MCE：相关虚拟地址", "trail"),
    (r"^\s*__u64\s+mce_kflags;", "MCE：内核标志", "trail"),
    (r"^\s*u64\s+mce_addr;", "MCE：物理地址", "trail"),
    (r"^\s*__u64\s+mce_ripv\s*:\s*1,", "MCE 位域：ripv(指令指针有效)/whole_page(整页)/reserved", "trail"),
    (r"^\s*struct callback_head\s+mce_kill_me;", "MCE 杀任务的 task_work 回调", "trail"),
    (r"^\s*int\s+mce_count;", "MCE 次数统计", "trail"),
    (r"^\s*struct llist_head\s+kretprobe_instances;", "kretprobe 实例链表", "trail"),
    (r"^\s*struct llist_head\s+rethooks;", "rethook 实例链表", "trail"),
    (r"^\s*struct callback_head\s+l1d_flush_kill;", "L1D flush 的延迟清理任务(SMT 安全)", "trail"),
    (r"^\s*union rv_task_monitor\s+rv\[RV_PER_TASK_MONITORS\];", "Runtime Verification 监视器(每任务)", "trail"),
    (r"^\s*struct user_event_mm\s*\*\s*user_event_mm;", "user events 跟踪的 mm 引用", "trail"),
    (r"^\s*randomized_struct_fields_end", "可随机化区域结束：新字段应加在此标记之前", "trail"),

    # ================= 结尾 =================
    (r"^\s*struct thread_struct\s+thread;", "【㉓ 架构相关线程状态】",
     "x86：内核栈指针 sp、fsbase、浮点状态等——必须放最后(内含变长结构)", "btrail"),
    (r"^\s*\};", "task_struct 结束", "trail"),
]


def block_comment(text):
    """把多行文本变成内核风格的块注释(带一个 tab 缩进)"""
    ls = text.split("\n")
    s = "\t/*\n"
    for l in ls:
        s += "\t * " + l + "\n"
    s += "\t */"
    return s


def main():
    with open(PATH, encoding="utf-8") as f:
        text = f.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()

    # 定位 task_struct 定义区域
    start = next(i for i, l in enumerate(lines) if re.match(r"^struct task_struct \{", l))
    end = next(i for i in range(start + 1, len(lines)) if re.match(r"^\s*\};", lines[i]))

    hit = [0] * len(MEMBERS)
    used_once = set()
    out = []
    for i, line in enumerate(lines):
        if start <= i <= end:
            for j, entry in enumerate(MEMBERS):
                if j in used_once:
                    continue
                pat = entry[0]
                if re.match(pat, line):
                    hit[j] += 1
                    mode = entry[-1]
                    if mode == "above_once":  # 只在第一次出现时插入
                        used_once.add(j)
                        mode = "above"
                    if mode == "btrail":  # 横幅 + 成员行尾注释
                        out.append("\t/* ===== " + entry[1] + " ===== */")
                        out.append(line.rstrip() + "\t/* " + entry[2] + " */")
                    elif mode == "babove":  # 横幅 + 成员上方块注释
                        out.append("\t/* ===== " + entry[1] + " ===== */")
                        out.append(block_comment(entry[2]))
                        out.append(line)
                    elif mode == "above":
                        out.append(block_comment(entry[1]))
                        out.append(line)
                    else:  # trail
                        out.append(line.rstrip() + ("\t/* " + entry[1] + " */" if entry[1] else ""))
                    break
            else:
                out.append(line)
        else:
            out.append(line)

    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(out) + nl)

    # 自检：每条规则应恰好命中 1 次
    misses = [(entry[0], entry[-1]) for j, entry in enumerate(MEMBERS) if hit[j] != 1]
    total = sum(hit)
    print("结构体区域: 行 %d ~ %d，共 %d 行" % (start + 1, end + 1, end - start + 1))
    print("命中注释: %d 条 / 规则 %d 条" % (total, len(MEMBERS)))
    if misses:
        print("未精确命中 1 次的规则(%d):" % len(misses))
        for pat, mode in misses:
            print("  [%s] %s" % (mode, pat))
    else:
        print("全部规则恰好命中 1 次 OK")


if __name__ == "__main__":
    main()
