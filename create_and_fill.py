import sys

from create_form import create_form
from fill_form import get_form_fields, generate_answers, submit_form

import anthropic


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_and_fill.py <num_responses>")
        sys.exit(1)

    num_responses = int(sys.argv[1])

    BRS_OPTIONS = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]

    # Step 1: Create the form
    form_id = create_form(
        title="Brief Resilience Scale (BRS)",
        questions=[
            {
                "title": "I tend to bounce back quickly after hard times.",
                "type": "MULTIPLE_CHOICE",
                "options": BRS_OPTIONS,
                "required": True,
            },
            {
                "title": "I have a hard time making it through stressful events.",
                "type": "MULTIPLE_CHOICE",
                "options": BRS_OPTIONS,
                "required": True,
            },
            {
                "title": "It does not take me long to recover from a stressful event.",
                "type": "MULTIPLE_CHOICE",
                "options": BRS_OPTIONS,
                "required": True,
            },
            {
                "title": "It is hard for me to snap back when something bad happens.",
                "type": "MULTIPLE_CHOICE",
                "options": BRS_OPTIONS,
                "required": True,
            },
            {
                "title": "I usually come through difficult times with little trouble.",
                "type": "MULTIPLE_CHOICE",
                "options": BRS_OPTIONS,
                "required": True,
            },
            {
                "title": "I tend to take a long time to get over set-backs in my life.",
                "type": "MULTIPLE_CHOICE",
                "options": BRS_OPTIONS,
                "required": True,
            },
        ],
    )

    # Step 2: Fill the form
    form_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    form_url, fields = get_form_fields(form_url)
    print(f"\nFound {len(fields)} fields, generating {num_responses} responses...\n")

    client = anthropic.Anthropic()
    for i in range(1, num_responses + 1):
        print(f"--- Response {i}/{num_responses} ---")
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

    print(f"\nDone! Created form and submitted {num_responses} responses.")
