"""Заполнение БД демонстрационными данными.

Покрывает основной функционал для показа: пользователи, клиенты, дела,
заметки, документы, задачи, события календаря, учёт времени, счета,
уведомления и переписка.

Использование:
    python manage.py seed_demo            # добавить демо-данные
    python manage.py seed_demo --clear    # очистить прежние данные и заполнить заново
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.audit.models import ActivityLog
from apps.billing.models import Invoice, InvoiceItem, TimeEntry
from apps.cases.models import Case, CaseNote
from apps.chat.models import ChatMessage
from apps.clients.models import Client, ContactPerson
from apps.documents.models import Document
from apps.notifications.models import Notification
from apps.tasks.models import Event, Task

DEMO_PASSWORD = 'demo12345'


class Command(BaseCommand):
    help = 'Заполняет базу демонстрационными данными для показа'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить существующие данные (кроме суперпользователей) перед заполнением',
        )
        parser.add_argument(
            '--skip-if-exists',
            action='store_true',
            help='Ничего не делать, если демо-данные уже есть (для автозапуска в docker)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['skip_if_exists'] and Client.objects.exists():
            self.stdout.write('Демо-данные уже существуют — пропускаю.')
            return

        random.seed(42)
        self.today = timezone.localdate()
        self.now = timezone.now()

        # Отключаем WS-сигнал уведомлений на время сидинга: без запущенного
        # ASGI/Redis он висит на таймауте, а нужные уведомления команда
        # создаёт сама в _create_notifications().
        from django.db.models.signals import post_save
        from apps.notifications.signals import notify_task_assignee
        post_save.disconnect(notify_task_assignee, sender=Task)

        if options['clear']:
            self._clear()

        users = self._create_users()
        clients = self._create_clients(users)
        cases = self._create_cases(users, clients)
        self._create_case_notes(cases, users)
        self._create_documents(cases, users)
        self._create_tasks(cases, users)
        self._create_events(cases, users)
        entries = self._create_time_entries(cases, users)
        self._create_invoices(cases, entries, users)
        self._create_notifications(users, cases)
        self._create_chat(users)

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово! Создано: пользователей {CustomUser.objects.count()}, '
            f'клиентов {Client.objects.count()}, дел {Case.objects.count()}, '
            f'задач {Task.objects.count()}, событий {Event.objects.count()}, '
            f'записей времени {TimeEntry.objects.count()}, счетов {Invoice.objects.count()}, '
            f'документов {Document.objects.count()}.'
        ))
        self.stdout.write(self.style.WARNING(
            f'Демо-пользователи (пароль у всех: {DEMO_PASSWORD}):\n'
            '  director — администратор\n'
            '  ivanov, petrova, sidorov — юристы'
        ))

    # ------------------------------------------------------------------ helpers
    def _clear(self):
        self.stdout.write('Очистка прежних данных...')
        ActivityLog.objects.all().delete()
        Notification.objects.all().delete()
        ChatMessage.objects.all().delete()
        InvoiceItem.objects.all().delete()
        Invoice.objects.all().delete()
        TimeEntry.objects.all().delete()
        Document.objects.all().delete()
        CaseNote.objects.all().delete()
        Task.objects.all().delete()
        Event.objects.all().delete()
        Case.objects.all().delete()
        ContactPerson.objects.all().delete()
        Client.objects.all().delete()
        CustomUser.objects.filter(is_superuser=False).delete()

    # ------------------------------------------------------------------ users
    def _create_users(self):
        self.stdout.write('Создание пользователей...')
        specs = [
            ('director', 'Анна', 'Воронцова', CustomUser.ROLE_ADMIN, '+7 (495) 100-10-01'),
            ('ivanov', 'Дмитрий', 'Иванов', CustomUser.ROLE_LAWYER, '+7 (495) 100-10-02'),
            ('petrova', 'Елена', 'Петрова', CustomUser.ROLE_LAWYER, '+7 (495) 100-10-03'),
            ('sidorov', 'Михаил', 'Сидоров', CustomUser.ROLE_LAWYER, '+7 (495) 100-10-04'),
        ]
        users = {}
        for username, first, last, role, phone in specs:
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': role,
                    'phone': phone,
                    'email': f'{username}@nuances.law',
                    'is_staff': role == CustomUser.ROLE_ADMIN,
                    'is_superuser': role == CustomUser.ROLE_ADMIN,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[username] = user
        return users

    # ------------------------------------------------------------------ clients
    def _create_clients(self, users):
        self.stdout.write('Создание клиентов...')
        admin = users['director']
        individuals = [
            ('Смирнов', 'Алексей', 'Викторович', 'a.smirnov@mail.ru', '+7 (916) 200-30-01'),
            ('Кузнецова', 'Ольга', 'Сергеевна', 'o.kuznetsova@mail.ru', '+7 (916) 200-30-02'),
            ('Морозов', 'Павел', 'Андреевич', 'p.morozov@mail.ru', '+7 (916) 200-30-03'),
            ('Новикова', 'Татьяна', 'Игоревна', 't.novikova@mail.ru', '+7 (916) 200-30-04'),
        ]
        companies = [
            ('ООО «ТехноСтрой»', '1027700123456', 'info@technostroy.ru', '+7 (495) 300-40-01'),
            ('АО «Северные Логистика»', '1057800234567', 'office@nordlog.ru', '+7 (812) 300-40-02'),
            ('ООО «Грин Энерджи»', '1147700345678', 'mail@greenenergy.ru', '+7 (495) 300-40-03'),
            ('ИП Фёдоров Р.К.', '316774600012345', 'fedorov.ip@mail.ru', '+7 (495) 300-40-04'),
        ]
        clients = []
        for last, first, middle, email, phone in individuals:
            clients.append(Client.objects.create(
                client_type=Client.TYPE_INDIVIDUAL,
                first_name=first, last_name=last, middle_name=middle,
                email=email, phone=phone, created_by=admin,
                tax_id=str(random.randint(100000000000, 999999999999)),
            ))
        for name, ogrn, email, phone in companies:
            c = Client.objects.create(
                client_type=Client.TYPE_LEGAL,
                company_name=name, registration_number=ogrn,
                email=email, phone=phone, created_by=admin,
                tax_id=str(random.randint(1000000000, 9999999999)),
                legal_address='г. Москва, ул. Тверская, д. 1',
            )
            ContactPerson.objects.create(
                client=c, first_name='Сергей', last_name='Директоров',
                position='Генеральный директор', phone=phone, email=email, is_primary=True,
            )
            clients.append(c)
        return clients

    # ------------------------------------------------------------------ cases
    def _create_cases(self, users, clients):
        self.stdout.write('Создание дел...')
        lawyers = [users['ivanov'], users['petrova'], users['sidorov']]
        admin = users['director']
        data = [
            ('Взыскание задолженности по договору поставки', Case.CATEGORY_CIVIL, Case.STATUS_ACTIVE),
            ('Расторжение брака и раздел имущества', Case.CATEGORY_FAMILY, Case.STATUS_ACTIVE),
            ('Трудовой спор о восстановлении на работе', Case.CATEGORY_LABOR, Case.STATUS_NEW),
            ('Банкротство юридического лица', Case.CATEGORY_BANKRUPTCY, Case.STATUS_ACTIVE),
            ('Защита по уголовному делу (ст. 159 УК РФ)', Case.CATEGORY_CRIMINAL, Case.STATUS_ON_HOLD),
            ('Корпоративный спор между учредителями', Case.CATEGORY_CORPORATE, Case.STATUS_ACTIVE),
            ('Оспаривание права собственности на участок', Case.CATEGORY_PROPERTY, Case.STATUS_NEW),
            ('Сопровождение сделки купли-продажи недвижимости', Case.CATEGORY_PROPERTY, Case.STATUS_CLOSED),
            ('Защита деловой репутации', Case.CATEGORY_CIVIL, Case.STATUS_CLOSED),
            ('Налоговый спор с ФНС', Case.CATEGORY_CORPORATE, Case.STATUS_ARCHIVED),
        ]
        cases = []
        for i, (title, category, status) in enumerate(data):
            client = clients[i % len(clients)]
            lead = lawyers[i % len(lawyers)]
            opened = self.today - timedelta(days=random.randint(20, 400))
            case = Case.objects.create(
                title=title, client=client, category=category, status=status,
                description=f'Дело по вопросу: {title.lower()}. Клиент: {client.display_name}.',
                lead_lawyer=lead, opened_at=opened, created_by=admin,
                hourly_rate=Decimal(random.choice([4000, 5000, 6000, 7500])),
                court_name='Арбитражный суд г. Москвы' if category in (
                    Case.CATEGORY_CORPORATE, Case.CATEGORY_BANKRUPTCY) else 'Замоскворецкий районный суд',
                court_case_number=f'А40-{random.randint(10000, 99999)}/2026',
                expected_close_date=self.today + timedelta(days=random.randint(30, 180)),
            )
            assigned = random.sample(lawyers, k=random.randint(1, 2))
            if lead not in assigned:
                assigned.append(lead)
            case.assigned_lawyers.set(assigned)
            if status in (Case.STATUS_CLOSED, Case.STATUS_ARCHIVED):
                case.closed_at = opened + timedelta(days=random.randint(30, 120))
                case.save(update_fields=['closed_at'])
            cases.append(case)
        return cases

    # ------------------------------------------------------------------ notes
    def _create_case_notes(self, cases, users):
        self.stdout.write('Создание заметок по делам...')
        lawyers = [users['ivanov'], users['petrova'], users['sidorov']]
        samples = [
            'Созвонился с клиентом, уточнил детали по договору.',
            'Подготовлен черновик искового заявления, направлен на проверку.',
            'Получены документы от противоположной стороны.',
            'Суд перенёс заседание на следующую неделю.',
            'Клиент предоставил дополнительные доказательства.',
            'Согласована позиция по делу с командой.',
        ]
        for case in cases[:7]:
            for _ in range(random.randint(1, 3)):
                CaseNote.objects.create(
                    case=case, author=random.choice(lawyers),
                    text=random.choice(samples),
                )

    # ------------------------------------------------------------------ documents
    def _create_documents(self, cases, users):
        self.stdout.write('Создание документов...')
        lawyers = [users['ivanov'], users['petrova'], users['sidorov']]
        templates = [
            ('Договор оказания юридических услуг.pdf', Document.TYPE_CONTRACT),
            ('Доверенность на представление интересов.pdf', Document.TYPE_POA),
            ('Исковое заявление.pdf', Document.TYPE_COURT_FILING),
            ('Письмо-претензия.pdf', Document.TYPE_CORRESPONDENCE),
        ]
        for case in cases:
            for title, dtype in random.sample(templates, k=random.randint(1, 3)):
                content = ContentFile(
                    f'Демонстрационный документ\nДело: {case.title}\nТип: {title}'.encode('utf-8'),
                    name=title,
                )
                Document.objects.create(
                    case=case, title=title, document_type=dtype,
                    file=content, uploaded_by=random.choice(lawyers),
                    description='Демо-документ для показа.',
                )

    # ------------------------------------------------------------------ tasks
    def _create_tasks(self, cases, users):
        self.stdout.write('Создание задач...')
        lawyers = [users['ivanov'], users['petrova'], users['sidorov']]
        admin = users['director']
        titles = [
            'Подготовить исковое заявление',
            'Собрать пакет документов',
            'Направить запрос в госорган',
            'Подготовиться к судебному заседанию',
            'Составить договор',
            'Провести встречу с клиентом',
            'Изучить материалы дела',
            'Подать апелляционную жалобу',
            'Согласовать стратегию защиты',
            'Проверить контрагента',
        ]
        priorities = [Task.PRIORITY_LOW, Task.PRIORITY_MEDIUM, Task.PRIORITY_HIGH, Task.PRIORITY_URGENT]
        active_cases = [c for c in cases if c.status in (Case.STATUS_ACTIVE, Case.STATUS_NEW, Case.STATUS_ON_HOLD)]
        for i in range(16):
            case = random.choice(active_cases)
            status = random.choices(
                [Task.STATUS_TODO, Task.STATUS_IN_PROGRESS, Task.STATUS_DONE, Task.STATUS_CANCELLED],
                weights=[40, 30, 25, 5],
            )[0]
            # mix of overdue, today, and upcoming deadlines
            offset = random.randint(-10, 21)
            due = self.today + timedelta(days=offset)
            task = Task.objects.create(
                title=random.choice(titles),
                description='Демо-задача для показа функционала.',
                case=case,
                assigned_to=random.choice(lawyers),
                created_by=admin,
                priority=random.choice(priorities),
                status=status,
                due_date=due,
            )
            if status == Task.STATUS_DONE:
                task.completed_at = self.now - timedelta(days=random.randint(1, 5))
                task.save(update_fields=['completed_at'])

    # ------------------------------------------------------------------ events
    def _create_events(self, cases, users):
        self.stdout.write('Создание событий календаря...')
        lawyers = [users['ivanov'], users['petrova'], users['sidorov']]
        admin = users['director']
        active_cases = [c for c in cases if c.status in (Case.STATUS_ACTIVE, Case.STATUS_NEW, Case.STATUS_ON_HOLD)]
        specs = [
            ('Судебное заседание', Event.TYPE_HEARING, 'Зал № 305, Арбитражный суд г. Москвы'),
            ('Встреча с клиентом', Event.TYPE_MEETING, 'Офис, переговорная'),
            ('Срок подачи апелляции', Event.TYPE_DEADLINE, ''),
            ('Предварительное слушание', Event.TYPE_HEARING, 'Замоскворецкий районный суд'),
            ('Консультация', Event.TYPE_MEETING, 'Онлайн (Zoom)'),
            ('Дедлайн по документам', Event.TYPE_DEADLINE, ''),
        ]
        for i in range(12):
            title, etype, location = random.choice(specs)
            case = random.choice(active_cases)
            day_offset = random.randint(-7, 21)
            start = self.now + timedelta(days=day_offset, hours=random.randint(-5, 6))
            start = start.replace(minute=0, second=0, microsecond=0)
            all_day = etype == Event.TYPE_DEADLINE
            event = Event.objects.create(
                title=title, event_type=etype, case=case,
                description=f'{title} по делу «{case.title}».',
                location=location, start_datetime=start,
                end_datetime=None if all_day else start + timedelta(hours=2),
                all_day=all_day, created_by=admin,
            )
            event.attendees.set(random.sample(lawyers, k=random.randint(1, 2)))

    # ------------------------------------------------------------------ time entries
    def _create_time_entries(self, cases, users):
        self.stdout.write('Создание записей учёта времени...')
        lawyers = [users['ivanov'], users['petrova'], users['sidorov']]
        descriptions = [
            'Анализ документов и материалов дела',
            'Подготовка процессуальных документов',
            'Участие в судебном заседании',
            'Консультация клиента',
            'Переговоры с противоположной стороной',
            'Составление правовой позиции',
        ]
        entries = []
        for case in cases:
            for _ in range(random.randint(3, 8)):
                lawyer = case.lead_lawyer or random.choice(lawyers)
                entry = TimeEntry.objects.create(
                    case=case, lawyer=lawyer,
                    date=self.today - timedelta(days=random.randint(1, 90)),
                    hours=Decimal(random.choice(['0.50', '1.00', '1.50', '2.00', '3.00', '4.00'])),
                    description=random.choice(descriptions),
                    hourly_rate=case.hourly_rate or Decimal('5000'),
                    is_billable=random.random() > 0.15,
                )
                entries.append(entry)
        return entries

    # ------------------------------------------------------------------ invoices
    def _create_invoices(self, cases, entries, users):
        self.stdout.write('Создание счетов...')
        admin = users['director']
        # статусы для разнообразия демо
        plan = [
            Invoice.STATUS_PAID,
            Invoice.STATUS_PAID,
            Invoice.STATUS_SENT,
            Invoice.STATUS_OVERDUE,
            Invoice.STATUS_DRAFT,
            Invoice.STATUS_SENT,
        ]
        billable_cases = [c for c in cases if c.time_entries.filter(is_billable=True, invoice__isnull=True).exists()]
        for status in plan:
            if not billable_cases:
                break
            case = billable_cases.pop(0)
            issue = self.today - timedelta(days=random.randint(5, 60))
            if status == Invoice.STATUS_OVERDUE:
                due = self.today - timedelta(days=random.randint(3, 20))
            else:
                due = issue + timedelta(days=14)
            invoice = Invoice.objects.create(
                case=case, client=case.client, status=status,
                issue_date=issue, due_date=due, tax_rate=Decimal('20.00'),
                created_by=admin, notes='Оплата в течение 14 дней с даты выставления.',
            )
            case_entries = list(case.time_entries.filter(is_billable=True, invoice__isnull=True))
            for entry in case_entries:
                item = InvoiceItem.objects.create(
                    invoice=invoice,
                    description=f'{entry.date} — {entry.description}',
                    quantity=entry.hours, unit_price=entry.hourly_rate,
                    amount=entry.amount, time_entry=entry,
                )
                entry.invoice = invoice
                entry.save(update_fields=['invoice'])
            invoice.recalculate_totals()
            if status == Invoice.STATUS_PAID:
                invoice.paid_date = due - timedelta(days=random.randint(1, 10))
                invoice.save(update_fields=['paid_date'])

    # ------------------------------------------------------------------ notifications
    def _create_notifications(self, users, cases):
        self.stdout.write('Создание уведомлений...')
        for username in ('ivanov', 'petrova', 'sidorov'):
            user = users[username]
            case = random.choice(cases)
            Notification.objects.create(
                user=user, title='Приближается дедлайн',
                body=f'Через 2 дня срок по делу «{case.title}».',
                link=f'/cases/{case.id}', is_read=False,
            )
            Notification.objects.create(
                user=user, title='Назначена новая задача',
                body='Вам назначена задача по активному делу.',
                link='/tasks', is_read=random.choice([True, False]),
            )

    # ------------------------------------------------------------------ chat
    def _create_chat(self, users):
        self.stdout.write('Создание сообщений чата...')
        director, ivanov, petrova = users['director'], users['ivanov'], users['petrova']
        msgs = [
            (director, ivanov, 'Дмитрий, как продвигается дело по взысканию задолженности?'),
            (ivanov, director, 'Готовлю исковое, к пятнице будет готово.'),
            (director, petrova, 'Елена, не забудьте про заседание в среду.'),
            (petrova, director, 'Спасибо, уже готовлюсь.'),
        ]
        for sender, recipient, text in msgs:
            ChatMessage.objects.create(user=sender, recipient=recipient, text=text)
