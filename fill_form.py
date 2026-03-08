import html as html_mod
import json
import re
import sys

import anthropic
import requests


def get_form_fields(form_url):
    """Fetch the form page and extract field IDs, labels, and options."""
    form_url = re.sub(r"/(edit|viewform).*$", "/viewform", form_url)
    if not form_url.endswith("/viewform"):
        form_url = form_url.rstrip("/") + "/viewform"

    resp = requests.get(form_url)
    resp.raise_for_status()
    html = resp.text

    match = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(.+?);\s*</script>", html, re.DOTALL)
    if not match:
        raise ValueError("Could not parse form data. Is the form public?")

    data = json.loads(match.group(1))

    # Extract hidden submission parameters
    hidden_params = {}
    for name in ("fvv", "fbzx", "partialResponse", "submissionTimestamp"):
        m = re.search(rf'name="{name}"[^>]*value="([^"]*)"', html)
        if m:
            hidden_params[name] = html_mod.unescape(m.group(1))

    # Count pages for pageHistory (page breaks have type 8)
    page_indices = []
    for i, item in enumerate(data[1][1]):
        if item[3] == 8:  # page break
            page_indices.append(i)
    # pageHistory should list all page numbers: 0,1,2,...,N
    num_pages = len(page_indices) + 1
    hidden_params["pageHistory"] = ",".join(str(i) for i in range(num_pages))

    fields = []
    for item in data[1][1]:
        title = item[1]
        if not item[4]:
            continue

        entry_id = item[4][0][0]
        field = {"title": title, "entry_id": f"entry.{entry_id}"}

        # Extract options if present (multiple choice, checkbox, dropdown)
        if item[4][0][1]:
            field["options"] = [opt[0] for opt in item[4][0][1]]

        fields.append(field)

    return form_url, fields, hidden_params


def generate_answers(client, fields, response_num, total):
    """Use Claude to generate answers with a unique persona."""
    fields_description = []
    for f in fields:
        title = f['title'].strip()
        desc = f"- {f['entry_id']}: {title}"
        if "options" in f:
            desc += f" (choose from: {', '.join(f['options'])})"
        fields_description.append(desc)

    prompt = f"""You are filling out a psychological survey as a realistic human persona.

PERSONA CREATION:
- Invent a believable, everyday person — think normal people: office workers, teachers, students, parents, retail staff, nurses, tradespeople, retirees, etc.
- Give them a realistic mix of traits — nobody is perfectly consistent. People have contradictions, moods, and nuances.
- Gender: strongly bias towards Female (~70-75% of the time), but occasionally Male or other.
- Age: vary across the available range.
- This is response {response_num} of {total}. Each response MUST feel like a genuinely different person.

ANSWER VARIATION:
- Use the FULL range of options for each scale. Don't cluster around the middle — real people give extreme answers too.
- Some people are very agreeable, some are disagreeable. Some are anxious, some are calm. Some are introverted, others extroverted. Reflect this diversity.
- For Likert scales, avoid defaulting to moderate/neutral answers. Real distributions have spread.
- For numeric scales (1-7), use the entire range across responses — don't hover around 3-5.
- Text fields should feel natural and brief, like a real person typing quickly.

Fill out this form as your persona. Each question is prefixed with its entry ID:

Questions:
{chr(10).join(fields_description)}

Respond with ONLY a JSON object mapping each entry ID (e.g. "entry.12345") to your answer.
Include a special key "_persona" with a brief 1-2 sentence description of your persona (name, age, occupation, key traits).
For multiple choice, pick exactly one of the given options.
For checkboxes, respond with a list of selected options.
For text fields, write a brief, realistic answer."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    # Try to extract JSON from markdown code block first
    json_match = re.search(r"```(?:json)?\s*(.+?)```", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)
    else:
        # Try to extract the first JSON object from the response
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)

    return json.loads(response_text.strip())


def submit_form(form_url, answers, hidden_params):
    """Submit a Google Form."""
    submit_url = re.sub(r"/viewform.*$", "/formResponse", form_url)

    form_data = {**hidden_params, **answers}
    resp = requests.post(submit_url, data=form_data)
    if resp.status_code == 200:
        print("  Submitted successfully!")
    else:
        print(f"  Submission failed with status {resp.status_code}")
    return resp


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fill_form.py <form_url> <num_responses>")
        sys.exit(1)

    form_url = sys.argv[1]
    num_responses = int(sys.argv[2])

    # Step 1: Discover fields
    form_url, fields, hidden_params = get_form_fields(form_url)
    print("Found fields:")
    for f in fields:
        options = f" [{', '.join(f['options'])}]" if "options" in f else ""
        print(f"  {f['entry_id']}: {f['title']}{options}")
    print(f"\nHidden params: pageHistory={hidden_params.get('pageHistory')}, fbzx={hidden_params.get('fbzx')}")

    # Step 2: Generate and submit responses
    client = anthropic.Anthropic()
    for i in range(1, num_responses + 1):
        print(f"\n--- Response {i}/{num_responses} ---")
        print("Generating answers...")
        llm_answers = generate_answers(client, fields, i, num_responses)

        persona = llm_answers.pop("_persona", None)
        if persona:
            print(f"  Persona: {persona}")

        for title, answer in llm_answers.items():
            print(f"  {title}: {answer}")

        form_data = {}
        for f in fields:
            answer = llm_answers.get(f["entry_id"])
            if answer is None:
                continue
            if isinstance(answer, list):
                for val in answer:
                    form_data.setdefault(f["entry_id"], []).append(val)
            else:
                form_data[f["entry_id"]] = answer

        submit_form(form_url, form_data, hidden_params)

    print(f"\nDone! Submitted {num_responses} responses.")
