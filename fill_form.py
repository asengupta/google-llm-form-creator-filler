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

    return form_url, fields


def generate_answers(client, fields, response_num, total):
    """Use Claude to generate answers with a unique persona."""
    fields_description = []
    for f in fields:
        desc = f"- {f['title']}"
        if "options" in f:
            desc += f" (choose from: {', '.join(f['options'])})"
        fields_description.append(desc)

    prompt = f"""You are filling out a survey as a unique, realistic persona.
First, invent a persona for yourself (age, occupation, personality, interests) — make it distinct.
This is response {response_num} of {total}, so vary your persona and answers from typical responses.

Fill out this form as that persona:

Questions:
{chr(10).join(fields_description)}

Respond with ONLY a JSON object mapping each question title to your answer.
For multiple choice, pick exactly one of the given options.
For checkboxes, respond with a list of selected options.
For text fields, write a brief, realistic answer."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    json_match = re.search(r"```(?:json)?\s*(.+?)```", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    return json.loads(response_text.strip())


def submit_form(form_url, answers):
    """Submit a Google Form."""
    submit_url = re.sub(r"/viewform.*$", "/formResponse", form_url)

    resp = requests.post(submit_url, data=answers)
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
    form_url, fields = get_form_fields(form_url)
    print("Found fields:")
    for f in fields:
        options = f" [{', '.join(f['options'])}]" if "options" in f else ""
        print(f"  {f['entry_id']}: {f['title']}{options}")

    # Step 2: Generate and submit responses
    client = anthropic.Anthropic()
    for i in range(1, num_responses + 1):
        print(f"\n--- Response {i}/{num_responses} ---")
        print("Generating answers...")
        llm_answers = generate_answers(client, fields, i, num_responses)
        for title, answer in llm_answers.items():
            print(f"  {title}: {answer}")

        form_data = {}
        for f in fields:
            answer = llm_answers.get(f["title"])
            if answer is None:
                continue
            if isinstance(answer, list):
                for val in answer:
                    form_data.setdefault(f["entry_id"], []).append(val)
            else:
                form_data[f["entry_id"]] = answer

        submit_form(form_url, form_data)

    print(f"\nDone! Submitted {num_responses} responses.")
