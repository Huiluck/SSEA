"""消费者守卫 —— 「声明了没有消费者的通道」是本项目反复出现的病。

08 §2.4 有明文约束：

    **动作必须可执行。协议中不允许存在无消费者的通道。**

``Action.__post_init__`` 落地了它的一半（新字段必须在 ``CHANNELS`` 登记），
``action.py`` 的模块 docstring 落地了另一半（六个通道各自的消费者表）。
**但那条表是散文。** 散文不会被 pytest 读，所以它只在有人去核对时才是真的。

实测（2026-09-28）：五个结构类别里 ``rules`` 零消费者，而它此前在
四个地方被当成活的——提案路径 ``ADD_RULE`` / ``UPDATE_RULE`` 通、门会校验、
Store 会升版本号、审计会记一笔，**只是没有任何代码读它去改变行为**。
``get_threshold()`` 当年那个洞（13 §4.6）与它是同一个形状，区别只是那次
发生在访问器上，这次发生在结构类别上。

所以本文件把两个面都扫成可比对的断言：

    结构类别（``FastLoopContext`` 的字段）   —— 每个类别都要有读者
    读取访问器（``FastLoopContext`` 的方法） —— 每个访问器都要有调用方
    Action 六通道                            —— 每个通道都要有读者

**扫描用 AST，不用文本。** 这不是洁癖：``adapters`` 死掉的那段时间里，
``action_decoder.py:46`` 与 ``instinct.py:9`` 的 docstring 都写着它的名字。
按文本扫，两个类别会显得很活；按 AST 扫，那两处只是字符串字面量。
**「提到名字」与「读这个字段」是两件事，本文件的全部价值就在这条分界上。**

本守卫有三个**登记表**，每个都必须写明理由和归属增量——形状照抄
``plasticity.DEFERRED_SCOPES``：一份声明式清单比一段注释强的地方在于，
它会过期，而过期会被测试抓到（下面的双向断言就是干这个的）。
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from SSEA.sse_protocols import Action, FastLoopContext

SSEA_DIR = Path(__file__).resolve().parent.parent / "SSEA"

# ----------------------------------------------------------------------
#  结构管理面：定义结构、或校验结构，**不是读结构去做事**
# ----------------------------------------------------------------------

#: 扫描时整个跳过的路径（目录名或文件名）。
#:
#: **这一条是承重的。** 见 ``STRUCTURE_MANAGEMENT`` 里 ``verification_gate.py``
#: 的理由——把门算成读者会让 ``rules`` 显得有消费者，守卫当场退化成
#: 它自己要防的那种假守卫。
STRUCTURE_MANAGEMENT: dict[str, str] = {
    "sse_protocols": (
        "它**定义**这些字段：``FastLoopContext`` 本体、它的读取方法、"
        "以及 ``StructureStore`` 都在这里。把定义处算成读者，等于让每个"
        "类别都被定义它的那个文件消费掉——守卫会恒绿。"
        "（``get_skill`` 等方法体内确实有 ``self.skills.get(...)``，"
        "那是定义的一部分，不是消费。）"
    ),
    "verification_gate.py": (
        "它读遍五个类别，但读的是**为了校验**（``_check_*`` 系列），"
        "不是读了去改变行为。第三级校验器的职责是「在不在边界内」，"
        "它自己不产生行为——这正是四权分立里门不评分的那一条。"
        "**这一条是承重的**：``rules`` 目前唯一的静态命中就是它，"
        "一旦把门算成读者，``rules`` 就会显得「有消费者」，"
        "而守卫会变成测试全绿、类别仍然死掉的那种假守卫。"
    ),
}

# ----------------------------------------------------------------------
#  登记表一：结构类别无消费者
# ----------------------------------------------------------------------

NO_CONSUMER_YET: dict[str, str] = {
    "rules": (
        "ΔR 的编译器（RuleCompiler）尚未实现，``rules`` 在 "
        "``experience_compiler.DEFERRED_DELTAS`` 里。提案路径"
        "（``ADD_RULE`` / ``UPDATE_RULE``）与门校验都在，**只是没有代码"
        "读它去改变行为**。归属增量：13 §6.6 的 RuleCompiler 一步。"
        "在那之前 ``rules`` 只应保持空表——**别用「反正没人读」当理由"
        "往里面写东西，那正是本守卫存在的理由。**"
    ),
}

# ----------------------------------------------------------------------
#  登记表二：读取访问器无调用方
# ----------------------------------------------------------------------

#: 当前**没有**空项——四个访问器全部删掉了（见 ``DELETED_ACCESSORS``）。
#: 表留着不删：它有双向断言守着，下一个零调用方的访问器会被它抓住，
#: 而它抓的方式与本文件其它登记表一样——**必须写明理由和归属增量**。
ACCESSOR_LEDGER: dict[str, str] = {}

#: 已**删除**的访问器 -> 为什么删。删掉的不能只留在 git 历史里：没有这条，
#: 后来者看到 ``skills`` 有 ``get_skill`` 而 ``adapters`` 没有对应方法，
#: 会按「对称」「完整性」把它补回来——那正是它们当初被加上的理由。
#:
#: 本表**不参与断言**（方法已经不存在，扫不到），纯粹是留给人的。
DELETED_ACCESSORS: dict[str, str] = {
    "get_threshold": (
        "**2026-09-28 删。** 消费 ``thresholds`` 的不是它，是**整个映射**："
        "``fast_loop.py`` 取 ``dict(self.context.thresholds)`` 交给解码器"
        "（解码器要按多个键取值，单键访问器不是它需要的形状）。"
        "**删它的理由是它的默认值是那个假的契约。** 读同一份数据的两个真消费者"
        "各自算各自的回落，**没有一个是 0.0**：解码器回落到 "
        "``config.gate_threshold``（``action_decoder.py`` 的 ``forward``），"
        "``plasticity._current_value`` 回落到 ``DEFAULT_BOUNDS[target]`` 的**中点**"
        "（它自己写了一段理由说明为什么 0.0 是错的：「0 对阈值是恒开，对相似度是"
        "恒命中——两个都是机制被关掉」）。于是 ``default`` 参数取什么值都对不上"
        "任何一个真消费者。**契约是照着一个想象中的消费者猜的，不是从消费者"
        "推出来的**——这就是它和 ``get_adapter`` / ``version_of`` 的共同形状，"
        "也是 14 §6.3.6「名字是标签，作用点是内容」低一级的重演。"
    ),
    "get_adapter": (
        "**2026-09-28 删。** 本能层要的是**整份 adapter 集合**"
        "（``decode_instinct_set(self.context.adapters)``，它按已知名字过滤），"
        "不是按名字取一份。方法是 ②.1 按「``adapters`` 该有个读取接口」的"
        "设想加的，加完消费者用了字段本身，它一次都没被调用过。"
        "它的**类别**（``adapters``）一直有真消费者——本例说明"
        "「给某个类别补一个接口」和「给这个接口找到消费者」是两件事，"
        "只做前一件就会造出下一个 ``get_threshold()``。"
    ),
    "get_retrieval_policy": (
        "**2026-09-28 删。** Memory System 读的是 ``context.retrieval`` 字段本身"
        "（``memory_system.py`` 的 ``__init__`` 与 ``use_context`` 两处），"
        "不是这个访问器。"
        "**它的存在理由是假的**：返回深拷贝是为了「调用方改不动存在结构里的"
        "那份」，但 ``retrieval`` 的形状是**扁平策略**——键就是策略字段名，"
        "``validate_retrieval_policy`` 对未知键直接 ``ValueError``，所以嵌套形状"
        "是系统**不会产生**的。顶层包成 ``MappingProxyType`` 之后就是全覆盖，"
        "深拷贝没有第二层要保护。真要一份可改的拷贝，调用点自己写 "
        "``deepcopy(dict(ctx.retrieval))``——**让这个需要在看得见的地方表达**。"
        "\n\n"
        "**附记（两个扫描面之间的耦合，留在案上）**：它体内读 ``self.retrieval``，"
        "而 ``sse_protocols/`` 是被 ``STRUCTURE_MANAGEMENT`` 排除的那一面。"
        "所以当年把 ``memory_system`` 改走这个访问器，会让 ``retrieval`` 类别的"
        "**唯一静态读**搬进被排除的文件，本守卫立刻误报「``retrieval`` 无消费者」"
        "——而真相是有。当时为它单开了一条 ``ACCESSOR_LEDGER`` 登记；现在四个访问器"
        "都删了，这个耦合不再被触发，但**它没有消失**：将来任何一个新的访问器"
        "只要体内读某个类别字段，同样的问题会回来。"
    ),
    "version_of": (
        "**2026-09-28 删。** 被 ``fingerprint()`` 严格支配：审计要问的是"
        "「这一步用的是哪一版结构」，那是**全部类别的版本号**，不是某一个。"
        "三个生产调用点（``fast_loop.py`` 记 ``StepRecord`` / "
        "``memory_system.py`` 记 ``_context_fingerprint`` / "
        "``experiments/_injection.py`` 记对照臂）用的都是 ``fingerprint()``。"
        "它顺带提供的类别名校验另有 ``structure_store.py`` 与 "
        "``plasticity.py`` 两份，各自的测试都在。"
    ),
}

# ----------------------------------------------------------------------
#  登记表三：静态扫不到的读者（本守卫的已知盲区）
# ----------------------------------------------------------------------

#: 文件 -> 它为什么扫不到。
#:
#: **声明盲区不是走过场。** 一个守卫最危险的状态不是报错，是**它以为自己
#: 扫全了**。``plasticity._current_value`` 用 ``getattr(structure, kind)``
#: 按计算出来的名字取类别，任何 AST 扫描都看不见它——把它记在这里，
#: 后来者才知道「无消费者」这个结论的射程到哪里为止。
DYNAMIC_READERS: dict[str, str] = {
    "plasticity.py": (
        "``_current_value()`` 用 ``getattr(structure, kind, None)`` 按**参数传进来的"
        "名字**取类别（``kind`` 是 ``\"thresholds\"`` / ``\"retrieval\"``），"
        "静态扫不到。**后果要说清楚**：这两个类别此刻另有静态读者"
        "（``fast_loop.py`` / ``memory_system.py``），所以盲区眼下不改变任何结论；"
        "**但若哪天静态读者只剩它一个**，守卫会报「无消费者」而真相是有——"
        "那时先改这里，别急着往 ``NO_CONSUMER_YET`` 里加东西。"
    ),
}

# ----------------------------------------------------------------------
#  扫描
# ----------------------------------------------------------------------


def _is_management(path: Path) -> bool:
    """路径是否属于结构管理面（定义或校验结构本身）。"""
    return any(part in STRUCTURE_MANAGEMENT for part in path.parts)


def reads_in_source(src: str, names: frozenset[str]) -> tuple[set[str], list[str]]:
    """源码里对 ``names`` 的**静态可见读**，以及动态 ``getattr`` 的表达式。

    返回 ``(命中的名字集合, 动态 getattr 的第二个实参表达式列表)``。

    认这几种形状（都要求名字取自字面量，否则静态看不见）：

        x.rules               属性读
        x["rules"]            下标读
        x.get("rules")        映射读
        getattr(x, "rules")   按字面量取

    不认这几种，因为它们是**提到名字**而不是读字段：

        "rules"               裸字面量（``plasticity`` 的类别登记表就是这种）
        # rules               注释
        \"\"\"rules\"\"\"        docstring
    """
    tree = ast.parse(src)
    found: set[str] = set()
    dynamic: list[str] = []

    def _literal(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr in names:
                found.add(node.attr)
        elif isinstance(node, ast.Subscript):
            v = _literal(node.slice)
            if v in names:
                found.add(v)
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "get" and node.args:
                v = _literal(node.args[0])
                if v in names:
                    found.add(v)
            elif isinstance(fn, ast.Name) and fn.id == "getattr" and len(node.args) >= 2:
                v = _literal(node.args[1])
                if v in names:
                    found.add(v)
                elif v is not None:
                    pass  # 字面量但不是我们找的名字：与本守卫无关
                else:
                    dynamic.append(ast.unparse(node.args[1]))

    return found, dynamic


def _scan(
    names: frozenset[str], root: Path | None = None
) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """扫 ``root/**/*.py``（默认 ``SSEA/``，跳过管理面）。

    返回 ``(名字 -> 读者文件集合, 文件 -> 动态 getattr 表达式列表)``。

    ``root`` 可注入是**为验收留的**：本守卫的验收方式不是「它今天绿」，
    是「人造一个死类别时它能红」（13 §7）。人造样本跑在 ``tmp_path`` 上，
    不碰真仓库。
    """
    readers: dict[str, set[str]] = {n: set() for n in names}
    dynamic: dict[str, list[str]] = {}
    for path in sorted((root or SSEA_DIR).rglob("*.py")):
        if "__pycache__" in path.parts or _is_management(path):
            continue
        found, dyn = reads_in_source(path.read_text(encoding="utf-8"), names)
        for n in found:
            readers[n].add(path.name)
        if dyn:
            dynamic[path.name] = dyn
    return readers, dynamic


def _category_names() -> list[str]:
    """五个结构类别：``FastLoopContext`` 的字段去掉 ``versions``。

    ``versions`` 不是注入物，是元数据（记录各类别版本号，用于审计归因），
    它没有提案路径也不该有——所以不参与「每个类别都要有消费者」这条断言。

    **从 ``dataclasses.fields`` 派生而不是抄一份名单**：类别是会被新增的
    （``retrieval`` 就是后加的），抄名单的话新类别会静默落在覆盖面之外，
    而「落在覆盖面之外」与「有消费者」在测试里长得一模一样。
    """
    return [f.name for f in dataclasses.fields(FastLoopContext) if f.name != "versions"]


def _accessor_names() -> list[str]:
    """``FastLoopContext`` 上不以 ``_`` 开头的方法。"""
    return sorted(
        n
        for n in vars(FastLoopContext)
        if not n.startswith("_") and callable(getattr(FastLoopContext, n))
    )


# ----------------------------------------------------------------------
#  结构类别
# ----------------------------------------------------------------------


class TestEveryStructureCategoryHasAReader:
    def test_no_unregistered_category_is_dead(self) -> None:
        """没有读者的类别必须**显式登记**在 ``NO_CONSUMER_YET``。"""
        readers, _ = _scan(frozenset(_category_names()))
        dead = sorted(n for n, who in readers.items() if not who)
        unregistered = [n for n in dead if n not in NO_CONSUMER_YET]
        assert not unregistered, (
            f"结构类别 {unregistered} 没有任何代码读它——"
            f"提案 / 验证门 / Store / 审计可能全通，而行为侧零影响。"
            f"要么补消费者，要么登记进 NO_CONSUMER_YET 并写明归属增量。"
            f"（读者表：{ {n: sorted(readers[n]) for n in dead} }）"
        )

    def test_registered_category_that_gained_a_reader_is_flagged(self) -> None:
        """登记了的类别若已出现消费者 → 也失败。

        反方向的那半条。没有它，``NO_CONSUMER_YET`` 会变成一份只增不减的
        名单：读了 ``rules`` 的代码加进来，登记项还留着，于是登记表开始
        说假话——而它存在的全部意义就是不説假话。
        """
        readers, _ = _scan(frozenset(_category_names()))
        stale = sorted(
            n for n in NO_CONSUMER_YET if n in readers and readers[n]
        )
        assert not stale, (
            f"{stale} 已在 NO_CONSUMER_YET 里登记为「无消费者」，"
            f"但已经出现读者 { {n: sorted(readers[n]) for n in stale} }。"
            f"请把它们移出登记表——清单烂掉的第一步就是它开始过期。"
        )

    def test_registry_keys_are_real_categories(self) -> None:
        """登记表的键必须是真类别。写错名字的登记项是一条永远不生效的豁免。"""
        cats = set(_category_names())
        bogus = sorted(set(NO_CONSUMER_YET) - cats)
        assert not bogus, f"NO_CONSUMER_YET 含不存在的类别 {bogus}；真类别：{sorted(cats)}"

    def test_registry_entries_all_state_a_reason(self) -> None:
        """每条登记都要写明理由——空理由等于没有登记。"""
        thin = sorted(k for k, v in NO_CONSUMER_YET.items() if len(v.strip()) < 20)
        assert not thin, f"NO_CONSUMER_YET 的这些项理由太短，等于没写：{thin}"


# ----------------------------------------------------------------------
#  读取访问器
# ----------------------------------------------------------------------


class TestEveryAccessorHasACaller:
    def test_no_unregistered_accessor_is_dead(self) -> None:
        """没有调用方的访问器必须登记在 ``ACCESSOR_LEDGER``。"""
        readers, _ = _scan(frozenset(_accessor_names()))
        dead = sorted(n for n, who in readers.items() if not who)
        unregistered = [n for n in dead if n not in ACCESSOR_LEDGER]
        assert not unregistered, (
            f"FastLoopContext 的访问器 {unregistered} 没有任何调用方。"
            f"**声明了没有消费者的接口就是本项目那个反复出现的病**"
            f"（13 §4.6 的 get_threshold 是第一次）。"
            f"要么把消费者接到它上面，要么登记进 ACCESSOR_LEDGER。"
        )

    def test_ledger_entry_that_gained_a_caller_is_flagged(self) -> None:
        """反方向：登记为「无调用方」的访问器有了调用方 → 失败。"""
        readers, _ = _scan(frozenset(_accessor_names()))
        stale = sorted(k for k in ACCESSOR_LEDGER if k in readers and readers[k])
        assert not stale, (
            f"{stale} 已在 ACCESSOR_LEDGER 里登记为「无调用方」，"
            f"但已被 { {k: sorted(readers[k]) for k in stale} } 调用。请移出登记表。"
        )

    def test_deleted_accessors_stay_deleted(self) -> None:
        """已删的访问器不许悄悄回来。

        ``DELETED_ACCESSORS`` 本身只是留给人的说明（方法不存在，扫不到），
        所以这里补一条真断言。**没有它，「删掉」只是一个 commit，不是一个性质**——
        而它们被加上的理由（「对称」「``adapters`` 该有个读取接口」）随时还在。
        """
        back = sorted(set(DELETED_ACCESSORS) & set(_accessor_names()))
        assert not back, (
            f"{back} 曾以「零调用方」为由删除（理由见 DELETED_ACCESSORS），"
            f"现在又回到 FastLoopContext 上了。要接消费者就从那张表移出，"
            f"并写清是哪一行行为会因它改变；不然就是把它又变成了 "
            f"``get_threshold()``。"
        )

    def test_ledger_keys_are_real_accessors(self) -> None:
        accessors = set(_accessor_names())
        bogus = sorted(set(ACCESSOR_LEDGER) - accessors)
        assert not bogus, f"ACCESSOR_LEDGER 含不存在的访问器 {bogus}；真访问器：{sorted(accessors)}"

    def test_accessor_scan_actually_sees_the_callers(self) -> None:
        """``get_skill`` 有三个生产调用方——先确认扫描器真的看得见调用。

        没有这条，上面「没有调用方」那些结论可能来自一个坏掉的扫描器，
        而不是来自真相。**一个恒说「全都没有调用方」的扫描器会让上面两条
        断言中的一条恒红、另一条恒绿**——两条都不会说出实情。
        """
        readers, _ = _scan(frozenset(_accessor_names()))
        assert readers["get_skill"], "get_skill 明明有三个调用方，扫描器却一个都没找到"


# ----------------------------------------------------------------------
#  盲区
# ----------------------------------------------------------------------


class TestTheBlindSpotStaysDeclared:
    def test_every_dynamic_reader_is_declared(self) -> None:
        """按计算名字取属性的地方，必须都登记在 ``DYNAMIC_READERS``。"""
        _, dynamic = _scan(frozenset(_category_names()))
        undeclared = sorted(f for f in dynamic if f not in DYNAMIC_READERS)
        assert not undeclared, (
            f"{undeclared} 里有 getattr(x, <变量>) 形式的类别读法，静态扫不到。"
            f"它可能是某个类别的真读者，请登记进 DYNAMIC_READERS 说明读的是哪个类别。"
        )

    def test_declared_blind_spot_is_still_there(self) -> None:
        """反方向：登记为盲区的文件若不再动态取属性，登记项该删。"""
        _, dynamic = _scan(frozenset(_category_names()))
        stale = sorted(f for f in DYNAMIC_READERS if f not in dynamic)
        assert not stale, (
            f"{stale} 已不再用 getattr(x, <变量>) 取类别，DYNAMIC_READERS 里的"
            f"登记过期了。清掉它——一份写着过期盲区的表会让守卫低估自己的射程。"
        )


# ----------------------------------------------------------------------
#  Action 六通道（08 §2.4 那条明文约束的另一半）
# ----------------------------------------------------------------------


class TestEveryActionChannelHasAReader:
    """六个通道各有读它去做事的代码。

    ``action.py`` 的 docstring 里有这张对照表，但那是散文。
    ``test_08_revisions.py`` 里曾有一条 ``test_channels_all_have_consumers``，
    而它只断言了 ``Action.CHANNELS`` 元组——**守的是名字，不是消费者**，
    名字对了而某个通道没人读，它照样绿。那条已按它实际做的事改名为
    ``test_channel_names_are_the_documented_six``，真断言落在这里。

    **扫描收窄到「从名叫 ``action`` 的变量上取通道」**，不是洁癖：
    放宽到任何 ``x.<通道名>`` 的话，``self.memory``（memory_system）与
    ``self.skill``（skill_library）会把 memory / skill 两个通道算成有人读——
    而它们读的是记忆系统和技能库，不是动作通道。
    """

    def _channel_readers(self) -> dict[str, set[str]]:
        readers: dict[str, set[str]] = {c: set() for c in Action.CHANNELS}
        for path in sorted(SSEA_DIR.rglob("*.py")):
            if "__pycache__" in path.parts or _is_management(path):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr in Action.CHANNELS
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "action"
                ):
                    readers[node.attr].add(path.name)
        return readers

    def test_every_channel_has_a_reader(self) -> None:
        readers = self._channel_readers()
        dead = sorted(c for c, who in readers.items() if not who)
        assert not dead, (
            f"Action 通道 {dead} 没有任何代码读它。08 §2.4："
            f"「协议中不允许存在无消费者的通道」——"
            f"而这条约束现在只在 docstring 里。"
            f"（读者表：{ {c: sorted(readers[c]) for c in Action.CHANNELS} }）"
        )

    def test_channel_readers_match_the_documented_table(self) -> None:
        """读者分布要与 ``action.py`` docstring 那张表一致。

        这条比上一条严：上一条只问「有没有人读」，这条问「是不是**表里写的
        那个**人读」。区别在于 self_modification 若被 locomotion 读了，
        上一条绿，而协议表已经错了。
        """
        readers = self._channel_readers()
        expected = {
            "locomotion": "environment.py",
            "manipulation": "environment.py",
            "communication": "environment.py",
            "memory": "environment.py",
            "self_modification": "environment.py",
            "skill": "skill_runner.py",
        }
        actual = {c: sorted(who) for c, who in readers.items()}
        assert actual == {c: [f] for c, f in expected.items()}, (
            f"通道读者与 action.py docstring 的对照表不一致：{actual}"
        )


# ----------------------------------------------------------------------
#  守卫自己能不能红
# ----------------------------------------------------------------------


class TestTheGuardCanActuallyGoRed:
    """本文件其余部分全是绿的，而**绿不算证明**（项目的纪律）。

    下面是一批合成样本与 ``tmp_path`` 上的假树：守卫在它们身上必须给出
    **指定的**答案。
    没有这类测试，本文件就只是又一句 docstring——**而且是一句恰好用来防
    「假守卫」的 docstring**，那比没有更糟：后来者会据此以为覆盖面有了。

    第三条尤其重要，它不是「能不能发现读者」，是「会不会**误报**读者」：
    一个把裸字符串也当读者的扫描器会让 ``rules`` 显得活的，而
    ``plasticity.UPDATABLE_SCOPES`` 里正躺着一个裸的 ``"rules"``。
    """

    NAMES = frozenset({"rules", "skills"})

    def test_a_docstring_mention_is_not_a_reader(self) -> None:
        """只在 docstring 里提到 → **不算**读者。

        这是本守卫存在的**全部理由**：``adapters`` 死掉的那段时间，
        ``action_decoder.py`` 与 ``instinct.py`` 的 docstring 都写着它的名字。
        """
        src = '"""本模块读 FastLoopContext.rules 来决定行为。"""\n'
        found, _ = reads_in_source(src, self.NAMES)
        assert found == set(), f"docstring 里的名字被当成了读者：{found}"

    def test_a_comment_mention_is_not_a_reader(self) -> None:
        src = "# rules 由 RuleCompiler 产出\nx = 1\n"
        found, _ = reads_in_source(src, self.NAMES)
        assert found == set(), f"注释里的名字被当成了读者：{found}"

    def test_a_bare_string_literal_is_not_a_reader(self) -> None:
        """裸字符串 → **不算**读者。

        ``plasticity.UPDATABLE_SCOPES`` 就是 ``("thresholds", "retrieval",
        "adapters", "skills", "rules")`` 这样的元组。按文本扫的话
        ``rules`` 会显得有消费者——**这个假阳性正是本守卫要防的那种假守卫**
        （测试全绿，类别仍然死掉）。
        """
        src = 'UPDATABLE_SCOPES = ("thresholds", "rules")\n'
        found, _ = reads_in_source(src, self.NAMES)
        assert found == set(), f"裸字面量被当成了读者：{found}"

    @pytest.mark.parametrize(
        "src",
        [
            "y = ctx.rules\n",
            "y = ctx['rules']\n",
            "y = ctx.get('rules')\n",
            "y = ctx.get('rules', {})\n",
            "y = getattr(ctx, 'rules')\n",
        ],
    )
    def test_a_real_read_is_a_reader(self, src: str) -> None:
        """真读法 → 算读者。五种形状都要认，否则守卫会漏报。"""
        found, _ = reads_in_source(src, self.NAMES)
        assert found == {"rules"}, f"{src!r} 没被认成读者：{found}"

    def test_a_computed_getattr_is_reported_as_dynamic(self) -> None:
        """``getattr(ctx, kind)`` → 静态看不见，必须报成动态。

        这是 ``plasticity._current_value`` 的形状。报成「读者」是过度声称
        （扫不出是哪一类），报成「不是读者」是漏报——**只能报成盲区**。
        """
        src = "def f(structure, kind):\n    return getattr(structure, kind, None)\n"
        found, dynamic = reads_in_source(src, self.NAMES)
        assert found == set(), f"计算出来的属性名不该算成静态读者：{found}"
        assert dynamic == ["kind"], f"动态 getattr 没被报出来：{dynamic}"

    def test_a_non_category_literal_getattr_is_ignored(self) -> None:
        """``getattr(ctx, 'foo')`` 与本守卫无关，不该被报成动态盲区。

        否则 ``DYNAMIC_READERS`` 会被一堆无关的 getattr 撑爆，
        而「登记表里全是噪音」和「没有登记表」一样没用。
        """
        src = "y = getattr(ctx, 'foo')\n"
        found, dynamic = reads_in_source(src, self.NAMES)
        assert found == set()
        assert dynamic == [], f"无关的 getattr 被报成了盲区：{dynamic}"

    def test_a_manufactured_dead_category_goes_red(self, tmp_path: Path) -> None:
        """**本文件的验收方式**：人造一个死类别，守卫必须报出来。

        上面几条验的是扫描原语分得清「提到名字」与「读字段」。这一条验的是
        **守卫本身**会红——用一棵 ``tmp_path`` 上的假树，不碰真仓库。

        造的形状就是 ``rules`` 的形状：有提案路径、有门校验、有审计，
        只是没人读。守卫必须恰好报出那一个新类别，而**不能**连有读者的
        ``skills`` 一起报——一个「恒报全死」的守卫也会红，但它什么都没守住。
        """
        pkg = tmp_path / "SSEA"
        pkg.mkdir()
        (pkg / "reader.py").write_text(
            "def f(ctx):\n    return ctx.skills\n", encoding="utf-8"
        )
        names = frozenset({"skills", "brand_new_category"})
        readers, _ = _scan(names, root=pkg)

        assert readers["skills"], "假树里明明有人读 skills，扫描器却说没有"
        dead = sorted(n for n, who in readers.items() if not who)
        assert dead == ["brand_new_category"], f"死类别集合不对：{dead}"
        # 未登记 ⇒ 上面那条断言（test_no_unregistered_category_is_dead）会红。
        assert "brand_new_category" not in NO_CONSUMER_YET

    def test_a_resurrected_accessor_goes_red(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """把删掉的访问器加回来 → 删除断言必须红。

        不碰真文件：``monkeypatch`` 在类上加一个方法，测完自动撤掉。
        **这一条是「能红才算」本身**——没有它，「已删」就只是一句
        永远为真的空话，而它们被加上的理由（「``adapters`` 该有个读取接口」）
        随时还在，补回来是顺手的事。
        """
        monkeypatch.setattr(
            FastLoopContext, "get_adapter", lambda self, name: None, raising=False
        )
        assert "get_adapter" in _accessor_names(), "monkeypatch 没生效，这条测试本身是坏的"
        with pytest.raises(AssertionError, match="零调用方"):
            TestEveryAccessorHasACaller().test_deleted_accessors_stay_deleted()

    def test_a_manufactured_dynamic_reader_goes_red(self, tmp_path: Path) -> None:
        """人造一处 ``getattr(ctx, kind)`` → 未登记，盲区那条断言必须红。"""
        pkg = tmp_path / "SSEA"
        pkg.mkdir()
        (pkg / "sneaky.py").write_text(
            "def f(ctx, kind):\n    return getattr(ctx, kind, None)\n",
            encoding="utf-8",
        )
        _, dynamic = _scan(frozenset({"rules"}), root=pkg)
        assert dynamic == {"sneaky.py": ["kind"]}
        assert "sneaky.py" not in DYNAMIC_READERS

    def test_management_files_are_excluded_from_the_scan(self, tmp_path: Path) -> None:
        """管理面读得再多也不算消费者——否则 ``rules`` 会被门救活。

        这条守的是排除机制本身。``verification_gate.py`` 读遍五个类别，
        一旦它被算成读者，``rules`` 显得有消费者，**守卫当场变成它自己要防的
        那种假守卫**。
        """
        pkg = tmp_path / "SSEA"
        (pkg / "sse_protocols").mkdir(parents=True)
        (pkg / "sse_protocols" / "defs.py").write_text(
            "y = ctx.rules\n", encoding="utf-8"
        )
        (pkg / "verification_gate.py").write_text("y = ctx.rules\n", encoding="utf-8")
        (pkg / "real_reader.py").write_text("y = ctx.skills\n", encoding="utf-8")

        readers, _ = _scan(frozenset({"rules", "skills"}), root=pkg)
        assert readers["rules"] == set(), "管理面被算成了 rules 的读者"
        assert readers["skills"] == {"real_reader.py"}, "真读者反而没被算进来"
