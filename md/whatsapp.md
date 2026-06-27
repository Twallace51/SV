whatsapp - What I added:

database.list_adultos_con_celular() — query returning every adulto that has at least one non-empty mobile number (id, nombres, paterno, materno, cell1, cell2).
utils.normalize_bolivia_phone() / utils.build_whatsapp_url() — strip formatting, prepend 591, and produce a https://wa.me/<number>?text=... URL.
whatsapp.py EnviarWhatsAppDialog — a message box, a checkable recipient table (one row per valid phone, both cell1/cell2), select-all/none, a live count, and an "Abrir chats" button that iterates the selection and opens each wa.me link with QDesktopServices.openUrl. It confirms before opening more than 10 chats.
Adultos menu — new "Enviar WhatsApp" action wired to on_adultos_whatsapp, imported in both import branches.
Tests — phone/URL helper cases plus a menu-action presence test.
How it works for the operator: type the message, leave everyone checked (or pick recipients), click "Abrir chats". WhatsApp opens one chat per recipient with the message pre-filled — the operator presses Send in each. This keeps it ToS-safe (no automated sending, no ban risk).

One thing to confirm: opening many chats at once spawns one browser tab / WhatsApp window per recipient, which is heavy for large lists. 
If you'd prefer a one-at-a-time "next recipient" flow instead of opening them all together, I can change it.


All pass. The WhatsApp dialog now uses a one-at-a-time flow instead of opening every chat at once.

How it works now:

Pick recipients (checkboxes, with Seleccionar todos / Quitar selección) and type the message.
Click "Abrir siguiente chat" — it snapshots the current selection, opens only the first recipient's WhatsApp chat, highlights that row, and updates a status line: Abierto 1 de N: <name>. Presione Enviar en WhatsApp. Quedan N-1.
The button label shows the remaining count: Abrir siguiente chat (N-1). Each subsequent click opens the next one.
When the last one is opened, the button becomes "Finalizado" and disables.
"Reiniciar" clears the run so you can re-select and start over. Changing any checkbox also resets an in-progress run (the snapshot is taken fresh on the next start).
This avoids spawning many browser/WhatsApp windows at once — only one opens per click, so the operator handles them sequentially.


