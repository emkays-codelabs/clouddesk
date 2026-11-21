---
title: MFA lockout and account recovery
category: login_issue
tags: [mfa, lockout, recovery-codes, new-phone, account-recovery]
summary: What to do when a user is locked out after too many MFA attempts or has lost access to their authenticator, including a new phone without recovery codes.
---
# MFA lockout and account recovery

## Why accounts get locked
After five failed multi-factor authentication (MFA) attempts, the account is locked for 30 minutes. This protects against guessing. A common cause is a new phone: the authenticator app was not transferred, so codes no longer match. Waiting out the lock does not fix a missing authenticator.

## Use a recovery code
Every user is shown ten single-use recovery codes when they turn on MFA. If the customer still has them, they can sign in with one on the MFA prompt by selecting "Use a recovery code". Each code works once, and they should create new codes afterwards in Settings, Security.

## No phone and no codes
When the user has lost both the authenticator and the recovery codes, support cannot simply turn MFA off. The user must prove their identity first. Ask them to start recovery from the login page by selecting "Can't access your authenticator". A verification link is sent to the account email, and after confirming it the user may reset MFA and enrol the new phone.

## Workspace admins can help
A workspace admin can reset MFA for a member from Settings, Members. This is the fastest route when the user belongs to a team, because the admin already knows the person.

## Security notes
Never reset MFA based only on a ticket, a phone call or a screenshot. If recovery was requested and the user did not ask for it, treat the report as a possible compromise and follow the suspicious login process.
