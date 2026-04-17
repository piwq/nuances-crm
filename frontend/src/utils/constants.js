export const CLIENT_TYPES = [
  { value: 'individual', label: 'Физическое лицо' },
  { value: 'legal_entity', label: 'Юридическое лицо' },
]

export const CASE_STATUSES = [
  { value: 'new', label: 'Новое', color: 'blue-grey' },
  { value: 'active', label: 'Активное', color: 'green' },
  { value: 'on_hold', label: 'Приостановлено', color: 'orange' },
  { value: 'closed', label: 'Закрыто', color: 'red' },
  { value: 'archived', label: 'В архиве', color: 'grey' },
]

export const CASE_CATEGORIES = [
  { value: 'civil', label: 'Гражданское' },
  { value: 'criminal', label: 'Уголовное' },
  { value: 'corporate', label: 'Корпоративное' },
  { value: 'family', label: 'Семейное' },
  { value: 'labor', label: 'Трудовое' },
  { value: 'property', label: 'Имущественное' },
  { value: 'bankruptcy', label: 'Банкротство' },
  { value: 'other', label: 'Прочее' },
]

export const TASK_PRIORITIES = [
  { value: 'low', label: 'Низкий', color: 'blue-grey' },
  { value: 'medium', label: 'Средний', color: 'blue' },
  { value: 'high', label: 'Высокий', color: 'orange' },
  { value: 'urgent', label: 'Срочно', color: 'red' },
]

export const TASK_STATUSES = [
  { value: 'todo', label: 'К выполнению', color: 'blue-grey' },
  { value: 'in_progress', label: 'В работе', color: 'blue' },
  { value: 'done', label: 'Выполнено', color: 'green' },
  { value: 'cancelled', label: 'Отменено', color: 'red' },
]

export const EVENT_TYPES = [
  { value: 'court_hearing', label: 'Судебное заседание', color: 'red' },
  { value: 'meeting', label: 'Встреча', color: 'blue' },
  { value: 'deadline', label: 'Дедлайн', color: 'orange' },
  { value: 'other', label: 'Прочее', color: 'grey' },
]

export const DOCUMENT_TYPES = [
  { value: 'contract', label: 'Договор' },
  { value: 'power_of_attorney', label: 'Доверенность' },
  { value: 'court_filing', label: 'Судебное обращение' },
  { value: 'evidence', label: 'Доказательство' },
  { value: 'correspondence', label: 'Переписка' },
  { value: 'other', label: 'Прочее' },
]

export const INVOICE_STATUSES = [
  { value: 'draft', label: 'Черновик', color: 'grey' },
  { value: 'sent', label: 'Отправлен', color: 'blue' },
  { value: 'paid', label: 'Оплачен', color: 'green' },
  { value: 'overdue', label: 'Просрочен', color: 'red' },
  { value: 'cancelled', label: 'Отменён', color: 'red' },
]

export const USER_ROLES = [
  { value: 'admin', label: 'Администратор' },
  { value: 'lawyer', label: 'Юрист' },
]
