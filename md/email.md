email - What I added:

database.list_adultos_con_email() — returns (id, nombres, paterno, materno, email) for every adulto with a non-empty email.
utils.normalize_email() — validates/normalizes an address (trim + lowercase, basic format check).
utils.build_mailto_url() — builds a mailto: URL from one or many recipients, with optional subject, body, and a use_bcc flag that puts addresses in BCC to keep them private on group sends. Drops invalid addresses; returns None if none are valid.
email.py EnviarEmailDialog — subject field, body box, a checkable recipient table, select-all/none, live count, and a "BCC (CCO)" checkbox (on by default). "Redactar correo" opens the default mail client via QDesktopServices.openUrl with everything pre-filled — the operator presses Send.
Adultos menu — new "Enviar Email" action wired to on_adultos_email, imported in both import branches.
Tests — email helper cases (normalize, single/multiple/BCC/subject+body/invalid filtering) plus a menu-action presence test.
How it works: pick recipients, type subject + message, click "Redactar correo" → your mail client opens a draft addressed to everyone (as BCC by default). Like WhatsApp, nothing sends automatically.

Two notes:

Long mailto: URLs (very large recipient lists or bodies) can hit OS/mail-client length limits. For big bulk sends to many parents, the official path is still a real SMTP/email-service sender — let me know if you'd like that as a separate, opt-in option.
The default mail client must be configured on the machine for mailto: to open something.

My recommendation: leave the email dialog as a single composed draft.

The two cases are genuinely different:

WhatsApp has no real bulk primitive — each recipient needs its own wa.me chat, so opening all at once spawns N windows. The one-at-a-time flow solves that.
Email already has a true bulk primitive: BCC. The current dialog opens one draft addressed to everyone (BCC by default), so there's no multi-window problem to fix. A one-at-a-time email flow would actually be a downgrade — more clicks for no benefit, and you'd lose the single-send convenience.
So no change is warranted unless you specifically want per-recipient personalization (e.g. greeting each parent by name), which BCC can't do. If that's the goal, I'd add an optional "one draft per recipient" mode rather than replace the BCC mode.

Want me to leave it as-is, or add that optional per-recipient mode?

All pass. The email dialog now has an optional per-recipient mode.

What changed in email.py:

New checkbox "Un correo por destinatario (use {nombre} para personalizar el saludo)".
Grupal mode (default, unchanged): one draft to everyone, BCC on by default. "Redactar correo" opens a single draft.
Per-recipient mode (when checked):
The BCC checkbox is disabled (irrelevant for single-recipient drafts).
{nombre} in the subject and body is replaced with each recipient's name.
Drafts open one at a time (same flow as WhatsApp): the button becomes "Abrir siguiente correo (N)", highlights the current row, and a status line shows Abierto X de N: <name>. Quedan …. When done it shows "Finalizado" and disables.
A "Reiniciar" button (visible only in this mode) restarts the run; changing the selection also resets an in-progress run.
So you get personalization without spawning N windows at once — exactly the trade-off that justifies the extra mode. Group BCC remains the quick default.
