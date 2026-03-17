from pydantic import BaseModel


class VolumeCommissionRateIn(BaseModel):
    company_name: str
    nifraim_rate: float | None = None
    volume_rate_per_million: float | None = None
    pension_accumulation: float | None = None
    changed_percent: float | None = None
    conversion_to_annuity: float | None = None
    payment_frequency: str | None = None
    paid_to: str | None = None
    notes: str | None = None


class VolumeCommissionRateOut(BaseModel):
    id: str
    company_name: str
    nifraim_rate: float | None
    volume_rate_per_million: float | None
    pension_accumulation: float | None
    changed_percent: float | None
    conversion_to_annuity: float | None
    payment_frequency: str | None
    paid_to: str | None
    notes: str | None

    model_config = {"from_attributes": True}


class VolumeCompareResponse(BaseModel):
    summary: dict
    matched: list[dict]
    in_production_only: list[dict]
    in_volume_only: list[dict]
    in_recruits_not_volume: list[dict]


class VolumeBonusResponse(BaseModel):
    companies: list[dict]
    grand_total: float
    warnings: list[str]


class VolumeBonusPaymentIn(BaseModel):
    company_name: str
    year: int
    is_paid: bool
    paid_date: str | None = None
    notes: str | None = None


class VolumeBonusPaymentOut(BaseModel):
    id: str
    company_name: str
    year: int
    is_paid: bool
    paid_date: str | None
    notes: str | None

    model_config = {"from_attributes": True}
