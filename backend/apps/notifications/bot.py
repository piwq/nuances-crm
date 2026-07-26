"""Telegram-бот CRM (aiogram 3): привязка, команды и inline-действия.

Запуск — management-команда run_telegram_bot (compose-сервис `bot`).
Синхронные хелперы вынесены отдельно и тестируются без aiogram.
Все сообщения — MarkdownV2 (жирный, моноширинные номера дел,
раскрывающиеся цитаты для длинных списков).
"""
from datetime import date, timedelta
from decimal import Decimal

from asgiref.sync import sync_to_async

DIGEST_DEADLINE_DAYS = 3      # сроки «на носу» в дайджесте
DEADLINES_HORIZON_DAYS = 30   # горизонт /deadlines
LIST_LIMIT = 10

_MDV2_SPECIAL = '_*[]()~`>#+-=|{}.!'


def esc(text):
    """Экранирование для MarkdownV2 — обязательно для всех динамических значений."""
    return ''.join('\\' + c if c in _MDV2_SPECIAL else c for c in str(text))


def expandable(lines):
    """Раскрывающаяся цитата MarkdownV2 (строки уже экранированы)."""
    if not lines:
        return ''
    if len(lines) == 1:
        return f'**>{lines[0]}||'
    body = '\n'.join('>' + l for l in lines[1:])
    return f'**>{lines[0]}\n{body}||'


def block(lines, collapse_after=4):
    """Короткий список — как есть, длинный — сворачиваем в цитату."""
    if len(lines) > collapse_after:
        return expandable(lines)
    return '\n'.join(lines)


HELP_TEXT = (
    'Это бот CRM *«Нюансы»*\\.\n\n'
    'Привязка аккаунта: в CRM откройте Профиль → «Привязать Telegram» '
    'и перейдите по ссылке\\.\n\n'
    '*Команды:*\n'
    '/today — что у меня сегодня\n'
    '/tasks — активные задачи\n'
    '/cases — мои дела\n'
    '/deadlines — процессуальные сроки\n'
    '/hours — мои часы за неделю и месяц\n'
    '/find текст — поиск по делам и клиентам'
)
NOT_LINKED_TEXT = 'Аккаунт не привязан\\. Откройте Профиль в CRM и нажмите «Привязать Telegram»\\.'


def get_user_by_chat(chat_id):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.filter(telegram_chat_id=str(chat_id)).first()


def _fmt_date(d):
    return esc(d.strftime('%d.%m.%Y'))


def _days_left(d):
    n = (d - date.today()).days
    if n < 0:
        return esc(f'просрочен на {-n} дн.')
    if n == 0:
        return esc('сегодня!')
    return esc(f'через {n} дн.')


def tasks_text(user):
    from apps.tasks.models import Task
    tasks = list(
        Task.objects.filter(assigned_to=user, status__in=['todo', 'in_progress'])
        .select_related('case').order_by('due_date')[:LIST_LIMIT]
    )
    if not tasks:
        return 'Активных задач нет 🎉'
    lines = []
    for t in tasks:
        line = f'▫️ {esc(t.title)}'
        if t.due_date:
            line += f' — до {_fmt_date(t.due_date)}'
        if t.case_id:
            line += f' \\(`{esc(t.case.case_number)}`\\)'
        lines.append(line)
    return '*Ваши задачи:*\n' + block(lines)


def cases_text(user):
    from apps.cases.models import Case
    from common.scoping import scope_cases
    cases = list(
        scope_cases(Case.objects.filter(status__in=['new', 'active', 'on_hold']), user)
        .order_by('-created_at')[:LIST_LIMIT]
    )
    if not cases:
        return 'Открытых дел нет\\.'
    lines = []
    for c in cases:
        line = f'▫️ `{esc(c.case_number)}` {esc(c.title)} — {esc(c.get_status_display())}'
        if c.key_deadline:
            line += f'\n   ⚖️ срок {_fmt_date(c.key_deadline)} \\({_days_left(c.key_deadline)}\\)'
        lines.append(line)
    return '*Ваши дела:*\n' + block(lines)


def deadlines_text(user):
    from apps.cases.models import Case
    from common.scoping import scope_cases
    horizon = date.today() + timedelta(days=DEADLINES_HORIZON_DAYS)
    cases = list(
        scope_cases(
            Case.objects.filter(
                key_deadline__isnull=False,
                key_deadline__lte=horizon,
                status__in=['new', 'active', 'on_hold'],
            ), user)
        .order_by('key_deadline')[:LIST_LIMIT]
    )
    if not cases:
        return f'Процессуальных сроков в ближайшие {DEADLINES_HORIZON_DAYS} дней нет 🎉'
    lines = []
    for c in cases:
        mark = '❗️' if c.key_deadline <= date.today() else '⚖️'
        line = (f'{mark} {_fmt_date(c.key_deadline)} — {esc(c.title)} '
                f'\\({_days_left(c.key_deadline)}\\)')
        if c.key_deadline_note:
            line += f'\n   _{esc(c.key_deadline_note)}_'
        lines.append(line)
    return '*Процессуальные сроки:*\n' + block(lines)


def hours_text(user):
    from django.db.models import Sum, F, DecimalField
    from apps.billing.models import TimeEntry

    def stats(date_from):
        # алиасы не должны совпадать с именами полей (hours=Sum('hours') падает)
        row = (TimeEntry.objects
               .filter(lawyer=user, is_billable=True, date__gte=date_from)
               .aggregate(
                   total_h=Sum('hours'),
                   total_amt=Sum(F('hours') * F('hourly_rate'),
                                 output_field=DecimalField(max_digits=14, decimal_places=2))))
        return row['total_h'] or Decimal('0'), row['total_amt'] or Decimal('0')

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    wh, wa = stats(week_start)
    mh, ma = stats(month_start)
    return (
        '*Мои часы:*\n'
        f'▫️ Эта неделя: *{esc(wh)} ч* — {esc(f"{wa:,.0f}").replace(esc(","), " ")} ₽\n'
        f'▫️ Этот месяц: *{esc(mh)} ч* — {esc(f"{ma:,.0f}").replace(esc(","), " ")} ₽'
    )


def find_text(user, query):
    from django.db.models import Q
    from apps.cases.models import Case
    from apps.clients.models import Client
    from common.scoping import scope_cases

    query = (query or '').strip()
    if len(query) < 3:
        return 'Введите минимум 3 символа: `/find иванов`'

    cases = list(
        scope_cases(Case.objects.filter(
            Q(title__icontains=query) | Q(case_number__icontains=query) |
            Q(client__last_name__icontains=query) | Q(client__company_name__icontains=query)
        ), user)[:5]
    )
    clients = list(Client.objects.filter(
        Q(last_name__icontains=query) | Q(company_name__icontains=query) |
        Q(tax_id__icontains=query)
    )[:5])

    if not cases and not clients:
        return f'По запросу «{esc(query)}» ничего не найдено\\.'

    parts = []
    if cases:
        parts.append('*Дела:*\n' + '\n'.join(
            f'▫️ `{esc(c.case_number)}` {esc(c.title)} — {esc(c.get_status_display())}'
            for c in cases))
    if clients:
        parts.append('*Клиенты:*\n' + '\n'.join(
            f'▫️ {esc(c.display_name)}' + (f' \\(ИНН {esc(c.tax_id)}\\)' if c.tax_id else '')
            for c in clients))
    return '\n\n'.join(parts)


def today_digest_text(user):
    """Утренняя сводка: заседания/события, задачи на сегодня, горящие сроки."""
    from django.utils import timezone
    from django.db.models import Q
    from apps.tasks.models import Task, Event
    from apps.cases.models import Case
    from common.scoping import scope_cases
    import datetime as dt

    today = timezone.localdate()
    day_start = timezone.make_aware(dt.datetime.combine(today, dt.time.min))
    day_end = timezone.make_aware(dt.datetime.combine(today, dt.time.max))

    events = list(
        Event.objects.filter(start_datetime__range=(day_start, day_end))
        .filter(Q(attendees=user) | Q(case__assigned_lawyers=user) |
                Q(case__lead_lawyer=user) | Q(created_by=user))
        .select_related('case').distinct().order_by('start_datetime')[:LIST_LIMIT]
    )
    tasks = list(
        Task.objects.filter(assigned_to=user, status__in=['todo', 'in_progress'],
                            due_date=today).select_related('case')[:LIST_LIMIT]
    )
    hot = list(
        scope_cases(Case.objects.filter(
            key_deadline__isnull=False,
            key_deadline__lte=today + timedelta(days=DIGEST_DEADLINE_DAYS),
            status__in=['new', 'active', 'on_hold'],
        ), user).order_by('key_deadline')[:LIST_LIMIT]
    )

    if not events and not tasks and not hot:
        return f'☀️ Доброе утро\\! На {_fmt_date(today)} ничего не запланировано 🎉'

    parts = [f'☀️ *Доброе утро\\! Сводка на {_fmt_date(today)}:*']
    if events:
        lines = []
        for e in events:
            t = timezone.localtime(e.start_datetime).strftime('%H:%M')
            line = f'▫️ {esc(t)} — {esc(e.title)} \\({esc(e.get_event_type_display())}\\)'
            if e.location:
                line += f'\n   📍 {esc(e.location)}'
            lines.append(line)
        parts.append('*События сегодня:*\n' + block(lines))
    if tasks:
        parts.append('*Задачи на сегодня:*\n' + block(
            [f'▫️ {esc(t.title)}' for t in tasks]))
    if hot:
        parts.append('*Горящие сроки:*\n' + block([
            f'❗️ {_fmt_date(c.key_deadline)} — {esc(c.title)} \\({_days_left(c.key_deadline)}\\)'
            for c in hot]))
    return '\n\n'.join(parts)


# ── sync-логика inline-кнопок ─────────────────────────────────────────────

def complete_task_via_chat(chat_id, task_id):
    """Кнопка «Выполнено». Возвращает текст ответа для пользователя."""
    from django.utils import timezone
    from apps.tasks.models import Task
    from common.scoping import user_can_access_case

    user = get_user_by_chat(chat_id)
    if not user:
        return None
    try:
        task = Task.objects.select_related('case').get(pk=task_id)
    except Task.DoesNotExist:
        return 'Задача уже удалена.'
    allowed = task.assigned_to_id == user.pk or user.is_admin or \
        (task.case_id and user_can_access_case(user, task.case))
    if not allowed:
        return 'Эта задача вам недоступна.'
    if task.status == 'done':
        return 'Задача уже была выполнена.'
    task.status = Task.STATUS_DONE
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at', 'updated_at'])
    return f'Задача «{task.title}» отмечена выполненной ✅'


def snooze_task_via_chat(chat_id, task_id):
    """Кнопка «+1 день» к сроку задачи."""
    from apps.tasks.models import Task
    from common.scoping import user_can_access_case

    user = get_user_by_chat(chat_id)
    if not user:
        return None
    try:
        task = Task.objects.select_related('case').get(pk=task_id)
    except Task.DoesNotExist:
        return 'Задача уже удалена.'
    allowed = task.assigned_to_id == user.pk or user.is_admin or \
        (task.case_id and user_can_access_case(user, task.case))
    if not allowed:
        return 'Эта задача вам недоступна.'
    base = task.due_date or date.today()
    task.due_date = max(base, date.today()) + timedelta(days=1)
    task.save(update_fields=['due_date', 'updated_at'])
    return f'Срок задачи перенесён на {task.due_date.strftime("%d.%m.%Y")} ⏰'


def link_account(token, chat_id):
    from apps.accounts.telegram_link import use_link_token
    return use_link_token(token, chat_id)


# ── aiogram-обвязка ──────────────────────────────────────────────────────

async def run_polling(token):
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import Command, CommandStart
    from aiogram.filters.command import CommandObject
    from aiogram.types import Message, CallbackQuery

    bot = Bot(token)
    dp = Dispatcher()
    MD = 'MarkdownV2'

    async def reply_for(message, builder, *args):
        user = await sync_to_async(get_user_by_chat)(message.chat.id)
        if not user:
            await message.answer(NOT_LINKED_TEXT, parse_mode=MD)
            return
        text = await sync_to_async(builder)(user, *args)
        await message.answer(text, parse_mode=MD)

    @dp.message(CommandStart())
    async def start(message: Message, command: CommandObject):
        payload = (command.args or '').strip()
        if payload:
            user = await sync_to_async(link_account)(payload, message.chat.id)
            if user:
                name = user.get_full_name() or user.username
                await message.answer(
                    f'✅ Telegram привязан к аккаунту *{esc(name)}*\\.\n\n{HELP_TEXT}',
                    parse_mode=MD)
            else:
                await message.answer(
                    'Ссылка недействительна или устарела\\. '
                    'Сгенерируйте новую в профиле CRM\\.', parse_mode=MD)
            return
        await message.answer(HELP_TEXT, parse_mode=MD)

    @dp.message(Command('help'))
    async def help_cmd(message: Message):
        await message.answer(HELP_TEXT, parse_mode=MD)

    @dp.message(Command('today'))
    async def today(message: Message):
        await reply_for(message, today_digest_text)

    @dp.message(Command('tasks'))
    async def tasks(message: Message):
        await reply_for(message, tasks_text)

    @dp.message(Command('cases'))
    async def cases(message: Message):
        await reply_for(message, cases_text)

    @dp.message(Command('deadlines'))
    async def deadlines(message: Message):
        await reply_for(message, deadlines_text)

    @dp.message(Command('hours'))
    async def hours(message: Message):
        await reply_for(message, hours_text)

    @dp.message(Command('find'))
    async def find(message: Message, command: CommandObject):
        user = await sync_to_async(get_user_by_chat)(message.chat.id)
        if not user:
            await message.answer(NOT_LINKED_TEXT, parse_mode=MD)
            return
        text = await sync_to_async(find_text)(user, command.args or '')
        await message.answer(text, parse_mode=MD)

    @dp.callback_query(F.data.startswith('task_done:'))
    async def cb_task_done(cb: CallbackQuery):
        task_id = cb.data.split(':', 1)[1]
        result = await sync_to_async(complete_task_via_chat)(cb.from_user.id, task_id)
        await cb.answer(result or 'Аккаунт не привязан.', show_alert=result is None)
        if result and 'выполненной' in result:
            try:
                await cb.message.edit_reply_markup(reply_markup=None)
            except Exception:  # noqa: BLE001 — сообщение могло устареть
                pass

    @dp.callback_query(F.data.startswith('task_snooze:'))
    async def cb_task_snooze(cb: CallbackQuery):
        task_id = cb.data.split(':', 1)[1]
        result = await sync_to_async(snooze_task_via_chat)(cb.from_user.id, task_id)
        await cb.answer(result or 'Аккаунт не привязан.', show_alert=result is None)

    await dp.start_polling(bot)
