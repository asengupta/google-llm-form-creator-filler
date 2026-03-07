# Form Filler

Create Google Forms and auto-fill them with LLM-generated responses.

## Setup

### Dependencies

```bash
pip install google-auth google-auth-oauthlib google-api-python-client anthropic requests
```

### Google Cloud (for form creation only)

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

### Create a form

Edit the questions in `create_form.py` and run:

```bash
python create_form.py
```

### Fill a form

```bash
python fill_form.py <form_url> <num_responses>
```

Example:

```bash
python fill_form.py "https://docs.google.com/forms/d/e/FORM_ID/viewform" 10
```

The script will:
1. Fetch the form and discover all fields and options
2. Generate a unique persona and realistic answers for each response using Claude
3. Submit each response automatically
