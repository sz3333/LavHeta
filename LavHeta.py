# ©️ LavHeta Project 2025
# 💜 by Lid & Mochi
# 🔗 https://github.com/sz3333/LavHeta

import json
import difflib
import requests
import logging
from typing import List, Tuple, Union
from dataclasses import dataclass
from hikkatl.tl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)

@dataclass
class LavModule:
    name: str
    author: str
    repo: str
    description: str
    commands: List[dict]
    install: str


@loader.tds
class LavHeta(loader.Module):
    """💜 Search and install modules from LavHeta Repository"""

    strings = {
        "name": "LavHeta",
        "no_query": "❌ <b>Укажи запрос для поиска!</b>",
        "no_results": "😿 <b>Ничего не найдено...</b>",
        "loading": "💠 <b>Загружаем базу LavHeta...</b>",
        "install_btn": "💜 Установить",
        "installed": "✅ <b>Модуль успешно установлен!</b>",
        "error": "❌ <b>Ошибка при установке!</b>",
        "result": (
            "✨ <b>Результаты по запросу:</b> <code>{query}</code>\n\n"
            "📦 <b>{name}</b>\n"
            "👤 <b>Автор:</b> {author}\n"
            "📁 <b>Репозиторий:</b> <code>{repo}</code>\n\n"
            "📜 <b>Описание:</b> {desc}\n\n"
            "🧩 <b>Команды:</b>\n{commands}\n\n"
            "🔗 <b>Ссылка для установки:</b>\n<code>{install}</code>"
        ),
    }

    def __init__(self):
        self._lavdb = []
        self._repolist = []
        self._loaded = False

    async def client_ready(self):
        if not self._loaded:
            await self._update_db()
            self._loaded = True

    async def _update_db(self):
        """Fetch module index and repo list"""
        try:
            json_data = (
                await utils.run_sync(
                    requests.get,
                    "https://raw.githubusercontent.com/sz3333/LavHeta/refs/heads/main/LavIndexRaw.json",
                )
            ).json()

            self._lavdb = [
                LavModule(
                    name=item.get("name", "Unknown"),
                    author=item.get("author", "Unknown"),
                    repo=item.get("repo", "Unknown"),
                    description=item.get("description", ""),
                    commands=item.get("commands", []),
                    install=item.get("install", ""),
                )
                for item in json_data.get("modules", [])
            ]

            text_data = (
                await utils.run_sync(
                    requests.get,
                    "https://raw.githubusercontent.com/sz3333/LavHeta/refs/heads/main/repos.txt",
                )
            ).text
            self._repolist = [r.strip() for r in text_data.splitlines() if r.strip()]
            logger.info(f"LavHeta loaded {len(self._lavdb)} modules and {len(self._repolist)} repos")

        except Exception as e:
            logger.error(f"[LavHeta] Load error: {e}")
            self._lavdb = []
            self._repolist = []

    def _search(self, query: str) -> List[Tuple[LavModule, float]]:
        """Search modules by name, description or repo"""
        results = []
        for module in self._lavdb:
            score = max(
                difflib.SequenceMatcher(None, query, module.name).ratio(),
                difflib.SequenceMatcher(None, query, module.description).ratio(),
                difflib.SequenceMatcher(None, query, module.repo).ratio(),
            )
            if score >= 0.4:
                results.append((module, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _format(self, module: LavModule, query: str) -> str:
        """Format result text"""
        commands_str = ""
        for cmd in module.commands:
            name = cmd.get("name", "")
            desc = cmd.get("description", {}).get("ru_doc") or cmd.get("description", {}).get("en_doc", "")
            commands_str += f"▫️ <code>{utils.escape_html(name)}</code> — {utils.escape_html(desc)}\n"

        return self.strings("result").format(
            query=utils.escape_html(query),
            name=utils.escape_html(module.name),
            author=utils.escape_html(module.author),
            repo=utils.escape_html(module.repo),
            desc=utils.escape_html(module.description),
            commands=commands_str or "—",
            install=utils.escape_html(module.install),
        )

    async def _install_module(self, call, module: LavModule, text: str):
        await call.edit("💜 <b>Установка...</b>")
        try:
            loader_mod = self.lookup("loader")
            await loader_mod.download_and_install(module.install, None)
            await call.edit(self.strings("installed"))
        except Exception as e:
            logger.error(f"[LavHeta] install error: {e}")
            await call.edit(self.strings("error"))

    @loader.command()
    async def lheta(self, message: Message):
        """<поиск> — ищет модули LavHeta"""
        query = utils.get_args_raw(message)
        if not query:
            await utils.answer(message, self.strings("no_query"))
            return

        if not self._lavdb:
            await utils.answer(message, self.strings("loading"))
            await self._update_db()

        results = self._search(query)
        if not results:
            await utils.answer(message, self.strings("no_results"))
            return

        index = 0
        module = results[index][0]
        text = self._format(module, query)
        await self.inline.form(
            message=message,
            text=text,
            reply_markup=self._buttons(query, results, index),
        )

    def _buttons(self, query: str, results, index: int):
        buttons = []
        if index > 0:
            buttons.append(
                {"text": "⬅️", "callback": self._switch, "args": (query, results, index - 1)}
            )
        buttons.append(
            {
                "text": self.strings("install_btn"),
                "callback": self._install_module,
                "args": (results[index][0], self._format(results[index][0], query)),
            }
        )
        if index < len(results) - 1:
            buttons.append(
                {"text": "➡️", "callback": self._switch, "args": (query, results, index + 1)}
            )
        return buttons

    async def _switch(self, call, query, results, new_index):
        mod = results[new_index][0]
        new_text = self._format(mod, query)
        await call.edit(new_text, reply_markup=self._buttons(query, results, new_index))