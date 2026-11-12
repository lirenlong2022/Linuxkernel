# 第二节：sched.h —— 进程描述符与调度核心头文件

> 源码版本：Linux 6.6.161（`include/linux/sched.h`，共 2605 行）
> 本节回答四个问题：
> ① sched.h 里到底有什么，重点在哪几个区？
> ② task_struct 的哪些成员是"调度核心"，必须吃透？
> ③ 进程状态、优先级、调度实体这三套"调度前置知识"怎么编码在 sched.h 里？
> ④ 一个 task_struct 描述的是"进程"还是"线程"？pid/tgid 是什么关系？
>
> 对应总路线《[Linux进程调度学习路线.md](../Linux进程调度学习路线.md)》第 2 节"**第一站：进程是什么——task_struct**"

---

## 0. 一句话定位

**sched.h 是内核最核心的头文件之一**：它定义 `struct task_struct`（进程描述符），并对外声明调度器的主 API（`schedule()`、唤醒族、`cond_resched()`、CPU 亲和等）。它的文件头注释就一句话：

```c
/*
 * Define 'struct task_struct' and provide the main scheduler
 * APIs (schedule(), wakeup variants, etc.)
 */
```

([sched.h:5-8](../linux-6.6.161/include/linux/sched.h#L5-L8))

> ⚠️ 注意区分两个 sched.h：
>
> - [include/linux/sched.h](../linux-6.6.161/include/linux/sched.h) —— **对全内核公开**的接口（本文档对象）
> - [kernel/sched/sched.h](../linux-6.6.161/kernel/sched/sched.h) —— **调度器内部私有**头文件（`struct rq`、`struct sched_class`、`cfs_rq` 都在那里，第二站再学）

---

## 1. sched.h 文件结构全景（2605 行分区地图）

读任何大文件先画分区图，sched.h 可分 13 个区：

| #  | 行号                                                           | 分区                               | 一句话                                                                                                                             |
| -- | -------------------------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 1  | [1-71](../linux-6.6.161/include/linux/sched.h#L1-L71)           | 头文件与前置声明                   | 包含 `<uapi/linux/sched.h>`、`<asm/current.h>`、`<linux/sched/prio.h>` 等；**`current` 宏就从 `asm/current.h` 来** |
| 2  | [73-141](../linux-6.6.161/include/linux/sched.h#L73-L141)       | **任务状态位掩码**           | `TASK_RUNNING`/`__TASK_STOPPED`/`EXIT_ZOMBIE` 等（重点区 ①）                                                                |
| 3  | [174-284](../linux-6.6.161/include/linux/sched.h#L174-L284)     | **set_current_state() 家族** | 改状态的唯一正规途径 + 内存屏障语义（重点区 ②）                                                                                   |
| 4  | [286-313](../linux-6.6.161/include/linux/sched.h#L286-L313)     | 调度主 API 声明                    | `schedule()` / `schedule_timeout()` / `io_schedule()` / `scheduler_tick()`                                                 |
| 5  | [315-395](../linux-6.6.161/include/linux/sched.h#L315-L395)     | 记账小结构                         | `sched_param` / `sched_info` / `prev_cputime`                                                                                |
| 6  | [397-507](../linux-6.6.161/include/linux/sched.h#L397-L507)     | 负载基础结构                       | 定点数约定（shift=10）、`load_weight`、**PELT 的 `sched_avg`**                                                           |
| 7  | [551-746](../linux-6.6.161/include/linux/sched.h#L551-L746)     | **三个调度实体**             | `sched_entity`(EEVDF) / `sched_rt_entity` / `sched_dl_entity`（重点区 ③）                                                   |
| 8  | [811-1688](../linux-6.6.161/include/linux/sched.h#L811-L1688)   | **`struct task_struct`**   | 本节主角，878 行（重点区 ④）                                                                                                      |
| 9  | [1690-1854](../linux-6.6.161/include/linux/sched.h#L1690-L1854) | PID 访问器                         | `task_pid_nr()` / `task_tgid_nr()` / `pid_alive()` / 状态→字符 `"RSDTtXZPI"`                                              |
| 10 | [1861-1994](../linux-6.6.161/include/linux/sched.h#L1861-L1994) | **PF_\* / PFA_\* 标志**      | 每任务标志位（`PF_KTHREAD` 等）                                                                                                  |
| 11 | [1996-2088](../linux-6.6.161/include/linux/sched.h#L1996-L2088) | 亲和与优先级 API                   | `set_cpus_allowed_ptr()` / `set_user_nice()` / `sched_setscheduler()`                                                        |
| 12 | [2089-2167](../linux-6.6.161/include/linux/sched.h#L2089-L2167) | 内核栈与查找/唤醒                  | `thread_union`、`find_task_by_vpid()`、**`wake_up_process()`**                                                         |
| 13 | [2169-2605](../linux-6.6.161/include/linux/sched.h#L2169-L2605) | 抢占与杂项                         | **`TIF_NEED_RESCHED` 操作、`cond_resched()`、`need_resched()`**、`task_cpu()`、rseq                                  |

---

## 2. 重点区 ①：进程状态机 —— `__state` 位掩码

### 2.1 为什么用位组合而不是枚举值？

这是学习路线第一站的问题 1。答案在源码注释里就写着：**两套独立标志（`__state` 管"可运行性"，`exit_state` 管"退出中"），位掩码保证改一套不会误伤另一套**（[sched.h:73-82](../linux-6.6.161/include/linux/sched.h#L73-L82)）。更深层的原因有三个：

1. **状态可以叠加**：`TASK_KILLABLE = TASK_UNINTERRUPTIBLE | TASK_WAKEKILL`（D 态 + 可被致命信号杀死）——枚举表达不了这种组合；
2. **唤醒检查是位测试**：`wake_up_state(p, state)` 用 `p->__state & state` 判断是否匹配，掩码就是天然参数；
3. **单一整型原子读写**：`WRITE_ONCE`/`READ_ONCE` 一条指令完成，不会撕裂。

### 2.2 状态位全表（[sched.h:84-128](../linux-6.6.161/include/linux/sched.h#L84-L128)）

**主状态（`__state`，互斥语义）：**

| 宏                       | 值    | 含义                                                                                 | 用户态表现 |
| ------------------------ | ----- | ------------------------------------------------------------------------------------ | ---------- |
| `TASK_RUNNING`         | 0x000 | **可运行**（在 CPU 上跑，或在 rq 里等 CPU）                                    | R          |
| `TASK_INTERRUPTIBLE`   | 0x001 | 睡眠，**可被信号唤醒**                                                         | S          |
| `TASK_UNINTERRUPTIBLE` | 0x002 | 睡眠，**不可被信号唤醒**（等 IO/锁，`kill -9` 无效）（上面三个都是普通状态） | D          |
| `__TASK_STOPPED`       | 0x004 | 停止（SIGSTOP/ptrace 挂起）                                                          | T          |
| `__TASK_TRACED`        | 0x008 | 被 ptrace 跟踪暂停                                                                   | t          |
| `TASK_PARKED`          | 0x040 | kthread 暂停（`kthread_park`，热插拔用）                                           | P          |
| `TASK_DEAD`            | 0x080 | 最后一次调度前：`do_exit()` 里 `schedule()` **永不返回**                   | X          |
| `TASK_NEW`             | 0x800 | fork 后、`wake_up_new_task()` 首次入队前                                           | —         |

**辅助位（与主状态组合使用）：**

| 宏                                   | 值              | 含义                                                   |
| ------------------------------------ | --------------- | ------------------------------------------------------ |
| `TASK_WAKEKILL`                    | 0x100           | 睡 D 态时仍可被**致命**信号唤醒（构成 KILLABLE） |
| `TASK_WAKING`                      | 0x200           | 正在被唤醒的瞬间（`ttwu` 中间态，防止重复唤醒）      |
| `TASK_NOLOAD`                      | 0x400           | 不记入系统负载（`TASK_IDLE` 的组成）                 |
| `TASK_FREEZABLE` / `TASK_FROZEN` | 0x2000 / 0x8000 | 休眠/冻结（cgroup freezer）                            |

**`exit_state` 专属（退出位）：** `EXIT_DEAD = 0x10`、`EXIT_ZOMBIE = 0x20`（[sched.h:91-92](../linux-6.6.161/include/linux/sched.h#L91-L92)）

**常用组合宏：**

```c
#define TASK_KILLABLE   (TASK_WAKEKILL | TASK_UNINTERRUPTIBLE)   // 可被杀死的 D 态
#define TASK_STOPPED    (TASK_WAKEKILL | __TASK_STOPPED)          // 真正的 T 态
#define TASK_IDLE       (TASK_UNINTERRUPTIBLE | TASK_NOLOAD)      // idle 线程
#define TASK_NORMAL     (TASK_INTERRUPTIBLE | TASK_UNINTERRUPTIBLE) // wake_up() 的默认掩码
```

### 2.3 状态机简图

```
                     fork (TASK_NEW) → wake_up_new_task()
                              │
                              ▼
  ┌──────────────┐   schedule()   ┌────────────────────┐
  │ 可运行 RUNNING │◄────被选中────│ 就绪（在 rq 中等待）│
  └──────┬───────┘               └─────────▲──────────┘
         │ 等待事件 set_current_state(S)     │ 事件到来 try_to_wake_up()
         ▼                                 │
  ┌──────────────────┐                    │
  │ INTERRUPTIBLE (S) │─────信号(SIGKILL 除外按掩码)──────┘
  │ UNINTERRUPTIBLE(D)│─────事件到来──────┘
  └──────────────────┘
         │ 收到 STOP/TRACE                    do_exit() → EXIT_ZOMBIE ──wait()──▶ EXIT_DEAD
         ▼                                              (schedule() 永不返回，TASK_DEAD)
   STOPPED / TRACED
```

`/proc` 里的状态字符由 [task_state_to_char()](../linux-6.6.161/include/linux/sched.h#L1837-L1840) 映射，字符表是 `"RSDTtXZPI"`（[sched.h:1830](../linux-6.6.161/include/linux/sched.h#L1830)）。

### 2.4 set_current_state()：改状态必须走的路（重点区 ②）

直接 `p->__state = x` 是**禁止**的。三个入口（[sched.h:211-237](../linux-6.6.161/include/linux/sched.h#L211-L237)）：

| 宏                         | 实现                                                  | 何时用                                           |
| -------------------------- | ----------------------------------------------------- | ------------------------------------------------ |
| `__set_current_state(s)` | `WRITE_ONCE(current->__state, s)`，**无屏障** | 条件检查与唤醒在同一把锁下，无需额外同步         |
| `set_current_state(s)`   | `smp_store_mb(...)`，**带完整内存屏障**       | 通用场景：保证"写状态"先于"检查条件"被唤醒方看到 |
| `set_special_state(s)`   | `pi_lock` 保护下写入                                | STOPPED/TRACED 等不走常规 wait-loop 的特殊状态   |

**为什么要内存屏障？** 看经典睡眠模式（注释原文 [sched.h:174-209](../linux-6.6.161/include/linux/sched.h#L174-L209)）：

```c
for (;;) {
    set_current_state(TASK_UNINTERRUPTIBLE);
    if (CONDITION)          // ① 检查条件
        break;
    schedule();             // ② 真的睡
}
__set_current_state(TASK_RUNNING);
```

唤醒侧是 `CONDITION = 1; wake_up_state(p, ...)`（`try_to_wake_up()` 访问 `p->__state` 前执行**完整屏障**）。屏障保证：唤醒者要么看到 `TASK_UNINTERRUPTIBLE`（正常走唤醒路径），要么条件已满足（睡着的循环多转一圈，`CONDITION` 检查兜底）——**两种情况都不会丢唤醒**。即使 `TASK_RUNNING` 的写入与状态写入发生碰撞，代价也只是多转一圈循环，注释里明确说明这是安全的。

---

## 3. 重点区 ③ 前置：优先级体系 0~139

> 三个 prio 字段和 `rt_priority` 在 task_struct 里（[sched.h:876-883](../linux-6.6.161/include/linux/sched.h#L876-L883)），但数值定义在 [include/linux/sched/prio.h](../linux-6.6.161/include/linux/sched/prio.h)（被 sched.h 第 28 行包含）。

### 3.1 一把统一的尺子

```
数值范围 0 ───────────── 99 ─────────────── 139
          RT 实时任务          CFS 普通任务
          (数字越小优先级越高 ← 统一方向)

nice 体系（用户视角）      rt_priority 体系（用户视角）
   -20 最急 … 0 … +19 最不急    0 最低 … 99 最高（方向相反！）
        ↓ NICE_TO_PRIO = nice+120        ↓ normal_prio = 99 - rt_priority
   static_prio 100~139        ──┐
        ↓ normal_prio（CFS）    │
        └────────┬──────────────┘
                 ↓ 统一到 normal_prio（0~139，方向统一：小=高）
                 ↓ effective_prio()：若发生优先级继承(PI)被提升，则取更小值
                 ↓
               p->prio（有效优先级，调度器真正使用）
```

常量（[prio.h](../linux-6.6.161/include/linux/sched/prio.h)）：

| 宏                  | 值       | 含义                          |
| ------------------- | -------- | ----------------------------- |
| `MAX_RT_PRIO`     | 100      | RT 区间上界（RT 优先级 0~99） |
| `MAX_PRIO`        | 140      | 总优先级数 0~139              |
| `NICE_WIDTH`      | 40       | nice 档数（-20~+19）          |
| `DEFAULT_PRIO`    | 120      | nice 0 的静态优先级           |
| `NICE_TO_PRIO(n)` | nice+120 | nice → static_prio           |

### 3.2 三个 prio 字段各管什么（学习路线问题 2）

| 字段            | 谁写                                                                             | 语义                                                                                                            |
| --------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `static_prio` | `set_user_nice()`（[core.c:7212](../linux-6.6.161/kernel/sched/core.c#L7212)）  | 用户通过 nice 设定的"出厂值"，仅 CFS 有意义，进程运行中不变                                                     |
| `normal_prio` | 每次策略变更时算                                                                 | **统一标尺**：CFS 任务 = `static_prio`；RT 任务 = `99 - rt_priority`；DL 任务 = -1（比谁都高）        |
| `prio`        | `effective_prio()`（[core.c:2188](../linux-6.6.161/kernel/sched/core.c#L2188)） | **有效优先级**：平时 = `normal_prio`；发生 RT 优先级继承时被临时提升为等待者的值。调度器/位图用的都是它 |

**为什么需要三个？**（学习路线问题 4 的答案）

- nice 和 rt_priority 是**两套方向相反、互不相干的用户接口**（nice 越小越急，rt_priority 越大越急），内核无法直接比大小，必须先归一化 → 这就是 `normal_prio` 存在的意义；
- `static_prio` 独立于 `normal_prio`，是因为**优先级继承**是临时的：PI 解除后要能回到"本来面目"，不能把提升后的值写回静态值；
- `prio` 独立于 `normal_prio`，同样是因为 PI 的临时提升不该污染"正常值"。

---

## 4. 重点区 ③：三个调度实体

task_struct 里嵌着三个实体（[sched.h:886-888](../linux-6.6.161/include/linux/sched.h#L886-L888)）：`se` / `rt` / `dl`。**一个任务同时只有其中一个被使用**（由 `sched_class` 决定），但字段上都占用空间——这是"以空间换简单"的设计。

### 4.1 `struct sched_entity` —— CFS 实体，6.6 起是 EEVDF（[sched.h:551-613](../linux-6.6.161/include/linux/sched.h#L551-L613)）

> ⚠️ 最重要的更新：**6.6 的 CFS 类已换成 EEVDF（最早合格虚拟截止期优先）**，不是传统教材的"取红黑树最左节点"。结构体上的导读注释（[sched.h:551-560](../linux-6.6.161/include/linux/sched.h#L551-L560)）三句话：
>
> - `vruntime` 决定**合格资格**：`vlag = avg_vruntime - vruntime >= 0` 才有资格被选；
> - `deadline` 决定**谁先跑**：合格实体中 deadline 最早者上 CPU；
> - 红黑树仍按 vruntime 排序，`min_deadline` 增强字段让它**兼作按 deadline 的堆**。

**重点成员：**

| 成员                  | 行号                                                       | 作用                                                                                                                    |
| --------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `load`              | [563](../linux-6.6.161/include/linux/sched.h#L563)          | 调度权重（nice → `sched_prio_to_weight[]` 折算，nice0=1024）；EEVDF 时间片与负载均衡都靠它                           |
| `run_node`          | [567](../linux-6.6.161/include/linux/sched.h#L567)          | 红黑树节点（按 vruntime 排序）                                                                                          |
| `deadline`          | [568](../linux-6.6.161/include/linux/sched.h#L568)          | 虚拟截止期（≈ vruntime + 本轮时间片折算），EEVDF 的"EDF"部分                                                           |
| `min_deadline`      | [570](../linux-6.6.161/include/linux/sched.h#L570)          | **子树增强字段**：子树内最早 deadline，使红黑树兼任按 deadline 的堆                                               |
| `on_rq`             | [575](../linux-6.6.161/include/linux/sched.h#L575)          | 是否在队列上（组调度下是递归语义）                                                                                      |
| `exec_start`        | [578](../linux-6.6.161/include/linux/sched.h#L578)          | 本次上 CPU 的时刻（`update_curr()` 用它算 `delta_exec`）                                                            |
| `sum_exec_runtime`  | [579](../linux-6.6.161/include/linux/sched.h#L579)          | 累计真实 CPU 时间（`/proc/PID/sched` 可见）                                                                           |
| `vruntime`          | [581](../linux-6.6.161/include/linux/sched.h#L581)          | **虚拟运行时间 = 加权后的 CPU 时间**（`delta_exec × 1024/权重`），公平性的核心标尺                             |
| `vlag`              | [583](../linux-6.6.161/include/linux/sched.h#L583)          | 虚拟滞后量 = `avg_vruntime - vruntime`；≥0 才有资格；新唤醒/新 fork 的"补偿"体现在这里                               |
| `slice`             | [586](../linux-6.6.161/include/linux/sched.h#L586)          | 本轮请求的时间片（基准 `sysctl_sched_base_slice` 按权重缩放）                                                         |
| `avg`               | [610](../linux-6.6.161/include/linux/sched.h#L610)          | **PELT** 负载跟踪（`struct sched_avg`，32ms 半衰期指数衰减；`load_avg` 用于均衡、`util_avg` 用于 EAS/调频） |
| `cfs_rq` / `my_q` | [596-598](../linux-6.6.161/include/linux/sched.h#L596-L598) | 组调度层级：本实体所在的队列 / 本实体（组）拥有的队列                                                                   |

PELT 数据结构本体在 [sched_avg:497-507](../linux-6.6.161/include/linux/sched.h#L497-L507)；权重结构 `load_weight` 在 [411](../linux-6.6.161/include/linux/sched.h#L411)；定点数约定（`SCHED_FIXEDPOINT_SHIFT = 10`）在 [404](../linux-6.6.161/include/linux/sched.h#L404)。

### 4.2 `struct sched_rt_entity` —— RT 实体（[sched.h:615-648](../linux-6.6.161/include/linux/sched.h#L615-L648)）

与 CFS 完全不同：**严格优先级调度，每个优先级一条链表 + 位图快速定位最高非空优先级**，高优先级永远先跑。

| 成员                    | 行号                                                       | 作用                                                                             |
| ----------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `run_list`            | [624](../linux-6.6.161/include/linux/sched.h#L624)          | 挂在 `rt_rq->active.queue[prio]` 的链表节点（同优先级 FIFO 排队）              |
| `time_slice`          | [632](../linux-6.6.161/include/linux/sched.h#L632)          | **SCHED_RR 时间片剩余**（每 tick 减 1，归零排到链尾触发重调度；FIFO 不用） |
| `timeout`             | [629](../linux-6.6.161/include/linux/sched.h#L629)          | RLIMIT_RTTIME 记账（实时任务 CPU 时间上限）                                      |
| `on_rq` / `on_list` | [636-637](../linux-6.6.161/include/linux/sched.h#L636-L637) | 在队列上 / 挂在链表上（组限流摘链时两者不同步）                                  |

### 4.3 `struct sched_dl_entity` —— Deadline 实体（[sched.h:650-746](../linux-6.6.161/include/linux/sched.h#L650-L746)）

**EDF（最早截止期优先）+ CBS（恒定带宽服务器）**：用户声明"每周期最多跑 runtime，必须在 deadline 前完成"，内核按绝对截止期排队 + 预算制限流，保证一个任务永远吃不饱也饿不死。这是 Linux 最强的 CPU 隔离机制。

| 成员                                             | 行号                                                       | 作用                                                                        |
| ------------------------------------------------ | ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| `rb_node`                                      | [664](../linux-6.6.161/include/linux/sched.h#L664)          | dl_rq 红黑树节点：**按绝对 deadline 排序，取最左**（真正的 EDF）      |
| `dl_runtime` / `dl_deadline` / `dl_period` | [673-675](../linux-6.6.161/include/linux/sched.h#L673-L675) | 用户声明参数（设置后不变）：每周期最多运行时间 / 相对截止期 / 周期          |
| `dl_bw`                                        | [676](../linux-6.6.161/include/linux/sched.h#L676)          | 带宽 = runtime/period，**准入控制**依据（所有 DL 任务总和 ≤ CPU 数） |
| `runtime`                                      | [686](../linux-6.6.161/include/linux/sched.h#L686)          | 本实例**剩余**预算（每 tick 扣减，可为负 = 超支）                     |
| `deadline`                                     | [687](../linux-6.6.161/include/linux/sched.h#L687)          | 本实例**绝对**截止期（新周期 = now + dl_deadline）                    |
| `dl_throttled`                                 | [712](../linux-6.6.161/include/linux/sched.h#L712)          | 限流中：预算耗尽，等 `dl_timer` 补时                                      |
| `dl_timer`                                     | [723](../linux-6.6.161/include/linux/sched.h#L723)          | **补时定时器**（CBS 预算恢复的核心）                                  |
| `inactive_timer`                               | [733](../linux-6.6.161/include/linux/sched.h#L733)          | 0-lag 优化：任务提前睡眠后，到"零滞后时刻"才把它从活跃利用率中剔除          |

---

## 5. 重点区 ④：task_struct 重点成员（811-1688）

### 5.0 先懂布局：三个"结构上"的讲究

**① `thread_info` 必须是第一个成员**（[sched.h:820-830](../linux-6.6.161/include/linux/sched.h#L820-L830)）

6.6 起 `thread_info` 已并入 task_struct（`CONFIG_THREAD_INFO_IN_TASK`，x86 标配）。第一个成员的位置约束来自 `current` 的实现：

- **历史设计**（老教材讲的）：task_struct 放在内核栈底，`current = sp & ~(THREAD_SIZE-1)` 直接从栈指针算出；
- **6.6 x86 现状**：`current` 走 **per-CPU 变量 `pcpu_hot.current_task`**（[arch/x86/include/asm/current.h](../linux-6.6.161/arch/x86/include/asm/current.h) 的 `get_current()`），由 `__switch_to` 在切换时更新，不再依赖栈指针掩码。栈与 task_struct 也已分离（`CONFIG_VMAP_STACK` 下 `stack_vm_area` 记录栈的 vmalloc 映射，[sched.h:1600-1602](../linux-6.6.161/include/linux/sched.h#L1600-L1602)）。

⚠️ 这就是学习路线问题 3 的答案，也是**常见误解修正点**："task_struct 在内核栈底"是 2.6/3.x 时代的布局，别拿它解释 6.6 的 `current`。

**② 随机化区**（[sched.h:840-844](../linux-6.6.161/include/linux/sched.h#L840-L844) 与 [1672-1676](../linux-6.6.161/include/linux/sched.h#L1672-L1676)）

`randomized_struct_fields_start/end` 之间所有字段会被 **randstruct 插件（KASLR 加固）打乱顺序**——防止攻击者靠已知偏移伪造 `cred` 等指针。调度关键字段（`thread_info`、`__state`）刻意放在标记之前，保持位置稳定。**新字段应加在 end 标记之前**（注释明确要求）。

**③ `thread` 必须放最后**（[sched.h:1680-1687](../linux-6.6.161/include/linux/sched.h#L1680-L1687)）

`thread_struct`（架构线程状态：内核栈 sp、fsbase、浮点/AVX 状态）内含**变长结构**，必须位于结构体末尾，注释加了三重警告。

### 5.1 重点成员分类总表（按"调度相关性"排序）

#### A 类：调度核心（必须背下来的）

| 成员                                                           | 行号                                                       | 说明                                                                                         |
| -------------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `__state`                                                    | [835](../linux-6.6.161/include/linux/sched.h#L835)          | 任务状态位掩码（第 2 节）                                                                    |
| `on_rq`                                                      | [874](../linux-6.6.161/include/linux/sched.h#L874)          | 是否在运行队列上（由调度器维护，与 `se.on_rq` 语义不同）                                   |
| `prio` / `static_prio` / `normal_prio` / `rt_priority` | [880-883](../linux-6.6.161/include/linux/sched.h#L880-L883) | 优先级四件套（第 3 节）                                                                      |
| `se` / `rt` / `dl`                                       | [886-888](../linux-6.6.161/include/linux/sched.h#L886-L888) | 三个调度实体（第 4 节）                                                                      |
| `sched_class`                                                | [889](../linux-6.6.161/include/linux/sched.h#L889)          | **所属调度类指针**（stop/dl/rt/fair/idle）——调度器"面向对象多态"的核心，第二站的主角 |
| `policy`                                                     | [926](../linux-6.6.161/include/linux/sched.h#L926)          | 调度策略：`SCHED_NORMAL/BATCH/IDLE/FIFO/RR/DEADLINE`（策略→类的映射）                     |
| `on_cpu`                                                     | [857](../linux-6.6.161/include/linux/sched.h#L857)          | 正在哪个 CPU 上运行（-1 = 未运行），SMP 调度核心状态                                         |
| `stats`                                                      | [914](../linux-6.6.161/include/linux/sched.h#L914)          | 调度统计（`/proc/PID/sched` 的来源）                                                       |
| `wake_entry`                                                 | [858](../linux-6.6.161/include/linux/sched.h#L858)          | 跨 CPU 唤醒链表节点（挂到目标 rq 的 wakelist）                                               |
| `sched_task_group`                                           | [898](../linux-6.6.161/include/linux/sched.h#L898)          | 所属 task_group（cgroup 组调度 `cpu.weight` 的载体）                                       |

#### B 类：身份与组织

| 成员                               | 行号                                                           | 说明                                                                                                                                                        |
| ---------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pid`                            | [1075](../linux-6.6.161/include/linux/sched.h#L1075)            | **内核任务 ID**（用户态 `gettid()`）；**内核调度的基本单位是任务，不是进程**                                                                  |
| `tgid`                           | [1076](../linux-6.6.161/include/linux/sched.h#L1076)            | **线程组 ID**（用户态 `getpid()`），同组线程共享                                                                                                    |
| `thread_pid`                     | [1112](../linux-6.6.161/include/linux/sched.h#L1112)            | 指向 `struct pid`（支持 PID 命名空间/引用计数；`pid_alive()` 就是判它非空）                                                                             |
| `pid_links[]`                    | [1113](../linux-6.6.161/include/linux/sched.h#L1113)            | PID/PGID/SID 三种类型的哈希链节点（按 pid 查任务）                                                                                                          |
| `comm[TASK_COMM_LEN]`            | [1190](../linux-6.6.161/include/linux/sched.h#L1190)            | 程序名，**最多 16 字节**（[TASK_COMM_LEN=16, sched.h:290-292](../linux-6.6.161/include/linux/sched.h#L290-L292)）；必须用 `get/set_task_comm()` 访问 |
| `tasks`                          | [967](../linux-6.6.161/include/linux/sched.h#L967)              | **全局任务链表节点**（`init_task.tasks` 为头；`ps`、`for_each_process` 遍历的就是它）                                                           |
| `thread_group` / `thread_node` | [1114-1115](../linux-6.6.161/include/linux/sched.h#L1114-L1115) | 线程组链表（头/节点，组长持有）                                                                                                                             |
| `group_leader`                   | [1100](../linux-6.6.161/include/linux/sched.h#L1100)            | 线程组组长（tgid 对应任务）                                                                                                                                 |
| `real_parent` / `parent`       | [1090-1093](../linux-6.6.161/include/linux/sched.h#L1090-L1093) | 真实父进程 / 逻辑父进程（被 ptrace 时 `parent` 是调试器，收 SIGCHLD 的对象）                                                                              |
| `children` / `sibling`         | [1098-1099](../linux-6.6.161/include/linux/sched.h#L1098-L1099) | 子进程链表头 / 兄弟链表节点                                                                                                                                 |
| `flags`                          | [853](../linux-6.6.161/include/linux/sched.h#L853)              | PF_\* 标志（见下）                                                                                                                                          |
| `ptrace`                         | [854](../linux-6.6.161/include/linux/sched.h#L854)              | 被 ptrace 跟踪状态                                                                                                                                          |

**重点 PF_\* 标志**（[sched.h:1861-1893](../linux-6.6.161/include/linux/sched.h#L1861-L1893)）：`PF_KTHREAD`(0x200000, 内核线程)、`PF_IDLE`(idle 线程)、`PF_EXITING`(退出中)、`PF_WQ_WORKER`/`PF_IO_WORKER`(workqueue/io_uring worker)、`PF_FORKNOEXEC`(fork 后未 exec)、`PF_RANDOMIZE`(ASLR)、`PF_NO_SETAFFINITY`(禁止改亲和)。

#### C 类：地址空间与生命周期

| 成员                            | 行号                                                           | 说明                                                                                                                  |
| ------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `mm`                          | [977](../linux-6.6.161/include/linux/sched.h#L977)              | 用户地址空间（页表/vma 树）。**内核线程为 NULL**——没有用户地址空间                                            |
| `active_mm`                   | [978](../linux-6.6.161/include/linux/sched.h#L978)              | 实际使用的地址空间：内核线程**借用**上一个任务的 mm，省去刷 TLB（`switch_mm` 里 `mm==NULL` 不换页表的原因） |
| `exit_state`                  | [981](../linux-6.6.161/include/linux/sched.h#L981)              | 退出状态（EXIT_ZOMBIE/EXIT_DEAD，与 `__state` 分开的两套位）                                                        |
| `exit_code` / `exit_signal` | [982-983](../linux-6.6.161/include/linux/sched.h#L982-L983)     | 退出码（父进程 wait 取回）/ 退出时发给父进程的信号                                                                    |
| `stack`                       | [850](../linux-6.6.161/include/linux/sched.h#L850)              | 内核栈基址（THREAD_SIZE 对齐）                                                                                        |
| `usage`                       | [851](../linux-6.6.161/include/linux/sched.h#L851)              | task_struct 引用计数（`get/put_task_struct`，归零才释放）                                                           |
| `rcu` / `rcu_users`         | [1593-1594](../linux-6.6.161/include/linux/sched.h#L1593-L1594) | **RCU 延迟释放头 + RCU 引用计数**——task_struct 最终经 RCU 释放（读者无锁遍历的前提）                          |
| `stack_refcount`              | [1605](../linux-6.6.161/include/linux/sched.h#L1605)            | 栈引用计数（栈可先于 task_struct 释放）                                                                               |

#### D 类：时间记账与切换计数

| 成员                      | 行号                                                           | 说明                                                       |
| ------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------- |
| `utime` / `stime`     | [1129-1130](../linux-6.6.161/include/linux/sched.h#L1129-L1130) | 用户态 / 内核态 CPU 时间（`/proc/PID/stat` 第 14/15 项） |
| `nvcsw`                 | [1145](../linux-6.6.161/include/linux/sched.h#L1145)            | **自愿上下文切换**（主动睡眠：read 阻塞等）          |
| `nivcsw`                | [1146](../linux-6.6.161/include/linux/sched.h#L1146)            | **非自愿上下文切换**（时间片耗尽 / 被抢占）          |
| `start_time`            | [1149](../linux-6.6.161/include/linux/sched.h#L1149)            | 进程启动时刻（`ps -o etime` 来源）                       |
| `min_flt` / `maj_flt` | [1155-1156](../linux-6.6.161/include/linux/sched.h#L1155-L1156) | 次缺页（无 IO）/ 主缺页（需读盘）                          |

#### E 类：信号、文件与凭据

| 成员                     | 行号                                                           | 说明                                                            |
| ------------------------ | -------------------------------------------------------------- | --------------------------------------------------------------- |
| `signal`               | [1219](../linux-6.6.161/include/linux/sched.h#L1219)            | 线程组共享的信号信息（挂起队列、rlimit、统计）                  |
| `sighand`              | [1220](../linux-6.6.161/include/linux/sched.h#L1220)            | 信号处理器表（sigaction，线程组共享，RCU 保护）                 |
| `blocked`              | [1221](../linux-6.6.161/include/linux/sched.h#L1221)            | 阻塞信号集（**线程私有**）                                |
| `pending`              | [1225](../linux-6.6.161/include/linux/sched.h#L1225)            | 待处理信号队列（线程私有；共享的在 `signal->shared_pending`） |
| `fs`                   | [1204](../linux-6.6.161/include/linux/sched.h#L1204)            | 根目录/当前目录/umask（线程组共享）                             |
| `files`                | [1207](../linux-6.6.161/include/linux/sched.h#L1207)            | 打开文件表 fd → struct file（`/proc/PID/fd`）                |
| `nsproxy`              | [1215](../linux-6.6.161/include/linux/sched.h#L1215)            | 命名空间集合（mount/net/pid/uts/ipc/user…）                    |
| `real_cred` / `cred` | [1172-1175](../linux-6.6.161/include/linux/sched.h#L1172-L1175) | 真实证书 / 有效证书（setuid 后两者不同；COW 共享）              |
| `jobctl`               | [987](../linux-6.6.161/include/linux/sched.h#L987)              | 作业控制位（`task_is_stopped` 判断的就是它 + `__state`）    |

#### F 类：锁与优先级继承（PI）

| 成员              | 行号                                                | 说明                                                                   |
| ----------------- | --------------------------------------------------- | ---------------------------------------------------------------------- |
| `pi_lock`       | [1251](../linux-6.6.161/include/linux/sched.h#L1251) | PI 数据结构锁（rt_mutex 优先级继承相关；`set_special_state` 也用它） |
| `pi_waiters`    | [1257](../linux-6.6.161/include/linux/sched.h#L1257) | 等待本任务持有的 rt_mutex 的任务集合（按优先级排序的红黑树）           |
| `pi_top_task`   | [1259](../linux-6.6.161/include/linux/sched.h#L1259) | 等待者中优先级最高者（决定本任务被提升到多高）                         |
| `pi_blocked_on` | [1261](../linux-6.6.161/include/linux/sched.h#L1261) | 本任务阻塞在哪个 rt_mutex 上（死锁检测 + PI 提升链）                   |
| `alloc_lock`    | [1248](../linux-6.6.161/include/linux/sched.h#L1248) | 保护 mm/files/fs 等共享指针的修改                                      |
| `wake_q`        | [1253](../linux-6.6.161/include/linux/sched.h#L1253) | 延迟唤醒队列节点（`wake_q_add` 攒批、离开锁后统一唤醒）              |

> 其余 500 多行成员（NUMA 策略、cgroup、futex、perf、rseq、审计、KASAN/kcov 等调试设施）大多是 `CONFIG_*` 可选功能，第一遍通读**不必逐字段**，知道"什么功能挂什么字段"即可。

---

## 6. 常用 API 速查（sched.h 后半部分）

| API                                     | 行号                                                                                                      | 作用                                                                   |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `schedule()`                          | [303](../linux-6.6.161/include/linux/sched.h#L303)                                                         | 主调度入口（第三站主线）                                               |
| `schedule_timeout()`                  | [298](../linux-6.6.161/include/linux/sched.h#L298)                                                         | 睡到超时（`MAX_SCHEDULE_TIMEOUT = LONG_MAX` = 永久睡眠）             |
| `io_schedule()`                       | [313](../linux-6.6.161/include/linux/sched.h#L313)                                                         | 等 IO 的睡眠（计入 iowait）                                            |
| `wake_up_process(p)`                  | [2131](../linux-6.6.161/include/linux/sched.h#L2131)                                                       | 唤醒指定任务（`try_to_wake_up` 的包装）                              |
| `wake_up_state(p, state)`             | [2130](../linux-6.6.161/include/linux/sched.h#L2130)                                                       | 按状态掩码唤醒                                                         |
| `wake_up_new_task(p)`                 | [2132](../linux-6.6.161/include/linux/sched.h#L2132)                                                       | **新 fork 任务首次入队**（第九站）                               |
| `cond_resched()`                      | [2269](../linux-6.6.161/include/linux/sched.h#L2269)                                                       | 显式调度点（voluntary preemption；PREEMPT_DYNAMIC 下行为随启动参数变） |
| `need_resched()`                      | [2393](../linux-6.6.161/include/linux/sched.h#L2393)                                                       | 检查 `TIF_NEED_RESCHED`（调度触发时机的主角）                        |
| `set_tsk_need_resched(p)`             | [2204](../linux-6.6.161/include/linux/sched.h#L2204)                                                       | 给任务置 NEED_RESCHED（tick 里调用）                                   |
| `set_cpus_allowed_ptr()`              | [2012](../linux-6.6.161/include/linux/sched.h#L2012)                                                       | 修改 CPU 亲和（`taskset` 的落点）                                    |
| `set_user_nice()` / `task_nice()`   | [2046](../linux-6.6.161/include/linux/sched.h#L2046) / [2055](../linux-6.6.161/include/linux/sched.h#L2055) | 改/查 nice 值                                                          |
| `sched_setscheduler()`                | [2064](../linux-6.6.161/include/linux/sched.h#L2064)                                                       | 改调度策略与参数（`chrt` 的落点）                                    |
| `find_task_by_vpid()`                 | [2122](../linux-6.6.161/include/linux/sched.h#L2122)                                                       | 按用户态 PID 找任务（PID 哈希表）                                      |
| `curr_task(cpu)` / `idle_task(cpu)` | [2084](../linux-6.6.161/include/linux/sched.h#L2084) / [2071](../linux-6.6.161/include/linux/sched.h#L2071) | 各 CPU 的当前任务 / idle 任务                                          |
| `task_cpu(p)`                         | [2403](../linux-6.6.161/include/linux/sched.h#L2403)                                                       | 任务所在 CPU（读 `thread_info.cpu`）                                 |

---

## 7. 四个问题的答案汇总（第一站过关自测）

| 问题                                      | 一句话答案                                                                                                                                                                                                              |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. 为什么 `__state` 用位组合？          | 状态可叠加（KILLABLE = D\|WAKEKILL）、唤醒用掩码匹配、整型原子读写；且与 `exit_state` 分两套位，互不误伤                                                                                                              |
| 2. 为什么有 static/normal/prio 三个字段？ | `static_prio` 存用户 nice 的"出厂值"；`normal_prio` 是把 nice 与 rt_priority 两套方向相反的体系**归一化**后的统一标尺；`prio` 是含**优先级继承临时提升**的有效值——三者各司其职，PI 解除后能恢复原状 |
| 3. task_struct 与内核栈/current 的关系？  | 传统布局是 task_struct 在栈底、`current` 用 `sp & ~(THREAD_SIZE-1)`；**6.6 x86 已改为 per-CPU `pcpu_hot.current_task` + THREAD_INFO_IN_TASK + VMAP_STACK**（栈与 task_struct 分离）                         |
| 4. nice 与 rt_priority 怎么统一？         | `normal_prio`：CFS = `nice+120`（100~139），RT = `99-rt_priority`（0~99），统一成"0~139 数值越小越优先"的同一把尺子                                                                                               |

---

## 8. 动手验证（对照 /proc 与 ps）

- [ ] `ps -eLo pid,tid,tgid,stat,pri,ni,comm` —— 找一个多线程进程（如 systemd），验证：`pid`（任务 ID）各不相同、`tgid` 相同、`pri` 与 `ni` 差 120、S/D/R/T 状态字母与 2.2 表对应
- [ ] `cat /proc/PID/stat` —— 对照 `utime`/`stime`（第 14/15 项）、`nvcsw`/`nivcsw`（第 38/39 项左右）、`start_time`
- [ ] `cat /proc/PID/sched` —— 对照 `se.sum_exec_runtime`、`se.vruntime`、`policy`、`prio`
- [ ] `ps -ef` 找一个内核线程（`[]` 括起来的，如 `[kworker/0:0]`）：它的 PF_KTHREAD 置位、`mm == NULL`——这就是它**没有用户地址空间**的体现
- [ ] 写内核模块：从 `init_task` 出发 `for_each_process()` 遍历，打印 `comm/pid/tgid/__state/prio/policy`，对照 `ps -eo` 输出

---

## 9. 一句话总结与下一步

**sched.h = 一张"任务"的完整户口本：`__state` 说它现在在干什么（位掩码状态机），`prio` 四件套说它多着急（统一到 0~139 的尺子），`se/rt/dl + sched_class` 说它归哪类调度器管（策略与机制的接口），`mm/fs/files/signal` 说它拥有什么资源（线程组共享 vs 线程私有）。**

下一步进入**第二站**：把 `sched_class` 指针当接口表，去 [kernel/sched/sched.h](../linux-6.6.161/kernel/sched/sched.h) 看 `struct sched_class` 与 `struct rq`——那时你会发现：本节背的每个调度字段，都是"谁在什么队列上、以什么优先级"这道题的输入。
