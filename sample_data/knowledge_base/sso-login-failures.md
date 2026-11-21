---
title: Troubleshooting SSO sign-in failures
category: login_issue
tags: [sso, saml, login, identity-provider, outage]
summary: Why a whole team can lose single sign-on at once and how to check status, certificates and fallback access.
---
# Troubleshooting SSO sign-in failures

## Symptoms
When single sign-on (SSO) breaks, users are redirected back to the CloudDesk login page with a generic error, or they see "SAML response could not be validated". If many people on one workspace fail at the same moment, the cause is almost always shared: a platform incident, an expired identity-provider certificate, or a changed configuration. A single user failing is usually an account or browser problem instead.

## Check platform status first
Open the service status page and look for an active identity or authentication incident. If one is listed, tell the customer that the issue is known, that no action is needed on their side, and share the incident reference. Do not ask the customer to rebuild their SSO configuration during an incident.

## Verify the identity provider configuration
If there is no incident, ask the workspace admin to confirm three things. First, the signing certificate uploaded to CloudDesk has not expired. Second, the Entity ID and the Assertion Consumer Service URL in the provider match the values shown in Settings, Security, Single sign-on. Third, the provider clock is within five minutes of real time, because assertions outside that window are rejected.

## Temporary access for blocked admins
Workspace owners can always sign in with email and a one-time code from the "Sign in without SSO" link, even when SSO is enforced. This lets an admin reach settings and upload a fresh certificate. Ordinary members stay blocked until SSO works again, so tell the customer the expected time to fix when an incident is open.

## When to escalate
Escalate to the identity engineering team when an enterprise workspace has been fully locked out for more than 30 minutes, or when the configuration checks above all pass and the error continues.
