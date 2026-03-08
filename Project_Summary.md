# PathShala AI: Project Summary

## The Invisible Crisis
In India, there are **1,10,000 single-teacher public schools**. In these environments, one educator is responsible for managing 60+ students simultaneously across Grades 1 through 5, in a single room, often with no internet access and zero supplementary teaching materials. Every evening, these teachers spend an exhausting 2+ hours manually writing 5 distinct lesson plans. Existing EdTech solutions entirely bypass this demographic because they target students directly or demand high-speed internet.

## The Solution
**PathShala AI** is a voice-powered AI teaching assistant—a "GitHub Copilot for Rural Teachers"—designed specifically to solve the crushing planning burden of the multi-grade classroom. 

By simply speaking into a basic Android or feature phone in Hindi or English (e.g., *"Today I need to teach Class 1 vowels and Class 3 the multiplication table"*), the teacher instantly receives a structured, 200-word lesson plan within 15 seconds. 

Crucially, **this is not a generic LLM wrapper**. The system is strictly engineered with multi-grade pedagogical intelligence: the AI *knows* the teacher can only give direct attention to one group at a time, so it automatically generates parallel activities—ensuring Class 1 is assigned independent written work on the blackboard while Class 3 receives direct oral instruction. 

## Technical Execution & Architecture
PathShala AI is built on a highly scalable, zero-maintenance **AWS Lambda Serverless** architecture integrated deeply with **Google Gemini** & **AWS Bedrock (Claude 3.5 Sonnet)**.

**Key Technical Pillars:**
1. **Serverless AI Pipeline:** 6 discrete AWS Lambda functions handle dynamic API routing, lesson generation, and OTP authentication without standing server costs.
2. **Contextual Intelligence Structure:** AI prompts are dynamically injected with the Indian NCERT curriculum database (fetched from **Amazon S3**) to ensure exact alignment with state syllabus standards.
3. **Multi-Modal Accessibility:** 
    - **Native Android App (Kotlin):** Features offline-capable on-device TTS, voice recognition, and an interactive Floating Call UI.
    - **Twilio Voice Integration:** Teachers without smartphones can simply dial a number to generate a lesson using natural Hindi voice response powered by **Amazon Polly**.
4. **The WhatsApp Flywheel:** Because rural teacher networks run on WhatsApp, every generated lesson is automatically formatted and delivered via the Twilio WhatsApp Sandbox, allowing a single lesson to be instantly forwarded to a 50-person block-level teacher group.
5. **Persistent History:** Every generated lesson plan is securely cached in **Amazon DynamoDB**, creating a verifiable audit trail of daily teaching activity.

## Impact & Viability
PathShala AI operates at an astonishingly lean cost of **₹35 ($0.42) per teacher per month**—a radical 12x reduction compared to the standard ₹5,000 annual government training programs. 

By aligning directly with the National Education Policy (NEP) 2020 mandate for technological integration, PathShala AI is built as a viable Government B2B SaaS model. Delivering 2 hours of daily time-savings directly to the educators who need it most, it tackles teacher burnout at the root, directly impacting the education of over 10 million underserved students.
