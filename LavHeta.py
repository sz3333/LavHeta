# meta developer: @LavHeta
# meta banner: https://raw.githubusercontent.com/sz3333/LavHeta/refs/heads/main/icon.jpg

__version__ = (1, 0, 0)

import aiohttp
import asyncio
import json
import logging
from typing import List, Dict, Optional
from .. import loader, utils
from ..types import InlineCall, InlineQuery

logger = logging.getLogger(__name__)


class LavHeta(loader.Module):
    """Module for searching modules in LavHeta repository"""

    strings = {
        "name": "LavHeta",
        "searching": "🔎 <b>Searching...</b>",
        "no_query": "❌ <b>Enter a query to search.</b>",
        "no_results": "❌ <b>No modules found.</b>",
        "result": (
            "🔎 <b>Result {idx}/{total} by query:</b> <code>{query}</code>\n\n"
            "📦 <code>{name}</code> <b>by</b> <code>{author}</code>\n"
            "📝 <b>Description:</b> {description}\n\n"
            "{commands}"
            "💾 <b>Install:</b> <code>{prefix}dlm {link}</code>"
        ),
        "result_single": (
            "🔎 <b>Result by query:</b> <code>{query}</code>\n\n"
            "📦 <code>{name}</code> <b>by</b> <code>{author}</code>\n"
            "📝 <b>Description:</b> {description}\n\n"
            "{commands}"
            "💾 <b>Install:</b> <code>{prefix}dlm {link}</code>"
        ),
        "commands": "👨‍💻 <b>Commands:</b>\n{cmds}\n\n",
        "inline_commands": "🤖 <b>Inline commands:</b>\n{cmds}\n\n",
        "no_info": "No information",
        "inline_no_query": "Enter a query to search",
        "inline_desc": "Name, command, description, author",
        "inline_no_results": "No modules found",
        "api_error": "❌ <b>Error loading modules list</b>",
        "rating_added": "👍 Rating submitted!",
        "rating_changed": "👍 Rating changed!",
        "prev_page": "◀️ Previous",
        "next_page": "▶️ Next",
        "page_info": "{current}/{total}",
    }

    strings_ru = {
        "searching": "🔎 <b>Поиск...</b>",
        "no_query": "❌ <b>Введите запрос для поиска.</b>",
        "no_results": "❌ <b>Модули не найдены.</b>",
        "result": (
            "🔎 <b>Результат {idx}/{total} по запросу:</b> <code>{query}</code>\n\n"
            "📦 <code>{name}</code> <b>от</b> <code>{author}</code>\n"
            "📝 <b>Описание:</b> {description}\n\n"
            "{commands}"
            "💾 <b>Установка:</b> <code>{prefix}dlm {link}</code>"
        ),
        "result_single": (
            "🔎 <b>Результат по запросу:</b> <code>{query}</code>\n\n"
            "📦 <code>{name}</code> <b>от</b> <code>{author}</code>\n"
            "📝 <b>Описание:</b> {description}\n\n"
            "{commands}"
            "💾 <b>Установка:</b> <code>{prefix}dlm {link}</code>"
        ),
        "commands": "👨‍💻 <b>Команды:</b>\n{cmds}\n\n",
        "inline_commands": "🤖 <b>Инлайн команды:</b>\n{cmds}\n\n",
        "no_info": "Нет информации",
        "inline_no_query": "Введите запрос для поиска",
        "inline_desc": "Название, команда, описание, автор",
        "inline_no_results": "Модули не найдены",
        "api_error": "❌ <b>Ошибка загрузки списка модулей</b>",
        "rating_added": "👍 Оценка отправлена!",
        "rating_changed": "👍 Оценка изменена!",
        "prev_page": "◀️ Назад",
        "next_page": "▶️ Вперед",
        "page_info": "{current}/{total}",
    }

    strings_ua = {
        "searching": "🔎 <b>Пошук...</b>",
        "no_query": "❌ <b>Введіть запит для пошуку.</b>",
        "no_results": "❌ <b>Модулі не знайдені.</b>",
        "result": (
            "🔎 <b>Результат {idx}/{total} за запитом:</b> <code>{query}</code>\n\n"
            "📦 <code>{name}</code> <b>від</b> <code>{author}</code>\n"
            "📝 <b>Опис:</b> {description}\n\n"
            "{commands}"
            "💾 <b>Встановлення:</b> <code>{prefix}dlm {link}</code>"
        ),
        "result_single": (
            "🔎 <b>Результат за запитом:</b> <code>{query}</code>\n\n"
            "📦 <code>{name}</code> <b>від</b> <code>{author}</code>\n"
            "📝 <b>Опис:</b> {description}\n\n"
            "{commands}"
            "💾 <b>Встановлення:</b> <code>{prefix}dlm {link}</code>"
        ),
        "commands": "👨‍💻 <b>Команди:</b>\n{cmds}\n\n",
        "inline_commands": "🤖 <b>Інлайн команди:</b>\n{cmds}\n\n",
        "no_info": "Немає інформації",
        "inline_no_query": "Введіть запит для пошуку",
        "inline_desc": "Назва, команда, опис, автор",
        "inline_no_results": "Модулі не знайдені",
        "api_error": "❌ <b>Помилка завантаження списку модулів</b>",
        "rating_added": "👍 Оцінка відправлена!",
        "rating_changed": "👍 Оцінка змінена!",
        "prev_page": "◀️ Назад",
        "next_page": "▶️ Вперед",
        "page_info": "{current}/{total}",
    }

    def __init__(self):
        self._modules_cache: List[Dict] = []
        self._cache_time: float = 0
        self._index_url = "https://raw.githubusercontent.com/sz3333/LavHeta/refs/heads/main/LavIndexRaw.json"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        await self._load_modules()

    async def _load_modules(self, force: bool = False) -> bool:
        """Load modules from index"""
        current_time = asyncio.get_event_loop().time()
        
        # Cache for 5 minutes
        if not force and self._modules_cache and (current_time - self._cache_time) < 300:
            return True

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self._index_url,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        data = json.loads(text)
                        self._modules_cache = data if isinstance(data, list) else []
                        self._cache_time = current_time
                        logger.info(f"Loaded {len(self._modules_cache)} modules from LavHeta")
                        return True
        except Exception as e:
            logger.error(f"Error loading modules: {e}")
            return False

        return False

    def _search_modules(self, query: str) -> List[Dict]:
        """Search modules by query"""
        query_lower = query.lower()
        results = []
        seen = set()

        for module in self._modules_cache:
            # Create unique key
            key = f"{module.get('name', '')}_{module.get('author', '')}"
            if key in seen:
                continue

            # Search in module name
            if query_lower in module.get("name", "").lower():
                results.append(module)
                seen.add(key)
                continue

            # Search in commands
            if "commands" in module and module["commands"]:
                for cmd in module["commands"]:
                    cmd_name = cmd.get("name", "")
                    if query_lower in cmd_name.lower():
                        results.append(module)
                        seen.add(key)
                        break

            # Search in description
            if query_lower in module.get("description", "").lower():
                if key not in seen:
                    results.append(module)
                    seen.add(key)
                continue

            # Search in author
            if query_lower in module.get("author", "").lower():
                if key not in seen:
                    results.append(module)
                    seen.add(key)

        return results

    def _format_commands(self, module: Dict) -> str:
        """Format commands for display"""
        if not module.get("commands"):
            return ""

        regular_cmds = []
        inline_cmds = []

        for cmd in module["commands"][:10]:  # Limit to 10 commands
            name = cmd.get("name", "")
            desc = cmd.get("description", "")
            
            if cmd.get("inline", False):
                inline_cmds.append(
                    f"<code>@{self.inline.bot_username} {utils.escape_html(name)}</code> - "
                    f"{utils.escape_html(desc) if desc else self.strings['no_info']}"
                )
            else:
                regular_cmds.append(
                    f"<code>{self.get_prefix()}{utils.escape_html(name)}</code> - "
                    f"{utils.escape_html(desc) if desc else self.strings['no_info']}"
                )

        result = ""
        if regular_cmds:
            result += self.strings["commands"].format(cmds="\n".join(regular_cmds))
        if inline_cmds:
            result += self.strings["inline_commands"].format(cmds="\n".join(inline_cmds))

        return result

    def _format_module(
        self,
        module: Dict,
        query: str,
        idx: int = 0,
        total: int = 1
    ) -> str:
        """Format module info for display"""
        name = utils.escape_html(module.get("name", "Unknown"))
        author = utils.escape_html(module.get("author", "Unknown"))
        description = utils.escape_html(module.get("description", self.strings["no_info"]))
        link = module.get("link", "")
        commands = self._format_commands(module)

        if total > 1:
            template = self.strings["result"]
            return template.format(
                idx=idx,
                total=total,
                query=utils.escape_html(query),
                name=name,
                author=author,
                description=description,
                commands=commands,
                prefix=self.get_prefix(),
                link=link
            )
        else:
            template = self.strings["result_single"]
            return template.format(
                query=utils.escape_html(query),
                name=name,
                author=author,
                description=description,
                commands=commands,
                prefix=self.get_prefix(),
                link=link
            )

    async def _nav_callback(
        self,
        call: InlineCall,
        modules: List[Dict],
        query: str,
        page: int
    ):
        """Navigation callback"""
        if not (0 <= page < len(modules)):
            await call.answer("Invalid page")
            return

        module = modules[page]
        text = self._format_module(module, query, page + 1, len(modules))
        
        markup = self._create_markup(modules, query, page)
        
        photo = module.get("banner") or module.get("pic")
        
        try:
            await call.edit(
                text=text,
                reply_markup=markup,
                **({"photo": photo} if photo else {})
            )
        except Exception:
            await call.edit(text=text, reply_markup=markup)

    def _create_markup(
        self,
        modules: List[Dict],
        query: str,
        page: int
    ) -> List[List[Dict]]:
        """Create inline markup with navigation"""
        buttons = []
        
        if len(modules) > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append({
                    "text": self.strings["prev_page"],
                    "callback": self._nav_callback,
                    "args": (modules, query, page - 1)
                })
            
            nav_row.append({
                "text": self.strings["page_info"].format(
                    current=page + 1,
                    total=len(modules)
                ),
                "callback": lambda c: c.answer()
            })
            
            if page < len(modules) - 1:
                nav_row.append({
                    "text": self.strings["next_page"],
                    "callback": self._nav_callback,
                    "args": (modules, query, page + 1)
                })
            
            buttons.append(nav_row)

        return buttons

    @loader.command()
    async def lavheta(self, message):
        """<query> - Search modules in LavHeta repository"""
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, self.strings["no_query"])
            return

        status_msg = await utils.answer(message, self.strings["searching"])

        # Reload modules if needed
        if not await self._load_modules():
            await utils.answer(message, self.strings["api_error"])
            return

        results = self._search_modules(args)

        if not results:
            await utils.answer(message, self.strings["no_results"])
            return

        # Limit results
        results = results[:50]

        module = results[0]
        text = self._format_module(module, args, 1, len(results))
        markup = self._create_markup(results, args, 0)

        photo = module.get("banner") or module.get("pic")

        try:
            await self.inline.form(
                message=message,
                text=text,
                reply_markup=markup,
                **({"photo": photo} if photo else {})
            )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Error creating form: {e}")
            await utils.answer(message, text)

    @loader.inline_handler()
    async def lavheta_inline(self, query: InlineQuery):
        """Search modules in LavHeta repository"""
        if not query.args:
            return {
                "title": self.strings["inline_no_query"],
                "description": self.strings["inline_desc"],
                "message": self.strings["no_query"],
                "thumb": "https://img.icons8.com/color/512/search.png",
            }

        await self._load_modules()
        results = self._search_modules(query.args)

        if not results:
            return {
                "title": self.strings["inline_no_results"],
                "description": self.strings["inline_desc"],
                "message": self.strings["no_results"],
                "thumb": "https://img.icons8.com/color/512/nothing-found.png",
            }

        return [
            {
                "title": utils.escape_html(module.get("name", "Unknown")),
                "description": utils.escape_html(module.get("description", ""))[:100],
                "message": self._format_module(module, query.args),
                "thumb": module.get("pic", "https://img.icons8.com/color/512/module.png"),
            }
            for module in results[:50]
        ]
