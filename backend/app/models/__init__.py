from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.commission_rate import CommissionRate
from app.models.recruit import Recruit
from app.models.paying_company import PayingCompany
from app.models.company_contact import CompanyContact
from app.models.subscription import Subscription
from app.models.portal_link import CustomerPortalLink
from app.models.portal_snapshot import PortalSnapshot
from app.models.agent_portal_offer import AgentPortalOffer, PortalOfferClick
from app.models.volume_commission_rate import VolumeCommissionRate
from app.models.volume_bonus_payment import VolumeBonusPayment
from app.models.production_summary import ProductionSummary
from app.models.debt import Debt
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.portal_run_batch import PortalRunBatch
from app.models.otp_inbox import OtpInbox
from app.models.agent_twilio_number import AgentTwilioNumber
from app.models.ai_document import AiDocument
from app.models.commission_comparison import CommissionComparison
from app.models.fund_track import FundTrack
from app.models.fund_track_fund import FundTrackFund
from app.models.yield_recommendation import YieldRecommendation
from app.models.pension_inquiry import PensionInquiry
from app.models.pension_holding import PensionHolding
from app.models.pension_audit import PensionAuditLog, PensionRawPayload
from app.models.maslaka_agent_link import MaslakaAgentLink
from app.models.sms_otp_template import SmsOtpTemplate
from app.models.worker_heartbeat import WorkerHeartbeat
from app.models.dm_conversation import DmConversation
from app.models.dm_message import DmMessage
from app.models.dm_presence import DmPresence
from app.models.mailbox_config import MailboxConfig
from app.models.mailbox_message import MailboxProcessedMessage
from app.models.mail_watch_sender import MailWatchSender
from app.models.mail_item import MailItem
from app.models.ai_usage import AiUsage
from app.models.mail_agent_profile import MailAgentProfile
from app.models.mail_agent_gap import MailAgentGap
from app.models.cycle_notification import CycleNotification
from app.models.agreement_request import AgreementRequest
from app.models.collection_case import CollectionCase
from app.models.ai_memory import AiMemory, AiIntentLog
from app.models.fund_market import FundMarketMonthly
from app.models.call_recording import CallRecording

# every process that loads the models (API, local worker, scripts) bumps users.ai_data_version on AI-relevant writes
from app.services.agent.versioning import register_listeners as _register_ai_version_listeners  # noqa: E402
_register_ai_version_listeners()

__all__ = ["User", "FileUpload", "ClientRecord", "CommissionRate", "Recruit", "PayingCompany", "CompanyContact", "Subscription", "CustomerPortalLink", "PortalSnapshot", "AgentPortalOffer", "PortalOfferClick", "VolumeCommissionRate", "VolumeBonusPayment", "ProductionSummary", "Debt", "PortalCredential", "PortalRun", "PortalRunBatch", "OtpInbox", "AgentTwilioNumber", "AiDocument", "CommissionComparison", "FundTrack", "FundTrackFund", "YieldRecommendation", "PensionInquiry", "PensionHolding", "PensionAuditLog", "PensionRawPayload", "MaslakaAgentLink", "SmsOtpTemplate", "WorkerHeartbeat", "DmConversation", "DmMessage", "DmPresence", "MailboxConfig", "MailboxProcessedMessage"]
from app.models.walkin_customer import WalkinCustomer
from app.models.blocked_phone import BlockedPhone
from app.models.harb_request import HarbRequest
from app.models.insurance_policy import InsurancePolicy
from app.models.policy_document import PolicyDocument
from app.models.gateway_state import GatewayState
