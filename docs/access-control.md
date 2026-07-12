# Access & registration

## Registration is invite-only

There is **no open registration**. A visitor who is not signed in can only reach
the login page — there is no page for creating an account. An account comes into
existence in exactly two ways, both driven by an administrator:

1. **Emailed invitation** (the usual path) — an administrator sends an invitation
   to an email address; the recipient follows a one-time link and sets their own
   password.
2. **Created directly** — an administrator adds the user in the Django admin and
   sets the password.

## Inviting someone

In the Django admin (`/admin/`):

1. Go to **Invitations → Add**.
2. Enter the person's **email**, the **project**, and their **role**.
3. Save. An email with an accept link is sent automatically.

The accept link:

- requires a valid, unguessable token,
- **expires after 14 days**,
- is **single-use** — once accepted it cannot be reused,
- shows an error page (not a signup form) if it is invalid, expired, or already
  used.

Use the **"Resend invitation email"** action on the Invitations list to send it
again. (With the default console email backend the message prints to the server
console instead of being delivered — configure SMTP to send for real; see
[setup](setup.md).)

## Projects, membership, and roles

Access is scoped per project: a signed-in user only sees and acts on projects
they are a member of. This is enforced on the server — hidden navigation is never
treated as a substitute for authorization.

Each membership carries a role:

| Role | Can view | Can comment, set review state, record decisions |
| --- | --- | --- |
| Author | Yes | Yes |
| Reviewer | Yes | Yes |
| Administrator | Yes | Yes |
| Stakeholder | Yes | No (read-only) |

To grant an existing user access to another project, add a **Membership** (Admin
→ Memberships → Add) with the appropriate role, or send them an invitation to
that project.

## Forgotten passwords

Users who already have an account can reset their own password from the
**"Forgot your password?"** link on the sign-in page. This also relies on email
delivery being configured.

## Removing access

- Delete a user's **Membership** to remove their access to a single project.
- Deactivate or delete the **User** in the admin to revoke access entirely.
- A signed-in user can export or delete **their own** account and content from
  the account page (`/me/`).
