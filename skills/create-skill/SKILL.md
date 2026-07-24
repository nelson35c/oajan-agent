---
name: create-skill
description: How to author a new reusable skill for Oajan.
---

# Creating a new skill

When the user asks you to create, learn, or remember a reusable procedure,
follow these steps.

1. Clarify the task if it is ambiguous — what should the skill accomplish,
   and what are the concrete steps?

2. Choose a name: lowercase, hyphenated, no spaces (e.g. `book-haircut`).

3. Write a one-sentence description, 60 characters or fewer, stating what
   the skill does. This is what future-you sees in the skill index, so make
   it specific.

4. Write the body as a numbered list of clear, executable steps. Reference
   the tools you actually have (calculator, web_search, read_file,
   write_file, the Apple tools) by name where relevant. Do not invent tools.

5. Call the `save_skill` tool with the name, description, and the full step
   text. This writes the skill to the skills folder for future use.

6. Confirm to the user that the skill was saved.