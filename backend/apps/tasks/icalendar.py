"""Сборка ICS-фида (RFC 5545) без внешних зависимостей — формат простой,
а лишняя библиотека на слабом сервере не нужна.
"""
import datetime as dt
from datetime import timedelta

from django.utils import timezone

PRODID = '-//Nuances CRM//Calendar Feed//RU'


def _escape(text):
    return (str(text or '')
            .replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\r\n', '\\n')
            .replace('\n', '\\n'))


def _fold(line):
    """RFC 5545: строки длиннее 75 октетов переносятся с ведущим пробелом."""
    raw = line.encode('utf-8')
    if len(raw) <= 75:
        return line
    chunks, start = [], 0
    limit = 73
    while start < len(raw):
        end = min(start + limit, len(raw))
        # граница должна попадать между символами: пока следующий байт —
        # продолжение многобайтового символа (10xxxxxx), сдвигаем назад
        while end > start + 1 and end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        chunks.append(raw[start:end].decode('utf-8'))
        start = end
    return '\r\n '.join(chunks)


def _utc(value):
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value.astimezone(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def build_calendar(name, events):
    """events: список dict(uid, summary, start, end, all_day, description, location, alarm_minutes)."""
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        f'PRODID:{PRODID}',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_escape(name)}',
        'X-WR-TIMEZONE:Europe/Moscow',
    ]
    stamp = _utc(timezone.now())

    for e in events:
        lines.append('BEGIN:VEVENT')
        lines.append(f'UID:{e["uid"]}')
        lines.append(f'DTSTAMP:{stamp}')
        if e.get('all_day'):
            day = e['start']
            end = e.get('end') or (day + timedelta(days=1))
            lines.append(f'DTSTART;VALUE=DATE:{day.strftime("%Y%m%d")}')
            lines.append(f'DTEND;VALUE=DATE:{end.strftime("%Y%m%d")}')
        else:
            start = e['start']
            end = e.get('end') or (start + timedelta(hours=1))
            lines.append(f'DTSTART:{_utc(start)}')
            lines.append(f'DTEND:{_utc(end)}')
        lines.append(f'SUMMARY:{_escape(e["summary"])}')
        if e.get('description'):
            lines.append(f'DESCRIPTION:{_escape(e["description"])}')
        if e.get('location'):
            lines.append(f'LOCATION:{_escape(e["location"])}')
        if e.get('alarm_minutes'):
            lines += [
                'BEGIN:VALARM',
                'ACTION:DISPLAY',
                f'DESCRIPTION:{_escape(e["summary"])}',
                f'TRIGGER:-PT{int(e["alarm_minutes"])}M',
                'END:VALARM',
            ]
        lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')
    return '\r\n'.join(_fold(l) for l in lines) + '\r\n'


def user_calendar_events(user):
    """События, процессуальные сроки и задачи пользователя для ICS."""
    from django.db.models import Q
    from apps.cases.models import Case
    from apps.tasks.models import Task, Event
    from common.scoping import scope_cases

    horizon_past = timezone.now() - timedelta(days=180)
    items = []

    events = (Event.objects
              .filter(start_datetime__gte=horizon_past)
              .filter(Q(attendees=user) | Q(case__assigned_lawyers=user) |
                      Q(case__lead_lawyer=user) | Q(created_by=user))
              .select_related('case').distinct())
    for ev in events:
        case_note = f'Дело: {ev.case.case_number} — {ev.case.title}' if ev.case_id else ''
        description = ' | '.join(filter(None, [ev.get_event_type_display(),
                                               ev.description, case_note]))
        items.append({
            'uid': f'event-{ev.id}@nuances-crm',
            'summary': ev.title,
            'start': ev.start_datetime.date() if ev.all_day else ev.start_datetime,
            'end': (ev.end_datetime.date() if ev.all_day and ev.end_datetime
                    else ev.end_datetime),
            'all_day': ev.all_day,
            'description': description,
            'location': ev.location,
            'alarm_minutes': 60 if not ev.all_day else None,
        })

    cases = scope_cases(
        Case.objects.filter(key_deadline__isnull=False,
                            status__in=['new', 'active', 'on_hold']), user)
    for case in cases:
        items.append({
            'uid': f'deadline-{case.uuid}@nuances-crm',
            'summary': f'⚖️ Срок: {case.title}',
            'start': case.key_deadline,
            'all_day': True,
            'description': ' | '.join(filter(None, [
                case.key_deadline_note, f'Дело: {case.case_number}'])),
            'alarm_minutes': None,
        })

    tasks = Task.objects.filter(
        assigned_to=user, due_date__isnull=False,
        status__in=['todo', 'in_progress']).select_related('case')
    for task in tasks:
        items.append({
            'uid': f'task-{task.id}@nuances-crm',
            'summary': f'✅ {task.title}',
            'start': task.due_date,
            'all_day': True,
            'description': ' | '.join(filter(None, [
                task.description,
                f'Дело: {task.case.case_number}' if task.case_id else ''])),
            'alarm_minutes': None,
        })

    return items
