"""Telegram-бот CRM (aiogram 3): привязка аккаунта и команды /tasks, /cases.

Запуск — management-команда run_telegram_bot (отдельный compose-сервис `bot`).
Синхронные хелперы вынесены отдельно, чтобы их можно было тестировать без aiogram.
"""
from asgiref.sync import sync_to_async

HELP_TEXT = (
    'Это бот CRM «Нюансы».\n\n'
    'Привязка аккаунта: в CRM откройте Профиль → «Привязать Telegram» '
    'и перейдите по ссылке.\n\n'
    'Команды:\n'
    '/tasks — мои активные задачи\n'
    '/cases — мои дела'
)
NOT_LINKED_TEXT = (
    'Аккаунт не привязан. Откройте Профиль в CRM и нажмите «Привязать Telegram».'
)


def get_user_by_chat(chat_id):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.filter(telegram_chat_id=str(chat_id)).first()


def tasks_text(user):
    from apps.tasks.models import Task
    tasks = list(
        Task.objects.filter(assigned_to=user, status__in=['todo', 'in_progress'])
        .select_related('case').order_by('due_date')[:10]
    )
    if not tasks:
        return 'Активных задач нет 🎉'
    lines = ['Ваши задачи:']
    for t in tasks:
        line = f'• {t.title}'
        if t.due_date:
            line += f' — до {t.due_date.strftime("%d.%m.%Y")}'
        if t.case_id:
            line += f' ({t.case.case_number})'
        lines.append(line)
    return '\n'.join(lines)


def cases_text(user):
    from apps.cases.models import Case
    from common.scoping import scope_cases
    cases = list(
        scope_cases(Case.objects.filter(status__in=['new', 'active', 'on_hold']), user)
        .order_by('-created_at')[:10]
    )
    if not cases:
        return 'Открытых дел нет.'
    lines = ['Ваши дела:']
    for c in cases:
        line = f'• {c.case_number}: {c.title} — {c.get_status_display()}'
        if c.key_deadline:
            line += f'\n  ⚖️ срок: {c.key_deadline.strftime("%d.%m.%Y")}'
        lines.append(line)
    return '\n'.join(lines)


def link_account(token, chat_id):
    from apps.accounts.telegram_link import use_link_token
    return use_link_token(token, chat_id)


async def run_polling(token):
    from aiogram import Bot, Dispatcher
    from aiogram.filters import Command, CommandStart
    from aiogram.filters.command import CommandObject
    from aiogram.types import Message

    bot = Bot(token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message, command: CommandObject):
        payload = (command.args or '').strip()
        if payload:
            user = await sync_to_async(link_account)(payload, message.chat.id)
            if user:
                name = user.get_full_name() or user.username
                await message.answer(f'✅ Telegram привязан к аккаунту {name}.\n\n{HELP_TEXT}')
            else:
                await message.answer(
                    'Ссылка недействительна или устарела. '
                    'Сгенерируйте новую в профиле CRM.')
            return
        await message.answer(HELP_TEXT)

    @dp.message(Command('tasks'))
    async def tasks(message: Message):
        user = await sync_to_async(get_user_by_chat)(message.chat.id)
        if not user:
            await message.answer(NOT_LINKED_TEXT)
            return
        await message.answer(await sync_to_async(tasks_text)(user))

    @dp.message(Command('cases'))
    async def cases(message: Message):
        user = await sync_to_async(get_user_by_chat)(message.chat.id)
        if not user:
            await message.answer(NOT_LINKED_TEXT)
            return
        await message.answer(await sync_to_async(cases_text)(user))

    await dp.start_polling(bot)
