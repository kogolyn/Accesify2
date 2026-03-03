🚀 AccessiFy
A Modular Access Lifecycle & Expiry Engine

📌 Project Overview

AccessiFy is a modular Access Lifecycle Engine designed to manage temporary, quota-based, and revocable access to protected digital resources.

Unlike traditional permission systems that grant static access, AccessiFy treats access as a dynamic, state-driven lifecycle that evolves over time and usage.

The system enforces:

Time-based expiry

Usage-based limits

Manual revocation

Controlled renewal

Real-time validation

AccessiFy is built to be extensible, scalable, and backend-enforced to prevent client-side manipulation.

🎯 Problem Statement

Modern systems (API platforms, subscription services, SaaS tools, digital libraries) require fine-grained access control that:

Expires after a defined duration

Limits resource consumption

Supports revocation

Allows renewal

Maintains integrity under concurrent access

Many implementations tightly couple access logic with application logic, making scaling and auditing difficult.

AccessiFy decouples access enforcement into a dedicated engine that can be integrated into larger systems.

🏗 Architectural Design

The system follows strict separation of concerns and modular layering.

1️⃣ Core Engine Layer

Responsible for:

Access validation logic

State transitions

Usage tracking

Expiry evaluation

This layer determines whether access is:

ACTIVE, EXPIRED, REVOKED

It is the source of truth.

2️⃣ API Layer (Backend)

Provides REST endpoints:

POST /grant-access

POST /validate

POST /use

POST /renew

POST /revoke

The API:

Performs input validation

Calls engine logic

Returns structured JSON responses

Prevents frontend bypass

All enforcement happens server-side.

3️⃣ Frontend Layer 

Provides:

User Portal

Admin Panel

Protected Resource View

Dynamic state feedback

Frontend responsibilities:

Trigger API calls

Display results

Reflect real-time access state

It does NOT control business logic.

🔁 Access Lifecycle Flow

Admin grants access with:

Duration (seconds)

Usage limit

Access state becomes ACTIVE.

When user attempts to use resource:

Engine validates time remaining

Engine checks usage count

If valid → usage increments

If invalid → state transitions to EXPIRED

Admin may:

Renew access

Revoke access

Every request re-evaluates access dynamically.

No state is trusted blindly.

🛠 Tech Stack

Backend:

Python (Flask)

In-memory data store 

Frontend:

HTML, CSS

Modular component structure

API abstraction layer

🔒 Logical Resilience

AccessiFy enforces:

Backend-only validation

Deterministic state transitions

Dynamic re-evaluation on each request

Controlled mutation of usage counters

Separation between policy definition (Admin) and policy consumption (User)

Frontend cannot override limits.

📊 Feature Set

✔ Grant time-limited access
✔ Grant usage-limited access
✔ Validate session
✔ Consume usage dynamically
✔ Renew duration or quota
✔ Revoke access manually
✔ Visual state feedback
✔ Protected content enforcement

📦 Installation
Clone Repository
git clone <repository-url>
cd AccessiFy
Backend Setup
pip install -r requirements.txt
python app.py

Runs on:

http://localhost:5000
Frontend Setup
npm install
npm run dev
🧪 Testing Strategy

Manual API testing via frontend

State transition validation

Expiry simulation

Usage overflow validation

Revocation override testing

🚀 Scalability Roadmap

Future improvements:

Persistent storage (PostgreSQL / Redis)

Distributed usage counters

Token-based authentication (JWT)

Role-based access policies

Multi-tenant support

Event logging & analytics dashboard

Rate limiting integration

Microservice extraction

The architecture supports horizontal scaling with minimal refactor.

👥 Team

Developed by Team AccessiFy
R&D Hackathon Submission
