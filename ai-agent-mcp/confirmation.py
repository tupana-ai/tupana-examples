"""Política de confirmación humana para las herramientas del MCP de Tupana.

Regla: TODO lo que no esté en la lista de solo lectura pide confirmación
(deny by default). Así, si el servidor agrega una herramienta nueva que escribe,
el agente no la ejecuta sin preguntarte.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

#: Herramientas que solo leen o calculan: se ejecutan sin preguntar.
READ_ONLY_TOOLS = frozenset(
    {
        # Documentos y clientes
        "get_documents",
        "search_documents",
        "get_document_link",
        "get_document_preview",
        "get_scheduled_documents",
        "find_clients",
        "get_entity_info",
        "enrich_client_from_rut",
        "get_suppliers",
        "get_top_clients",
        "get_top_products",
        "parse_document_to_invoice",
        # Reportes e impuestos
        "report_documents",
        "get_monthly_revenue",
        "get_sii_books",
        "get_f29_summary",
        "get_tax_summary",
        "generate_chart",
        "generate_multi_series_chart",
        # Cobranza y bancos (lectura)
        "get_pending_invoices",
        "get_bank_movements",
        "get_payment_documents",
        "get_reconciliation_suggestions",
        "get_reconciliations",
        # Contabilidad (lectura)
        "get_journal_entries",
        "get_ledger",
        "get_balance_sheet",
        "get_income_statement",
        "get_chart_of_accounts",
        "get_account_balance",
        # Guías y reglas
        "get_app_guide",
        "get_app_link",
        "list_capabilities",
        "how_to",
        "get_capabilities",
        "get_invoice_flow",
        "get_invoice_ui_spec",
        "get_invoice_validation_schema",
        "validate_invoice_draft",
        "get_customer_lookup_flow",
        "get_invoice_item_rules",
        "get_invoice_reference_rules",
        "get_invoice_preview_flow",
        "get_invoice_issuance_flow",
        "get_async_strategy",
        "get_integration_setup",
        "get_invoice_contract_findings",
        "get_error_resolution",
        "get_design_system",
        "get_tupana_connect_guide",
        # Base pública de empresas del SII
        "search_sii_companies",
        "find_growing_sii_companies",
        "get_sii_companies_metadata",
        "find_sii_prospects",
        "get_sii_company_history",
        "get_sii_market_summary",
    }
)

#: Herramientas cuyo efecto no se puede deshacer: se avisa con más fuerza.
IRREVERSIBLE_TOOLS = frozenset(
    {"emit_document", "send_document_email", "reconcile_movement", "create_journal_entry"}
)


def needs_confirmation(tool_name: str) -> bool:
    return tool_name not in READ_ONLY_TOOLS


def describe_call(tool_name: str, arguments: dict[str, Any]) -> str:
    header = (
        "ACCIÓN IRREVERSIBLE" if tool_name in IRREVERSIBLE_TOOLS else "Acción que modifica datos"
    )
    if tool_name == "emit_document":
        header = "EMISIÓN AL SII (irreversible: el documento queda emitido con folio)"
    pretty = json.dumps(arguments, ensure_ascii=False, indent=2)
    return f"\n⚠️  {header}\nHerramienta: {tool_name}\nArgumentos:\n{pretty}\n"


def ask_human(
    tool_name: str, arguments: dict[str, Any], prompt: Callable[[str], str] = input
) -> bool:
    """Muestra la llamada y pide un 'sí' explícito. Cualquier otra respuesta es no."""
    print(describe_call(tool_name, arguments))
    answer = prompt("¿Confirmas? Escribe 'si' para continuar: ").strip().lower()
    return answer in {"si", "sí", "s", "yes", "y"}


DECLINED_MESSAGE = (
    "El usuario NO autorizó esta acción. No la reintentes ni busques otra herramienta "
    "para lograr lo mismo; pregúntale qué quiere cambiar."
)
