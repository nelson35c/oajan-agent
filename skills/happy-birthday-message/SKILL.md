---
name: happy-birthday-message
description: Send a personalized happy birthday message by creating a note.
---

1. Prompt the user to enter the recipient's full name.
2. Prompt the user to enter the recipient's contact information (email address or phone number).
3. Prompt the user to enter a personalized birthday message. If the user leaves this empty, use a default message: "Happy Birthday, <Name>! May your day be filled with joy and surprises."
4. Compose the final message: "Dear <Name>,\n\n<Personalized Message>"
5. Use the `create_note` function to create a new note in the macOS Notes app. Set the note title to "Happy Birthday: <Name>" and the note body to the composed message along with the contact information. Example body format:
   ```markdown
   **Contact:** <contact info>

   Dear <Name>,

   <Personalized Message>
   ```
6. Return a confirmation that the note has been created, e.g., "Happy Birthday note for <Name> has been created."
