from django.urls import path
from . import views, reports

urlpatterns = [
    path('billing/time-entries/export/', views.time_entries_csv_view, name='time-entry-export'),
    path('billing/invoices/export/', views.invoices_csv_view, name='invoice-export'),
    path('billing/time-entries/', views.TimeEntryListCreateView.as_view(), name='time-entry-list'),
    path('billing/time-entries/summary/', views.time_entry_summary_view, name='time-entry-summary'),
    path('billing/monthly-stats/', views.billing_monthly_stats_view, name='billing-monthly-stats'),
    path('billing/time-entries/<int:pk>/', views.TimeEntryDetailView.as_view(), name='time-entry-detail'),
    path('billing/invoices/', views.InvoiceListCreateView.as_view(), name='invoice-list'),
    path('billing/invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('billing/invoices/<int:pk>/generate-from-entries/', views.generate_from_entries_view, name='invoice-generate'),
    path('billing/invoices/<int:pk>/mark-sent/', views.mark_sent_view, name='invoice-mark-sent'),
    path('billing/invoices/<int:pk>/mark-paid/', views.mark_paid_view, name='invoice-mark-paid'),
    path('billing/invoices/<int:pk>/send-email/', views.send_invoice_email_view, name='invoice-send-email'),
    path('billing/invoices/<int:pk>/pdf/', views.invoice_pdf_view, name='invoice-pdf'),
    path('billing/invoice-items/', views.InvoiceItemListCreateView.as_view(), name='invoice-item-list'),
    path('billing/invoice-items/<int:pk>/', views.InvoiceItemDetailView.as_view(), name='invoice-item-detail'),
    path('billing/reports/', reports.reports_view, name='billing-reports'),
]
