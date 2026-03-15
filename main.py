import time
import json
import os
import textwrap
from collections import defaultdict
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.star import Context, Star, register


@register("anti_repeat", "灵汐", "防重复指令拦截器", "1.0.0")
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context, config_file="config.json"):
        super().__init__(context)
        # 优化的记录结构：使用 defaultdict 减少键查找开销
        # 结构：{user_id: {content: {'time': float, 'warned': bool}}}
        self.history = defaultdict(dict)

        # 默认配置值
        self.cooldown_seconds = 3.0
        self.WarnMessage = "核心逻辑混乱，不要再发啦！"  # 警告消息
        self.GJC = []  # 关键词列表
        self.enable_keyword_check = False  # 是否启用关键词检查
        self.enable_warn_word_check = True  # 是否启用言语警告
        
        # 配置文件路径：保存到 data 目录下，防止插件更新时丢失
        # 格式：data/config/rate_limit_plugin/config.json
        self.config_dir = os.path.join(get_astrbot_data_path(), "config", "rate_limit_plugin")
        self.config_file = os.path.join(self.config_dir, config_file)

        # 预编译关键词检查相关数据
        self._keyword_check_enabled = False
        self._keywords_set = set()

        # 加载配置
        self.load_config()

    def load_config(self):
        """启动时从文件读取配置"""
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    # 读取配置，如果不存在则使用默认值
                    self.cooldown_seconds = data.get(
                        "cooldown_seconds", self.cooldown_seconds
                    )
                    self.WarnMessage = data.get("warn_message", self.WarnMessage)
                    self.GJC = data.get("gjc", self.GJC)
                    self.enable_keyword_check = data.get(
                        "enable_keyword_check", self.enable_keyword_check
                    )
                    self.enable_warn_word_check = data.get(
                        "enable_warn_word_check", self.enable_warn_word_check
                    )
                    print(
                        f"成功读取配置：CD={self.cooldown_seconds}s, 关键词检查={self.enable_keyword_check}"
                    )

                    # 更新预编译数据
                    self._update_keyword_cache()

            except Exception as e:
                print(f"读取失败，使用默认配置。错误：{e}")
        else:
            print("配置文件不存在，将使用初始配置并创建文件。")
            self.save_config()

    def save_config(self):
        """将当前的所有配置保存到文件"""
        try:
            # 确保配置目录存在
            os.makedirs(self.config_dir, exist_ok=True)
            
            data = {
                "cooldown_seconds": self.cooldown_seconds,
                "warn_message": self.WarnMessage,
                "gjc": self.GJC,
                "enable_keyword_check": self.enable_keyword_check,
                "enable_warn_word_check": self.enable_warn_word_check,
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                # indent=4 可以让生成的 json 文件带缩进，方便阅读
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"配置已保存到：{self.config_file}")
        except Exception as e:
            print(f"保存失败：{e}")

    def _update_keyword_cache(self):
        """更新关键词检查缓存，提高检查效率"""
        self._keyword_check_enabled = self.enable_keyword_check and bool(self.GJC)
        if self._keyword_check_enabled:
            # 创建关键词集合用于快速查找
            self._keywords_set = {k.strip() for k in self.GJC if k.strip()}
        else:
            self._keywords_set.clear()

    @filter.command_group("lx")
    def lx(self):
        pass

    @filter.command("lxhelp", alias={"拦截帮助"})
    async def lxhelp(self, event: AstrMessageEvent):
        help_message = textwrap.dedent(f"""
             【灵汐指令拦截帮助】
             [介绍]
             当同一用户在 {self.cooldown_seconds}s 内发送两次相同内容，将自动拦截后续指令。
             关键词检查状态：{"开启" if self.enable_keyword_check else "关闭"}

             [指令]
             注意：除帮助指令外需要添加 lx 为主指令。
             当前警告语句：{self.WarnMessage}

             1. lxhelp 或 拦截帮助 -> 获得拦截插件帮助信息
             2. set_cooldown 或 冷却设置 -> 调整冷却时间 (当前：{self.cooldown_seconds}s)
             3. 设置警告 -> 设置触发拦截时的回复内容
             4. 设置关键词 -> 设置关键词（多个用逗号分隔）
             5. 添加关键词 -> 添加单个关键词
             6. 删除关键词 -> 删除单个关键词
             7. 开关关键词检查 -> 启用/禁用关键词检查功能
             8. 查看关键词列表 -> 显示当前关键词列表
             9. 开关警告词 -> 开关用户多次发送时是否发送警告词
             
             """).strip()
        yield event.plain_result(help_message)

    @lx.command("set_cooldown", alias={"冷却设置"})
    @filter.permission_type(PermissionType.ADMIN)
    async def set_cd(self, event: AstrMessageEvent, seconds: str):
        try:
            new_time = float(seconds)
            if new_time < 0:
                yield event.plain_result("冷却时间不能为负数。")
                return

            self.cooldown_seconds = new_time
            self.history.clear()  # 清空历史记录以应用新时间
            self.save_config()  # 保存配置

            yield event.plain_result(
                f"冷却时间已更新为：{self.cooldown_seconds} 秒并已保存。"
            )
        except ValueError:
            yield event.plain_result("格式错误，请输入数字。")

    # 设置警告语句
    @lx.command("设置警告")
    @filter.permission_type(PermissionType.ADMIN)
    async def set_warnmessage(self, event: AstrMessageEvent, wm: str):
        self.WarnMessage = wm
        self.save_config()  # 保存配置
        yield event.plain_result(f"警告语句已更新并保存：{self.WarnMessage}")

    # 开关发送警告
    @lx.command("开关警告词发送", alias={"开关警告词"})
    @filter.permission_type(PermissionType.ADMIN)
    async def toggle_warn_word_check(self, event: AstrMessageEvent):
        self.enable_warn_word_check = not self.enable_warn_word_check
        self.save_config()
        status = "开启" if self.enable_warn_word_check else "关闭"
        yield event.plain_result(f"警告词功能已{status}")

    # 设置关键词（覆盖）
    @lx.command("设置关键词")
    @filter.permission_type(PermissionType.ADMIN)
    async def set_keywords(self, event: AstrMessageEvent, keywords: str):
        # 按空格或逗号分割关键词
        self.GJC = [
            k.strip() for k in keywords.replace("，", ",").split(",") if k.strip()
        ]
        self._update_keyword_cache()  # 更新缓存
        self.save_config()
        yield event.plain_result(f"已设置关键词：{self.GJC}")

    # 添加关键词而不是覆盖
    @lx.command("添加关键词")
    @filter.permission_type(PermissionType.ADMIN)
    async def add_keyword(self, event: AstrMessageEvent, keyword: str):
        keyword = keyword.strip()
        if keyword and keyword not in self.GJC:
            self.GJC.append(keyword)
            self._update_keyword_cache()  # 更新缓存
            self.save_config()
            yield event.plain_result(f"已添加关键词：{keyword}，当前列表：{self.GJC}")
        else:
            yield event.plain_result(f"关键词 {keyword} 已存在或为空")

    # 删除关键词
    @lx.command("删除关键词", alias={"关键词删除"})
    @filter.permission_type(PermissionType.ADMIN)
    async def del_keyword(self, event: AstrMessageEvent, keyword: str):
        keyword = keyword.strip()
        if keyword in self.GJC:
            self.GJC.remove(keyword)
            self._update_keyword_cache()  # 更新缓存
            self.save_config()  # 保存配置
            yield event.plain_result(f"关键词删除成功！当前列表：{self.GJC}")
        else:
            yield event.plain_result(f"关键词 {keyword} 不在列表中。")

    # 开关关键词检查功能
    @lx.command("开关关键词检查", alias={"切换关键词检查"})
    @filter.permission_type(PermissionType.ADMIN)
    async def toggle_keyword_check(self, event: AstrMessageEvent):
        self.enable_keyword_check = not self.enable_keyword_check
        self._update_keyword_cache()  # 更新缓存
        self.save_config()
        status = "开启" if self.enable_keyword_check else "关闭"
        yield event.plain_result(f"关键词检查功能已{status}")

    # 查看关键词列表
    @lx.command("查看关键词列表", alias={"显示关键词", "关键词列表"})
    @filter.permission_type(PermissionType.ADMIN)
    async def show_keywords(self, event: AstrMessageEvent):
        if self.GJC:
            keywords_str = "\n".join(
                [f"{i + 1}. {keyword}" for i, keyword in enumerate(self.GJC)]
            )
            yield event.plain_result(
                f"当前关键词列表：\n{keywords_str}\n\n关键词检查功能：{'开启' if self.enable_keyword_check else '关闭'}"
            )
        else:
            yield event.plain_result("当前没有设置关键词。")

    # === 事件监听部分 ===
    @filter.event_message_type(EventMessageType.ALL, priority=10)
    async def intercept_repeats(self, event: AstrMessageEvent):
        # 1. 基础检查
        content = event.message_str
        if not content:
            return

        # 2. 检查是否包含关键词（仅在启用关键词检查时）
        if self._keyword_check_enabled and self._keywords_set:
            # 优化：使用 any() 短路评估和预编译的关键词集合
            if not any(keyword in content for keyword in self._keywords_set):
                return
        # 如果没有启用关键词检查，则检查所有消息

        # 3. 创建唯一标识
        user_id = event.get_sender_id()
        current_time = time.time()

        # 获取用户的历史记录
        user_history = self.history[user_id]

        # 4. 检查冷却
        if content in user_history:
            record = user_history[content]
            last_time = record["time"]
            has_warned = record["warned"]

            if current_time - last_time < self.cooldown_seconds:
                # === 触发拦截 ===
                # 只有在还没警告过的情况下，才发送警告
                if not has_warned:
                    if not self.enable_warn_word_check:
                        return
                    message_chain = MessageChain().message(self.WarnMessage)
                    await self.context.send_message(
                        event.unified_msg_origin, message_chain
                    )
                    # 标记该记录为"已警告"
                    user_history[content]["warned"] = True

                # 更新时间防止无限刷（可选，延长冷却）
                user_history[content]["time"] = current_time

                # 核心：停止事件传播
                event.stop_event()
                return

        # 5. 更新/新建记录 (重置 warned 状态)
        user_history[content] = {"time": current_time, "warned": False}

        # 6. 定期清理过期历史（每 100 条记录清理一次，避免频繁清理）
        if len(user_history) >= 100 and len(user_history) % 100 == 0:
            self._cleanup_user_history(user_id, current_time)

    def _cleanup_user_history(self, user_id: str, current_time: float):
        """清理指定用户的过期历史记录"""
        user_history = self.history[user_id]
        # 阈值设置为冷却时间的 2 倍，保留足够的历史数据
        threshold = self.cooldown_seconds * 2

        # 过滤过期记录
        expired_keys = [
            content
            for content, record in user_history.items()
            if current_time - record["time"] >= threshold
        ]

        for key in expired_keys:
            del user_history[key]

        # 如果用户没有任何历史记录了，从主字典中删除用户条目
        if not user_history:
            del self.history[user_id]

    def cleanup_history(self):
        """清理所有过期历史数据（保留原方法以保证兼容性）"""
        current_time = time.time()
        threshold = self.cooldown_seconds * 2

        # 清理过期的用户和记录
        users_to_delete = []
        for user_id, user_history in self.history.items():
            # 清理过期记录
            expired_keys = [
                content
                for content, record in user_history.items()
                if current_time - record["time"] >= threshold
            ]

            for key in expired_keys:
                del user_history[key]

            # 如果用户没有任何历史记录，标记删除
            if not user_history:
                users_to_delete.append(user_id)

        # 删除空用户条目
        for user_id in users_to_delete:
            del self.history[user_id]
