"""Builds app/demo_data/osint_cache.json.

Every `content` block below is text retrieved from the cited public URL on
2026-10-06 during an analyst OSINT session (Firecrawl scrape, main-content
extraction, markdown formatting stripped). Nothing is paraphrased or invented.
Only the passages relevant to the assessment are retained — not full pages.

Sources with no AI content (vendor home pages) are kept on purpose: they are
part of the negative-evidence record (sources checked that showed nothing).
"""
import json
from pathlib import Path

RETRIEVED = "2026-10-06T16:30:00+00:00"
ORIGIN = "Analyst OSINT session snapshot, 2026-10-06 (Firecrawl scrape of public page; relevant passages retained verbatim)"

SOURCES = [
    # ------------------------------------------------------------------ V-001
    {
        "vendor_ref": "V-001",
        "found_by": ['ai_documentation', 'insights'],
        "url": "https://www.automworx.com/what-is-ai-enablement-in-automic-workload-automation/",
        "title": "What is AI Enablement in Automic Workload Automation? | AutomWorx",
        "published_date": "2025-08-26",
        "content": (
            "What is AI Enablement in Automic Workload Automation?\n\n"
            "The AI Revolution in Enterprise Automation\n\n"
            "AI enablement isn’t just about adding a new feature; it’s about creating a smarter, more proactive automation ecosystem. "
            "For enterprises using Automic, this means leveraging technologies like generative AI (GenAI), machine learning (ML), and predictive analytics to enhance existing automation workflows.\n\n"
            "Automate troubleshooting: When a job fails, the AI assistant can analyze logs and reports, identify the problem, and even suggest potential fixes, drastically reducing mean time to repair.\n\n"
            "Real-World Use Cases\n\n"
            "Automated Troubleshooting: A bank’s daily batch job fails. The AI assistant in Automic instantly analyzes the logs from the failed execution, explains the reason for the failure in plain English, and suggests a code snippet to fix the issue. The IT team can resolve the problem in minutes, not hours.\n\n"
            "Ready to get started? Contact us."
        ),
    },
    {
        "vendor_ref": "V-001",
        "found_by": ['ai_documentation', 'insights'],
        "url": "https://www.automworx.com/automic-automation-v26-turning-orchestration-into-the-control-center-for-enterprise-ai/",
        "title": "Automic Automation V26: Turning Orchestration Into the Control Center for Enterprise AI | AutomWorx",
        "published_date": "2026-09-17",
        "content": (
            "Automic Automation V26: Turning Orchestration Into the Control Center for Enterprise AI\n\n"
            "What’s Actually Different Day-to-Day\n\n"
            "AI Assistant, built on MCP. Automic’s AI layer connects to your models through the Model Context Protocol, acting as both client and server. "
            "Ask it what happened in last night’s run, and it parses logs, execution reports, and documentation to tell you not just what happened, but why root causes, upstream delays, similar fixes that worked before.\n\n"
            "Bring your own LLM. On SaaS, a default model comes built in. On-prem, you connect Automic to whichever LLM provider you already use cloud-hosted or a local model. Same governance either way. The model changes; the control layer doesn’t.\n\n"
            "AI-assisted scripting and workflow building. The AI Assistant explains, troubleshoots, and generates scripts on request, including converting a Python script to PowerShell on the spot. Natural-language workflow building is part of this too.\n\n"
            "What This Means for Your Operation\n\n"
            "At Automworx, we help teams evaluate, implement, and get real value out of Automic Automation V26, from migration to configuration for a live environment."
        ),
    },
    # ------------------------------------------------------------------ V-002
    {
        "vendor_ref": "V-002",
        "found_by": ['press_releases', 'ai_documentation', 'investor_disclosures'],
        "url": "https://investors.fiserv.com/news-releases/news-release-details/fiserv-collaborates-microsoft-accelerate-ai-driven-innovation",
        "title": "Fiserv Collaborates with Microsoft to Accelerate AI-Driven Innovation - Fiserv, Inc.",
        "published_date": "2026-01-08",
        "content": (
            "Fiserv Collaborates with Microsoft to Accelerate AI-Driven Innovation\n\n"
            "January 8, 2026\n\n"
            "Fiserv will deploy Microsoft 365 Copilot across its global workforce, equipping employees with access to advanced AI tools that enhance productivity, accelerate decision-making, and elevate the quality of work. "
            "In parallel, Fiserv is working with Microsoft to expand its use of Microsoft Foundry, an Azure-powered AI platform designed to build, customize, deploy, and manage AI applications safely and securely.\n\n"
            "This expanded relationship with Microsoft builds on Fiserv’s existing use of Microsoft Foundry and deployment of Microsoft’s GitHub Copilot. "
            "To date, Fiserv has processed more than 100 billion tokens in Foundry, enhancing products, client servicing experiences, and its proprietary developer gateway.\n\n"
            "Deepening Investment in AI\n\n"
            "Across Fiserv, AI already powers fraud detection, risk management, and personalized engagement for financial institutions; enables smarter decisioning and higher authorization rates for merchants; and improves client servicing, compliance, and developer productivity.\n\n"
            "Forward-Looking Statements\n\n"
            "The factors that could cause Fiserv’s actual results to differ materially include, among others: Fiserv and Microsoft’s ability to successfully deploy and embed artificial intelligence solutions into its platforms and operations; exposure to liability as a result of any misuse of artificial intelligence by Fiserv’s personnel; the integration of third-party artificial intelligence models with our services relies on certain safeguards implemented by the third-party developers which may be insufficient; and other factors included in “Risks Factors” in Fiserv’s filings with the SEC."
        ),
    },
    {
        "vendor_ref": "V-002",
        "found_by": ['insights', 'product_pages'],
        "url": "https://www.fiserv.com/en/insights/articles-and-blogs/core-banking-modernization-4-technologies-shaping-the-future-of-financial-services.html",
        "title": "Core Banking Modernization: 4 Technologies Shaping the Future of Financial Services | Fiserv",
        "published_date": "2026-01-19",
        "content": (
            "Core Banking Modernization: 4 Technologies Shaping the Future of Financial Services\n\n"
            "AI continues to find its footing in financial services\n\n"
            "Although AI is likely the murkiest advancement reshaping core banking modernization, White believes “the writing is on the wall that this is where the industry is moving.”\n\n"
            "The team at Fiserv has seen an increasing number of AI use cases around client services and support, fraud prevention and even loan origination. "
            "And White predicts the impact of AI on financial services will grow even larger as the industry addresses issues such as unintentional bias and privacy risk."
        ),
    },
    # ------------------------------------------------------------------ V-003
    {
        "vendor_ref": "V-003",
        "found_by": ['official_website', 'product_pages'],
        "url": "https://www.fssi-ca.com/",
        "title": "Print and Mail Outsourcing | Secure eDelivery | FSSI",
        "published_date": None,
        "content": (
            "High-Volume Print and Mail Outsourcing\n\n"
            "Secure processing of statements, bills, invoices, checks, letters and direct mail.\n\n"
            "Mail Outsourcing\n\n"
            "High-speed, intelligent mail inserters and mailpiece tracking ensure impeccable data integrity, timely delivery, and compliance-ready reporting.\n\n"
            "Electronic Bill Presentment\n\n"
            "Increase convenience and customer loyalty with innovative, highly-customizable online document presentment solutions that provide a feature-rich, scalable user experience.\n\n"
            "SOC 2 + HITRUST CSF, HIPAA compliance – yes, we have them all, and more."
        ),
    },
    {
        "vendor_ref": "V-003",
        "found_by": ['ai_documentation', 'insights'],
        "url": "https://www.fssi-ca.com/use-predictive-analytics-to-forecast-your-consumers-next-purchase/",
        "title": "Understanding Customer Analytics: Predictive Insights for Success | FSSI",
        "published_date": "2017-03-20",
        "content": (
            "Understanding Customer Analytics: Predictive Insights for Success\n\n"
            "Data-Driven Crystal Ball: The Rise of Artificial Intelligence\n\n"
            "In the quest for marketing excellence, technological advancements are always sought after. And the future of predictive analytics lies in the realm of artificial intelligence (AI). "
            "AI has grown smarter with each passing day, thanks to machine learning capabilities.\n\n"
            "Our custom programs have attracted clients from far and wide, seeking our expertise in using customer analytics to predict behaviors and applying targeted data to impact marketing campaigns.\n\n"
            "Customer analytics is not just about knowing what your customers want today; it’s about predicting what they’ll want tomorrow. "
            "By leveraging artificial intelligence and machine learning, we can tap into the vast amount of customer data available to us. "
            "It’s like having a marketing genie who knows your wishes before you even voice them."
        ),
    },
    # ------------------------------------------------------------------ V-004
    {
        "vendor_ref": "V-004",
        "found_by": ['official_website', 'product_pages'],
        "url": "https://terrapintech.com/",
        "title": "Wealth Data Solutions | Terrapin Technologies, Inc.",
        "published_date": None,
        "content": (
            "Scale your wealth firm, not your back office.\n\n"
            "Terrapin Technologies is the end-to-end data platform for wealth management. One platform for compensation, compliance, reporting, and advisor analytics, so you can add advisors, enter new markets, and act on what your data is telling you, without the operational drag.\n\n"
            "Terrapin tracks, calculates, and pays commissions across any plan structure, however complex.\n\n"
            "Our reporting and business intelligence tools turn raw numbers into the insights your leadership and your advisors actually use."
        ),
    },
    {
        "vendor_ref": "V-004",
        "found_by": ['ai_documentation', 'insights'],
        "url": "https://terrapintech.com/ai-ready-data-wealth-management/",
        "title": "AI-Ready Data for Wealth Management Firms",
        "published_date": "2026-07-27",
        "content": (
            "AI-Ready Data for Wealth Management: Why the Foundation Comes First\n\n"
            "For wealth management leadership, this article explains what \"AI-ready\" data actually means for a firm and why building that foundation pays off in reporting and decision-making, whether or not the firm ever adopts a single AI tool.\n\n"
            "Low-risk uses like notetaking, drafting, research, and summarization can and should continue.\n\n"
            "At Terrapin, we help wealth management firms map the systems behind the questions they most need to answer, reconcile the entities and calculations that don't currently line up, and build a reusable, governed data foundation that improves reporting now and supports responsible AI later."
        ),
    },
    # ------------------------------------------------------------------ V-005
    {
        "vendor_ref": "V-005",
        "found_by": ['ai_documentation'],
        "url": "https://www.bny.com/corporate/global/en/about-us/technology-innovation/artificial-intelligence.html",
        "title": "Artificial Intelligence | BNY",
        "published_date": None,
        "content": (
            "ARTIFICIAL INTELLIGENCE AT BNY\n\n"
            "For more than five years, BNY has been creating Artificial Intelligence (AI) enabled solutions for financial services – and we’re continuing to move fast to accelerate our AI journey. "
            "We are the first major bank to deploy an AI Supercomputer (powered by NVIDIA) to accelerate processing capacity and to launch AI enabled capabilities. "
            "We have over 125 AI-enabled solutions in production, as well as our own Enterprise AI platform.\n\n"
            "Introducing Eliza\n\n"
            "Our enterprise AI platform, Eliza, is built on the premise of foundational, reusable capabilities and is designed to enhance client service, company operations and drive cultural transformation through the power of artificial intelligence.\n\n"
            "OpenAI, the company behind ChatGPT, has spotlighted BNY’s forward-thinking approach to deploying AI across the organization to increase efficiency and drive change.\n\n"
            "AI AT WORK TODAY, EVOLVING FOR TOMORROW\n\n"
            "We have over 125 AI-enabled solutions in production ⁠–⁠ from predictive analytics and automation to anomaly detection ⁠–⁠ designed to help clients transform their business while optimizing our own infrastructure.\n\n"
            "Latest News & Insights\n\n"
            "BNY Collaborates with Google Cloud to Advance its Eliza AI Platform with Gemini Enterprise"
        ),
    },
    {
        "vendor_ref": "V-005",
        "found_by": ['insights', 'product_pages'],
        "url": "https://www.bny.com/corporate/global/en/insights/ai-and-payments-fraud-an-evolving-landscape.html",
        "title": "How AI Is Changing Payments Fraud and Fraud Prevention | BNY",
        "published_date": None,
        "content": (
            "AI and Payments Fraud: An Evolving Landscape\n\n"
            "Meeting the Challenge\n\n"
            "As AI drives increasing sophistication and loss levels, organizations need to ensure that their own capacity to fight fraud is evolving through the use of AI, too. "
            "BNY has AI-based anomaly detection in its own Payment Validation solution, including machine learning and advanced analytics. "
            "These technologies deliver real-time, continuous monitoring, detection and response to potential fraud, keeping organizations and their customers safer."
        ),
    },
    {
        "vendor_ref": "V-005",
        "found_by": ['third_party_partner'],
        "url": "https://openai.com/index/bny/",
        "title": "BNY builds “AI for everyone, everywhere” with OpenAI | OpenAI",
        "published_date": "2025-12-12",
        "content": (
            "BNY builds “AI for everyone, everywhere” with OpenAI\n\n"
            "December 12, 2025\n\n"
            "Products: ChatGPT, API\n\n"
            "From its start, Eliza was designed not just as a tool, but as a system of work, pairing BNY’s governance rigor with leading models—including OpenAI frontier models—to help employees build safely and confidently.\n\n"
            "Eliza also introduced the concept of advanced AI agents—what BNY calls “digital employees”—with identities, access controls, and dedicated workflows. "
            "Digital employees handle everything from payment instruction validation to code security enhancements."
        ),
    },
    # ------------------------------------------------------------------ V-006
    {
        "vendor_ref": "V-006",
        "found_by": ['official_website', 'product_pages'],
        "url": "https://www.theclearinghouse.org/payment-systems/rtp",
        "title": "Real Time Payments | The Clearing House",
        "published_date": None,
        "content": (
            "Always Ready. The RTP® Network, Trusted by Financial Institutions Nationwide\n\n"
            "The RTP network is the market-leading real-time payments infrastructure used by financial institutions (FIs) to send and receive electronic payments in the U.S. securely, instantly, and at scale.\n\n"
            "Smart Messaging: Rich ISO® 20022 data for real-time reconciliation\n\n"
            "The RTP network is purpose-built to handle growing payment volumes and increasing transaction values."
        ),
    },
    {
        "vendor_ref": "V-006",
        "found_by": ['ai_documentation', 'industry_press'],
        "url": "https://www.theclearinghouse.org/advocacy/Articles/2026/06/The-Clearing-House-and-the-Bank-Policy-Institute-Support-Regulatory-Proposal-to-Modernize-Anti-Money-Laundering-Rules",
        "title": "The Clearing House and the Bank Policy Institute Support Regulatory Proposal to Modernize Anti-Money Laundering Rules",
        "published_date": None,  # URL path indicates June 2026; exact day not shown
        "content": (
            "The Clearing House and the Bank Policy Institute filed a letter supporting the Financial Crimes Enforcement Network’s (FinCEN) proposed changes to modernize the regulations implementing the Bank Secrecy Act which aims to prevent illicit finance.\n\n"
            "The Associations also urge FinCEN to promote innovation and improve supervisory consistency by creating a formal framework that encourages the responsible use of technologies such as artificial intelligence, machine learning, digital identity tools, and blockchain analytics without exposing banks to additional supervisory risk."
        ),
    },
]

# Searches run during the analyst session that returned no vendor-owned AI
# material. Recorded so the negative-evidence statement is defensible.
SEARCH_LOG = [
    {"vendor_ref": "V-001", "query": "site:automworx.com AI", "result": "8 results; vendor blog posts about Automic AI features (two retained)."},
    {"vendor_ref": "V-002", "query": "Fiserv DNA core banking AI", "result": "No DNA-specific AI disclosure on fiserv.com; enterprise-level sources retained."},
    {"vendor_ref": "V-002", "query": "site:fiserv.com artificial intelligence fraud agentic AI financial institutions", "result": "Investor press release retained."},
    {"vendor_ref": "V-003", "query": "Financial Statement Services FSSI artificial intelligence", "result": "Home page and one marketing article retained; LinkedIn hashtag post not retained (LOW reliability)."},
    {"vendor_ref": "V-003", "query": "site:fssi-ca.com AI OR \"artificial intelligence\" OR \"machine learning\"", "result": "Marketing blog articles only."},
    {"vendor_ref": "V-004", "query": "Terrapin Technologies wealth management AI", "result": "Thought-leadership article and home page retained."},
    {"vendor_ref": "V-005", "query": "BNY Eliza AI platform payments", "result": "BNY AI page and OpenAI customer story retained."},
    {"vendor_ref": "V-005", "query": "BNY treasury services payments AI real-time payments fraud machine learning", "result": "BNY payments-fraud insight retained."},
    {"vendor_ref": "V-006", "query": "The Clearing House RTP fraud artificial intelligence machine learning", "result": "No TCH statement of AI use in RTP/ACH operations; third-party articles only."},
    {"vendor_ref": "V-006", "query": "site:theclearinghouse.org artificial intelligence", "result": "Advocacy and conference material only; one advocacy article retained."},
]

out = Path(__file__).resolve().parents[1] / "app" / "demo_data" / "osint_cache.json"
out.parent.mkdir(parents=True, exist_ok=True)
for s in SOURCES:
    s["retrieved_at"] = RETRIEVED
    s["cache_origin"] = ORIGIN
out.write_text(json.dumps({"snapshot_date": "2026-10-06", "origin": ORIGIN, "sources": SOURCES,
                           "search_log": SEARCH_LOG}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote {out} ({len(SOURCES)} sources)")
