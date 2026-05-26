# DEC-002: Upgrade to newer Gemini 2.5 Flash model for AI Service

## Context & Problem Statement
The Telegram AI service originally utilized the `gemini-1.5-flash` model via the Google Generative AI SDK (`google.generativeai`). However, API calls started failing with `CONSUMER_SUSPENDED` and subsequently, attempts to manually update the model name to an unsupported format (like `Gemini 2.5 Flash-Lite`) resulted in `400 * GenerateContentRequest.model: unexpected model name format` errors. Upon investigating the available models for the assigned API key, we found that the `gemini-1.5` series was no longer listed, and the SDK requires exact model name formatting (lowercase with hyphens).

## Decision
We will upgrade the AI response generation model to `gemini-2.5-flash`, which is actively supported and available in the current Google Generative AI SDK, maintaining the correct formatting expected by the SDK.

## Status
`Accepted`

## Consequences
- **Positive:** The system successfully communicates with the Gemini API, generating responses accurately without formatting or suspension errors.
- **Negative:** We must remain vigilant about Google's model deprecation policies, as older models may become unavailable requiring prompt updates to the `model_name` string in the code.

## Implementation Notes
- Updated `model_name="gemini-2.5-flash"` in `ai_service.py` where `genai.GenerativeModel` is instantiated.
- Configured `.env` loading to happen early in `main.py` before `ai_service.py` is initialized so the correct API key is passed into `genai.configure()`.