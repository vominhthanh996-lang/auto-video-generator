# Outlook Mail helper

Local helper for reading Outlook mail through Microsoft Graph.

## Setup

1. Create a Microsoft Entra app registration.
2. Copy the app's Application (client) ID.
3. In **Authentication**, enable **Allow public client flows**.
4. In **API permissions**, add Microsoft Graph delegated permission `Mail.Read`.
5. Put the app client ID in an environment variable:

```powershell
setx OUTLOOK_CLIENT_ID "your-client-id"
```

Open a new PowerShell window after `setx`, then sign in:

```powershell
python plugins\outlook-mail\scripts\outlook_mail.py login
```

Read today's inbox messages:

```powershell
python plugins\outlook-mail\scripts\outlook_mail.py today --limit 20
```

Search mail:

```powershell
python plugins\outlook-mail\scripts\outlook_mail.py search "invoice" --limit 10
```

Tokens are stored in `plugins/outlook-mail/.secrets/token.json`, which is ignored by git.

## Company account fallback

If your company account blocks Microsoft Entra app registration or user consent, use Outlook Desktop on this Windows machine instead:

```powershell
powershell -ExecutionPolicy Bypass -File E:\ThanhMV\outlook-mail\scripts\read_outlook_desktop.ps1 -Limit 20
```

This reads the default mailbox already signed into Outlook Desktop and does not require `OUTLOOK_CLIENT_ID`.

## Notes

- This uses delegated `Mail.Read`, so it can read only the mailbox that signs in.
- Work or school tenants may require admin approval depending on tenant policy.
- Delete `.secrets/token.json` to sign out locally.
- Microsoft docs: https://learn.microsoft.com/en-us/graph/permissions-reference and https://learn.microsoft.com/en-us/entra/identity-platform/scopes-oidc
