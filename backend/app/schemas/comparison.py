from pydantic import BaseModel


class ProductionProduct(BaseModel):
    product: str | None = None
    product_type: str | None = None
    company: str | None = None
    company_full: str | None = None
    premium: float | None = None
    policy_number: str | None = None
    status: str | None = None
    accumulation: float | None = None
    sign_date: str | None = None
    track: str | None = None
    client_phone: str | None = None
    client_email: str | None = None
    employer_name: str | None = None
    employer_id: str | None = None


class CommissionProduct(BaseModel):
    product: str | None = None
    account: str | None = None
    balance: float | None = None
    commission: float | None = None
    annual_pct: float | None = None
    monthly_pct: float | None = None
    fund_type: str | None = None
    management_fee: float | None = None
    management_fee_amount: float | None = None


class ProductMatch(BaseModel):
    policy_number: str | None = None
    production_product: str | None = None
    commission_product: str | None = None
    company: str | None = None
    premium: float | None = None
    accumulation: float | None = None
    commission: float | None = None
    balance: float | None = None
    monthly_pct: float | None = None
    annual_pct: float | None = None
    track: str | None = None
    management_fee: float | None = None
    management_fee_amount: float | None = None


class PaymentStatusUpdate(BaseModel):
    id_number: str
    policy_number: str
    paid: bool


class UnmatchedProduction(BaseModel):
    product: str | None = None
    product_type: str | None = None
    company: str | None = None
    company_full: str | None = None
    premium: float | None = None
    policy_number: str | None = None
    accumulation: float | None = None
    sign_date: str | None = None
    track: str | None = None
    client_phone: str | None = None
    client_email: str | None = None
    employer_name: str | None = None
    employer_id: str | None = None


class UnmatchedCommission(BaseModel):
    product: str | None = None
    account: str | None = None
    commission: float | None = None
    balance: float | None = None
    company: str | None = None
    fund_type: str | None = None


class ProductMatchResult(BaseModel):
    matched: list[ProductMatch] = []
    unmatched_production: list[UnmatchedProduction] = []
    unmatched_commission: list[UnmatchedCommission] = []


class ComparisonCustomer(BaseModel):
    id_number: str
    first_name: str | None = None
    last_name: str | None = None
    match_status: str
    production_count: int = 0
    commission_count: int = 0
    paid_count: int = 0
    unpaid_count: int = 0
    total_premium: float = 0
    total_commission: float = 0
    has_paying_company: bool = False
    client_phone: str | None = None
    client_email: str | None = None
    employer_name: str | None = None
    employer_id: str | None = None
    production_products: list[ProductionProduct] = []
    commission_products: list[CommissionProduct] = []
    product_matches: ProductMatchResult = ProductMatchResult()


class ComparisonSummary(BaseModel):
    total_customers: int = 0
    matched: int = 0
    only_in_production: int = 0
    only_in_commission: int = 0
    total_premium: float = 0
    total_commission: float = 0


class ComparisonResponse(BaseModel):
    summary: ComparisonSummary
    customers: list[ComparisonCustomer]
    available_companies: list[str] = []
    commission_company_source: str | None = None
    commission_company_sources: list[str] = []
    commission_category: str | None = None
    commission_category_label: str | None = None
