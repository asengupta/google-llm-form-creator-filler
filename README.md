# Form Filler

Create Google Forms and auto-fill them with LLM-generated responses using Claude.

## Setup

### Dependencies

```bash
pip install google-auth google-auth-oauthlib google-api-python-client anthropic requests
```

### Google Cloud (for form creation)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the **Google Forms API**
3. Create **OAuth 2.0 Client ID** credentials (Desktop app)
4. Download and save as `credentials.json` in this directory

### Anthropic (for form filling)

Set your API key:

```bash
export ANTHROPIC_API_KEY="your-key"
```

## Usage

### Create and fill a form (end-to-end)

Creates a Brief Resilience Scale (BRS) form and fills it with LLM-generated responses:

```bash
python create_and_fill.py <num_responses>
```

Example:

```bash
python create_and_fill.py 10
```

### Create a form only

Edit the questions in `create_form.py` and run:

```bash
python create_form.py
```

### Fill an existing form

```bash
python fill_form.py <form_url> <num_responses>
```

Example:

```bash
python fill_form.py "https://docs.google.com/forms/d/e/FORM_ID/viewform" 10
```

## How it works

1. `create_form.py` — Creates a Google Form via the Forms API
2. `fill_form.py` — Fetches a form's HTML, extracts field IDs and options, uses Claude to generate a unique persona and realistic answers for each response, and submits via POST
3. `create_and_fill.py` — Combines both: creates the form, then fills it
