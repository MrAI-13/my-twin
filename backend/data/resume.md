# Michel Randy Djouonang

240-806-8162 | michelrandy13@gmail.com | [GitHub](https://github.com/michelrandy) | Baltimore

## Applied AI Engineer & Multi-Agent Systems Architect

Applied AI Engineer with a M.S. in Telecommunications Engineering and a unique foundation in enterprise agile software delivery and full-stack agentic architecture. Specialized in designing, deploying, and maintaining multi-agent systems, RAG pipelines, and automated cloud infrastructure. Brings a powerful combination of rigorous systems engineering, Agile project management, and operational business acumen to translate complex bottlenecks into scalable, secure AI workflows hosted on AWS.

## Technical Skills

- AI & Agentic Frameworks: OpenAI SDK, CrewAI, LangGraph, Model Context Protocol (MCP), Generative & Conversational AI, RAG
- Cloud & Infrastructure: AWS. Familiarity with GCP, Azure, Vercel
- DevOps & Deployment: Terraform IaC, GitHub Actions CI/CD, Docker, Langchain
- Automation & Integrations: Make.com, n8n, Webhooks, FastAPI, REST APIs, Clerk Auth, Vapi AI, Relevance AI, Python, Next.js

## Professional Experience

### Digital Marketing Mavericks — Founder & Lead AI Engineer | January 2025 - Present

- Architect and deploy autonomous AI voice receptionists (via Vapi AI) for commercial service contractors, engineering complex webhook architectures in Make.com to dynamically parse caller intent and manage live calendar bookings.
- Engineered an internal multi-agent CrewAI pipeline that reduced lead qualification and content generation overhead, eliminating manual data processing and saving 10 hours/week.
- Deployed automated, multi-channel outbound pipelines handling 500 targeted B2B interactions monthly, linking technical API integrations to measurable business ROI.
- Integrated real-time CRM updates to ensure seamless data flow between AI agents and client sales databases.

### IDEXX Laboratories — Scrum Master | May 2022 - May 2025

- Led Agile software development practices (Scrum/Kanban) across multiple cross-functional engineering pods of 10 developers, ensuring reliable delivery of enterprise-grade technical products.
- Facilitated sprint planning, daily stand-ups, and retrospectives, optimizing workflow efficiency and removing technical blockers for CI/CD deployment pipelines.
- Bridged the gap between technical developers and business stakeholders, ensuring engineering outputs aligned with corporate objectives and release schedules.
- Mentored teams on Lean principles to reduce cycle time and improve the quality of software deployments via Scrum and Kanban techniques.

## AI Projects Completed

### 1. AI Career Twin

- Goal: An autonomous AI Agent representing me to recruiters, linked via my resume.
- Architecture: Static frontend using Next.js deployed on AWS S3 via CloudFront. Backend is a FastAPI Python application running on an AWS Lambda function, making Bedrock calls to an LLM (gpt-oss).
- Agent Capabilities & Tools: Equipped with personal knowledge, a Pushover tool for notifications, and a Google Calendar tool to book interviews.

### 2. AI Assistant for Dentists (Multi-Agent System)

- Framework: Built using Vapi AI and Make.com for complex tool-calling and integrations.
- Agents (5 specialized roles):
  - Intake Router Agent: Identifies caller (new/existing patient) and optionally routes to an emergency line.
  - Admin Agent: Collects new patient information and routes the call.
  - Billing Specialist: Answers questions about bills, insurance, etc.
  - Scheduler Agent: Manages appointment scheduling using Google Calendar.
  - Nurse Triage Agent: Answers medical questions and provides advice, restricted to its knowledge base, and performs preliminary patient intake.
- Integrations & Tools: Agents manage the practice's CRM, Google Calendar, send text messages and emails, and issue push notifications.

### 3. RAG Pipeline for Topic Research

- Pipeline Flow: Uses AWS EventBridge to trigger a Lambda scheduler.
- Research & Ingestion: The scheduler starts an agent in AWS App Runner to conduct research on a specific topic (also triggerable via a REST API) using Bedrock and a Playwright MCP server.
- Storage & Inference: Information is stored as vectors in AWS S3 via a Lambda ingest function which leverages SageMaker inference endpoints for processing.

## Education & Certifications

- Master of Science in Telecommunications Engineering — University of Maryland
- AI Engineer Production Track: Deploy LLMs & Agents at Scale — Completed
- AI Engineer Agentic Track: The Complete Agent & MCP Course — Completed
- AI Engineer Core Track: LLM Engineering, RAG, QLoRA, Agents — In Progress
- AWS Solutions Architect Associate — 2021-2024
- PSM (Professional Scrum Master) I — Completed
