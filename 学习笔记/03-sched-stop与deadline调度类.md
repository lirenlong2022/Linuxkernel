# 第三节：stop 与 deadline 调度类 —— 系统里优先级最高的两个"贵族"

> 源码版本：Linux 6.6.161（`kernel/sched/stop_task.c` 131 行 + `kernel/sched/deadline.c` 约 3000 行）
> 本节回答八个问题：
> ① stop 类为什么**没有队列**？`rq->stop` 单指针是怎么来的？
> ② `struct sched_dl_entity` 的字段怎么分区？三个用户参数 + 两个动态账本 + 四个状态位分别是什么？
> ③ DL 的 CBS 规则是什么？`dl_throttled`（限流）的完整生命周期是怎样的？
> ④ `enqueue_task_dl` 的三条路径（两个特殊分支 + 正常路径）各处理什么？
> ⑤ 出队为什么三行就够？`dequeue_task_dl` 凭什么简单？
> ⑥ 运行期四连——抢占（`wakeup_preempt_dl`/`resched_curr`）、选人（`pick_next_task_dl` 与"让位下一类"）、上台（`set_next_task_dl`）、切类（`switched_to/from_dl`）——各做什么？
> ⑦ PI（优先级继承）是怎么影响 DL 调度的？`pi_se` / `is_dl_boosted` 是什么？
> ⑧ 约束 deadline 任务的"死区窗口"补丁 `dl_check_constrained_dl` 在防什么？
>
> 对应总路线《[Linux进程调度学习路线.md](../Linux进程调度学习路线.md)》第 3 节"**第二站：调度器框架——sched_class 与 rq**"与第 7 节"**第六站：实时调度——确定性优先**"

---

## 0. 一句话定位

内核有五个调度类，按优先级从高到低：

```
stop  >  dl  >  rt  >  fair  >  idle
(迁移/停机) (SCHED_DEADLINE) (FIFO/RR) (CFS) (每CPU空闲任务)
```

- **stop**：每 CPU 一个特殊任务（migration/N、stop_machine 线程），优先级最高、**永不被抢占**，没有队列，只有一个指针。
- **dl**：用户态可申请 `SCHED_DEADLINE`，用 **EDF**（最早 deadline 优先）选任务、用 **CBS**（Constant Bandwidth Server）管预算——是本节的主角。

本节先读 stop（结构最简单、最好建立"类回调"的直觉），再攻 dl（实体字段 + 调度逻辑 + 两个硬骨头：限流与 PI 提升）。

---

## 1. 调度类框架回顾（读类之前先懂"类"）

调度类是**函数指针表**：[`struct sched_class`](../linux-6.6.161/kernel/sched/sched.h#L2247) 定义在调度器私有头文件里，定义了 `enqueue_task` / `dequeue_task` / `pick_next_task` / `put_prev_task` / `set_next_task` 等一批回调。

两个关键机制：

1. **[`DEFINE_SCHED_CLASS(name)`](../linux-6.6.161/kernel/sched/sched.h#L2333) 宏**：把实例放进独立的链接器 section，链接脚本按优先级**逆序**排布（宏注释里特别强调 *CAREFUL*）；
2. **[`for_each_class`](../linux-6.6.161/kernel/sched/sched.h#L2345)**：从高到低遍历五个类，`pick_next_task` 就是"问 stop 有没有任务 → 没有问 dl → 没有问 rt → …"。

回调的通用契约（对读任何类都适用）：

| 回调 | 时机 | 语义 |
|---|---|---|
| `enqueue_task` | 任务变为可运行 | 放进本类的队列/账目 |
| `dequeue_task` | 任务变为不可运行 | 从队列/账目移除 |
| `pick_next_task` | 需要选下一个任务 | 选出并做好上台准备 |
| `put_prev_task` | 当前任务下台 | 结算本次执行 |
| `set_next_task` | 新任务上台 | 记录执行起点 |

---

## 2. stop 类：没有队列的最高特权

### 2.1 stop 任务是什么、住在哪

每个 CPU 有一个 stop 任务（CPU 热插拔/stop_machine 用它执行特殊工作）。它由 [`sched_set_stop_task()`](../linux-6.6.161/kernel/sched/core.c#L3661) 设置，核心就一行：

```c
cpu_rq(cpu)->stop = stop;   // core.c:3695 —— 直接写指针,没有入队动作
```

在 [`struct rq`](../linux-6.6.161/kernel/sched/sched.h#L963) 里，stop 任务与 `curr`、`idle` 并列，是**一个单指针**：

```c
struct task_struct __rcu	*curr;   // sched.h:1017
struct task_struct		*idle;   // sched.h:1018
struct task_struct		*stop;   // sched.h:1019 ← 注意:不是队列!
```

### 2.2 为什么没有队列：`struct rq` 是"每 CPU 总运行队列"

关键认知：**`rq` 不是某个调度类的队列，而是每 CPU 一个的总运行队列**，各调度类把自己的子队列**嵌**在里面：

```c
struct cfs_rq		cfs;   // sched.h:999  CFS 红黑树
struct rt_rq		rt;    // sched.h:1000  RT 优先级队列
struct dl_rq		dl;    // sched.h:1001  DL EDF 红黑树
struct task_struct	*stop; // sched.h:1019  stop 无队列,只有指针
```

stop 类每 CPU **至多一个任务**，且永不被抢占——无队可排，所以不需要队列结构。

### 2.3 enqueue / dequeue：只维护计数器

[`enqueue_task_stop`](../linux-6.6.161/kernel/sched/stop_task.c#L55-L58) 与 [`dequeue_task_stop`](../linux-6.6.161/kernel/sched/stop_task.c#L60-L64) 各只有一行：

```c
add_nr_running(rq, 1);   // enqueue:nr_running++
sub_nr_running(rq, 1);   // dequeue:nr_running--
```

[`add_nr_running`](../linux-6.6.161/kernel/sched/sched.h#L2498-L2515) 除了改 `rq->nr_running`（[sched.h:971](../linux-6.6.161/kernel/sched/sched.h#L971)，每 CPU 可运行任务总数，负载均衡/统计用），还顺带处理 tracepoint 和 `rd->overload` 过载标记。

真正让任务"可见/不可见"的是通用框架在类回调**前后**置的 `on_rq` 标志：

```c
// core.c:2143-2145  activate_task()
enqueue_task(rq, p, flags);            // → 分派到 enqueue_task_stop
p->on_rq = TASK_ON_RQ_QUEUED;          // 之后才置位
```

"stop 任务已入队"的判断函数是 [`sched_stop_runnable`](../linux-6.6.161/kernel/sched/sched.h#L2356-L2359)：

```c
return rq->stop && task_on_rq_queued(rq->stop);
```

它被三处消费——这就是 enqueue/dequeue 计数器的全部意义：

| 消费者 | 作用 |
|---|---|
| [`pick_task_stop`](../linux-6.6.161/kernel/sched/stop_task.c#L36-L42) | 在队才返回 `rq->stop`，否则 NULL 让位给下一类 |
| [`balance_stop`](../linux-6.6.161/kernel/sched/stop_task.c#L18-L22) | 告诉负载均衡器本 CPU 是否"忙" |
| rt.c:1706、deadline.c:1986 | **RT/DL 选任务前先查它**——stop 在队则一个任务都不敢选 |

### 2.4 记账链条：`set_next_task` → `put_prev_task`

`se.exec_start` 是所有调度类共用的"本次运行起点"记账字段。stop 类上台时 [set_next_task_stop](../linux-6.6.161/kernel/sched/stop_task.c#L31-L34) 记起点：

```c
stop->se.exec_start = rq_clock_task(rq);   // 任务时钟:扣除中断时间的纯执行时钟
```

下台时 [put_prev_task_stop](../linux-6.6.161/kernel/sched/stop_task.c#L71-L74) 调 `update_curr_common(rq)` 结算：`delta = now - exec_start` 累进 `sum_exec_runtime`（[fair.c:1153-1173](../linux-6.6.161/kernel/sched/fair.c#L1153-L1173)）。**上台记起点、下台结账**，缺了上台这一行，下台就会算出虚假执行时间。

> RT 的 `set_next_task_rt` 第一行做的也是同一件事（[rt.c:1743](../linux-6.6.161/kernel/sched/rt.c#L1743)）——`exec_start` 是跨类通用字段。

### 2.5 stop 类成员速查表（[stop_task.c:106-160](../linux-6.6.161/kernel/sched/stop_task.c#L106-L160)）

| 回调 | 行为 |
|---|---|
| enqueue/dequeue | 只维护 `nr_running` |
| yield_task | `BUG()`——stop 让出 CPU 毫无意义 |
| wakeup_preempt | 空——永不被抢占 |
| pick_next_task | 在队返回 `rq->stop` + 记 exec_start |
| put_prev_task | 结算执行时间 |
| set_next_task | 记 exec_start；`first` 参数忽略 |
| balance (SMP) | 返回"本 CPU 是否忙" |
| pick_task (SMP) | core scheduling 专用：只选不设 |
| select_task_rq (SMP) | 返回 `task_cpu(p)`——永不迁移 |
| set_cpus_allowed (SMP) | 公共实现，亲和性被限制在原 CPU |
| task_tick | 空——无时间片/带宽检查 |
| prio_changed / switched_to | `BUG()`——stop 优先级固定、用户态不可能切进来 |
| update_curr | 空——结算已在 put_prev 完成 |

---

## 3. DL 调度实体：`struct sched_dl_entity` 字段地图

定义在 [include/linux/sched.h:551-760](../linux-6.6.161/include/linux/sched.h#L551-L760) 区（`task_struct` 通过内嵌 `dl` 成员持有）。字段分五组：

| 组 | 字段 | 含义 |
|---|---|---|
| **① 用户声明的参数**（静态） | `dl_runtime` / `dl_deadline` / `dl_period` | 每个周期最多执行 / 相对截止期 / 周期长度（`sched_setattr` 传入） |
| | `dl_bw` / `dl_density` | 带宽 `runtime/period` / 密度 `runtime/deadline`（准入检查用） |
| **② 运行账本**（动态） | `runtime` | **本实例剩余预算**，每次执行结算扣减，可为负（超支） |
| | `deadline` | 本实例**绝对**截止期，补给时推进 |
| | `flags` | `SCHED_FLAG_RECLAIM`（可回收别人未用带宽）、`SCHED_FLAG_DL_OVERRUN`（超支发 SIGXCPU） |
| **③ 状态位**（[sched.h:744-749](../linux-6.6.161/include/linux/sched.h#L744-L749)） | `dl_throttled` | **限流中**：预算耗尽，等补给 |
| | `dl_yielded` | 主动让出过 CPU |
| | `dl_non_contending` | 睡着但仍计入活跃利用率（0-lag 优化） |
| | `dl_overrun` | 请求了超支通知 |
| **④ 定时器** | `dl_timer` | **补给定时器**，到期补预算（throttle 的救星） |
| | `inactive_timer` | 0-lag 带宽回收定时器 |
| **⑤ PI 提升凭证** | `pi_se` | 指向"当前使用谁的参数"的实体（第 7 节详解） |

**区分两组"参数"**：`dl_runtime/dl_deadline/dl_period` 是用户写的**合同**，`runtime/deadline` 是运行时**账本**——前者永不变，后者每时每刻在变。

---

## 4. CBS 规则与限流生命周期

### 4.1 两条规则

DL 任务签的合同是 `(runtime, deadline, period)`，内核用 CBS 保证两条：

1. **帧内**：每个实例的 `runtime` 必须在 `deadline` 之前用完（用完即限流）；
2. **帧间（带宽隔离）**：任意长度为 `period` 的窗口内，执行不超过 `runtime`——保证该任务最多占 `runtime/period` 的 CPU 比例。

### 4.2 `dl_throttled` 完整生命周期

以 `runtime=10ms, period=deadline=100ms`（10% 带宽）为例：

```
t=0       周期开始,runtime=10ms
t=0~10ms  运行,[update_curr_dl] 每 tick 扣 runtime
t=10ms    runtime=0 → dl_throttled=1,摘出红黑树,补给定时器定在 t=100
t=10~100  任务 on_rq、可被唤醒,但不在树里 → pick 不到 → 拿不到 CPU
t=100     dl_task_timer 触发 → 补给:runtime=10,deadline=200 → 重新入队
```

**触发点** [`update_curr_dl`](../linux-6.6.161/kernel/sched/deadline.c#L1304-L1394)：

```c
delta_exec = update_curr_common(rq);          // now - exec_start
// 按频率/容量缩放(或按 GRUB-PA 回收带宽计算)
dl_se->runtime -= scaled_delta_exec;          // 扣预算

if (dl_runtime_exceeded(dl_se) || dl_se->dl_yielded) {
    dl_se->dl_throttled = 1;                  // ① 限流
    __dequeue_task_dl(rq, curr, 0);           // ② 摘出红黑树
    start_dl_timer(curr);                     // ③ 武装补给定时器
}
```

**恢复点** [`dl_task_timer`](../linux-6.6.161/kernel/sched/deadline.c#L1106) → [`replenish_dl_entity`](../linux-6.6.161/kernel/sched/deadline.c#L833-L879)：

```c
while (dl_se->runtime <= 0) {                // 超支大时跳多个周期
    dl_se->deadline += dl_period;            // deadline 推进
    dl_se->runtime  += dl_runtime;           // 补满预算
}
dl_se->dl_throttled = 0;                     // 解除限流
```

**限流 ≠ 睡眠**：任务仍是 `TASK_RUNNING`、仍 `on_rq`，只是调度器故意不给它 CPU——这正是带宽隔离的实现方式。对比 RT 的 `rt_throttled`（组级、整个 rt_rq 一起限流），DL 是**任务级**、每人独立账本和独立定时器。

---

## 5. DL 入队：`enqueue_task_dl` 的三条路径

总览（[enqueue_task_dl](../linux-6.6.161/kernel/sched/deadline.c#L1726)）：

```
enqueue_task_dl()
├─ 分支一:PI 提升中(is_dl_boosted)
│   └─ 同时被 throttle → 取消补给定时器、清 throttle(提升优先于限流)
├─ 分支二:非 DL 任务即将降回原类
│   └─ 清 throttle 后直接 return(不值得补给)
└─ 正常路径:
    ① wait_start 统计起点
    ② 迁移中 → 补 ENQUEUE_MIGRATING 标志
    ③ enqueue_dl_entity(核心,见下)
    ④ 非当前 && 未限流 && 可迁移 → 入 pushable 队列
```

### 5.1 正常路径第 ③ 步:`enqueue_dl_entity`([deadline.c:1628](../linux-6.6.161/kernel/sched/deadline.c#L1628))

```
a. constrained deadline 检查(第 8 节的死区窗口补丁)
b. RESTORE/MIGRATING → add_rq_bw + add_running_bw(带宽账目登记到新 rq)
c. throttled 且非补给 → task_contending(活跃利用率记账)后 return,不进树
   └─ 已武装的补给定时器到期后会带 ENQUEUE_REPLENISH 再来,那时才插树
d. 按 flags 更新参数(三选一):
   · ENQUEUE_WAKEUP    → update_dl_entity:新实例(推进 period、补满 runtime)
   · ENQUEUE_REPLENISH → replenish_dl_entity:补给
   · RESTORE 且 deadline 已过 → setup_new_dl_entity:重置
e. __enqueue_dl_entity → 插入 EDF 红黑树
```

**插树本身** [`__enqueue_dl_entity`](../linux-6.6.161/kernel/sched/deadline.c#L1599-L1608)：

```c
rb_add_cached(&dl_se->rb_node, &dl_rq->root, __dl_less);  // EDF 顺序
inc_dl_tasks(dl_se, dl_rq);   // 连锁更新四个账目:
// dl_nr_running++ / rq->nr_running++ / 更新 earliest_dl / 登记 rd->cpudl 堆
```

`__dl_less`（[deadline.c:1518](../linux-6.6.161/kernel/sched/deadline.c#L1518)）就是 EDF 的比较函数：**deadline 越早越靠左**。`pick_next_task_dl` 取最左节点即可。

### 5.2 第 ④ 步:两棵树的分工

| 树 | 存什么 | 谁用 |
|---|---|---|
| `rq->dl.root`（EDF 主树） | 所有可运行 DL 任务 | `pick_next_task_dl` 选人 |
| `rq->dl.pushable_dl_tasks_root` | 可迁移、未限流、非当前的任务 | `push_dl_task`/`pull_dl_task` 找"最早 deadline 且推得走"的任务 |

入队同时维护**两棵树**、**两组带宽账目**（rq 级 `this_bw` + running 级 `running_bw`）和**全局 cpudl 堆**——这就是 DL 类比 stop 类复杂的原因：DL 任务要参与多 CPU 间 deadline 感知的迁移。

### 5.3 为什么"入队 ≠ 进树"

三张对照表记牢：

| 入队时状态 | 路径 |
|---|---|
| throttled 且非补给 | 不进树，只做账目修正（`task_contending`），等已武装的定时器 |
| throttled 且 `ENQUEUE_REPLENISH` | 补给 + 插树（复活） |
| 未 throttled | 正常更新参数 + 插树 |

限流任务被唤醒时，它醒了、想跑（"active contending"），活跃利用率必须计入账目（否则其他 RECLAIM 任务会错误地回收它的带宽）——但没预算就不能进树。这与 stop 类"入队只加计数器"是同一思路的 DL 版本。

### 5.4 出队为什么简单:[`dequeue_task_dl`](../linux-6.6.161/kernel/sched/deadline.c#L1817)

就三行:

```c
static void dequeue_task_dl(struct rq *rq, struct task_struct *p, int flags)
{
	update_curr_dl(rq);                   // ① 先结算:预算扣光会当场限流
	if (p->on_rq == TASK_ON_RQ_MIGRATING) // ② 迁移场景补标志
		flags |= DEQUEUE_MIGRATING;
	__dequeue_task_dl(rq, p, flags);      // ③ 真正的摘除
}
```

真正的摘除 [`__dequeue_task_dl`](../linux-6.6.161/kernel/sched/deadline.c#L1808) 也不长,关键就几处:

```c
if (RB_EMPTY_NODE(&dl_se->rb_node))
	return;                     // 本来就不在 EDF 树里(限流中) → 无事可做
...
rb_erase_cached(...);           // 摘树
dec_dl_tasks(dl_se, dl_rq);     // 与 inc_dl_tasks 对称的四个账目
...
if (flags & DEQUEUE_SLEEP)
	task_non_contending(dl_se); // 睡着 → 0-lag:带宽先记账,回收交给 inactive_timer
```

**为什么比入队简单**——三个原因:

1. **幂等设计**:`RB_EMPTY_NODE` 一查,不在树上直接返回。限流任务本就"on_rq 但不在树"(§5.3),出队自然无事可做——所有复杂度在入队时已经"分流"过了;
2. **限流任务留在 pushable 树**:出队不动它,真正删除任务(退出/迁移)时才由 `dl_task_offline_migration` 统一清理;
3. **复杂活推给定时器**:`DEQUEUE_SLEEP` 只把任务标成 `dl_non_contending`(0-lag),带宽账目先不动,回收交给 `inactive_timer` 到期再做。

**入队/出队的信息不对称**:入队要回答"三种状态(正常/限流/补给)各走哪条路",出队只需回答"在不在树里"——一个 if 就完了。

---

## 6. 运行期:抢占、选人与上台

### 6.1 抢占:[`wakeup_preempt_dl`](../linux-6.6.161/kernel/sched/deadline.c#L1994) 与"预约"语义

```c
if (dl_entity_preempt(&p->dl, &rq->curr->dl)) {
	resched_curr(rq);   // 只是"预约"切换,不是切换本身
	return;
}
```

- [`dl_entity_preempt`](../linux-6.6.161/kernel/sched/sched.h#L266-L271):被唤醒者 p 是 SUGOV 调速实体,或 p 的 deadline **早于**当前任务 → 该抢。deadline 相同不互相抢(EDF 下它们同时限,谁先跑完都一样);
- [`resched_curr`](../linux-6.6.161/kernel/sched/core.c#L1055-L1077):本地置 `TIF_NEED_RESCHED`,远程发 IPI——**只预约,不换人**。真正的切换发生在当前任务走到内核路径尽头的调度点、进入 `__schedule` 时。

**谁决定调这个回调**:通用 [`wakeup_preempt`](../linux-6.6.161/kernel/sched/core.c#L2232-L2245)——同类任务问本类的 `wakeup_preempt` 回调;更高类任务出现(如 rt 醒来、curr 是 dl)直接 `resched_curr`,连回调都不问。

### 6.2 选人:[`pick_next_task_dl`](../linux-6.6.161/kernel/sched/deadline.c#L2109) 与"让位下一类"协议

选人 = 取 EDF 红黑树**最左节点**(deadline 最早)。[`pick_task_dl`](../linux-6.6.161/kernel/sched/deadline.c#L2084) 只做"树空 → NULL,否则取最左";`pick_next_task_dl` 在它外面再包一层:

```c
p = pick_task_dl(rq);
if (p)
	set_next_task_dl(rq, p, true);   // 选中的同时做上台准备
return p;                            // NULL 原样返回 → 让位
```

**"返回 NULL 让位下一类"在哪实现**:不在 DL 类里,而在框架层 [`__pick_next_task`](../linux-6.6.161/kernel/sched/core.c#L6003-L6041):

```c
for_each_class(class) {              // stop → dl → rt → fair → idle
	p = class->pick_next_task(rq);
	if (p)
		return p;                    // 本类有人 → 到此为止
}
BUG();                               // idle 类永远有任务,走不到这
```

类回调的返回值本质是个**布尔答案**:"本类有没有人上台"。[core.c:6015-6029](../linux-6.6.161/kernel/sched/core.c#L6015-L6029) 的 CFS 快路径是优化:rq 里只剩 CFS 任务时跳过 `for_each_class`,直接摘最左。

### 6.3 上台:[`set_next_task_dl`](../linux-6.6.161/kernel/sched/deadline.c#L2034) 七步

与 stop 类同款起手,后面多出一串 DL 特有的活:

1. `exec_start = rq_clock_task(rq)` —— 记执行起点(跨类通用,§2.4);
2. 结束等待统计(`schedstat`/`sched_info` 记账);
3. 从 **pushable 树摘除**——正在跑的任务不能再被 push 走;
4. `if (!first) return` —— core scheduling 对同一 CPU 二次确认时跳过 5~7 步(第一次真上台已做完);
5. **hrtick** 布置([`hrtick_enabled_dl`](../linux-6.6.161/kernel/sched/sched.h#L2578)):精确到"预算耗尽那一刻"的高精度定时器,不用等周期 tick,耗尽立刻重调度;
6. **跨类 PELT**:刚从别的类切进来,重建 load 平均跟踪(`__dl_update_load_avg_se`);
7. [`deadline_queue_push_tasks`](../linux-6.6.161/kernel/sched/deadline.c#L651):把"推任务"挂到 balance 回调里**延迟执行**——此刻还握着 rq 锁,不敢直接调 push。

下台 [`put_prev_task_dl`](../linux-6.6.161/kernel/sched/deadline.c#L2128) 与之对称:`update_curr_dl` 结算(预算耗尽当场限流)、更新 load 平均、最后把自己重新 `enqueue_pushable_dl_task`(多 CPU 可迁移时重新可被 push)。

### 6.4 切类:[`switched_from_dl`](../linux-6.6.161/kernel/sched/deadline.c#L2699) / [`switched_to_dl`](../linux-6.6.161/kernel/sched/deadline.c#L2760) 的对称

| | `switched_from_dl`(离开 DL) | `switched_to_dl`(进入 DL) |
|---|---|---|
| 定时器 | 取消 `inactive_timer`(0-lag 回收不再适用) | 同样取消——任务真正要跑 DL 了 |
| cpuset | `dec_dl_tasks_cs`(DL 任务数 −1) | `inc_dl_tasks_cs`(+1) |
| 账目 | 在队 → 摘树 + `remove_rq_bw`;boosted 状态另有分支 | 睡眠中切入 → **只** `add_rq_bw`(登记带宽,不插树——睡着不抢 CPU) |
| 队列/抢占 | — | 在队且非当前 → 入队 + 检查是否该抢占当前 |
| PELT | — | 就是当前任务 → 重建 load 跟踪(旧类的作废) |

一进一出完全镜像:from 减账/摘树,to 加账/入树;共同点是**绝不无条件插树**——睡眠任务只登记带宽,把"能不能跑"留给未来的 wakeup。

---

## 7. PI 优先级继承与 DL

### 7.1 优先级反转问题

```
A(低优先级)持锁 → C(高优先级)等锁被阻塞 → B(中优先级)抢占 A 一直跑
→ A 拿不到 CPU 放不了锁 → C 被 B 无限期压住(优先级反转)
```

**PI 解法**：C 阻塞在 A 的锁上时，内核把 C 的优先级"借"给 A，让 A 尽快跑完临界区放锁。实现是 [`rt_mutex_setprio()`](../linux-6.6.161/kernel/sched/core.c#L7088)：只改**有效优先级** `p->prio`，不动 `p->normal_prio`（任务自己的静态优先级）——锁释放后自动降回（deboost）。

### 7.2 DL 的两种提升（[core.c:7157-7184](../linux-6.6.161/kernel/sched/core.c#L7157-L7184)）

1. **RT 任务持锁，DL 任务等锁** → RT 任务**临时切进 DL 类**，直接借用等待者的 deadline/runtime 参数运行；
2. **DL 任务持锁，更早 deadline 的 DL 任务等锁** → 持锁者继承顶等待者的 deadline（"deadline 继承"）。

### 7.3 `pi_se` 与 `is_dl_boosted`

`pi_se` 的语义：**"本任务当前使用谁的 DL 参数"**。默认指向自己（[init_dl_entity](../linux-6.6.161/kernel/sched/deadline.c#L3216-L3218) `dl_se->pi_se = dl_se`），提升时指向顶等待者的实体（core.c:7170）。判断函数（[deadline.c:86-89](../linux-6.6.161/kernel/sched/deadline.c#L86-L89)）：

```c
static inline bool is_dl_boosted(struct sched_dl_entity *dl_se)
{
	return pi_of(dl_se) != dl_se;   // pi_se 指向别人 = 正在被提升
}
```

`CONFIG_RT_MUTEXES=n` 时它是**常量 false**（[deadline.c:96-99](../linux-6.6.161/kernel/sched/deadline.c#L96-L99)），编译器直接优化掉所有相关分支。

### 7.4 提升覆盖限流的三个位置

背后的统一逻辑：**被提升的任务手里攥着锁，锁后堵着更高优先级的任务——限流它会连累所有人**。

| 位置 | 行为 |
|---|---|
| `enqueue_task_dl` 分支一 | boosted 且 throttled → 取消定时器、清 throttle，正常入队 |
| `update_curr_dl` throttle 路径（[deadline.c:1363](../linux-6.6.161/kernel/sched/deadline.c#L1363)） | 预算耗尽但 boosted → 立即 `ENQUEUE_REPLENISH` 重新入队继续跑 |
| `dl_task_timer`（[deadline.c:1128](../linux-6.6.161/kernel/sched/deadline.c#L1128)） | 补给定时器对 boosted 任务直接忽略 |

补给函数还用 `pi_of()` 决定**用谁的参数补给**：boosted 时用 donor 的 `dl_runtime/dl_period`——"借谁的 deadline 跑，就用谁的预算补"。

---

## 8. 约束 deadline 的"死区窗口"补丁

### 8.1 规则回顾与漏洞

"runtime 必须在 deadline 前用完"由 `update_curr_dl` 严格执行。但任务可能**自愿睡眠**，deadline 过了才醒：

```
t=0    新实例:runtime=10ms, deadline=t=30, period=100ms
t=0~3  跑了 3ms,阻塞在 I/O 上睡觉(剩 7ms)
t=35   醒来 ← deadline(30)已过,下周期起点(100)未到
```

按通用唤醒规则（`update_dl_entity`：deadline 已过 → 发新票 `deadline=now+dl_deadline`、补满 runtime），新帧 **[35, 65] 整个落在旧周期 [0, 100) 内部** → 本周期可跑 3+10=13ms > 10ms → **突破带宽承诺**。这对隐式 deadline（deadline=period）无害（帧边界=周期边界），对约束 deadline（deadline<period）就是漏洞。

### 8.2 补丁:[`dl_check_constrained_dl`](../linux-6.6.161/kernel/sched/deadline.c#L1241-L1255)

```c
if (dl_time_before(dl_se->deadline, rq_clock(rq)) &&          // now > deadline
    dl_time_before(rq_clock(rq), dl_next_period(dl_se))) {    // now < 下周期起点
    if (unlikely(is_dl_boosted(dl_se) || !start_dl_timer(p)))
        return;                       // 豁免:提升中 / 定时器已在跑
    dl_se->dl_throttled = 1;          // ① 拦下这次"非法激活",不插树不给 CPU
    if (dl_se->runtime > 0)
        dl_se->runtime = 0;           // ② 作废过期帧的残余预算,防与新预算叠加
}                                     // ③ start_dl_timer 定在下周期起点
```

**条件拆解**：

- [`dl_time_before(a,b)`](../linux-6.6.161/include/linux/sched/deadline.h#L25-L28) = `(s64)(a-b) < 0`：环绕安全的"早于"比较（差 < 2^63 ns 即正确）；
- [`dl_next_period`](../linux-6.6.161/kernel/sched/deadline.c#L1033-L1036) = `deadline - dl_deadline + dl_period` = **下周期起点**（代数：deadline − dl_deadline 是本周期起点）；
- 两者同时成立 = 当前时刻落在"**deadline 已过、周期未结束**"的死区窗口内。

**漂亮推论**：隐式 deadline 时 `dl_next_period == deadline`，条件一（now > deadline）与条件二（now < deadline）矛盾——**窗口长度为 0**，if 永远进不去。所以调用处用 `!dl_is_implicit(dl_se)` 守卫（[deadline.c:1640](../linux-6.6.161/kernel/sched/deadline.c#L1640)），印证这套逻辑只为约束 deadline 任务存在。

---

## 9. `DEFINE_SCHED_CLASS(dl)` 成员速查（[deadline.c:2863](../linux-6.6.161/kernel/sched/deadline.c#L2863)）

| 成员 | 要点 |
|---|---|
| enqueue / dequeue_task | 按 EDF 插/摘红黑树;可迁移任务进 pushable 队列 |
| yield_task | 放弃本周期剩余预算(置 `dl_yielded` 强制限流) |
| wakeup_preempt | deadline 更早 → `resched_curr` 预约切换(§6.1);相同则不互相抢 |
| pick_next_task / pick_task | 取红黑树最左(最早 deadline);树空返回 NULL 让位下一类(§6.2) |
| set_next_task / put_prev_task | 上台七步(§6.3):记 exec_start→结束等统→摘 pushable→`first` 短路→hrtick→跨类 PELT→延迟 push;下台对称 |
| balance | 无 DL 任务时从过载 CPU pull;返回"本 CPU 是否忙" |
| select_task_rq | 当前 CPU 有更早 deadline 且不可迁移的任务 → 找更晚的 CPU |
| migrate_task_rq | 唤醒迁移中:从原 rq 扣 running_bw/this_bw |
| set_cpus_allowed | 跨 cpuset 迁移先扣源域总带宽(目标域已预留) |
| rq_online / rq_offline | CPU 上线/下线:登记/移除 `rd->cpudl` 堆与 overloaded 标记 |
| task_woken | 当前不重调度时主动 push 推走被唤醒任务 |
| find_lock_rq | 找 deadline 更晚的 CPU 并加锁,最多 3 次 |
| task_tick | tick 里结算预算,耗尽置 NEED_RESCHED;hrtick 重新布置 |
| task_fork | 空——DL 任务不允许 fork |
| prio_changed | 出现更早 deadline 就请求重调度 |
| switched_from / switched_to | 镜像对称(§6.4):from 减账/摘树,to 加账/入树;睡眠切入只登记带宽不插树 |
| update_curr | 扣 runtime(按频率/容量缩放或 GRUB-PA),耗尽即 throttle |
| task_is_throttled (SCHED_CORE) | 限流任务不参与 core 挑选 |

---

## 10. 今日一句话总结

| | stop | deadline |
|---|---|---|
| 队列 | **没有**——`rq->stop` 单指针 | EDF 红黑树 + pushable 树 |
| 入队出队 | 只维护 `nr_running` 计数器 | 插树/摘树 + 带宽账目 + cpudl 堆;出队幂等(`RB_EMPTY_NODE` 一查了事) |
| 选人 | 在队就选(唯一任务) | deadline 最早的(EDF);树空返回 NULL 让位下一类 |
| 抢占 | 无(永不被抢) | 被唤醒者 deadline 更早 → `resched_curr` 只预约不切换 |
| 预算机制 | 无(永远跑) | CBS:耗尽即 throttle,deadline 到期补给 |
| PI 影响 | 无 | 提升覆盖限流(pi_se 借参数) |
| 特殊补丁 | — | 约束 deadline 死区窗口(`dl_check_constrained_dl`) |

**六条核心直觉**：

1. `rq` 是每 CPU 总运行队列,调度类的子队列嵌在里面——stop 没有子队列,只有一个指针;
2. "入队" ≠ "进树":stop 入队只加计数器,DL 限流任务入队只记账——真正的"可被选中"状态由 `on_rq` + 树成员资格共同决定;
3. DL 的确定性来自两条规则:**帧内**(runtime 在 deadline 前用完)与**帧间**(任意 period 窗口不超 runtime),throttle 是执行这两条规则的"预算警察";
4. PI 是实时调度的"例外条款":持锁者被提升后,限流对它网开一面——因为锁链上还堵着更高优先级的任务;
5. `resched_curr` 只"预约"切换:置 `TIF_NEED_RESCHED` 或发 IPI,真正换人发生在当前任务走到内核路径尽头的 `__schedule`——所以抢占类回调都短小;
6. `pick_next_task` 返回 NULL = "本类没人,让位下一类":`for_each_class` 从高到低挨个问,idle 类兜底(`__pick_next_task` 里那个 `BUG()` 永远走不到)。

---

## 附:今日阅读路线(源码行号锚点)

| 顺序 | 文件 | 位置 |
|---|---|---|
| 1 | `kernel/sched/stop_task.c` | 全文件 131 行(带注释版) |
| 2 | `kernel/sched/sched.h` | `struct rq`(963)、`struct sched_class`(2247)、`sched_stop_runnable`(2356)、`add_nr_running`(2498)、`dl_entity_preempt`(266)、`hrtick_enabled_dl`(2578) |
| 3 | `include/linux/sched.h` | `struct sched_dl_entity`(551-760) |
| 4 | `kernel/sched/deadline.c` | `is_dl_boosted`(86)、`task_contending`(451)、`replenish_dl_entity`(833)、`dl_next_period`(1033)、`dl_task_timer`(1106)、`dl_check_constrained_dl`(1241)、`update_curr_dl`(1304)、`__enqueue_dl_entity`(1602)、`enqueue_dl_entity`(1628)、`enqueue_task_dl`(1726)、`__dequeue_task_dl`(1808)、`dequeue_task_dl`(1817)、`wakeup_preempt_dl`(1994)、`set_next_task_dl`(2034)、`pick_task_dl`(2084)、`pick_next_task_dl`(2109)、`put_prev_task_dl`(2128)、`switched_from_dl`(2699)、`switched_to_dl`(2760)、`prio_changed_dl`(2812)、`DEFINE_SCHED_CLASS(dl)`(2863)、`init_dl_entity`(3216) |
| 5 | `kernel/sched/core.c` | `sched_set_stop_task`(3661)、`rt_mutex_setprio`(7088)、`activate_task`(2136)、`resched_curr`(1055)、`wakeup_preempt`(2232)、`__pick_next_task`(6003) |
| 6 | `include/linux/sched/deadline.h` | `dl_time_before`(25) |
