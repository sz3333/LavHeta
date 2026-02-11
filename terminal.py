import asyncio
import os
import signal
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command

BOT_TOKEN = "YOUR_TOKEN"
OWNER_ID = 123456789  # только для себя

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

activecmds = {}
pending_sudo = {}

# -------------------- потоковое чтение --------------------
async def read_stream(stream, label: str):
    data = b""
    last_text = ""
    while True:
        chunk = await stream.read(1024)
        if not chunk:
            break
        data += chunk
        last_text = data.decode(errors="ignore")[-4000:]
    return last_text  # возвращаем последний кусок

# -------------------- запуск команды --------------------
async def run_command(message: types.Message, cmd: str, use_sudo=False, sudo_pass=None):
    sent_msg = await message.answer(f"<pre>Запуск: {cmd}</pre>", parse_mode="HTML")

    if use_sudo and sudo_pass is not None:
        cmd = f"sudo -S {cmd}"

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=os.setsid,
    )
    activecmds[message.message_id] = proc

    if use_sudo and sudo_pass is not None:
        proc.stdin.write((sudo_pass + "\n").encode())
        await proc.stdin.drain()

    # читаем stdout и stderr параллельно
    last_stdout, last_stderr = await asyncio.gather(
        read_stream(proc.stdout, "STDOUT"),
        read_stream(proc.stderr, "STDERR")
    )

    rc = await proc.wait()

    final_text = ""
    if last_stdout:
        final_text += f"<b>STDOUT:</b>\n<pre>{last_stdout}</pre>\n"
    if last_stderr:
        final_text += f"<b>STDERR:</b>\n<pre>{last_stderr}</pre>\n"
    final_text += f"\nКод выхода: {rc}\nКоманда завершена"

    await sent_msg.edit_text(final_text, parse_mode="HTML")
    del activecmds[message.message_id]

# -------------------- Команды --------------------
@router.message(Command(commands=["terminal", "apt", "pip"]))
async def handle_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split(" ", 1)
    args = parts[1] if len(parts) > 1 else ""
    cmd = args

    if message.text.startswith("/apt"):
        cmd = f"apt {args} -y"
    elif message.text.startswith("/pip"):
        cmd = f"pip {args}"

    if cmd.startswith("sudo"):
        pending_sudo[message.from_user.id] = cmd.replace("sudo ", "", 1)
        await message.answer("Введите sudo пароль")
        return

    await run_command(message, cmd)

# -------------------- Sudo обработка --------------------
@router.message()
async def handle_sudo(message: types.Message):
    user_id = message.from_user.id
    if user_id in pending_sudo:
        cmd = pending_sudo.pop(user_id)
        sudo_pass = message.text
        await message.delete()
        await run_command(message, cmd, use_sudo=True, sudo_pass=sudo_pass)

# -------------------- Terminate --------------------
@router.message(Command(commands=["terminate"]))
async def terminate_cmd(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.answer("Укажи message_id процесса для terminate")
        return
    try:
        msg_id = int(parts[1])
        if msg_id in activecmds:
            os.killpg(activecmds[msg_id].pid, signal.SIGTERM)
            await message.answer(f"Процесс {msg_id} убит")
        else:
            await message.answer("Процесс не найден")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# -------------------- запуск --------------------
dp.include_router(router)

if __name__ == "__main__":
    import asyncio

    async def main():
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()

    asyncio.run(main())