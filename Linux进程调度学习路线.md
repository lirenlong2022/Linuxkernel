# Linux 进程调度学习路线（主线二 · 细化版）

> 源码版本：**Linux 6.6.161**（LTS）
> 定位：总路线《Linux内核学习路线.md》第 4 节"主线二：进程管理与调度"的展开
> 学习方式：源码阅读为主，实验验证为辅——"读—改—跑—验证"循环
> 建议周期：**4~6 周**（按每天 2~3 小时计，可弹性伸缩）

---

## 0. 贯穿全程的一条主线（先背下来，边学边对照）

进程调度的所有代码都服务于这一个循环，读任何文件时都问自己"它在这条链上的哪一环"：

```
① 触发时机                   ② 调度入口              ③ 选择下一个进程           ④ 切换
时钟中断 tick ──────────┐
进程主动睡眠/阻塞 ────────┼──→ schedule() ──→ __schedule() ──→ pick_next_task() ──→ context_switch()
中断/系统调用返回时检查 ──┘        core.c:6789         core.c:6004/6081        core.c:5337
 TIF_NEED_RESCHED                                     └→ sched_class->pick_next_task
                                                          (stop→dl→rt→fair→idle)
⑤ 切换的汇编：__switch_to() → __switch_to_asm()   (arch/x86/kernel/process_64.c:561 → arch/x86/entry/entry_64.S:226)

⑥ 唤醒侧（反向箭头）：try_to_wake_up() ──→ select_task_rq() ──→ enqueue_task() ──→ check_preempt_wakeup()
                           core.c:4213
```

同时要分清"三层"：**策略层**（要不要换、何时换）→ **机制层**（怎么选、怎么记账）→ **架构层**（寄存器/栈怎么切）。

---

## 1. 第 0 步：磨刀与全局地图（0.5~1 天）

### 前置知识自查

- [ ] 红黑树（CFS 的核心数据结构，插入/删除/最左节点查询 O(log n)）
- [ ] 内核侵入式链表 `list_head`（task_struct 的组织方式）
- [ ] per-CPU 变量概念（每个 CPU 一个运行队列的前提）
- [ ] 中断上半部/下半部的基本概念（时钟中断是调度的"心跳"）
- [ ] AT&T 汇编能读懂 `mov`/`push`/`pop`/`call`（上下文切换用）

### 内核调度器文件地图（知道"什么在哪里"）

先浏览 [kernel/sched/](linux-6.6.161/kernel/sched/) 目录，对照下表建立索引：

| 文件 | 职责 |
| --- | --- |
| [core.c](linux-6.6.161/kernel/sched/core.c) | **调度核心**：schedule()、pick_next_task()、context_switch()、唤醒、tick |
| [fair.c](linux-6.6.161/kernel/sched/fair.c) | **CFS** 调度类（默认、普通进程） |
| [rt.c](linux-6.6.161/kernel/sched/rt.c) | 实时调度类 SCHED_FIFO / SCHED_RR |
| [deadline.c](linux-6.6.161/kernel/sched/deadline.c) | SCHED_DEADLINE（EDF 限期调度） |
| [idle.c](linux-6.6.161/kernel/sched/idle.c) | idle 调度类（最低优先级，无事可做时） |
| [stop_task.c](linux-6.6.161/kernel/sched/stop_task.c) | stop 类（最高优先级，用于 CPU 热插拔/隔离） |
| [sched.h](linux-6.6.161/kernel/sched/sched.h) | **调度器内部头文件**：`struct rq`、`struct sched_class`、`sched_entity` 都在这 |
| [topology.c](linux-6.6.161/kernel/sched/topology.c) | 调度域 sched_domain（多核负载均衡的地基） |
| [pelt.c](linux-6.6.161/kernel/sched/pelt.c) | PELT 负载跟踪的纯数学部分 |
| [loadavg.c](linux-6.6.161/kernel/sched/loadavg.c) | `/proc/loadavg` 系统平均负载 |
| [clock.c](linux-6.6.161/kernel/sched/clock.c) | 调度时钟 rq_clock（vruntime 记账的时间基准） |
| [cputime.c](linux-6.6.161/kernel/sched/cputime.c) | CPU 时间记账（utime/stime，/proc/PID/stat） |
| [cpufreq.c](linux-6.6.161/kernel/sched/cpufreq.c) + [cpufreq_schedutil.c](linux-6.6.161/kernel/sched/cpufreq_schedutil.c) | schedutil 调频 governor（调度器驱动 CPU 频率） |
| [cpupri.c](linux-6.6.161/kernel/sched/cpupri.c) / [cpudeadline.c](linux-6.6.161/kernel/sched/cpudeadline.c) | RT/DL 的每 CPU 辅助结构（优先级位图/堆） |
| [debug.c](linux-6.6.161/kernel/sched/debug.c) / [stats.c](linux-6.6.161/kernel/sched/stats.c) | `/proc/sched_debug`、`/proc/schedstat` |
| [completion.c](linux-6.6.161/kernel/sched/completion.c) / [wait.c](linux-6.6.161/kernel/sched/wait.c) / [swait.c](linux-6.6.161/kernel/sched/swait.c) | 等待队列三件套（睡眠唤醒的载体） |
| [autogroup.c](linux-6.6.161/kernel/sched/autogroup.c) | 终端会话自动分组（为什么编译时桌面不卡） |
| [psi.c](linux-6.6.161/kernel/sched/psi.c) | PSI 资源压力统计（进阶可选） |
| [core_sched.c](linux-6.6.161/kernel/sched/core_sched.c) | SMT 核间安全隔离（进阶可选） |

> 技巧：把 [Documentation/scheduler/index.rst](linux-6.6.161/Documentation/scheduler/index.rst) 的目录过一遍，官方文档比很多博客准确。

---

## 2. 第一站：进程是什么——task_struct（1~2 天）

**目标**：吃透调度器操作的对象。先懂"进程"，再懂"调度"。

### 精读清单

- [ ] [include/linux/sched.h:746](linux-6.6.161/include/linux/sched.h#L746) `struct task_struct`：**不要求逐字段**，重点字段逐行注释：
      - 身份类：`pid` / `tgid` / `comm` / `tasks`（全局链表） / `thread_group`
      - 状态类：`__state` / `exit_state` / `flags`（PF_*）
      - 调度类：`prio` / `static_prio` / `normal_prio` / `rt_priority` / `policy` / `sched_class` / `se`（sched_entity）
      - 地址空间：`mm` / `active_mm`（内核线程为什么 `mm == NULL`？）
      - 栈与抢占：`stack` / `preempt_count`（与 thread_info 的关系）
- [ ] 进程状态机：`TASK_RUNNING` / `TASK_INTERRUPTIBLE` / `TASK_UNINTERRUPTIBLE` / `TASK_STOPPED` / `EXIT_ZOMBIE` / `EXIT_DEAD`，`set_current_state()` 的写法与内存屏障
- [ ] 内核栈与 `current` 宏：[arch/x86/include/asm/current.h](linux-6.6.161/arch/x86/include/asm/current.h)（6.6 的 thread_info 已并入 task_struct，怎么用 sp 定位？）
- [ ] 优先级体系全景图：0~139 区间 = RT 0~99 + CFS 100~139（nice -20~+19），三个 prio 字段的关系（`effective_prio()`）
- [ ] `pid/tgid` 与线程组：`getpid()` 和 `gettid()` 分别返回谁？`clone` 的 `CLONE_THREAD` 标志

### 带着这些问题读

1. 为什么 `__state` 用位组合（`__TASK_*` 常量）而不是枚举值？
2. 为什么要有 `static_prio` / `normal_prio` / `prio` 三个字段？RT 进程和 CFS 进程各自哪几个生效？
3. 为什么把 task_struct 放在内核栈底（低地址）？thread_info 合并进去后 `current` 怎么实现？
4. `nice` 和 `rt_priority` 是两套不相关的数值体系，内核怎么统一？

### 动手验证

- [ ] 写内核模块：从 `init_task` 出发遍历 `for_each_process()`，打印所有进程的 `comm/pid/tgid/state/prio/policy`，对照 `ps -eo pid,tgid,stat,pri,ni,comm` 的输出
- [ ] `ps -eLo pid,tid,stat,comm` 找一个多线程进程（如 systemd），验证 tgid/pid 关系

---

## 3. 第二站：调度器框架——sched_class 与 rq（1~2 天）

**目标**：看懂调度器的"面向对象"设计——策略被抽象成类，核心代码只认接口。

### 精读清单

- [ ] [kernel/sched/sched.h:2247](linux-6.6.161/kernel/sched/sched.h#L2247) `struct sched_class`：这是全书最重要的一张"接口表"
      - `enqueue_task` / `dequeue_task` / `yield_task` / `pick_next_task` / `task_tick` / `wakeup_preempt` / `select_task_rq` / `balance` / `update_curr`……
      - 想清楚：**任何调度策略 = 这组函数的不同实现**
- [ ] [kernel/sched/sched.h:963](linux-6.6.161/kernel/sched/sched.h#L963) `struct rq`：每 CPU 运行队列
      - `cfs` / `rt` / `dl` 三个子队列、`nr_running`、`curr`、`idle`、`clock`
      - 6.6 的 per-CPU 化改进：为什么把 `rq` 拆成 core / fair / rt / dl 几部分（per-CPU 对齐与 cache 友好）
- [ ] 五个调度类与优先级次序：**stop > deadline > rt > fair > idle**——在 [core.c:9984](linux-6.6.161/kernel/sched/core.c#L9984) `sched_init()` 里看它们如何按顺序链接、如何绑定到每 CPU 的 rq
- [ ] 策略 vs 类：`SCHED_NORMAL/BATCH/IDLE` → fair 类，`SCHED_FIFO/RR` → rt 类，`SCHED_DEADLINE` → dl 类；`sched_setattr()` 系统调用如何落到 `__setscheduler` 上

### 带着这些问题读

1. 为什么内核用函数指针表（sched_class）而不是 switch-case 按 policy 分发？这给调度器带来了什么扩展性（想想 6.12 的 sched_ext）？
2. 为什么每个 CPU 一个 `rq` 而不是全局一条队列？（提示：锁竞争、cache 亲和）
3. `rq->curr` 指向正在运行的进程，那"正在运行"的进程还在 rq 队列里吗？

### 动手验证

- [ ] `cat /proc/sched_debug`，逐字段对照 `struct rq` 和 `cfs_rq` 的成员（`nr_running`、`min_vruntime`、`.exec_clock`……）
- [ ] 读 [Documentation/scheduler/sched-design-CFS.rst](linux-6.6.161/Documentation/scheduler/sched-design-CFS.rst)（很短，10 分钟）

---

## 4. 第三站：一次调度是怎么发生的——schedule() 主路径（2~3 天）★核心

**目标**：把第 0 节的链条 ②③④⑤ 一行行走通。这是整个调度学习的高潮，值得反复读三遍。

### 精读清单

- [ ] [core.c:6789](linux-6.6.161/kernel/sched/core.c#L6789) `schedule()` → `__schedule()` 逐行精读（先关抢占 → 取当前 rq → 处理 prev：若睡眠则 `deactivate_task` → `pick_next_task` → `context_switch` → 恢复）
- [ ] [core.c:6081](linux-6.6.161/kernel/sched/core.c#L6081) `pick_next_task()` 与 [core.c:6004](linux-6.6.161/kernel/sched/core.c#L6004) `__pick_next_task()`：为什么要拆两个？（无 RT/DL 任务时的快路径优化，`nr_running` 计数）
- [ ] [core.c:5337](linux-6.6.161/kernel/sched/core.c#L5337) `context_switch()`：两件事——`switch_mm_irqs_off()` 换地址空间（[arch/x86/mm/tlb.c](linux-6.6.161/arch/x86/mm/tlb.c)）+ `switch_to()` 换寄存器栈
- [ ] x86 架构层切换：
      - [arch/x86/kernel/process_64.c:561](linux-6.6.161/arch/x86/kernel/process_64.c#L561) `__switch_to()`：换内核栈、换线程局部存储（FS）
      - [arch/x86/entry/entry_64.S:226](linux-6.6.161/arch/x86/entry/entry_64.S#L226) `__switch_to_asm`：**逐行读汇编**——保存 callee-saved 寄存器（rbx/rbp/r12~r15）到 prev 的栈，从 next 的栈恢复，最后 `jmp __switch_to`，返回地址天然变成 next 上次切出的地方
- [ ] 切回点：`finish_task_switch()` / `schedule_tail()`——被换走的进程再回来时从哪继续？
- [ ] 核心心智模型：**上下文切换 = 两个进程各自在自己的内核栈上执行"保存/恢复"，切换完成时 prev 的返回地址在 next 的栈里**。画一张 rsp 切换前后的栈示意图

### 带着这些问题读

1. 为什么切换时只需要保存 callee-saved 寄存器？caller-saved 寄存器谁来管？
2. `switch_to(prev, next, prev)` 宏为什么传 3 个参数、第三个还是 prev？"切换在第一个函数返回前完成"是什么意思？
3. 内核线程 `mm == NULL` 时 `switch_mm` 为什么不换页表（借 active_mm）？
4. `__schedule()` 开头为什么必须 `preempt_disable()` + `raw_spin_lock`？被抢占的进程回来时锁怎么处理（`finish_task_switch` 里的 `raw_spin_unlock_irq`）？

### 动手验证

- [ ] `trace-cmd record -e sched:sched_switch -e sched:sched_wakeup ls`，用 kernelshark 或 `trace-cmd report` 看切换序列
- [ ] QEMU + GDB：在 `__schedule` 打断点，`bt` 看完整调用栈（验证"从哪触发调度"）

---

## 5. 第四站：何时发生调度——触发时机与抢占（2 天）

**目标**：调度不是"想切就切"，所有切换都是被某个事件触发。理解触发点 = 理解"时机"。

### 精读清单

- [ ] 时钟 tick：[core.c:5649](linux-6.6.161/kernel/sched/core.c#L5649) `scheduler_tick()` → `curr->sched_class->task_tick()`；顺带看 [kernel/time/tick-sched.c](linux-6.6.161/kernel/time/tick-sched.c) 理解 HZ/jiffies/动态 tick（nohz）
- [ ] 主动放弃：进程睡眠（`wait_event*` → `schedule()`）、`sched_yield()`、`cond_resched()`（voluntary preemption，[core.c](linux-6.6.161/kernel/sched/core.c) 中 `might_resched` 的检查点）
- [ ] 被动抢占：`TIF_NEED_RESCHED` 标志位——tick 里置位，**返回用户态前 / 中断返回时**检查（[arch/x86/entry/common.c](linux-6.6.161/arch/x86/entry/common.c) 的 `exit_to_user_mode_prepare` / `raw_irqentry_exit_cond_resched`）
- [ ] 抢占计数：[include/linux/preempt.h](linux-6.6.161/include/linux/preempt.h) `preempt_count` 的位域布局（抢占位 + 软中断位 + 硬中断位），`preempt_disable/enable`；`CONFIG_PREEMPT` 与 `preempt_schedule()`（[core.c:6905](linux-6.6.161/kernel/sched/core.c#L6905)）
- [ ] 唤醒路径：[core.c:4213](linux-6.6.161/kernel/sched/core.c#L4213) `try_to_wake_up()` → `select_task_rq()`（该去哪个 CPU）→ `enqueue_task()` → `check_preempt_wakeup()`（要不要立刻抢占当前进程）

### 带着这些问题读

1. 6.6 默认 `CONFIG_PREEMPT_NONE` 意味着内核态执行中不会被打断，为什么？服务器/桌面/实时三种配置怎么选（CONFIG_PREEMPT_DYNAMIC 在 6.6 是默认）？
2. 为什么置了 `TIF_NEED_RESCHED` 不立刻切，非要等到"返回用户态/抢占点"？
3. 唤醒一个进程时，为什么可能把当前 CPU 上正在运行的进程踢下去（抢占），却不一定切换 CPU？
4. `preempt_count` 为什么要同时记录软中断和硬中断占用？（提示：软中断上下文不能睡眠）

### 动手验证

- [ ] bpftrace 一行观察：`bpftrace -e 't:sched:sched_switch { printf("%s -> %s\n", args.prev_comm, args.next_comm); }'`
- [ ] `cat /proc/interrupts` 看 local timer interrupts 的增长速率 ≈ HZ

---

## 6. 第五站：CFS 调度器——公平性的艺术（5~7 天）★最重

**目标**：完整吃透 CFS。这是现代 Linux 调度的主体，面试和工作都绕不开。

### 精读清单（按"记账→入队→选择→抢占→tick"顺序）

- [ ] 设计哲学：`vruntime` 虚拟运行时间——CPU 时间的"公平货币"；阅读 [Documentation/scheduler/sched-design-CFS.rst](linux-6.6.161/Documentation/scheduler/sched-design-CFS.rst)，了解它为什么取代了 O(1) 调度器
- [ ] 数据结构：`sched_entity` / `cfs_rq`（[sched.h](linux-6.6.161/kernel/sched/sched.h)）；`min_vruntime` 的意义
- [ ] 记账 [fair.c:1201](linux-6.6.161/kernel/sched/fair.c#L1201) `update_curr()`：`vruntime += delta_exec × (NICE_0_LOAD / weight)`——**vruntime 是加权时间**；`calc_delta_fair()` 的逆运算
- [ ] 权重表：`sched_prio_to_weight[]` 数组（[core.c](linux-6.6.161/kernel/sched/core.c)），nice 0 = 1024，nice ±1 约 ±10%；`NICE_0_LOAD` 与 `inv_weight`（除法变乘法）
- [ ] 入队 [fair.c:6750](linux-6.6.161/kernel/sched/fair.c#L6750) `enqueue_task_fair()`：`place_entity()`（**睡眠醒来/新进程的 vruntime 补偿**）→ 插入红黑树 → `update_cfs_group`
- [ ] 选择 [fair.c:8433](linux-6.6.161/kernel/sched/fair.c#L8433) `pick_next_task_fair()` → `pick_eevdf()`（[fair.c:975](linux-6.6.161/kernel/sched/fair.c#L975)）：在按 vruntime 排序的红黑树上选**合格的（vlag≥0）且 deadline 最早**的实体。⚠️ **6.6 起是 EEVDF 调度器，不是传统 CFS**——旧教材"取最左节点"的说法已过时；`se->deadline/min_deadline/vlag/slice` 就是 EEVDF 字段（[sched.h:551](linux-6.6.161/include/linux/sched.h#L551) 的 sched_entity 注释里有导读）
- [ ] 唤醒抢占 [fair.c:8323](linux-6.6.161/kernel/sched/fair.c#L8323) `check_preempt_wakeup_fair()`：`sysctl_sched_wakeup_granularity`，vruntime 差多少才允许抢占
- [ ] tick 侧 [fair.c:12707](linux-6.6.161/kernel/sched/fair.c#L12707) `task_tick_fair()` → `check_preempt_tick()`：当前进程"理想时间片"用完就置位 NEED_RESCHED
- [ ] 参数面：`/proc/sys/kernel/sched_latency_ns`（调度周期）、`sched_min_granularity_ns`（最小时间片）、`sched_wakeup_granularity_ns`，理解三者关系
- [ ] PELT 负载跟踪（进阶必读）：[pelt.c](linux-6.6.161/kernel/sched/pelt.c) 的指数衰减公式（半衰期 32ms），`load_avg`（用于负载均衡）与 `util_avg`（用于 EAS/调频）的区别；阅读 [Documentation/scheduler/sched-pelt.rst](linux-6.6.161/Documentation/scheduler/sched-pelt.rst)
- [ ] 组调度（进阶）：`task_group`、cgroup v2 的 `cpu.weight`、autogroup；`update_cfs_group` 的层级记账

### 带着这些问题读

1. 为什么用红黑树而不是最小堆？（提示：EEVDF 下这棵树身兼两职——按 vruntime 排序 + 用 min_deadline 增强字段当按 deadline 的堆）
2. 睡眠醒来的进程 vruntime 如何补偿？为什么补偿后它通常能"插队"（交互性从哪来）？
3. `fork` 出的子进程 vruntime 从谁继承？继承 `min_vruntime` 和继承父进程各有什么问题？
4. nice 0 和 nice 19 的两个死循环进程，CPU 占比是多少？（权重 1024 : 15，不是 1:1！）
5. 为什么 PELT 用指数衰减而不是滑动窗口？（O(1) 更新）
6. 内核为什么需要 `rq_clock`（[clock.c](linux-6.6.161/kernel/sched/clock.c)）而不是直接用 jiffies？（精度与 nohz）

### 动手验证

- [ ] 两个死循环（一个 `nice 19`），`top` 观察 CPU 占比 ≈ 1024:15；`/proc/sched_debug` 里对比两者 vruntime 增长速度
- [ ] `perf sched record -- sleep 5 && perf sched latency` 看平均延迟；`perf sched map` 可视化切换
- [ ] 修改（实验内核）`sysctl_sched_min_granularity_ns` 观察响应变化
- [ ] bpftrace 打印 `sched_switch` 时 prev/next 的 `se.vruntime`：`bpftrace -e 't:sched:sched_switch { printf("%d vs %d\n", args.prev_task->se.vruntime, args.next_task->se.vruntime); }'`

---

## 7. 第六站：实时调度——确定性优先（2~3 天）

**目标**：理解 RT/DL 与 CFS 的根本区别：**实时 = 可预测的时限，不是"更快"**。

### 精读清单

- [ ] [rt.c](linux-6.6.161/kernel/sched/rt.c)：SCHED_FIFO / SCHED_RR，优先级 0~99，用位图找最高优先级（`cpupri.c`），同优先级链表轮转；RT 限流（`sched_rt_period_us` / `sched_rt_runtime_us`，防 RT 饿死 CFS）
- [ ] [deadline.c](linux-6.6.161/kernel/sched/deadline.c)：EDF（最早截止期优先）+ CBS（Constant Bandwidth Server）；三个参数 `runtime / deadline / period`，准入控制（`sched_setattr` 失败条件）；阅读 [Documentation/scheduler/sched-deadline.rst](linux-6.6.161/Documentation/scheduler/sched-deadline.rst)
- [ ] [stop_task.c](linux-6.6.161/kernel/sched/stop_task.c)：stop 类——最高优先级的"停机任务"（CPU 热插拔、内核隔离迁移用）
- [ ] 优先级反转与 PI：[kernel/locking/rtmutex.c](linux-6.6.161/kernel/locking/rtmutex.c) 的优先级继承；理解反转三要素（高/中/低优先级 + 锁）
- [ ] 多核 RT 的 push/pull 迁移（rt.c 中的 `push_rt_task` / `pull_rt_task`，进阶）

### 带着这些问题读

1. SCHED_RR 和 SCHED_FIFO 的唯一区别是什么？RR 的"时间片"由谁决定？
2. 为什么 DL 的 CBS 需要准入控制，而 FIFO/RR 不需要？
3. RT 限流默认 `rt_runtime=0.95s / rt_period=1s`，为什么内核宁可让 RT 限流也要保住 5% 给 CFS？
4. 优先级继承为什么只对 RT 锁有意义（PI 链）？

### 动手验证

- [ ] `chrt -f 99 yes > /dev/null &`，观察系统卡顿 → 再验证限流：把 `sched_rt_runtime_us` 调小，观察 CPU 占用被压到 95%
- [ ] `chrt -d --sched-runtime 10000000 --sched-deadline 50000000 --sched-period 100000000 0 yes > /dev/null &` 用 DL 跑一个"10ms/50ms"的周期任务
- [ ] `cat /proc/sched_debug | grep -A5 dl_rq` 观察 DL 记账

---

## 8. 第七站：多核与负载均衡（3~4 天）

**目标**：单 CPU 调度懂了，看多核——"每 CPU 一队列"带来的代价与补偿。

### 精读清单

- [ ] 调度域拓扑：[topology.c](linux-6.6.161/kernel/sched/topology.c) `struct sched_domain` / `sched_group`，层级 SMT → MC → DIE → NUMA；`build_sched_domains()` 怎么从 CPU 拓扑构建（x86 侧在 [arch/x86/kernel/smpboot.c](linux-6.6.161/arch/x86/kernel/smpboot.c) 提供 `cpu_coregroup_mask` 等回调）
- [ ] 均衡时机：**idle balance**（CPU 空闲主动找活，`newidle_balance`）、**periodic balance**（`rebalance_domains` 周期触发）、**active balance**（失败后把任务"推"走）；都在 [fair.c](linux-6.6.161/kernel/sched/fair.c) 的 `load_balance()` / `find_busiest_group()` / `detach_tasks()`
- [ ] 唤醒选核：[fair.c](linux-6.6.161/kernel/sched/fair.c) `select_task_rq_fair()` / `wake_affine()`：睡眠唤醒倾向回原 CPU（cache 热）还是去 idle CPU（快响应）的权衡
- [ ] NUMA 考量：跨 node 迁移代价、`numa_balancing`（[fair.c](linux-6.6.161/kernel/sched/fair.c) 里 CONFIG_NUMA_BALANCING 部分，进阶）
- [ ] EAS 能效调度（进阶）：[Documentation/scheduler/sched-energy.rst](linux-6.6.161/Documentation/scheduler/sched-energy.rst)，`select_task_rq_fair` 里的 `find_energy_efficient_cpu()`；与 schedutil 调频（[cpufreq_schedutil.c](linux-6.6.161/kernel/sched/cpufreq_schedutil.c)）联动

### 带着这些问题读

1. 为什么唤醒进程时"选哪个 CPU"（`select_task_rq`）也要交给调度类实现？CFS 和 RT 的选核逻辑为什么不同？
2. 负载均衡的"负载"用的是什么指标（PELT load_avg）？为什么不直接数 `nr_running`？
3. 为什么均衡要分 idle / periodic / active 三种，只用一种会怎样？
4. `taskset` 把进程绑核后，均衡器还会迁移它吗？

### 动手验证

- [ ] `taskset -c 0 yes > /dev/null &` + 单核死循环，观察其它核的 idle 进程与均衡行为（`mpstat -P ALL 1`）
- [ ] `/proc/schedstat` 的 domain 字段对照 `load_balance` 统计；`perf probe` 或 bpftrace 数 `load_balance` 调用次数
- [ ] 对照 [Documentation/admin-guide/cgroup-v2.rst](linux-6.6.161/Documentation/admin-guide/cgroup-v2.rst) 的 cpu 控制器做一次 cgroup 权重实验

---

## 9. 第八站：进程生命周期全景——fork / exec / exit（2~3 天）

**目标**：把"调度"放回"进程的一生"里看，串起主线二的另外两块。

### 精读清单

- [ ] [kernel/fork.c](linux-6.6.161/kernel/fork.c) `copy_process()`：`sched_fork()`（子进程 vruntime 初始化、`__state = TASK_NEW`）→ 复制完 → `wake_up_new_task()`（**首次入队**：`check_preempt_wakeup` 让子进程可能先于父进程跑——`fork` 后父子谁先跑不确定）
- [ ] [kernel/exec.c](linux-6.6.161/kernel/exec.c) `do_execve()` 与调度的关系（exec 不创建新进程，只换镜像；`comm` 何时更新）
- [ ] [kernel/exit.c:818](linux-6.6.161/kernel/exit.c#L818) `do_exit()`：置 `EXIT_ZOMBIE` → 调 `schedule()` **且永不返回**（最后一次调度切换）；僵尸进程由父进程 `wait` 收割（[kernel/exit.c](linux-6.6.161/kernel/exit.c) `wait_task_zombie`）；孤儿进程 reparent 到 init
- [ ] 内核线程：`kthreadd` → `kthread_create()`（[kernel/kthread.c](linux-6.6.161/kernel/kthread.c)），与用户进程的区别（`mm == NULL`、不能有用户栈）

### 带着这些问题读

1. 为什么 `fork` 出的子进程不直接运行，而是先入队等调度？（TASK_NEW 状态的作用）
2. `do_exit()` 里调 `schedule()` 之后为什么代码不会继续执行？"最后一次切换"切换给了谁？
3. 僵尸进程占内存吗？`ZOMBIE` 状态保留了什么？
4. 内核线程为什么必须有 `kthreadd` 这种"造线程的线程"？

### 动手验证

- [ ] 写模块挂 `fork` 计数（或用 bpftrace `t:sched:sched_process_fork`），跑 `make -j` 观察
- [ ] `sleep 100 &` 然后 `kill` 它，`ps` 看到 `<defunct>` 僵尸态，读 `/proc/PID/status` 的 State 字段对照 `__state` 值

---

## 10. 第九站：综合验证与输出（2~3 天）

**目标**：把知识固化成"能讲出来、能画出来、能查出来"。

### 毕业考核清单（全部能答上 = 通关）

- [ ] 不看代码默写完整调用链：tick → `scheduler_tick` → 置 `TIF_NEED_RESCHED` → 返回用户态检查 → `schedule` → `__schedule` → `pick_next_task` → `context_switch` → `switch_mm` + `__switch_to` → `__switch_to_asm`
- [ ] 能画出 `sched_class` 接口表并说明 CFS 每项实现的位置
- [ ] 能解释：vruntime 为什么公平？nice 如何影响权重？唤醒抢占的条件？
- [ ] 能解释：`preempt_count` 各位段含义；用户态/内核态抢占差异
- [ ] 能解释：RT 限流为什么必要；DL 的 CBS 三个参数
- [ ] 能解释：负载均衡三种时机；NUMA 下为什么迁移要谨慎
- [ ] `perf sched` 全家桶会用；bpftrace 能写 sched_* 观测脚本

### 输出物

- [ ] 笔记三篇（存入 `学习笔记/`，延续现有编号 `02-sched-*.md`）：
      1. `02-sched-框架`：sched_class / rq / 优先级体系 / schedule() 主路径
      2. `03-sched-CFS`：vruntime 记账、红黑树、唤醒抢占、PELT
      3. `04-sched-上下文切换`：__schedule → __switch_to 汇编级详解 + 栈切换图
- [ ] 一张全景图（用 draw.io / excalidraw）：调度触发时机 × 调度主路径 × 各调度类
- [ ] 对照总路线《Linux内核学习路线.md》主线二，勾选完成项

### 可选进阶方向（主线完成后按兴趣挑）

- [ ] sched_ext：可扩展调度器（6.12 合入，6.6 没有；了解 BPF 调度器的思想）
- [ ] PREEMPT_RT：实时抢占补丁的架构思路
- [ ] EAS + schedutil 能效调度的完整链路
- [ ] `core_sched` / SMT 侧信道隔离

---

## 11. 参考资源

### 内核文档（优先读官方）

- [Documentation/scheduler/](linux-6.6.161/Documentation/scheduler/)：`sched-design-CFS.rst`、`sched-pelt.rst`、`sched-deadline.rst`、`sched-energy.rst`、`schedutil.rst`
- [Documentation/admin-guide/cgroup-v2.rst](linux-6.6.161/Documentation/admin-guide/cgroup-v2.rst)（cpu 控制器）
- [Documentation/scheduler/completion.rst](linux-6.6.161/Documentation/scheduler/completion.rst)（等待机制）

### 书籍

- 《Linux 内核设计与实现》(LKD) 第 4 章——最好的入门地图
- 《深入理解 Linux 内核》(ULK) 第 7 章——老但讲清了调度器演进史（O(1) → CFS 对比）
- 《Linux 内核深度解析》第 3 章（余华兵）——对 4.x 内核，流程图多，适合对照
- 《奔跑吧 Linux 内核》——实验性强

### 工具与在线资源

- [Bootlin Elixir（6.6.161）](https://elixir.bootlin.com/linux/v6.6.161/source)——看"谁调用了它"（referenced by）
- `perf sched` / `ftrace` / `bpftrace` / `trace-cmd`——验证理解的金钥匙
- `/proc/sched_debug` / `/proc/schedstat` / `/proc/sys/kernel/sched_*`——零成本的观测窗口

---

## 12. 学习方法建议（重要）

1. **带着问题读**：每站先看"带着这些问题读"再翻代码，读完后能用一句话答出每个问题才算过。
2. **只走 x86 路径**：架构相关代码只看 `arch/x86/`，其它架构跳过（思路相同，寄存器不同）。
3. **先主线后支线**：`fair.c` 有 12000+ 行，但主线只有 5 个函数（update_curr / enqueue / pick / check_preempt / task_tick）；第一次通读跳过 `CONFIG_*` 统计分支（CFS_BANDWIDTH、NUMA_BALANCING、GROUP_SCHED 可后补）。
4. **每站一图**：读完画一张调用链/结构图——画不出来就是没懂。
5. **实验环境优先于进度**：宁可慢一点，也要在 QEMU 里把 `perf sched`、`/proc/sched_debug` 跑起来；"只看不跑容易忘"。
6. **笔记进 `学习笔记/`**：沿用现有 `01-arch-*` 的编号风格，每篇开头写明"本节回答什么问题"。
